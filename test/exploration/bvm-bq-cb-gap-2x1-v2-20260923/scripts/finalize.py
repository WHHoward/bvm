#!/usr/bin/env python3
"""Create exact-grid paired views and evidence-only experiment summaries."""

from __future__ import annotations

import argparse
import csv
import html
import json
import subprocess
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from common import (MATRIX, PLOTTER, REPO, ROOT, cases, in_half_open_window,
                    read_json, run_dir, sha256, write_json)
from plot_run import externalize
from analyze_run import integrate_actual

ANALYSIS = ROOT / "analysis"
PLOTS = ROOT / "plots"
PLOT_QA = ROOT / "qa" / "plot_qa.json"
SUMMARY_SIGNALS = ["V(FINAL_OUT)", "V(R_TERM)", "P(BJ1|XGAP2)",
                   "I(L2|XACC2)", "I(L2|XGAP1)"]
COMPARE_WINDOWS = {"final_read_110_121": (110.0, 121.0),
                   "post_read_121_200": (121.0, 200.0),
                   "read_response_110_200": (110.0, 200.0)}


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def read_raw_series(run_id: str, signal: str, bounds: tuple[float, float]):
    raw = run_dir(run_id) / "raw.csv"
    data: dict[Decimal, tuple[str, str]] = {}
    with raw.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if signal not in (reader.fieldnames or []):
            raise ValueError(f"missing comparison signal {signal} in {raw}")
        for row in reader:
            token = row["time"]
            t_s = Decimal(token)
            if in_half_open_window(token, bounds):
                if t_s in data:
                    raise ValueError(f"duplicate stored time in {raw}: {token}")
                data[t_s] = (token, row[signal])
    return raw, data


def write_compare_plot(signal: str, window: str, bounds: tuple[float, float], runs: list[dict[str, Any]]) -> dict[str, Any]:
    series = {}
    time_tokens: dict[Decimal, str] = {}
    raw_hashes_before = {case["run_id"]: sha256(run_dir(case["run_id"]) / "raw.csv") for case in runs}
    for case in runs:
        raw, data = read_raw_series(case["run_id"], signal, bounds)
        series[case["run_id"]] = data
        for t_s, (token, _value) in data.items():
            time_tokens.setdefault(t_s, token)
    grid = sorted(time_tokens)
    directory = PLOTS / "comparison"
    directory.mkdir(parents=True, exist_ok=True)
    stem = f"{signal.replace('(', '_').replace(')', '').replace('|', '_').replace('/', '_')}__{window}"
    output = directory / f"{stem}.html"
    comparison_dir = ANALYSIS / "comparison_inputs"
    comparison_dir.mkdir(parents=True, exist_ok=True)
    projected = comparison_dir / f"{stem}.csv"
    sidecar = comparison_dir / f"{stem}.manifest.json"
    if projected.exists() or sidecar.exists() or output.exists():
        raise RuntimeError(f"append-only comparison artifact already exists: {stem}")
    fields = ["time"] + [f"{signal} [{case['run_id']}]" for case in runs]
    with projected.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for t_s in grid:
            row = {"time": time_tokens[t_s]}
            for case in runs:
                sample = series[case["run_id"]].get(t_s)
                row[f"{signal} [{case['run_id']}]" ] = sample[1] if sample else ""
            writer.writerow(row)
    renamed = [f"{signal} [{case['run_id']}]" for case in runs]
    temporary_html = output.with_suffix(".tmp.html")
    command = [sys.executable, str(PLOTTER), str(projected), "-x", str(temporary_html),
               "-t", "sep_comb", "-c", "dark", "-j", "2pi", "-w",
               f"Four-run raw comparison — {signal} — {window}", "-s", *renamed]
    completed = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    if completed.returncode != 0 or not temporary_html.is_file():
        raise RuntimeError(f"classic comparison plot failed for {signal}/{window}: {completed.stderr[-1200:]}")
    output.write_text(temporary_html.read_text(encoding="utf-8"), encoding="utf-8")
    temporary_html.unlink()
    externalize(output)
    html_text = output.read_text(encoding="utf-8", errors="replace")
    if "unknown" in html_text.lower():
        raise RuntimeError(f"classic comparison contains an Unknown axis/label: {output}")
    raw_hashes_after = {case["run_id"]: sha256(run_dir(case["run_id"]) / "raw.csv") for case in runs}
    if raw_hashes_before != raw_hashes_after:
        raise RuntimeError(f"raw hash changed during comparison rendering for {signal}/{window}")
    grid_equal = all(list(series[case["run_id"]]) == list(series[runs[0]["run_id"]]) for case in runs[1:])
    raw_hashes = raw_hashes_after
    sidecar_manifest = {"schema": "bvm-bq-cb-gap-comparison-input-v1",
                        "signal": signal, "window": window, "window_ps": list(bounds),
                        "run_ids": [case["run_id"] for case in runs], "raw_sha256": raw_hashes,
                        "comparison_csv_path": projected.relative_to(ROOT).as_posix(),
                        "comparison_csv_sha256": sha256(projected),
                        "comparison_plot_path": output.relative_to(ROOT).as_posix(),
                        "exact_timestamp_union": True, "missing_samples": "blank",
                        "interpolation": False, "resampling": False,
                        "sample_count": len(grid), "case_sample_counts": {
                            run_id: len(data) for run_id, data in series.items()},
                        "scientific_interpretation_performed": False}
    write_json(sidecar, sidecar_manifest)
    return {"path": output.relative_to(ROOT).as_posix(), "sha256": sha256(output),
            "signal": signal, "window": window, "window_ps": list(bounds),
            "run_ids": [case["run_id"] for case in runs], "raw_sha256": raw_hashes,
            "comparison_csv_path": projected.relative_to(ROOT).as_posix(),
            "comparison_csv_sha256": sha256(projected),
            "comparison_sidecar_path": sidecar.relative_to(ROOT).as_posix(),
            "comparison_sidecar_sha256": sha256(sidecar),
            "union_sample_count": len(grid), "case_sample_counts": {
                run_id: len(data) for run_id, data in series.items()},
            "exact_common_grid": grid_equal, "alignment": "exact timestamp union; missing samples blank; no interpolation/resampling",
            "renderer": "scripts/josim-plot2.py", "plot_type": "sep_comb",
            "theme": "dark", "phase_display": "raw P radians; -j 2pi navigation only",
            "descriptive_only": True}


def make_terminal_deltas(run_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    control_id = "N0_00"
    outputs = []
    rows_csv = []
    for window, bounds in COMPARE_WINDOWS.items():
        read_values = {case["run_id"]: read_raw_series(case["run_id"], "V(R_TERM)", bounds)[1]
                       for case in run_records}
        control = read_values[control_id]
        for case in run_records:
            run_id = case["run_id"]
            current = read_values[run_id]
            same_grid = list(current) == list(control)
            if not same_grid:
                outputs.append({"run_id": run_id, "control_run_id": control_id,
                                "window": window, "window_ps": list(bounds),
                                "status": "UNKNOWN_GRID_MISMATCH", "pointwise_subtraction": False})
                continue
            times = list(current)
            deltas = [float(current[t][1]) - float(control[t][1]) for t in times]
            area = integrate_actual([current[t][0] for t in times], deltas)
            max_abs = max((abs(value) for value in deltas), default=0.0)
            for t_s, voltage_delta in zip(times, deltas):
                rows_csv.append({"window": window, "run_id": run_id, "control_run_id": control_id,
                                 "time_s": current[t_s][0], "delta_V_R_TERM_V": voltage_delta})
            outputs.append({"run_id": run_id, "control_run_id": control_id,
                            "window": window, "window_ps": list(bounds),
                            "status": "EXACT_GRID_DERIVED", "pointwise_subtraction": True,
                            "sample_count": len(times), "max_abs_voltage_delta_v": max_abs,
                            "signed_integral_delta_v_s": area,
                            "signed_integral_delta_phi0": area / 2.067833848e-15,
                            "control_raw_sha256": sha256(run_dir(control_id) / "raw.csv"),
                            "run_raw_sha256": sha256(run_dir(run_id) / "raw.csv"),
                            "interpolation": False, "resampling": False})
    path = ANALYSIS / "terminal_delta_vs_N0_00.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["window", "run_id", "control_run_id", "time_s", "delta_V_R_TERM_V"])
        writer.writeheader()
        writer.writerows(rows_csv)
    return outputs


def write_result_brief(run_records: list[dict[str, Any]], comparisons: list[dict[str, Any]], terminal_deltas: list[dict[str, Any]]) -> None:
    matrix = read_json(MATRIX)
    rows = []
    for case in cases():
        metrics = read_json(run_dir(case["run_id"]) / "analysis" / "metrics.json")
        selected = {(item["stage"], item["window"]): item for item in metrics["jj_phase_area_metrics"]}
        def cell(stage: str) -> str:
            item = selected.get((stage, "final_read"), {})
            if item.get("status") != "RECORDED":
                return "UNKNOWN"
            return f"phase {item['phase_delta_turns_navigation']:.6g} turn-nav; area {item['voltage_area_phi0']:.6g} Φ0"
        terminal = next((item for item in metrics["terminal_area_metrics"] if item["window"] == "read_response"), {})
        term = f"{terminal.get('signed_area_phi0', float('nan')):.6g} Φ0" if terminal.get("status") == "RECORDED" else "UNKNOWN"
        rows.append((case["run_id"], cell("ACC1_BJ1"), cell("GAP1_BJ1"), cell("ACC2_BJ1"), cell("GAP2_BJ1"), term))
    table = ["| mask/run | ACC1 BJ1 phase / area | GAP1 BJ1 phase / area | ACC2 BJ1 phase / area | GAP2 BJ1 phase / area | terminal signed area `[110,200)` |",
             "|---|---:|---:|---:|---:|---:|"]
    case_mask = {case["run_id"]: case["mask"] for case in cases()}
    table.extend(f"| {case_mask[run_id]} / {run_id} | {a1} | {g1} | {a2} | {g2} | {term} |"
                 for run_id, a1, g1, a2, g2, term in rows)
    text = [f"# Evidence-only result — {matrix['experiment_id']}", "",
            "Status: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.",
            "Scientific interpretation: `NOT PERFORMED` (the required authorization token was not supplied).",
            "V2 physical solve count: 4/4. Cumulative JoSIM transient invocations including the unretained v1 incident: 5; the v1 output is excluded from evidence. Automatic follow-up: none.", "",
            "## OBSERVED", "",
            "All four registered runs completed with raw mechanical QA plus an independent Decimal arithmetic cross-check; the raw probe set and classic standalone/comparison visualizations are retained.",
            "The table reports measured local phase endpoint progression (turns are `rad/(2π)` navigation) and signed voltage-time area on the same JJ and registered `[110,121)` stored-sample window. Terminal area is signed `V(R_TERM)` integral divided by Φ0 on `[110,200)`. These values are not event counts or functional classifications.", "",
            *table, "", "## DERIVED", "",
            "Terminal pointwise deltas versus `N0_00` are included only where actual stored timestamps match exactly; otherwise the paired subtraction is `UNKNOWN`. See `analysis/terminal_delta_vs_N0_00.csv` and `analysis/comparison_summary.json`.",
            "No population truth-table verdict, event count, SFQ-delivery claim, earliest-failure localization, mechanism explanation, convergence claim, or parameter recommendation is assigned in this operator report.", "",
            "## Evidence", "",
            "- Per-run classic review and stimulus/output pages: `plots/N*/review.html`, `plots/N*/stimulus.html`.",
            "- Four-run classic comparison index: `plots/comparison/index.html`.",
            "- Per-run raw metrics and QA: `runs/N*/analysis/`.",
            "- Independent arithmetic reproduction from raw: `runs/N*/analysis/independent_check.json`.",
            "- Machine preflight, execution and plot QA: `analysis/PREFLIGHT_QA.json`, `analysis/EXECUTION.json`, `qa/plot_qa.json`, `qa/comparison_qa.json`.",
            "- Provenance: `analysis/SOURCE_LOCK.json`, each run's `metadata.json` and `source_manifest.json`.",
            "- Raw files are immutable; no interpolation/resampling was performed; plots are descriptive only.", ""]
    (ROOT / "RESULT_BRIEF.md").write_text("\n".join(text), encoding="utf-8")


def write_evidence_manifests(run_records: list[dict[str, Any]], plot_manifest: dict[str, Any], compare_entries: list[dict[str, Any]], terminal_deltas: list[dict[str, Any]]) -> None:
    items = []
    for case in cases():
        directory = run_dir(case["run_id"])
        raw = directory / "raw.csv"
        deck = directory / "actual_deck.cir"
        metrics = directory / "analysis" / "metrics.json"
        independent = directory / "analysis" / "independent_check.json"
        items.append({"run_id": case["run_id"], "mask": case["mask"], "population_input_label": case["population"],
                      "raw_path": raw.relative_to(ROOT).as_posix(), "raw_sha256": sha256(raw), "raw_bytes": raw.stat().st_size,
                      "deck_path": deck.relative_to(ROOT).as_posix(), "deck_sha256": sha256(deck),
                      "metadata_path": (directory / "metadata.json").relative_to(ROOT).as_posix(),
                      "source_manifest_path": (directory / "source_manifest.json").relative_to(ROOT).as_posix(),
                      "analysis_metrics_path": metrics.relative_to(ROOT).as_posix(),
                      "analysis_metrics_sha256": sha256(metrics),
                      "independent_check_path": independent.relative_to(ROOT).as_posix(),
                      "independent_check_sha256": sha256(independent)})
    raw_manifest = {"schema": "bvm-bq-cb-gap-raw-analysis-handoff-v2",
                    "experiment_id": read_json(MATRIX)["experiment_id"],
                    "authorized_run_ids": [item["run_id"] for item in cases()],
                    "physical_solve_count": len(run_records), "runs": items,
                    "cumulative_solver_invocations_including_v1_incident": 5,
                    "v1_incident_data_included": False,
                    "plot_manifest_path": "analysis/plot_manifest.json",
                    "plot_manifest_sha256": sha256(ROOT / "analysis" / "plot_manifest.json"),
                    "comparison_plot_paths": [entry["path"] for entry in compare_entries],
                    "comparison_input_paths": [entry["comparison_csv_path"] for entry in compare_entries],
                    "comparison_sidecar_paths": [entry["comparison_sidecar_path"] for entry in compare_entries],
                    "terminal_delta_statuses": terminal_deltas,
                    "terminal_delta_csv_path": "analysis/terminal_delta_vs_N0_00.csv",
                    "terminal_delta_csv_sha256": sha256(ANALYSIS / "terminal_delta_vs_N0_00.csv"),
                    "independent_raw_arithmetic_qa": "PASS",
                    "scientific_interpretation_performed": False,
                    "raw_immutable": True, "interpolation": False, "resampling": False}
    transformation_registry = {
        "schema": "bvm-bq-cb-gap-transformations-v1",
        "raw_mutation": False,
        "transformations": [
            {"id": "DIRECT_RAW_PHASE_ENDPOINT_ARITHMETIC", "purpose": "compute registered phase endpoint progression",
             "input": "immutable JoSIM P(...) raw unwrapped radians", "operation": "direct last-minus-first stored endpoint subtraction; no modulo or re-unwrapping",
             "unit_conversion": "divide by 2*pi only for navigation value", "interpolation": False},
            {"id": "SAME_JJ_SIGNED_VOLTAGE_AREA", "purpose": "mechanical phase/area cross-check",
             "operation": "trapezoidal integration of same JJ voltage over actual stored timestamps in same half-open window; dt from exact stored seconds tokens",
             "interpolation": False, "resampling": False},
            {"id": "PLOT_COLUMN_AND_WINDOW_PROJECTION", "purpose": "classic josim-plot2 views",
             "operation": "select registered source columns and optionally stored rows where start_ps <= time_ps < end_ps; preserve original CSV text tokens",
             "windows_ps": {"final_read": [110, 121], "post_read": [121, 200], "read_response": [110, 200]},
             "interpolation": False, "resampling": False, "raw_overwrite": False},
            {"id": "FOUR_CASE_PLOT_UNION_GRID", "purpose": "descriptive comparison overlay",
             "operation": "exact timestamp union; absent case samples represented as blank cells",
             "interpolation": False, "resampling": False},
            {"id": "TERMINAL_DELTA_VERSUS_N0_00", "purpose": "registered paired terminal voltage comparison",
             "operation": "subtract V(R_TERM) pointwise only when parsed stored time grids are exactly identical",
             "otherwise": "UNKNOWN_GRID_MISMATCH", "interpolation": False, "resampling": False},
        ],
        "scientific_interpretation_performed": False,
    }
    write_json(ANALYSIS / "TRANSFORMATION_REGISTRY.json", transformation_registry)
    write_json(ANALYSIS / "comparison_summary.json", {
        "schema": "bvm-bq-cb-gap-comparison-summary-v1",
        "control_run_id": "N0_00", "comparison_windows_ps": {name: list(bounds) for name, bounds in COMPARE_WINDOWS.items()},
        "comparison_signals": SUMMARY_SIGNALS,
        "terminal_pointwise_deltas": terminal_deltas,
        "plot_entries": compare_entries,
        "exact_decimal_timestamp_matching": True,
        "interpolation": False, "resampling": False,
        "scientific_interpretation_performed": False,
    })
    raw_manifest.update({"transformation_registry_path": "analysis/TRANSFORMATION_REGISTRY.json",
                         "transformation_registry_sha256": sha256(ANALYSIS / "TRANSFORMATION_REGISTRY.json"),
                         "comparison_summary_path": "analysis/comparison_summary.json",
                         "comparison_summary_sha256": sha256(ANALYSIS / "comparison_summary.json")})
    write_json(ROOT / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", raw_manifest)
    lines = ["# Evidence Manifest", "", f"Experiment: `{raw_manifest['experiment_id']}`", "",
             "This package preserves all four authorized immutable raw CSVs, exact decks/stimuli, metadata, source snapshots, mechanical analysis, classic plots and comparison views.", "",
             "V2 registered four new physical solves. The unretained v1 incident transient is excluded from this package; cumulative solver invocations across both attempts are five.",
             "Independent Decimal arithmetic QA re-read each raw and reproduced the mechanical endpoint/area calculations.",
             "## Runs", "", "| Run | Mask | Raw bytes | Raw SHA-256 | Deck SHA-256 | Independent QA SHA-256 |", "|---|---|---:|---|---|---|"]
    lines.extend(f"| {item['run_id']} | {item['mask']} | {item['raw_bytes']} | `{item['raw_sha256']}` | `{item['deck_sha256']}` | `{item['independent_check_sha256']}` |" for item in items)
    lines.extend(["", "## Visualization", "",
                  f"Standalone plot count: {len(plot_manifest['entries'])}; comparison plot count: {len(compare_entries)}.",
                  "Renderer: `scripts/josim-plot2.py`; `sep_comb`, dark theme, `-j 2pi`. P is raw radians; phase turns are navigation only.",
                  "Excitation and outputs appear together in the classic whole-chain overview plots. Window plots use only stored samples in half-open registered windows; no interpolation or resampling.", "",
                  "## Interpretation boundary", "",
                  "Scientific interpretation was not performed. This evidence package does not classify SFQ delivery, count population outcomes, localize a failure, or assert a mechanism. Review is pending.", ""])
    (ROOT / "EVIDENCE_MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Create paired views and evidence-only result files")
    args = parser.parse_args()
    matrix = read_json(MATRIX)
    records = read_json(ANALYSIS / "EXECUTION.json")
    if records.get("status") != "ALL_FOUR_SOLVES_RAW_AND_INDEPENDENT_QA_PASS" or len(records.get("runs", [])) != 4:
        raise RuntimeError("all four solver receipts, mechanical QA, and independent raw arithmetic QA must pass before finalization")
    plot_qa = read_json(PLOT_QA)
    if plot_qa.get("status") != "PASS" or len(plot_qa.get("cases", [])) != 4:
        raise RuntimeError("standalone plot QA must PASS before comparison visualization")
    run_records = cases()
    compare_entries = []
    for signal in SUMMARY_SIGNALS:
        for window, bounds in COMPARE_WINDOWS.items():
            compare_entries.append(write_compare_plot(signal, window, bounds, run_records))
    terminal_deltas = make_terminal_deltas(run_records)
    comparison_qa = {"schema": "bvm-bq-cb-gap-comparison-qa-v1", "status": "PASS" if compare_entries else "FAIL",
                     "standalone_completed_first": True, "plot_count": len(compare_entries),
                     "entries": compare_entries,
                     "paired_subtraction_requires_exact_grid": True,
                     "mismatched_points": "blank in visual overlay; not interpolated",
                     "terminal_delta_rows": len(terminal_deltas), "scientific_interpretation_performed": False}
    write_json(ROOT / "qa" / "comparison_qa.json", comparison_qa)
    compdir = PLOTS / "comparison"
    links = "\n".join(f"<li><a href='{html.escape(Path(entry['path']).name)}'>{html.escape(entry['signal'])} — {html.escape(entry['window'])}</a> — cases: {', '.join(entry['run_ids'])}</li>" for entry in compare_entries)
    (compdir / "index.html").write_text("<!doctype html><html><head><meta charset='utf-8'><title>Four-run comparison</title><style>body{font:16px Arial;background:#111;color:#eee;margin:28px}a{color:#8ecbff}</style></head><body><h1>Four-run classic comparison</h1><p>Exact timestamp union, no interpolation/resampling. Paired numeric subtraction is only reported where stored grids match exactly. P is raw radians; -j 2pi is navigation only.</p><ul>" + links + "</ul><p><a href='../index.html'>Experiment plot index</a></p></body></html>", encoding="utf-8")
    write_result_brief(run_records, compare_entries, terminal_deltas)
    plot_manifest = read_json(ANALYSIS / "plot_manifest.json")
    write_evidence_manifests(run_records, plot_manifest, compare_entries, terminal_deltas)
    result = {"schema": "bvm-bq-cb-gap-result-v2", "experiment_id": matrix["experiment_id"],
              "status": "EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW",
              "parent_head": read_json(ANALYSIS / "PREFLIGHT_QA.json").get("parent_head"),
              "authorized_run_ids": [item["run_id"] for item in run_records],
              "physical_solve_count": 4, "raw_mechanical_qa": "PASS",
              "independent_raw_arithmetic_qa": "PASS",
              "cumulative_solver_invocations_including_v1_incident": 5,
              "v1_incident_data_included": False,
              "standalone_visualization_qa": plot_qa["status"],
              "comparison_visualization_qa": comparison_qa["status"],
              "scientific_interpretation_performed": False,
              "scientific_review_authorization_token": None, "automatic_follow_up": False,
              "summary_path": "RESULT_BRIEF.md", "evidence_manifest_path": "EVIDENCE_MANIFEST.md",
              "raw_handoff_manifest_path": "RAW_ANALYSIS_HANDOFF_MANIFEST.json",
              "finalized_at": now()}
    write_json(ROOT / "result.json", result)
    # These navigation links are intentionally simple; every chart is classic josim-plot2 output.
    index_lines = ["<!doctype html><html><head><meta charset='utf-8'><title>BVM-BQ-CB-GAP experiment plots</title><style>body{font:16px Arial;background:#111;color:#eee;margin:28px}a{color:#8ecbff}</style></head><body><h1>BVM → BQ → CB → ACC → GAP — classic plot index</h1><p>Classic josim-plot2 standalone views first, followed by exact-grid four-run comparison. Descriptive only; scientific interpretation not performed.</p><ul>"]
    index_lines.extend(f"<li><a href='{case['run_id']}/review.html'>{case['run_id']} classic review</a> · <a href='{case['run_id']}/stimulus.html'>stimulus + output</a></li>" for case in run_records)
    index_lines.extend(["<li><a href='comparison/index.html'>Four-run comparison plots</a></li>", "</ul></body></html>"])
    (PLOTS / "index.html").write_text("\n".join(index_lines), encoding="utf-8")
    print(json.dumps({"status": "PASS", "standalone_plot_count": plot_qa["plot_count"],
                      "comparison_plot_count": len(compare_entries), "terminal_delta_records": len(terminal_deltas),
                      "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
