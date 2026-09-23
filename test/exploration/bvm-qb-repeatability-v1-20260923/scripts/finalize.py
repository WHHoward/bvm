#!/usr/bin/env python3
"""Finalize mechanical run QA, historical-prefix comparisons, and run indexes."""

from __future__ import annotations

import csv
import html
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import (REPO, REGRESSION_MATRIX, ROOT, file_record, read_json,
                    repo_rel, sha256, write_json)
import plot_case

PHASE_A_ROOT = REPO / "test" / "exploration" / "bvm-qb-50ghz-merge-v1-20260922" / "phase_a_repeated_read" / "runs"
COMPARE_WINDOW_PS = [0.0, 240.0]
KEY_COMPARE_SIGNALS = ["P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBIN)", "V(QBOUT)", "V(R_TERM)"]
PLOT_COMPARE_SIGNALS = ["P(BJ2|XBQ1)", "V(R_TERM)"]


def solver_warning_stderr_matches(warning_qa: dict[str, Any], metadata: dict[str, Any],
                                 stderr_path: Path) -> bool:
    if not stderr_path.is_file() or warning_qa.get("status") != "PASS":
        return False
    actual = sha256(stderr_path)
    metadata_hash = metadata.get("stderr", {}).get("sha256")
    return (warning_qa.get("stderr_sha256") == actual and
            (metadata_hash is None or metadata_hash == actual))


def archive_failed_finalization() -> dict[str, Any] | None:
    analysis_dir = ROOT / "analysis"
    final_path = analysis_dir / "FINAL_QA.json"
    sidecar_path = analysis_dir / "FINAL_QA.sha256"
    result_path = ROOT / "result.json"
    if not final_path.is_file():
        return None
    previous = read_json(final_path)
    if previous.get("status") == "PASS":
        raise RuntimeError("refusing to rerun finalization over an already passing immutable FINAL_QA")
    if not sidecar_path.is_file() or not result_path.is_file():
        raise RuntimeError("failed finalization attempt is incomplete; preserve/audit it before rerunning")
    attempt_number = 1
    while (analysis_dir / "attempts" / f"FINALIZATION_ATTEMPT{attempt_number}").exists():
        attempt_number += 1
    attempt_name = f"FINALIZATION_ATTEMPT{attempt_number}"
    attempt_dir = analysis_dir / "attempts" / attempt_name
    attempt_dir.mkdir(parents=True, exist_ok=False)
    sources = {"FINAL_QA.json": final_path, "FINAL_QA.sha256": sidecar_path,
               "result.json": result_path}
    files = {}
    for name, source in sources.items():
        target = attempt_dir / name
        shutil.copy2(source, target)
        files[name] = {"path": repo_rel(target), "sha256": sha256(target)}
    write_json(attempt_dir / "archive_manifest.json", {
        "schema": "bvm-qb-repeatability-failed-finalization-archive-v1",
        "attempt": attempt_name, "files": files,
        "prior_final_qa_status": previous.get("status"),
        "prior_final_qa_checks": previous.get("checks", []),
        "purpose": "preserve failed mechanical finalization before another analysis-only QA pass",
        "scientific_interpretation_performed": False,
    })
    return {"path": repo_rel(attempt_dir / "archive_manifest.json"),
            "sha256": sha256(attempt_dir / "archive_manifest.json"),
            "prior_final_qa_sha256": sha256(final_path)}


def validate_postsolve_finalizer_repairs(preflight: dict[str, Any], execution: dict[str, Any],
                                         source_lock: dict[str, Any], matrix: dict[str, Any]) -> list[dict[str, Any]]:
    first_path = ROOT / "analysis" / "POST_SOLVE_TOOL_REPAIR.json"
    second_path = ROOT / "analysis" / "POST_SOLVE_TOOL_REPAIR_ATTEMPT2.json"
    if not first_path.is_file():
        return []
    first = read_json(first_path)
    raw_hashes = {case["case_id"]: sha256(ROOT / "runs" / case["case_id"] / "raw.csv")
                  for case in matrix["cases"] if (ROOT / "runs" / case["case_id"] / "raw.csv").is_file()}
    preflight_sha = sha256(ROOT / "analysis" / "PREFLIGHT_QA.json")
    lock_sha = sha256(ROOT / "analysis" / "PLATFORM_SOURCE_LOCK.json")
    finalizer_path = ROOT / "scripts" / "finalize.py"
    test_path = ROOT / "tests" / "test_platform.py"
    finalizer_sha = sha256(finalizer_path)
    test_sha = sha256(test_path)
    original_failed = ROOT / "analysis" / "attempts" / "FINALIZATION_ATTEMPT1" / "FINAL_QA.json"
    intermediate_failed = ROOT / "analysis" / "attempts" / "FINALIZATION_ATTEMPT2" / "FINAL_QA.json"
    repair1_valid = (
        first.get("schema") == "bvm-qb-repeatability-postsolve-tool-repair-v1" and
        first.get("repair_id") == "POSTSOLVE_STDERR_HASH_COMPAT_V1" and
        first.get("changed_role") == "FINALIZER" and
        first.get("preflight_head") == preflight.get("git", {}).get("head") and
        first.get("preflight_qa_sha256") == preflight_sha and first.get("source_lock_sha256") == lock_sha and
        original_failed.is_file() and first.get("prior_final_qa_sha256") == sha256(original_failed) and
        read_json(original_failed).get("status") == "FAIL" and
        "solver-warning/unsupported-probe QA failed or changed: REG_A_QB2X1_N1" in read_json(original_failed).get("checks", []) and
        intermediate_failed.is_file() and
        first.get("current_finalizer_sha256") == read_json(intermediate_failed).get("sealed_file_sha256", {}).get(repo_rel(finalizer_path)) and
        first.get("previous_finalizer_sha256") == preflight.get("source_hashes", {}).get("FINALIZER", {}).get("sha256") ==
        source_lock.get("source_hashes", {}).get("FINALIZER", {}).get("sha256") and
        first.get("raw_sha256_by_case") == raw_hashes and len(raw_hashes) == 5 and
        first.get("physical_solve_count") == 5 and first.get("new_physical_solve_count") == 0 and
        first.get("scientific_interpretation_performed") is False
    )
    if not repair1_valid:
        return []

    intermediate_failure = ROOT / "analysis" / "attempts" / "FINALIZATION_ATTEMPT2" / "FINAL_QA.json"
    if not second_path.is_file():
        # Repair one is valid; source-role changes not covered by it remain a hard QA failure.
        if finalizer_sha != first.get("current_finalizer_sha256"):
            return []
        return [first]
    second = read_json(second_path)
    if not intermediate_failure.is_file():
        return []
    previous_check = "frozen preflight source changed before finalization: PLATFORM_TESTS"
    second_valid = (
        second.get("schema") == "bvm-qb-repeatability-postsolve-tool-repair-v1" and
        second.get("repair_id") == "POSTSOLVE_FINALIZER_TEST_COVERAGE_V1" and
        second.get("preflight_head") == preflight.get("git", {}).get("head") and
        second.get("preflight_qa_sha256") == preflight_sha and second.get("source_lock_sha256") == lock_sha and
        second.get("prior_final_qa_sha256") == sha256(intermediate_failure) and
        read_json(intermediate_failure).get("status") == "FAIL" and
        previous_check in read_json(intermediate_failure).get("checks", []) and
        second.get("supersedes_repair_sha256") == sha256(first_path) and
        second.get("raw_sha256_by_case") == raw_hashes and len(raw_hashes) == 5 and
        second.get("physical_solve_count") == 5 and second.get("new_physical_solve_count") == 0 and
        second.get("scientific_interpretation_performed") is False and
        second.get("changed_components") == [
            {"role": "FINALIZER", "previous_sha256": first.get("current_finalizer_sha256"),
             "current_sha256": finalizer_sha},
            {"role": "PLATFORM_TESTS",
             "previous_sha256": preflight.get("source_hashes", {}).get("PLATFORM_TESTS", {}).get("sha256"),
             "current_sha256": test_sha},
        ] and finalizer_sha == second.get("current_finalizer_sha256")
    )
    return [first, second] if second_valid else []


def read_raw(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        if len(headers) != len(set(headers)):
            raise ValueError(f"duplicate raw column in {path}")
        return headers, list(reader)


def parameter_subset(values: dict[str, Any]) -> dict[str, str]:
    keys = ("JM1_AREA", "JM2_AREA", "RJM1", "RJM2", "LM1", "LM2", "LM3", "LPM",
            "JS1_AREA", "JS2_AREA", "RSH_JS1", "RSH_JS2", "LS1", "LS2", "LS3", "RS",
            "LPSL", "RSL", "LSL", "RBL", "LPBL", "RWL", "LPWL", "RSE", "LPSE",
            "QB_LIN", "QB_BJS_AREA", "QB_L1", "QB_L2", "QB_BJ1_AREA", "QB_RJ1",
            "QB_BJ2_AREA", "QB_RJ2", "QB_L3", "QB_IB", "ARRAY_SIZE", "CANDIDATE", "DT")
    return {key: str(values.get(key)) for key in keys}


def normalized_deck(text: str) -> list[str]:
    result = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("*") or stripped.lower().startswith(".include"):
            continue
        if stripped.lower().startswith(".tran"):
            tokens = stripped.split()
            result.append(f".tran {tokens[1].lower()} <computed-stop>")
        else:
            result.append(" ".join(stripped.lower().split()))
    return result


def normalized_source(path: Path) -> list[str]:
    return [" ".join(line.lower().split()) for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("*")]


def parse_unit(token: str) -> float:
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)([munpf]?)", token)
    if not match:
        raise ValueError(f"cannot parse stimulus number {token}")
    factor = {"": 1.0, "m": 1e-3, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}[match.group(2)]
    return float(match.group(1)) * factor


def normalized_stimulus(path: Path, last_ps: float) -> dict[str, list[tuple[float, float]]]:
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("*") or " pwl(" not in line.lower():
            continue
        head, rest = line.split("pwl(", 1)
        source = head.split()[0]
        tokens = rest.rstrip(") ").split()
        pairs = [(parse_unit(tokens[i]) * 1e12, parse_unit(tokens[i + 1]))
                 for i in range(0, len(tokens), 2)]
        result[source] = [(t, value) for t, value in pairs if t <= last_ps + 1e-9]
    return result


def raw_prefix_compare(old_raw: Path, new_raw: Path) -> dict[str, Any]:
    old_headers, old_rows = read_raw(old_raw)
    new_headers, new_rows = read_raw(new_raw)
    start, end = COMPARE_WINDOW_PS
    old = [(float(row["time"]) * 1e12, row) for row in old_rows
           if start <= float(row["time"]) * 1e12 < end]
    new = [(float(row["time"]) * 1e12, row) for row in new_rows
           if start <= float(row["time"]) * 1e12 < end]
    grid_equal = len(old) == len(new) and all(a[0] == b[0] for a, b in zip(old, new))
    common_headers = [key for key in old_headers if key in new_headers]
    exact = grid_equal and old_headers == new_headers and all(
        all(a[1][key] == b[1][key] for key in old_headers)
        for a, b in zip(old, new))
    descriptors: dict[str, Any] = {}
    if grid_equal:
        for key in KEY_COMPARE_SIGNALS:
            if key not in common_headers:
                continue
            diffs = [float(b[1][key]) - float(a[1][key]) for a, b in zip(old, new)]
            descriptors[key] = {"sample_count": len(diffs),
                                 "exact_text_equal": all(a[1][key] == b[1][key] for a, b in zip(old, new)),
                                 "max_abs_difference_raw_units": max((abs(x) for x in diffs), default=0.0),
                                 "rms_difference_raw_units": math.sqrt(sum(x * x for x in diffs) / len(diffs)) if diffs else None}
    return {"window_ps": COMPARE_WINDOW_PS, "window_semantics": "[start,end)",
            "old_sample_count": len(old), "new_sample_count": len(new),
            "stored_time_grid_exactly_equal": grid_equal,
            "raw_headers_exactly_equal": old_headers == new_headers,
            "common_header_count": len(common_headers),
            "raw_prefix_exactly_equal": exact,
            "descriptive_key_signal_differences": descriptors,
            "interpolation_or_resampling": False,
            "acceptance_tolerance": None}


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def excluded_from_finalization_seal(path: Path) -> bool:
    return ("__pycache__" in path.parts or path.suffix == ".pyc" or
            path.name in {"FINAL_QA.json", "FINAL_QA.sha256", "PACKAGE_QA.json", "PACKAGE_CHECKPOINTS.json"} or
            (path.parent.name == "handoff" and path.suffix == ".zip"))


def make_comparison_input(old_raw: Path, new_raw: Path, output: Path,
                          old_sha: str, new_sha: str, run_id: str) -> dict[str, Any] | None:
    old_headers, old_rows = read_raw(old_raw)
    new_headers, new_rows = read_raw(new_raw)
    old_selected = [(float(row["time"]) * 1e12, row) for row in old_rows
                    if COMPARE_WINDOW_PS[0] <= float(row["time"]) * 1e12 < COMPARE_WINDOW_PS[1]]
    new_selected = [(float(row["time"]) * 1e12, row) for row in new_rows
                    if COMPARE_WINDOW_PS[0] <= float(row["time"]) * 1e12 < COMPARE_WINDOW_PS[1]]
    selected_signals = [signal for signal in PLOT_COMPARE_SIGNALS if signal in old_headers and signal in new_headers]
    if not selected_signals or len(old_selected) != len(new_selected) or any(
            a[0] != b[0] for a, b in zip(old_selected, new_selected)):
        return None
    fields = ["time"]
    mapping = {}
    for signal in selected_signals:
        old_name = f"{signal} [historical]"
        new_name = f"{signal} [new]"
        fields.extend((old_name, new_name))
        mapping[old_name] = {"source_raw": str(old_raw), "source_column": signal, "source_sha256": old_sha}
        mapping[new_name] = {"source_raw": str(new_raw), "source_column": signal, "source_sha256": new_sha}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for (old_t, old_row), (new_t, new_row) in zip(old_selected, new_selected):
            if old_t != new_t:
                raise ValueError("comparison grid changed during projection")
            row = {"time": old_row["time"]}
            for signal in selected_signals:
                row[f"{signal} [historical]"] = old_row[signal]
                row[f"{signal} [new]"] = new_row[signal]
            writer.writerow(row)
    sidecar = {"schema": "bvm-qb-repeatability-exact-grid-comparison-input-v1",
               "run_id": run_id, "window_ps": COMPARE_WINDOW_PS,
               "window_semantics": "[start,end)", "actual_sample_count": len(old_selected),
               "actual_first_sample_ps": old_selected[0][0], "actual_last_sample_ps": old_selected[-1][0],
               "old_raw_path": repo_rel(old_raw), "old_raw_sha256": old_sha,
               "new_raw_path": repo_rel(new_raw), "new_raw_sha256": new_sha,
               "derived_csv": repo_rel(output), "derived_csv_sha256": sha256(output),
               "column_mapping": mapping,
               "transformation": "exact-time-grid row join and direct-column projection only",
               "interpolation": False, "resampling": False, "smoothing": False}
    write_json(output.with_suffix(output.suffix + ".metadata.json"), sidecar)
    return sidecar


def compare_reference(case: dict[str, Any], run_dir: Path, reference_run: str) -> dict[str, Any]:
    old_dir = REPO / reference_run
    old_raw, new_raw = old_dir / "raw.csv", run_dir / "raw.csv"
    source_lock = read_json(ROOT / "analysis" / "PLATFORM_SOURCE_LOCK.json")
    locked_sources = source_lock.get("source_hashes", {})
    reference_paths = {
        "METADATA": old_dir / "metadata.json", "DECK": old_dir / "actual_deck.cir",
        "STIMULUS": old_dir / "stimulus.inc", "SOURCE_MANIFEST": old_dir / "source_manifest.json",
        "BVM": old_dir / "snapshot" / "sources" / "bvm_tunable.cir",
        "QB": old_dir / "snapshot" / "sources" / "bq_tunable.cir",
        "JJ": old_dir / "snapshot" / "sources" / "jjmit.cir",
        "JTL": old_dir / "snapshot" / "sources" / "jtl2.cir",
    }
    for suffix, path in reference_paths.items():
        locked = locked_sources.get(f"{case['case_id']}_REFERENCE_{suffix}", {}).get("sha256")
        if not path.is_file() or not locked or sha256(path) != locked:
            raise ValueError(f"historical comparison input differs from frozen source lock: {path}")
    scope = read_json(ROOT / "analysis" / "REFERENCE_ANALYSIS_SCOPE.json")
    frozen_reference_hashes = {item["path"]: item["sha256"] for item in scope.get("authorized_inputs", [])}
    old_rel = repo_rel(old_raw)
    old_sha = sha256(old_raw)
    if frozen_reference_hashes.get(old_rel) != old_sha:
        raise ValueError(f"historical raw differs from the scope-bound hash: {old_rel}")
    old_metadata = read_json(old_dir / "metadata.json")
    old_source = read_json(old_dir / "source_manifest.json")
    new_metadata = read_json(run_dir / "metadata.json")
    new_source = read_json(run_dir / "source_manifest.json")
    old_params = parameter_subset(old_metadata["parameters"])
    new_params = parameter_subset(new_metadata["parameters"])
    old_expected = old_metadata.get("expected", {})
    new_snapshot = read_json(run_dir / "stimulus_snapshot.json")
    mask_match = old_expected.get("mask") == new_metadata["parameters"].get("MASK")
    old_read_starts = [float(x) for x in old_expected.get("read_starts_ps", [])]
    new_read_starts = [float(x["read_start_ps"]) for x in new_snapshot.get("read_schedule", [])]
    read_schedule_match = old_read_starts == new_read_starts
    candidate_match = old_expected.get("candidate") == new_metadata["parameters"].get("CANDIDATE")
    parameter_match = old_params == new_params and mask_match and candidate_match and read_schedule_match
    last_ps = float(new_snapshot["last_stimulus_time_ps"])
    old_stim = normalized_stimulus(old_dir / "stimulus.inc", last_ps)
    new_stim = normalized_stimulus(run_dir / "stimulus.inc", last_ps)
    stimulus_match = old_stim == new_stim
    deck_match = normalized_deck((old_dir / "actual_deck.cir").read_text(encoding="utf-8")) == normalized_deck(
        (run_dir / "actual_deck.cir").read_text(encoding="utf-8"))
    old_src = {item["role"]: item for item in old_source.get("sources", [])}
    new_src = {item["role"]: item for item in new_source.get("sources", [])}
    jj_jtl_match = all(old_src.get(role, {}).get("sha256") == new_src.get(role, {}).get("sha256")
                       for role in ("JJ_MODEL", "JTL"))
    source_dir_old = old_dir / "snapshot" / "sources"
    source_dir_new = run_dir / "snapshot" / "sources"
    bvm_match = normalized_source(source_dir_old / "bvm_tunable.cir") == normalized_source(source_dir_new / "bvm_tunable.cir")
    qb_match = normalized_source(source_dir_old / "bq_tunable.cir") == normalized_source(source_dir_new / "bq_tunable.cir")
    new_sha = sha256(new_raw)
    prefix = raw_prefix_compare(old_raw, new_raw)
    comparison_input = ROOT / "plots" / "comparisons" / f"{run_dir.name}_raw_prefix_exact_grid.csv"
    subset = make_comparison_input(old_raw, new_raw, comparison_input, old_sha, new_sha, run_dir.name)
    figure = None
    if subset:
        signals = list(subset["column_mapping"])
        output = ROOT / "plots" / "comparisons" / f"{run_dir.name}_historical_raw_prefix.html"
        figure = plot_case.render_classic(comparison_input, output, signals,
                                          f"{run_dir.name} — historical raw prefix comparison",
                                          ROOT / "plots" / "assets" / "plotly.min.js",
                                          new_raw, new_sha, subset)
    compatibility = "EXACT_INPUT_AND_RAW_PREFIX" if parameter_match and stimulus_match and deck_match and jj_jtl_match and bvm_match and qb_match and prefix["raw_prefix_exactly_equal"] else "DESCRIPTIVE_DIFFERENCE_REQUIRES_REVIEW"
    return {"case_id": case["case_id"], "reference_run": reference_run,
            "reference_raw_path": repo_rel(old_raw), "reference_raw_sha256": old_sha,
            "new_run_path": repo_rel(run_dir), "new_raw_sha256": new_sha,
            "historical_parameter_match": parameter_match,
            "historical_candidate_match": candidate_match,
            "historical_mask_match": mask_match,
            "historical_read_schedule_match": read_schedule_match,
            "normalized_stimulus_points_match_through_last_registered_endpoint": stimulus_match,
            "normalized_actual_deck_match_ignoring_include_paths_and_stop": deck_match,
            "jj_and_jtl_source_hashes_match": jj_jtl_match,
            "normalized_rendered_bvm_matches": bvm_match,
            "normalized_rendered_qb_matches": qb_match,
            "raw_prefix_comparison": prefix,
            "comparison_plot": figure,
            "descriptive_regression_compatibility": compatibility,
            "not_a_scientific_verdict": True}


def build_html(comparisons: list[dict[str, Any]], summary_rows: list[dict[str, Any]]) -> str:
    style = "body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:24px;line-height:1.45}a{color:#8ecbff}table{border-collapse:collapse;width:100%;margin:12px 0 26px}th,td{border:1px solid #555;padding:6px 8px;text-align:left;font-size:13px}th{background:#262626}small{color:#aaa}"
    rows = []
    for item in comparisons:
        fig = item.get("comparison_plot")
        plot_link = f"<a href='{html.escape(__import__('os').path.relpath(REPO / fig['path'], ROOT / 'plots'))}'>classic raw-prefix plot</a>" if fig else "not rendered: stored grids differ"
        prefix = item["raw_prefix_comparison"]
        rows.append(f"<tr><td>{html.escape(item['case_id'])}</td><td>{html.escape(Path(item['reference_run']).name)}</td>"
                    f"<td>{'yes' if item['historical_parameter_match'] else 'no'}</td>"
                    f"<td>{'yes' if item['normalized_stimulus_points_match_through_last_registered_endpoint'] else 'no'}</td>"
                    f"<td>{'yes' if item['normalized_actual_deck_match_ignoring_include_paths_and_stop'] else 'no'}</td>"
                    f"<td>{prefix['old_sample_count']} / {prefix['new_sample_count']}</td>"
                    f"<td>{'yes' if prefix['raw_prefix_exactly_equal'] else 'no'}</td><td>{plot_link}</td></tr>")
    run_rows = "".join(f"<tr><td>{html.escape(row['run_id'])}</td><td>{html.escape(row['test_mode'])}</td>"
                        f"<td>{html.escape(row['candidate'])}</td><td>{html.escape(row['mask'])}</td>"
                        f"<td>{row['read_count']}</td><td>{row['stop_ps']}</td>"
                        f"<td><a href='../{html.escape(row['run_id'])}/plots/review.html'>run review</a></td></tr>"
                        for row in summary_rows)
    return "\n".join(("<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>",
                       f"<title>Repeatability regression comparison</title><style>{style}</style></head><body>",
                       "<h1>Platform regression comparison</h1>",
                       "<p>Descriptive compatibility only. Historical/current raw overlays are shown only on an exactly matching stored time grid in [0,240) ps, covering the full historical stored prefix. No interpolation or physical verdict is used.</p>",
                       "<h2>A/B/C historical references</h2>",
                       "<table><tr><th>case</th><th>reference</th><th>parameters</th><th>PWL points</th><th>netlist</th><th>samples old/new</th><th>exact raw prefix</th><th>plot</th></tr>",
                       *rows, "</table><h2>A–E run index</h2>",
                       "<table><tr><th>run</th><th>mode</th><th>candidate</th><th>mask</th><th>reads</th><th>STOP ps</th><th>page</th></tr>",
                       run_rows, "</table><small>Phase turns and threshold-based candidate assignments are navigation records only, not SFQ counts or physical acceptance criteria.</small>",
                       "</body></html>"))


def finalize() -> dict[str, Any]:
    matrix = read_json(REGRESSION_MATRIX)
    runs: list[dict[str, Any]] = []
    checks: list[str] = []
    by_case = {}
    prior_finalization_archive = archive_failed_finalization()
    execution_path = ROOT / "analysis" / "REGRESSION_EXECUTION.json"
    preflight_path = ROOT / "analysis" / "PREFLIGHT_QA.json"
    source_lock_path = ROOT / "analysis" / "PLATFORM_SOURCE_LOCK.json"
    tool_repair_paths = [ROOT / "analysis" / "POST_SOLVE_TOOL_REPAIR.json",
                         ROOT / "analysis" / "POST_SOLVE_TOOL_REPAIR_ATTEMPT2.json"]
    execution = read_json(execution_path) if execution_path.is_file() else {}
    preflight = read_json(preflight_path) if preflight_path.is_file() else {}
    source_lock = read_json(source_lock_path) if source_lock_path.is_file() else {}
    if execution.get("status") != "ALL_REGISTERED_RUNS_COMPLETE" or execution.get("completed_solve_count") != 5:
        checks.append("independent A–E execution receipt does not record exactly five completed runs")
    if execution.get("authorized_solve_count") != 5 or execution.get("preflight_status") != "PASS":
        checks.append("execution receipt is not bound to the authorized five-solve preflight")
    expected_new_solves = 4 if execution.get("existing_physical_solve_count") == 1 else 5
    new_physical_solve_count = int(execution.get("new_physical_solve_count", -1))
    if (execution.get("physical_solve_count") != 5 or
            new_physical_solve_count != expected_new_solves):
        checks.append("execution ledger physical/new solve totals do not match the registered A–E matrix")
    if execution.get("preflight_head") != preflight.get("git", {}).get("head"):
        checks.append("execution receipt and persisted preflight HEAD differ")
    if not preflight_path.is_file() or execution.get("preflight_qa_sha256") != sha256(preflight_path):
        checks.append("execution receipt is not bound to the persisted PREFLIGHT_QA.json")
    if (not source_lock_path.is_file() or
            preflight.get("platform_source_lock_sha256") != sha256(source_lock_path) or
            execution.get("preflight_head") != preflight.get("git", {}).get("head")):
        checks.append("execution ledger is not bound to the source lock and preflight head")
    if preflight.get("status") != "PASS":
        checks.append("persisted machine preflight is not PASS")
    postsolve_tool_repairs = validate_postsolve_finalizer_repairs(
        preflight, execution, source_lock, matrix)
    if any(path.is_file() for path in tool_repair_paths) and not postsolve_tool_repairs:
        checks.append("post-solve analysis tool repair record is missing, malformed, or not raw/solve preserving")
    if preflight.get("git", {}).get("head") != subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip():
        checks.append("finalization HEAD differs from the registered preflight HEAD")
    try:
        from preflight import frozen_paths
        accepted_repair_roles = set()
        for repair in postsolve_tool_repairs:
            if repair.get("changed_role"):
                accepted_repair_roles.add(repair["changed_role"])
            accepted_repair_roles.update(item.get("role") for item in repair.get("changed_components", []))
        for role, path in frozen_paths():
            if not path.is_file() or preflight.get("source_hashes", {}).get(role, {}).get("sha256") != sha256(path):
                if role in accepted_repair_roles:
                    continue
                checks.append(f"frozen preflight source changed before finalization: {role}")
    except Exception as exc:
        checks.append(f"cannot revalidate frozen source closure: {type(exc).__name__}: {exc}")
    execution_records = {item.get("case_id"): item for item in execution.get("runs", [])}
    expected_case_order = [item["case_id"] for item in matrix["cases"]]
    if [item.get("case_id") for item in execution.get("runs", [])] != expected_case_order:
        checks.append("independent execution receipt case order differs from registered A–E matrix")
    expected_actions = (["REANALYZED_EXISTING_RAW", *(["NEW_PHYSICAL_SOLVE"] * 4)]
                        if execution.get("existing_physical_solve_count") == 1 else
                        ["NEW_PHYSICAL_SOLVE"] * 5)
    if execution.get("existing_physical_solve_count") == 1 and execution.get("runs"):
        first_resume_action = execution["runs"][0].get("action")
        if first_resume_action in {"REANALYZED_EXISTING_RAW", "REUSED_EXISTING_ANALYSIS"}:
            expected_actions = [first_resume_action, *(["NEW_PHYSICAL_SOLVE"] * 4)]
    if [item.get("action") for item in execution.get("runs", [])] != expected_actions:
        checks.append("execution actions do not match either a fresh A–E batch or the registered A-recovery/B–E resume")
    for case in matrix["cases"]:
        run_id = case["case_id"]
        run_dir = ROOT / "runs" / run_id
        if not (run_dir / "result.json").is_file():
            checks.append(f"missing run result: {run_id}")
            continue
        metadata = read_json(run_dir / "metadata.json")
        result = read_json(run_dir / "result.json")
        execution_record = execution_records.get(run_id, {})
        receipt_rel = execution_record.get("receipt_path", "")
        receipt_leaf = Path(receipt_rel).name
        allowed_receipt_names = {f"{run_id}.json", *(f"{run_id}_attempt{n}.json" for n in range(2, 100))}
        receipt_path = REPO / receipt_rel
        if (Path(receipt_rel).parent.as_posix() != repo_rel(ROOT / "analysis" / "receipts") or
                receipt_leaf not in allowed_receipt_names):
            checks.append(f"execution receipt path is not a registered immutable attempt path: {run_id}")
            receipt_path = ROOT / "analysis" / "receipts" / f"{run_id}.json"
        receipt = read_json(receipt_path) if receipt_path.is_file() else {}
        if not receipt:
            checks.append(f"independent execution receipt missing: {run_id}")
        else:
            if (not execution_record or execution_record.get("receipt_path") != repo_rel(receipt_path) or
                    execution_record.get("receipt_sha256") != sha256(receipt_path)):
                checks.append(f"independent receipt hash does not match execution ledger: {run_id}")
            if (receipt.get("parameters") != metadata.get("parameters") or
                    receipt.get("solver") != metadata.get("solver")):
                checks.append(f"independent receipt parameters/solver differ from run metadata: {run_id}")
            current_tree = {repo_rel(path): sha256(path) for path in sorted(run_dir.rglob("*"))
                            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"}
            artifact_paths = {"metadata": run_dir / "metadata.json", "result": run_dir / "result.json",
                              "raw": run_dir / "raw.csv", "deck": run_dir / "actual_deck.cir",
                              "stimulus": run_dir / "stimulus.inc", "config_snapshot": run_dir / "config_snapshot.env",
                              "stimulus_snapshot": run_dir / "stimulus_snapshot.json",
                              "source_manifest": run_dir / "source_manifest.json",
                              "stdout": run_dir / "stdout.txt", "stderr": run_dir / "stderr.txt",
                              "run_log": run_dir / "run.log"}
            if execution_record.get("action") in {"REANALYZED_EXISTING_RAW", "REUSED_EXISTING_ANALYSIS"}:
                recovery_rel = execution_record.get("analysis_recovery_receipt_path", "")
                recovery_leaf = Path(recovery_rel).name
                allowed_recovery_names = {f"{run_id}_reanalysis.json",
                                          *(f"{run_id}_reanalysis_attempt{n}.json" for n in range(2, 100)),
                                          *(f"{run_id}_revalidation_attempt{n}.json" for n in range(2, 100))}
                recovery_path = REPO / recovery_rel
                if (Path(recovery_rel).parent.as_posix() != repo_rel(ROOT / "analysis" / "receipts") or
                        recovery_leaf not in allowed_recovery_names):
                    checks.append(f"analysis recovery receipt path is not allowed: {run_id}")
                    recovery_path = ROOT / "analysis" / "receipts" / f"{run_id}_reanalysis.json"
                recovery = read_json(recovery_path) if recovery_path.is_file() else {}
                if (execution_record.get("analysis_recovery_receipt_path") != repo_rel(recovery_path) or
                        execution_record.get("analysis_recovery_receipt_sha256") != (sha256(recovery_path) if recovery_path.is_file() else None)):
                    checks.append(f"analysis recovery receipt hash does not match execution ledger: {run_id}")
                if (receipt.get("execution_status") != "RUN_PASS" or receipt.get("physical_solve_count") != 1 or
                        receipt.get("artifact_status") != "INVALID" or receipt.get("runner_exit_code") == 0 or
                        receipt.get("artifact_sha256", {}).get("raw") != metadata.get("raw", {}).get("sha256")):
                    checks.append(f"original solve receipt does not preserve the failed analyzer/valid solve attempt: {run_id}")
                if (recovery.get("action") not in {"REANALYZED_EXISTING_RAW_NO_SOLVE",
                                                    "REVALIDATED_EXISTING_ANALYSIS_NO_SOLVE"} or
                        recovery.get("preflight_head") != execution.get("preflight_head") or
                        recovery.get("preflight_qa_sha256") != execution.get("preflight_qa_sha256") or
                        recovery.get("runner_exit_code") != 0 or recovery.get("artifact_status") != "VALID" or
                        recovery.get("physical_solve_count") != 1 or recovery.get("new_physical_solve_count") != 0 or
                        recovery.get("raw_sha256") != metadata.get("raw", {}).get("sha256") or
                        recovery.get("parameters") != metadata.get("parameters") or
                        recovery.get("solver") != metadata.get("solver") or
                        recovery.get("run_tree_file_sha256") != current_tree):
                    checks.append(f"analysis-only recovery receipt is incomplete or mismatched: {run_id}")
                original_tree = receipt.get("run_tree_file_sha256", {})
                original_result_rel = repo_rel(run_dir / "result.json")
                for original_rel, expected_hash in original_tree.items():
                    path = (run_dir / "analysis" / "attempts" / "ANALYSIS_ATTEMPT1" / "result.json"
                            if original_rel == original_result_rel else REPO / original_rel)
                    if not path.is_file() or sha256(path) != expected_hash:
                        checks.append(f"original solve-time artifact changed or was not archived: {run_id}/{original_rel}")
                if recovery.get("action") == "REVALIDATED_EXISTING_ANALYSIS_NO_SOLVE":
                    prior_analysis = ROOT / "analysis" / "receipts" / f"{run_id}_reanalysis.json"
                    if (recovery.get("validated_existing_analysis_receipt_path") != repo_rel(prior_analysis) or
                            recovery.get("validated_existing_analysis_receipt_sha256") != (sha256(prior_analysis) if prior_analysis.is_file() else None)):
                        checks.append(f"A reused-analysis receipt does not bind the prior successful reanalysis: {run_id}")
                for key, path in artifact_paths.items():
                    if recovery.get("artifact_sha256", {}).get(key) != sha256(path):
                        checks.append(f"reanalysis receipt artifact hash differs: {run_id}/{key}")
                archive_root = ROOT / "analysis" / "attempts" / "PLATFORM_ATTEMPT1"
                old_pref = archive_root / "PREFLIGHT_QA.json"
                old_exec = archive_root / "REGRESSION_EXECUTION.json"
                old_receipt = archive_root / f"{run_id}_solver_receipt.json"
                old_result = run_dir / "analysis" / "attempts" / "ANALYSIS_ATTEMPT1" / "result.json"
                if not all(path.is_file() for path in (old_pref, old_exec, old_receipt, old_result)):
                    checks.append("original stopped-at-A analysis/solve records were not archived")
                else:
                    old_pref_data, old_exec_data = read_json(old_pref), read_json(old_exec)
                    old_receipt_data = read_json(old_receipt)
                    old_ledger = old_exec_data.get("runs", [{}])[0]
                    manifest_path = archive_root / "archive_manifest.json"
                    manifest = read_json(manifest_path) if manifest_path.is_file() else {}
                    if (sha256(old_receipt) != sha256(receipt_path) or
                            sha256(old_result) != receipt.get("artifact_sha256", {}).get("result") or
                            old_exec_data.get("status") != "STOPPED_ON_FAILURE" or
                            old_pref_data.get("status") != "PASS" or
                            old_pref_data.get("git", {}).get("head") != old_exec_data.get("preflight_head") or
                            old_exec_data.get("preflight_qa_sha256") != sha256(old_pref) or
                            old_ledger.get("receipt_sha256") != sha256(receipt_path) or
                            old_receipt_data.get("preflight_head") != old_exec_data.get("preflight_head") or
                            old_receipt_data.get("preflight_qa_sha256") != old_exec_data.get("preflight_qa_sha256") or
                            manifest.get("files", {}).get("REG_A_QB2X1_N1_solver_receipt.json", {}).get("sha256") != sha256(old_receipt)):
                        checks.append("archived original A attempt chain/hash validation failed")
            else:
                if (receipt.get("preflight_head") != execution.get("preflight_head") or
                        receipt.get("preflight_qa_sha256") != execution.get("preflight_qa_sha256") or
                        receipt.get("runner_exit_code") != 0 or receipt.get("execution_status") != "RUN_PASS" or
                        receipt.get("artifact_status") != "VALID" or receipt.get("physical_solve_count") != 1):
                    checks.append(f"independent solve receipt is incomplete/invalid: {run_id}")
                for key, path in artifact_paths.items():
                    if receipt.get("artifact_sha256", {}).get(key) != sha256(path):
                        checks.append(f"independent receipt artifact hash differs: {run_id}/{key}")
                if current_tree != receipt.get("run_tree_file_sha256", {}):
                    checks.append(f"entire run directory differs from its independent completion receipt: {run_id}")
        analysis_qa = read_json(run_dir / "analysis" / "analysis_qa.json")
        plot_qa = read_json(run_dir / "plots" / "plot_qa.json")
        raw_qa = read_json(run_dir / "analysis" / "raw_qa.json")
        warning_qa = read_json(run_dir / "analysis" / "solver_warning_qa.json")
        signal_manifest_path = run_dir / "analysis" / "signal_manifest.csv"
        if not solver_warning_stderr_matches(warning_qa, metadata, run_dir / "stderr.txt"):
            checks.append(f"solver-warning/unsupported-probe QA failed or changed: {run_id}")
        if (not signal_manifest_path.is_file() or
                sha256(signal_manifest_path) != analysis_qa.get("signal_manifest_sha256")):
            checks.append(f"signal manifest hash missing/mismatched: {run_id}")
        else:
            with signal_manifest_path.open("r", encoding="utf-8", newline="") as stream:
                signal_rows = list(csv.DictReader(stream))
            unknown_rows = [row for row in signal_rows if row.get("status") == "UNKNOWN"]
            if (len(unknown_rows) != 1 or unknown_rows[0].get("raw_column") != "V(IB|XBQ1)" or
                    unknown_rows[0].get("physical_quantity") != "voltage"):
                checks.append(f"known unsupported probe is not explicitly recorded UNKNOWN: {run_id}")
        current_raw_sha = sha256(run_dir / "raw.csv")
        if result.get("artifact_status") != "VALID" or analysis_qa.get("status") != "PASS" or plot_qa.get("status") != "PASS" or raw_qa.get("status") != "PASS":
            checks.append(f"run QA not PASS: {run_id}")
        if (plot_qa.get("all_excitation_and_output_signals_share_classic_plot") is not True or
                plot_qa.get("no_custom_svg_or_iframe_visual_shell") is not True):
            checks.append(f"one-shot-style combined classic stimulus/output visualization QA failed: {run_id}")
        if metadata.get("execution_status") != "RUN_PASS":
            checks.append(f"solver status not PASS: {run_id}")
        for artifact_key in ("config_snapshot", "stimulus_snapshot", "stimulus", "deck", "source_manifest",
                             "stdout", "stderr", "run_log"):
            record = metadata.get(artifact_key, {})
            if not record and artifact_key in {"stdout", "stderr", "run_log"}:
                # The first registered A solve predates log-hash fields in metadata; its
                # immutable parent receipt carries those logs' whole-run tree hash.
                continue
            artifact_path = REPO / str(record.get("path", ""))
            if not artifact_path.is_file() or not record.get("sha256") or sha256(artifact_path) != record.get("sha256"):
                checks.append(f"solve-time provenance hash mismatch for {artifact_key}: {run_id}")
        source_manifest = read_json(run_dir / "source_manifest.json")
        if source_manifest.get("parameters") != metadata.get("parameters"):
            checks.append(f"source manifest parameters differ from run metadata: {run_id}")
        for source_record in source_manifest.get("sources", []):
            source_path = REPO / source_record.get("path", "")
            if not source_path.is_file() or sha256(source_path) != source_record.get("sha256"):
                checks.append(f"source snapshot hash mismatch: {run_id}/{source_record.get('role')}")
        solve_raw_sha = metadata.get("raw", {}).get("sha256")
        analysis_hashes = analysis_qa.get("raw_sha256_before_after", {})
        if not (current_raw_sha == solve_raw_sha == result.get("raw_sha256") == raw_qa.get("raw_sha256") ==
                plot_qa.get("raw_sha256") == analysis_hashes.get("before") == analysis_hashes.get("after")):
            checks.append(f"raw hash lineage mismatch across solve/analyze/plot/finalize: {run_id}")
        plot_manifest_path = run_dir / "plots" / "plot_manifest.json"
        plot_manifest = read_json(plot_manifest_path)
        metadata_plot_hash = metadata.get("plots", {}).get("plot_manifest_sha256")
        if (plot_manifest.get("raw_sha256") != current_raw_sha or
                plot_qa.get("plot_manifest_sha256") != sha256(plot_manifest_path) or
                (metadata_plot_hash is not None and metadata_plot_hash != sha256(plot_manifest_path))):
            checks.append(f"plot manifest/raw hash lineage mismatch: {run_id}")
        for key, field in (("review_page", "review_page_sha256"), ("stimulus_page", "stimulus_page_sha256")):
            page_path = REPO / plot_manifest.get(key, "")
            expected_page_sha = plot_manifest.get(field)
            metadata_page_sha = metadata.get("plots", {}).get(field)
            if (not page_path.is_file() or not expected_page_sha or sha256(page_path) != expected_page_sha or
                    plot_qa.get(field) != expected_page_sha or
                    (metadata_page_sha is not None and metadata_page_sha != expected_page_sha)):
                checks.append(f"plot page provenance hash mismatch ({key}): {run_id}")
        for plot_entry in plot_manifest.get("entries", []):
            page_path = REPO / plot_entry.get("path", "")
            input_path = REPO / plot_entry.get("plot_input_path", "")
            if (not page_path.is_file() or sha256(page_path) != plot_entry.get("sha256") or
                    not input_path.is_file() or sha256(input_path) != plot_entry.get("plot_input_sha256") or
                    plot_entry.get("raw_path") != repo_rel(run_dir / "raw.csv") or
                    plot_entry.get("raw_sha256") != current_raw_sha):
                checks.append(f"grouped plot/raw/input hash lineage mismatch: {run_id}/{plot_entry.get('stem')}")
            subset = plot_entry.get("stored_grid_subset")
            if subset:
                sidecar = input_path.with_suffix(input_path.suffix + ".metadata.json")
                if not sidecar.is_file() or read_json(sidecar) != subset:
                    checks.append(f"focused-plot exact-grid sidecar mismatch: {run_id}/{plot_entry.get('stem')}")
        if float(metadata["parameters"]["STOP_PS"]) <= float(read_json(run_dir / "stimulus_snapshot.json")["last_stimulus_time_ps"]):
            checks.append(f"STOP fails to cover stimulus: {run_id}")
        assignment = read_json(run_dir / "analysis" / "event_assignment.json")["qa"]
        if assignment.get("status") != "PASS" or not assignment.get("assigned_terminal_candidates_never_reused"):
            checks.append(f"candidate assignment invariant failed: {run_id}")
        jtl_path_qa = analysis_qa.get("jtl_candidate_path_qa", {})
        if jtl_path_qa.get("invariant_status") != "PASS":
            checks.append(f"JTL candidate-path uniqueness/ordering QA failed: {run_id}")
        params = metadata["parameters"]
        row = {"run_id": run_id, "test_mode": params["TEST_MODE"], "candidate": params["CANDIDATE"],
               "array_size": params["ARRAY_SIZE"], "mask": params["MASK"], "read_count": params["READ_COUNT"],
               "read_starts_ps": ";".join(str(x["read_start_ps"]) for x in read_json(run_dir / "stimulus_snapshot.json")["read_schedule"]),
               "stop_ps": params["STOP_PS"], "raw_sha256": current_raw_sha,
               "raw_qa": raw_qa["status"], "analysis_qa": analysis_qa["status"], "plot_qa": plot_qa["status"],
               "assignment_qa": assignment["status"], "jtl_path_qa": jtl_path_qa.get("invariant_status"),
               "jtl_path_status": jtl_path_qa.get("status"),
               "complete_unique_jtl_paths": jtl_path_qa.get("complete_unique_path_count", 0)}
        runs.append(row)
        by_case[run_id] = run_dir

    if len(runs) != int(matrix["authorized_solve_count"]):
        checks.append(f"registered case result count is {len(runs)}, expected {matrix['authorized_solve_count']}")
    if len({row["run_id"] for row in runs}) != len(runs):
        checks.append("duplicate run IDs in regression summary")
    expected_run_ids = {case["case_id"] for case in matrix["cases"]}
    observed_run_dirs = [path for path in (ROOT / "runs").iterdir()
                         if path.is_dir() and ((path / "metadata.json").exists() or (path / "raw.csv").exists())]
    observed_run_ids = {path.name for path in observed_run_dirs}
    unexpected_run_ids = sorted(observed_run_ids - expected_run_ids)
    missing_run_ids = sorted(expected_run_ids - observed_run_ids)
    if unexpected_run_ids:
        checks.append(f"unregistered run directories exist: {unexpected_run_ids}")
    if missing_run_ids:
        checks.append(f"registered run directories missing: {missing_run_ids}")
    total_physical_solve_count = 0
    for path in observed_run_dirs:
        metadata_path = path / "metadata.json"
        if metadata_path.is_file():
            total_physical_solve_count += int(read_json(metadata_path).get("physical_solve_count", 0))
        elif (path / "raw.csv").is_file():
            total_physical_solve_count += 1
            checks.append(f"raw exists without solve metadata: {path.name}")
    if total_physical_solve_count != int(matrix["authorized_solve_count"]):
        checks.append(f"actual physical solve count is {total_physical_solve_count}, expected {matrix['authorized_solve_count']}")

    comparisons = []
    for case in matrix["cases"]:
        reference = case.get("reference_run")
        if not reference or case["case_id"] not in by_case:
            continue
        comparisons.append(compare_reference(case, by_case[case["case_id"]], reference))
    input_mismatches = [item["case_id"] for item in comparisons
                        if not all((item["historical_parameter_match"],
                                    item["normalized_stimulus_points_match_through_last_registered_endpoint"],
                                    item["normalized_actual_deck_match_ignoring_include_paths_and_stop"],
                                    item["jj_and_jtl_source_hashes_match"],
                                    item["normalized_rendered_bvm_matches"],
                                    item["normalized_rendered_qb_matches"]))]
    for run_id in input_mismatches:
        checks.append(f"historical input closure mismatch: {run_id}")
    historical_prefix_exact = all(item["raw_prefix_comparison"]["raw_prefix_exactly_equal"] for item in comparisons)
    historical_compatibility = ("DESCRIPTIVE_EXACT_RAW_PREFIX_COMPATIBILITY"
                                 if comparisons and historical_prefix_exact and not input_mismatches
                                 else "DESCRIPTIVE_DIFFERENCE_REQUIRES_REVIEW")

    comparison_plot_checks = []
    for item in comparisons:
        figure = item.get("comparison_plot")
        if figure is None:
            comparison_plot_checks.append({"case_id": item["case_id"],
                                           "status": "NOT_APPLICABLE_GRID_MISMATCH",
                                           "reason": "No interpolation; exact stored grids are required for an overlay."})
            continue
        path = REPO / figure["path"]
        body = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
        ok = (path.is_file() and sha256(path) == figure["sha256"] and
              not any(token in body for token in ("Unknown", "cdn.plot.ly", "plotly.js v", "var Plotly=")))
        subset = figure.get("stored_grid_subset")
        if subset:
            derived = REPO / subset["derived_csv"]
            sidecar = derived.with_suffix(derived.suffix + ".metadata.json")
            old_raw = REPO / subset["old_raw_path"]
            new_raw = REPO / subset["new_raw_path"]
            ok = (ok and derived.is_file() and sha256(derived) == subset["derived_csv_sha256"] and
                  sidecar.is_file() and read_json(sidecar) == subset and
                  old_raw.is_file() and sha256(old_raw) == subset["old_raw_sha256"] and
                  new_raw.is_file() and sha256(new_raw) == subset["new_raw_sha256"])
        if not ok:
            checks.append(f"comparison visualization QA failed: {item['case_id']}")
        comparison_plot_checks.append({"case_id": item["case_id"], "status": "PASS" if ok else "FAIL",
                                       "path": figure["path"], "sha256": figure["sha256"]})
    comparison_plot_qa = {"schema": "bvm-qb-repeatability-comparison-plot-qa-v1",
                          "status": "PASS" if all(item["status"] != "FAIL" for item in comparison_plot_checks) else "FAIL",
                          "cases": comparison_plot_checks, "pointwise_plot_requires_exact_time_grid": True,
                          "interpolation_or_resampling": False, "descriptive_only": True}

    analysis_dir = ROOT / "analysis"
    write_csv(analysis_dir / "summary.csv",
              ["run_id", "test_mode", "candidate", "array_size", "mask", "read_count", "read_starts_ps", "stop_ps",
               "raw_sha256", "raw_qa", "analysis_qa", "plot_qa", "assignment_qa", "jtl_path_qa",
               "jtl_path_status", "complete_unique_jtl_paths"], runs)
    write_json(analysis_dir / "REGRESSION_COMPARISON.json", {
        "schema": "bvm-qb-repeatability-regression-comparison-v1",
        "comparisons": comparisons,
        "scientific_interpretation_performed": False,
        "comparison_window_ps": COMPARE_WINDOW_PS,
        "pointwise_comparison_requires_exact_time_grid": True,
        "interpolation_or_resampling": False,
    })
    write_json(analysis_dir / "REGRESSION_COMPARISON_PLOT_QA.json", comparison_plot_qa)
    write_json(analysis_dir / "plot_manifest.json", {
        "schema": "bvm-qb-repeatability-series-plot-manifest-v1",
        "renderer": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi",
        "run_manifests": [repo_rel(ROOT / "runs" / row["run_id"] / "plots" / "plot_manifest.json") for row in runs],
        "comparison_figures": [item["comparison_plot"] for item in comparisons if item.get("comparison_plot")],
        "result_overview": repo_rel(ROOT / "plots" / "RESULT_OVERVIEW.html"),
        "regression_comparison": repo_rel(ROOT / "plots" / "REGRESSION_COMPARISON.html"),
        "raw_immutable": True, "scientific_interpretation_performed": False,
    })
    write_json(analysis_dir / "provenance.json", {
        "schema": "bvm-qb-repeatability-provenance-v1",
        "experiment": ROOT.name,
        "preflight": read_json(analysis_dir / "PREFLIGHT_QA.json"),
        "runs": [{"run_id": row["run_id"], "metadata": file_record("metadata", ROOT / "runs" / row["run_id"] / "metadata.json"),
                  "source_manifest": file_record("source_manifest", ROOT / "runs" / row["run_id"] / "source_manifest.json"),
                  "raw": file_record("raw", ROOT / "runs" / row["run_id"] / "raw.csv")} for row in runs],
        "scientific_interpretation_performed": False,
    })
    comparison_html = build_html(comparisons, runs)
    (ROOT / "plots" / "REGRESSION_COMPARISON.html").parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "plots" / "REGRESSION_COMPARISON.html").write_text(comparison_html, encoding="utf-8")
    index_lines = ["<!doctype html><html><head><meta charset='utf-8'><title>BVM-QB repeatability run index</title>",
                   "<style>body{font-family:Arial,sans-serif;background:#111;color:#eee;margin:24px}a{color:#8ecbff}table{border-collapse:collapse;width:100%}td,th{border:1px solid #555;padding:7px;text-align:left}th{background:#262626}</style></head><body>",
                   "<h1>BVM array → JSL → QB → JTL repeatability</h1>",
                   "<p>Independent run pages use the one-shot platform's compact classic josim-plot approach. This index and its linked tables are descriptive only.</p>",
                   "<p><a href='REGRESSION_COMPARISON.html'>A–E regression comparison</a> · <a href='../analysis/RESULT_BRIEF.md'>RESULT_BRIEF.md</a> · <a href='../analysis/summary.csv'>summary.csv</a></p>",
                   "<table><tr><th>run</th><th>mode</th><th>candidate</th><th>mask</th><th>STOP ps</th><th>raw</th><th>review</th><th>stimulus</th></tr>"]
    for row in runs:
        rid = html.escape(row["run_id"])
        index_lines.append(f"<tr><td>{rid}</td><td>{html.escape(row['test_mode'])}</td><td>{html.escape(row['candidate'])}</td><td>{html.escape(row['mask'])}</td><td>{row['stop_ps']}</td><td><a href='../runs/{rid}/raw.csv'>raw.csv</a></td><td><a href='../runs/{rid}/plots/review.html'>review</a></td><td><a href='../runs/{rid}/plots/stimulus.html'>stimulus</a></td></tr>")
    index_lines.extend(["</table></body></html>"])
    (ROOT / "plots" / "RESULT_OVERVIEW.html").write_text("\n".join(index_lines), encoding="utf-8")

    status = "PASS" if not checks else "FAIL"
    registered_raw_count = len([row for row in runs if row["raw_sha256"]])
    final_qa = {
        "schema": "bvm-qb-repeatability-final-qa-v1", "status": status,
        "execution_status": "ALL_REGISTERED_RUNS_COMPLETE" if registered_raw_count == 5 and total_physical_solve_count == 5 else "INCOMPLETE",
        "physical_solve_count": total_physical_solve_count,
        "existing_physical_solve_count": int(execution.get("existing_physical_solve_count", 0)),
        "new_physical_solve_count": new_physical_solve_count,
        "registered_cases_with_raw": registered_raw_count,
        "unexpected_run_ids": unexpected_run_ids, "authorized_solve_count": 5,
        "raw_artifact_qa": "PASS" if all(row["raw_qa"] == "PASS" for row in runs) and len(runs) == 5 else "FAIL",
        "analysis_qa": "PASS" if all(row["analysis_qa"] == "PASS" for row in runs) and len(runs) == 5 else "FAIL",
        "plot_qa": "PASS" if all(row["plot_qa"] == "PASS" for row in runs) and len(runs) == 5 else "FAIL",
        "comparison_plot_qa": comparison_plot_qa["status"],
        "event_assignment_invariants": "PASS" if all(row["assignment_qa"] == "PASS" for row in runs) and len(runs) == 5 else "FAIL",
        "jtl_assignment_safety_checks": "PASS" if all(row["jtl_path_qa"] == "PASS" for row in runs) and len(runs) == 5 else "FAIL",
        "complete_unique_jtl_path_counts": {row["run_id"]: row["complete_unique_jtl_paths"] for row in runs},
        "observed_jtl_path_statuses": {row["run_id"]: row["jtl_path_status"] for row in runs},
        "historical_comparisons": [{"case_id": item["case_id"], "compatibility": item["descriptive_regression_compatibility"],
                                    "exact_raw_prefix": item["raw_prefix_comparison"]["raw_prefix_exactly_equal"]}
                                   for item in comparisons],
        "historical_input_closure_status": "PASS" if not input_mismatches else "FAIL",
        "historical_compatibility_status": historical_compatibility,
        "postsolve_tool_repairs": [file_record("postsolve_tool_repair", path) for path in tool_repair_paths if path.is_file()],
        "prior_failed_finalization_archive": prior_finalization_archive,
        "checks": checks, "scientific_interpretation_performed": False,
        "automatic_follow_up": False,
        "interpretation_ceiling": "platform/mechanical regression only; no physical recovery, SFQ, Gate, maximum-frequency, or mechanism verdict",
    }
    brief = [
        "# BVM-QB repeatability platform — run summary", "",
        "## OBSERVED", "",
        f"- Physical solves found: {total_physical_solve_count} total ({new_physical_solve_count} new in this execution); registered A–E cases with raw: {registered_raw_count}/5.",
        "- Every per-run raw is hash-bound; analyses use actual stored-grid samples only.",
        "- A/B/C historical raw prefix equality and input/deck comparison are recorded in `REGRESSION_COMPARISON.json`.",
        "- D writes a single-read-to-STOP recovery trace; E's complete sequence schedule and computed STOP are recorded in snapshots.",
        "", "## DERIVED", "",
        "- Cycle phase/voltage-area arithmetic uses the same QB junction and the same half-open upstream cycle on the actual stored grid.",
        "- Candidate pairing is voltage-threshold navigation only; assignments are monotonic, unique when possible, and otherwise `AMBIGUOUS`.",
        "- BJ2→12 JTL-junction→terminal candidate paths are reported only when ordered and unique; `NO_COMPLETE_PATH_OBSERVED`, missing, or competing stage candidates remain explicit and are not mislabeled PASS.",
        "- Component deltas and same-unit vector distances are relative to the median PRE_1 window; no recovery threshold is defined.",
        "", "## PLATFORM LIMITATIONS", "",
        "- P(...) is raw radians; turns are `rad/(2*pi)` navigation only, not SFQ counts.",
        "- `V(IB|XBQ1)` is a known unsupported current-source branch voltage in this JoSIM build; it is recorded as `UNKNOWN` in each signal manifest while `I(IB|XBQ1)` remains probed.",
        "- Voltage candidates and terminal assignments do not establish an event count, SFQ transmission, physical recovery, state retention, or population-preserving quantization.",
        "- No timestep convergence, parameter sensitivity, hardware inference, or physical mechanism review was performed.",
        "", "## REGRESSION STATUS", "",
        f"- Mechanical final QA: `{status}`; physical solve count={total_physical_solve_count} total, {new_physical_solve_count} new; authorized=5.",
        f"- A/B/C descriptive raw-prefix compatibility: `{historical_compatibility}` (not a physical verdict).",
        "- See `analysis/FINAL_QA.json`, `analysis/summary.csv`, and `plots/REGRESSION_COMPARISON.html`.",
        "", "## NEXT SCIENTIFIC EXPERIMENTS NOT YET RUN", "",
        "- No recovery-boundary sweep, READ-period sweep, candidate tuning, additional fan-in, or follow-up solve was started.",
        "- Further scientific interpretation awaits explicit review authorization.", "",
    ]
    (analysis_dir / "RESULT_BRIEF.md").write_text("\n".join(brief), encoding="utf-8")
    if status != "PASS":
        result_status = "PLATFORM_REGRESSION_QA_FAIL"
    elif historical_compatibility != "DESCRIPTIVE_EXACT_RAW_PREFIX_COMPATIBILITY":
        result_status = "DESCRIPTIVE_REGRESSION_DIFFERENCE_REQUIRES_REVIEW"
    else:
        result_status = "PLATFORM_REGRESSION_COMPLETE_AWAITING_SCIENTIFIC_REVIEW"
    write_json(ROOT / "result.json", {"schema": "bvm-qb-repeatability-result-v1",
                                      "status": result_status,
                                      "artifact_status": "VALID" if status == "PASS" else "INVALID",
                                      "physical_solve_count": total_physical_solve_count,
                                      "new_physical_solve_count": new_physical_solve_count,
                                      "authorized_solve_count": 5,
                                      "historical_compatibility_status": historical_compatibility,
                                      "scientific_interpretation_performed": False,
                                      "automatic_follow_up": False,
                                      "final_qa": repo_rel(analysis_dir / "FINAL_QA.json")})
    sealed_files = {repo_rel(path): sha256(path)
                    for path in sorted(ROOT.rglob("*"))
                    if path.is_file() and not excluded_from_finalization_seal(path)}
    final_qa["sealed_file_sha256"] = sealed_files
    final_qa["sealed_file_count"] = len(sealed_files)
    write_json(analysis_dir / "FINAL_QA.json", final_qa)
    (analysis_dir / "FINAL_QA.sha256").write_text(
        f"{sha256(analysis_dir / 'FINAL_QA.json')}  FINAL_QA.json\n", encoding="utf-8")
    return final_qa


def main() -> int:
    qa = finalize()
    print(json.dumps({key: qa.get(key) for key in (
        "status", "execution_status", "physical_solve_count", "authorized_solve_count",
        "historical_compatibility_status", "checks", "sealed_file_count")},
        ensure_ascii=False, indent=2))
    return 0 if qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
