#!/usr/bin/env python3
"""Mechanical, actual-grid QA and classic paired plots for A021/A023 and A022/A024."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import os
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

import diagonal_platform as platform

SERIES = platform.SERIES
REPO = platform.REPO
TASK = SERIES / "analysis" / "cb-direct-d1-20261009"
RUNS = SERIES / "runs"
HANDOFF = SERIES / "handoff"
PRIOR_SOURCE_PACKAGE = (
    "bvm-4x4-diagonal-array-v1-20261009_delta_T1_CHAIN_A020_A022_20261009_source.zip",
    "52425d327a7d0b58a9e664f19eb95658b16aaca385321b651bb6153c751aef5c",
)
PRIOR_RAW_PACKAGES = {
    "A020_CHAIN_ALL_QUIET": (
        "bvm-4x4-diagonal-array-v1-20261009_delta_T1_CHAIN_A020_A022_20261009_A020_CHAIN_ALL_QUIET_raw.zip",
        "bf978aa2e9061dc7cbe5eabfe8643a494dd09dc37d4416b519408d4dd01d22e6",
        "ab13d65c671065fbfcd628ff7e4ffc0a9dc0506105bcd2a5bdefd91488aa763d"),
    "A021_CHAIN_ALL_GLOBAL_CLOCK": (
        "bvm-4x4-diagonal-array-v1-20261009_delta_T1_CHAIN_A020_A022_20261009_A021_CHAIN_ALL_GLOBAL_CLOCK_raw.zip",
        "21477be494024eb224c2fd4aec919638ab85fc03bf4cc80396d92aa127533f12",
        "85ffd3a00a6815115307d917c9b35d3b06dd7ac240c61ca8bfd47b957e975e9e"),
    "A022_CHAIN_PAPER_GLOBAL_CLOCK": (
        "bvm-4x4-diagonal-array-v1-20261009_delta_T1_CHAIN_A020_A022_20261009_A022_CHAIN_PAPER_GLOBAL_CLOCK_raw.zip",
        "8e18c88bf37d327b3d8e7064fc9b62a2d4a2f783dbc46c9234b45e08fec0cfb8",
        "2095fc87f129e844abfe21a0ccafb21e9ef2c72b67e7b6c34c8ca8f50935d9cb"),
}
PAIRINGS = (
    ("A021_CHAIN_ALL_GLOBAL_CLOCK", "A023_CB_DIRECT_D1_ALL_CLOCK", "A021_vs_A023_D1"),
    ("A022_CHAIN_PAPER_GLOBAL_CLOCK", "A024_CB_DIRECT_D1_PAPER_CLOCK", "A022_vs_A024_D1"),
)
WINDOWS = ("ARRAY_FINAL_READ", "PRE_CLOCK", "CLOCK_EDGE", "POST_CLOCK", "TOTAL")
COMMON_SIGNALS = (
    "V(DOUT_D0)", "V(DOUT_D1)", "P(BJ1|XCB_D1_L2)", "V(BJ1|XCB_D1_L2)",
    "V(C_D0)", "P(B_J10|XT1_D0)", "V(B_J10|XT1_D0)", "P(B_J11|XT1_D0)", "V(B_J11|XT1_D0)",
    "I(V_CBU_A_D1)", "I(V_CBU_B_D1)", "V(CBU_OUT_D1)", "I(V_T1_LINK_D1)", "V(T1_I_D1)",
    "P(B_J1|XT1_D1)", "V(B_J1|XT1_D1)", "P(B_J9|XT1_D1)", "V(B_J9|XT1_D1)",
    "P(B_J10|XT1_D1)", "V(B_J10|XT1_D1)", "P(B_J11|XT1_D1)", "V(B_J11|XT1_D1)",
    "V(S_D1)", "V(C_D1)", "V(CLK_D1)",
    *(signal for stage in range(2, 7) for signal in
      (f"V(CBU_OUT_D{stage})", f"V(T1_I_D{stage})", f"V(S_D{stage})", f"V(C_D{stage})",
       f"V(CLK_D{stage})", f"P(B_J11|XT1_D{stage})", f"V(B_J11|XT1_D{stage})")),
    "V(DFF_O)", "V(CLK_DFF)",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_new_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _run_records(run_id: str) -> dict[str, Any]:
    run_dir = RUNS / run_id
    result = read_json(run_dir / "result.json")
    qa = read_json(run_dir / "qa.json")
    raw_qa = read_json(run_dir / "chain_qa.json")
    metrics = read_json(run_dir / "metrics.json")
    probe = read_json(run_dir / "probe_manifest.json")
    plot_qa = read_json(run_dir / "plot_qa.json")
    raw = run_dir / "raw.csv"
    digest = sha(raw)
    if (result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
            result.get("raw_sha256") != digest or qa.get("status") != "PASS" or
            qa.get("raw_sha256_before_analysis") != digest or qa.get("raw_sha256_after_analysis") != digest or
            raw_qa.get("status") != "PASS" or raw_qa.get("raw_sha256_after_analysis") != digest or
            metrics.get("raw_sha256") != digest or plot_qa.get("status") != "PASS" or
            plot_qa.get("raw_sha256_after") != digest or probe.get("profile") != "t1_chain_focus"):
        raise RuntimeError(f"run artifact, mechanical QA, or raw identity failed: {run_id}")
    if run_id.startswith("A023_") or run_id.startswith("A024_"):
        case = read_json(run_dir / "case_manifest.json").get("case", {})
        if case.get("CBU_OVERRIDE_D1") != "CB_DIRECT" or case.get("FOCUS_STAGE") != "D1":
            raise RuntimeError(f"run case manifest lacks the registered D1 override/focus: {run_id}")
    for page in plot_qa.get("pages", []):
        path = SERIES / page["path"]
        if not path.is_file() or sha(path) != page.get("sha256"):
            raise RuntimeError(f"standalone classic plot hash mismatch: {run_id}/{page.get('path')}")
    return {"run_id": run_id, "run_dir": run_dir, "raw": raw, "raw_sha256": digest,
            "result": result, "qa": qa, "raw_qa": raw_qa, "metrics": metrics,
            "probe": probe, "plot_qa": plot_qa}


def _metric_indexes(metrics: dict[str, Any]) -> tuple[dict, dict, dict]:
    return (
        {(item["signal"], item["window"]): item for item in metrics["waveforms"]},
        {(item["signal"], item["window"]): item for item in metrics["currents"]},
        {(item["phase_signal"], item["window"]): item for item in metrics["same_jj_phase_voltage"]},
    )


def _record_for(indexes: tuple[dict, dict, dict], signal: str, window: str) -> dict[str, Any]:
    kind = signal[0]
    index = indexes[0] if kind == "V" else indexes[1] if kind == "I" else indexes[2]
    try:
        return index[(signal, window)]
    except KeyError as exc:
        raise RuntimeError(f"registered metric missing {signal} / {window}") from exc


def _flatten_metric(run_id: str, role: str, raw_sha: str, signal: str,
                    window: str, record: dict[str, Any]) -> dict[str, Any]:
    kind = signal[0]
    row: dict[str, Any] = {"run_id": run_id, "role": role, "raw_sha256": raw_sha,
                           "signal": signal, "window": window,
                           "interpolation_or_resampling": False}
    if kind == "V":
        row.update({"kind": "voltage", "unit": "V", "min": record["min_v"],
                    "max": record["max_v"], "p2p": record["peak_to_peak_v"],
                    "time_of_max_ps": record["time_of_max_s"] * 1e12,
                    "time_of_min_ps": record["time_of_min_s"] * 1e12,
                    "signed_area_v_s": record["signed_area_v_s"],
                    "signed_area_phi0_arithmetic": record["signed_area_phi0_arithmetic"]})
    elif kind == "I":
        row.update({"kind": "current", "unit": "A", "min": record["min_a"],
                    "max": record["max_a"], "p2p": record["peak_to_peak_a"],
                    "charge_c": record["charge_c"], "direction": record.get("direction")})
    else:
        row.update({"kind": "phase", "unit": "rad", "phase_delta_rad": record["phase_delta_rad"],
                    "phase_delta_turns_navigation": record["phase_delta_rad_over_2pi_navigation"],
                    "same_jj_voltage_area_v_s": record["voltage_area_v_s_same_jj_same_rows"],
                    "same_jj_voltage_area_phi0_arithmetic": record["voltage_area_phi0_arithmetic"],
                    "phase_minus_area_turn_residual": record["phase_minus_area_turn_arithmetic"]})
    return row


def _stored_grid(run: dict[str, Any], signal_set: set[str]) -> tuple[list[float], list[str]]:
    times, columns, header = platform.read_raw(run["raw"], signal_set)
    if set(columns) != signal_set or len(times) != run["raw_qa"]["sample_count"]:
        raise RuntimeError(f"selected comparison probes missing or sample count changed: {run['run_id']}")
    return list(times), header


def _existing_raw_reference_closure() -> list[dict[str, Any]]:
    source_name, source_sha = PRIOR_SOURCE_PACKAGE
    source_path = HANDOFF / source_name
    if not source_path.is_file() or sha(source_path) != source_sha:
        raise RuntimeError("A020-A022 source checkpoint package identity mismatch")
    source_qa = read_json(HANDOFF / f"{Path(source_name).stem}_PACKAGE_QA.json")
    if source_qa.get("status") != "PASS" or source_qa.get("package_sha256") != source_sha:
        raise RuntimeError("A020-A022 source checkpoint PACKAGE_QA mismatch")
    with zipfile.ZipFile(source_path) as archive:
        manifest = json.loads(archive.read("DELTA_MANIFEST.json"))
    if (manifest.get("head_commit") != "6364256321eb7c7437ef20ec14a3ba604e7b4d15" or
            manifest.get("base_commit") != "64b4e18e2d944fd982f5b200490f7b7575339b46" or
            manifest.get("package_group") != "source"):
        raise RuntimeError("A020-A022 source checkpoint lineage mismatch")
    refs = list(manifest.get("referenced_existing_raw_sha256", []))
    if len(refs) != 19 or len({item.get("run_id") for item in refs}) != 19:
        raise RuntimeError("A020-A022 source checkpoint must reference exactly A001-A019")
    for run_id, (name, expected_zip_sha, expected_raw_sha) in PRIOR_RAW_PACKAGES.items():
        path = HANDOFF / name
        qa_path = HANDOFF / f"{Path(name).stem}_PACKAGE_QA.json"
        qa = read_json(qa_path)
        if (not path.is_file() or sha(path) != expected_zip_sha or qa.get("status") != "PASS" or
                qa.get("package_sha256") != expected_zip_sha or qa.get("source_commit") != manifest["head_commit"]):
            raise RuntimeError(f"prior {run_id} package identity/QA mismatch")
        with zipfile.ZipFile(path) as archive:
            prior = json.loads(archive.read("DELTA_MANIFEST.json"))
        raw_path = f"test/exploration/{SERIES.name}/runs/{run_id}/raw.csv"
        if (prior.get("raw_sha256_by_run") != {run_id: expected_raw_sha} or
                prior.get("included_file_sha256", {}).get(raw_path) != expected_raw_sha):
            raise RuntimeError(f"prior {run_id} raw/package manifest mismatch")
        refs.append({"run_id": run_id, "raw_path": f"runs/{run_id}/raw.csv",
                     "raw_sha256": expected_raw_sha, "source_package_name": name,
                     "source_package_sha256": expected_zip_sha})
    if len(refs) != 22 or len({item["run_id"] for item in refs}) != 22:
        raise RuntimeError("prior raw-reference closure is not exactly A001-A022")
    return refs


def _write_pair_html(pair_name: str, baseline: dict[str, Any], candidate: dict[str, Any],
                     signals: list[str], grid_equal: bool) -> dict[str, Any]:
    target = SERIES / "plots" / "comparison" / f"{pair_name}.html"
    if target.exists():
        raise FileExistsError(f"refusing to overwrite comparison HTML: {target}")
    plotter = platform._plotter_module()
    sections, run_records = [], []
    for role, run in (("baseline", baseline), ("CB_DIRECT", candidate)):
        before = sha(run["raw"])
        times, columns, _header = platform.read_raw(run["raw"], set(signals))
        frame = pd.DataFrame({"time": times, **{signal: list(columns[signal]) for signal in signals}})
        fig = plotter.seperate_combined_layout(
            frame, SimpleNamespace(subset=signals, jump="2pi"))
        fig.update_layout(title=f"{run['run_id']} — {role}; {pair_name}", template="plotly_dark",
                          autosize=True, width=None)
        div = fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})
        if "Plotly.newPlot" not in div or '"responsive": true' not in div or "staticPlot" in div:
            raise RuntimeError(f"classic comparison plot did not retain interactive responsive config: {pair_name}")
        sections.append(f"<section><h2>{html.escape(run['run_id'])}</h2>"
                        f"<p>Raw SHA-256: <code>{run['raw_sha256']}</code></p>{div}</section>")
        after = sha(run["raw"])
        if before != after:
            raise RuntimeError(f"raw changed while plotting comparison: {run['run_id']}")
        run_records.append({"run_id": run["run_id"], "role": role, "raw_sha256_before": before,
                            "raw_sha256_after": after, "sample_count": len(times),
                            "signals": signals, "native_grid_only": True})
    asset_ref = Path(os.path.relpath(platform.PLOTLY_ASSET, target.parent)).as_posix()
    page = ("<!doctype html><html><head><meta charset=\"utf-8\"><style>html,body,main{width:100%;margin:0;padding:0;}"
            "body{background:#111;color:#eee;overflow-x:hidden;}main{max-width:none;width:100%;}section{padding:8px 2%;}"
            f"</style><script src=\"{html.escape(asset_ref)}\"></script></head><body><main><h1>{html.escape(pair_name)}</h1>"
            "<p>Classic josim-plot2 sep_comb/dark/-j 2pi. Cases are in separate sections on their native stored grids; "
            "no interpolation or resampling. Phase turns are navigation arithmetic, not event counts.</p>"
            f"<p>Exact stored grids identical: {str(grid_equal).lower()}.</p>" + "\n".join(sections) +
            "</main></body></html>\n")
    if page.count(asset_ref) != 1:
        raise RuntimeError(f"comparison page shared Plotly asset reference invalid: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(page, encoding="utf-8")
    if not target.is_file() or "Plotly.newPlot" not in page or '"responsive": true' not in page:
        raise RuntimeError(f"comparison HTML QA failed: {target}")
    return {"path": target.relative_to(SERIES).as_posix(), "sha256": sha(target),
            "status": "PASS", "shared_plotly_asset": asset_ref,
            "shared_plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
            "signals": signals, "runs": run_records,
            "exact_stored_grids_identical": grid_equal,
            "interpolation_or_resampling": False,
            "renderer": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi"}


def build_postrun_evidence(batch: dict[str, Any]) -> dict[str, Any]:
    run_ids = [item["run_id"] for item in batch.get("runs", [])]
    expected = ["A023_CB_DIRECT_D1_ALL_CLOCK", "A024_CB_DIRECT_D1_PAPER_CLOCK"]
    if run_ids != expected or batch.get("physical_solve_count_completed") != 2:
        raise RuntimeError(f"completed run set is not exactly A023/A024: {run_ids}")
    baseline_ids = [item[0] for item in PAIRINGS]
    all_runs = {run_id: _run_records(run_id) for run_id in (*baseline_ids, *expected)}
    table_rows, pair_rows, pair_records, plot_pages = [], [], [], []
    direct_jj_rows = []
    for baseline_id, candidate_id, pair_name in PAIRINGS:
        baseline, candidate = all_runs[baseline_id], all_runs[candidate_id]
        common = list(COMMON_SIGNALS)
        baseline_times, _ = _stored_grid(baseline, set(common))
        candidate_times, _ = _stored_grid(candidate, set(common))
        exact_grid = baseline_times == candidate_times
        indexes = {run["run_id"]: _metric_indexes(run["metrics"]) for run in (baseline, candidate)}
        for role, run in (("baseline", baseline), ("CB_DIRECT", candidate)):
            for item in run["metrics"]["waveforms"]:
                table_rows.append(_flatten_metric(run["run_id"], role, run["raw_sha256"],
                                                  item["signal"], item["window"], item))
            for item in run["metrics"]["currents"]:
                table_rows.append(_flatten_metric(run["run_id"], role, run["raw_sha256"],
                                                  item["signal"], item["window"], item))
            for item in run["metrics"]["same_jj_phase_voltage"]:
                table_rows.append(_flatten_metric(run["run_id"], role, run["raw_sha256"],
                                                  item["phase_signal"], item["window"], item))
        for signal in common:
            for window in WINDOWS:
                base_record = _record_for(indexes[baseline_id], signal, window)
                candidate_record = _record_for(indexes[candidate_id], signal, window)
                base_row = _flatten_metric(baseline_id, "baseline", baseline["raw_sha256"],
                                           signal, window, base_record)
                candidate_row = _flatten_metric(candidate_id, "CB_DIRECT", candidate["raw_sha256"],
                                                signal, window, candidate_record)
                numeric_field = ("phase_delta_rad" if signal.startswith("P(") else
                                 "charge_c" if signal.startswith("I(") else "signed_area_v_s")
                delta = None
                if exact_grid and numeric_field is not None:
                    delta = candidate_row.get(numeric_field) - base_row.get(numeric_field)
                pair_rows.append({"pair": pair_name, "signal": signal, "window": window,
                                  "unit": candidate_row["unit"],
                                  "baseline_run_id": baseline_id, "baseline_raw_sha256": baseline["raw_sha256"],
                                  "baseline_metrics": base_row,
                                  "candidate_run_id": candidate_id, "candidate_raw_sha256": candidate["raw_sha256"],
                                  "candidate_metrics": candidate_row,
                                  "exact_stored_grid_identical": exact_grid,
                                  "paired_delta_field": numeric_field if exact_grid else None,
                                  "paired_delta_value": delta,
                                  "interpolation_or_resampling": False})
        direct_metrics = _metric_indexes(candidate["metrics"])
        for signal in ("P(BJ1|XCBU_D1)", "P(BJ2|XCBU_D1)", "I(V_CBU_A_D1)",
                       "I(V_CBU_B_D1)", "V(CBU_JOIN_D1)", "V(CBU_OUT_D1)",
                       "I(V_T1_LINK_D1)", "V(T1_I_D1)", "V(C_D0)", "V(S_D1)", "V(C_D1)"):
            for window in WINDOWS:
                record = _record_for(direct_metrics, signal, window)
                direct_jj_rows.append({"pair": pair_name, "run_id": candidate_id,
                                       "raw_sha256": candidate["raw_sha256"],
                                       **_flatten_metric(candidate_id, "CB_DIRECT", candidate["raw_sha256"],
                                                         signal, window, record)})
        timing = next(item for item in candidate["metrics"]["stage_timing_descriptors"]
                      if item["stage"] == "D1")
        page = _write_pair_html(pair_name, baseline, candidate, common, exact_grid)
        plot_pages.append(page)
        pair_records.append({"pair": pair_name, "baseline_run_id": baseline_id,
                             "candidate_run_id": candidate_id,
                             "baseline_raw_sha256": baseline["raw_sha256"],
                             "candidate_raw_sha256": candidate["raw_sha256"],
                             "baseline_sample_count": baseline["raw_qa"]["sample_count"],
                             "candidate_sample_count": candidate["raw_qa"]["sample_count"],
                             "exact_stored_grid_identical": exact_grid,
                             "common_signal_count": len(common),
                             "d1_stage_timing_descriptor": timing,
                             "pairwise_differences_computed": exact_grid,
                             "phase_turns_are_event_counts": False,
                             "event_classifier": None,
                             "interpolation_or_resampling": False})

    metrics_path = TASK / "CB_DIRECT_D1_METRICS.csv"
    pair_path = TASK / "PAIRED_COMPARISON.csv"
    direct_path = TASK / "CB_DIRECT_D1_FOCUS.csv"
    for path, rows in ((metrics_path, table_rows), (pair_path, pair_rows), (direct_path, direct_jj_rows)):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite mechanical analysis: {path}")
        keys = list(dict.fromkeys(key for row in rows for key in row))
        with path.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=keys)
            writer.writeheader()
            writer.writerows(rows)

    runs_summary = []
    for run_id in expected:
        run = all_runs[run_id]
        runs_summary.append({"run_id": run_id, "case": run["result"].get("case"),
                             "raw_path": run["raw"].relative_to(SERIES).as_posix(),
                             "raw_sha256": run["raw_sha256"], "raw_bytes": run["raw"].stat().st_size,
                             "sample_count": run["raw_qa"]["sample_count"],
                             "time_range_s": [run["raw_qa"]["time_start_s"], run["raw_qa"]["time_end_s"]],
                             "dt_min_s": run["raw_qa"]["dt_min_s"], "dt_max_s": run["raw_qa"]["dt_max_s"],
                             "probe_count": run["raw_qa"]["probe_count"],
                             "artifact_status": run["result"]["artifact_status"],
                             "qa_status": run["qa"]["status"],
                             "deck_sha256": run["result"]["deck_sha256"],
                             "stimulus_sha256": run["result"]["stimulus_sha256"]})
    comparison = {"schema": "bvm-4x4-cb-direct-d1-mechanical-comparison-v1",
                  "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
                  "batch_id": platform.CB_DIRECT_D1_BATCH_ID,
                  "physical_solve_count": 2, "runs": runs_summary,
                  "pairs": pair_records,
                  "measurement_files": {"all_run_metrics": metrics_path.relative_to(SERIES).as_posix(),
                                        "paired_common_signals": pair_path.relative_to(SERIES).as_posix(),
                                        "CB_DIRECT_D1_focus": direct_path.relative_to(SERIES).as_posix()},
                  "plots": plot_pages,
                  "event_classifier": None, "SFQ_count": "NOT_CLASSIFIED",
                  "scientific_interpretation_performed": False, "automatic_follow_up": False}
    comparison_path = TASK / "CB_DIRECT_D1_COMPARISON.json"
    write_new_json(comparison_path, comparison)
    plot_qa = {"schema": "bvm-4x4-cb-direct-d1-comparison-plot-qa-v1",
               "status": "PASS", "raws_immutable": all(
                   item["runs"][0]["raw_sha256_before"] == item["runs"][0]["raw_sha256_after"] and
                   item["runs"][1]["raw_sha256_before"] == item["runs"][1]["raw_sha256_after"]
                   for item in plot_pages),
               "pages": plot_pages, "plotter_sha256": platform.sha256(platform.PLOTTER),
               "plotly_asset_sha256": platform.sha256(platform.PLOTLY_ASSET),
               "html_in_package": False, "scientific_interpretation_performed": False}
    plot_qa_path = TASK / "COMPARISON_PLOT_QA.json"
    write_new_json(plot_qa_path, plot_qa)

    result_brief = _result_brief(runs_summary, pair_records, comparison_path, plot_pages,
                                 metrics_path, pair_path, direct_path)
    brief_path = TASK / "RESULT_BRIEF.md"
    brief_path.write_text(result_brief, encoding="utf-8", newline="\n")
    evidence_manifest = _evidence_manifest(runs_summary, pair_records, comparison_path,
                                           plot_qa_path, metrics_path, pair_path, direct_path)
    evidence_path = TASK / "EVIDENCE_MANIFEST.md"
    evidence_path.write_text(evidence_manifest, encoding="utf-8", newline="\n")
    existing_refs = _existing_raw_reference_closure()
    raw_manifest = {"schema": "bvm-raw-analysis-handoff-v1",
                    "experiment_id": "bvm-4x4-cb-direct-d1-20261009",
                    "batch_id": platform.CB_DIRECT_D1_BATCH_ID,
                    "physical_solve_count": 2, "raw_is_immutable_solver_output": True,
                    "raw_modified_by_analysis": False, "time_grid": "native JoSIM stored samples",
                    "time_integrals": "actual timestamps, trapezoid, half-open windows; no interpolation",
                    "phase_raw_unit": "radians", "turns_are_event_counts": False,
                    "runs": [{"run_id": item["run_id"], "raw_path": item["raw_path"],
                              "raw_sha256": item["raw_sha256"], "raw_bytes": item["raw_bytes"],
                              "artifact_status": item["artifact_status"], "qa_status": item["qa_status"],
                              "plot_paths": [page["path"] for page in all_runs[item["run_id"]]["plot_qa"]["pages"]],
                              "package_group": f"{item['run_id']}_raw"} for item in runs_summary],
                    "existing_raw_references": existing_refs,
                    "scientific_interpretation_performed": False, "automatic_follow_up": False}
    raw_handoff_path = TASK / "RAW_ANALYSIS_HANDOFF_MANIFEST.json"
    write_new_json(raw_handoff_path, raw_manifest)
    return {"comparison_path": comparison_path.relative_to(SERIES).as_posix(),
            "comparison_sha256": sha(comparison_path),
            "comparison_qa_path": plot_qa_path.relative_to(SERIES).as_posix(),
            "comparison_qa_sha256": sha(plot_qa_path),
            "result_brief_path": brief_path.relative_to(SERIES).as_posix(),
            "evidence_manifest_path": evidence_path.relative_to(SERIES).as_posix()}


def _result_brief(runs: list[dict[str, Any]], pairs: list[dict[str, Any]],
                  comparison_path: Path, pages: list[dict[str, Any]],
                  all_metrics: Path, pair_metrics: Path, direct_metrics: Path) -> str:
    lines = ["# A023/A024 CB_DIRECT D1 evidence brief", "",
             "Status: `MECHANICAL_QA_PASS_AWAITING_USER_REVIEW`", "",
             "Scientific interpretation: `NOT PERFORMED`; SFQ/event count: `NOT_CLASSIFIED`.",
             "No parameter changes, additional sJTL, or follow-up solve.", "",
             "| Run | Raw bytes | Raw SHA-256 | Artifact / QA | Samples |", "|---|---:|---|---|---:|"]
    for item in runs:
        lines.append(f"| {item['run_id']} | {item['raw_bytes']} | `{item['raw_sha256']}` | "
                     f"{item['artifact_status']} / {item['qa_status']} | {item['sample_count']} |")
    lines.extend(["", "## Matched pair records", "",
                  "| Pair | Native time grids exactly equal | Common signals | D1 timing descriptor |",
                  "|---|---:|---:|---|"])
    for pair in pairs:
        lines.append(f"| {pair['pair']} | {pair['exact_stored_grid_identical']} | {pair['common_signal_count']} | "
                     f"`{pair['d1_stage_timing_descriptor']['timing_label']}` |")
    lines.extend(["", "Waveform/pulse candidates are descriptive navigation only. Cross-run pointwise subtraction was "
                  "performed only when the complete stored grids were exactly identical; otherwise each case is "
                  "reported on its native grid without interpolation. Same-JJ phase and voltage-area values are "
                  "paired within the same raw, junction, direction, and window.", "",
                  "Detailed actual-grid metrics:",
                  f"- All-run metrics: `{all_metrics.relative_to(SERIES).as_posix()}`",
                  f"- Paired common signals: `{pair_metrics.relative_to(SERIES).as_posix()}`",
                  f"- D1 CB/direct focus: `{direct_metrics.relative_to(SERIES).as_posix()}`",
                  f"- Comparison JSON: `{comparison_path.relative_to(SERIES).as_posix()}`",
                  "- Local HTML pages: " + ", ".join(f"`{page['path']}`" for page in pages), "",
                  "This artifact does not decide whether CB_DIRECT functionally succeeds or explain any observed difference.", ""])
    return "\n".join(lines)


def _evidence_manifest(runs: list[dict[str, Any]], pairs: list[dict[str, Any]],
                       comparison_path: Path, plot_qa_path: Path,
                       all_metrics: Path, pair_metrics: Path, direct_metrics: Path) -> str:
    rows = ["# CB_DIRECT D1 A023/A024 evidence manifest", "",
            "State: `MECHANICAL_QA_PASS_AWAITING_USER_REVIEW`  ",
            "Physical solves: exactly 2  ",
            "Scientific interpretation / event classification: `NOT_PERFORMED` / `NOT_CLASSIFIED`", "",
            "Canonical CB_0928 remains unchanged and is identified in each run's source manifest by SHA-256 "
            f"`{platform.SOURCE_SHA256['CB']}`. New D1 connectivity has two zero-volt current-sensor branches "
            "meeting at CBU_JOIN_D1; no isolation or extra sJTL is present.", "",
            "| Run | Raw bytes | Raw SHA-256 | Deck SHA-256 | Artifact / QA |", "|---|---:|---|---|---|"]
    for item in runs:
        rows.append(f"| {item['run_id']} | {item['raw_bytes']} | `{item['raw_sha256']}` | "
                    f"`{item['deck_sha256']}` | {item['artifact_status']} / {item['qa_status']} |")
    rows.extend(["", "Matched pairs: A021/A023 (ALL) and A022/A024 (PAPER).", "",
                 f"- Mechanical comparison: `{comparison_path.relative_to(SERIES).as_posix()}` (SHA-256 `{sha(comparison_path)}`).",
                 f"- Paired plot QA: `{plot_qa_path.relative_to(SERIES).as_posix()}` (SHA-256 `{sha(plot_qa_path)}`).",
                 f"- All-run metrics: `{all_metrics.relative_to(SERIES).as_posix()}`.",
                 f"- Paired common-signal metrics: `{pair_metrics.relative_to(SERIES).as_posix()}`.",
                 f"- CB_DIRECT D1 focus metrics: `{direct_metrics.relative_to(SERIES).as_posix()}`.",
                 "- HTML is local and excluded from DELTA ZIPs.",
                 "- A001-A022 raw is referenced by exact package/raw identity, not recopied.",
                 "- No physical result is upgraded to SFQ count or functional success.", ""])
    return "\n".join(rows)


if __name__ == "__main__":
    print("This module is invoked by cb_direct_d1_batch.py after the exact two-run matrix.")
