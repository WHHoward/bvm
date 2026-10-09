#!/usr/bin/env python3
"""Mechanical tables and classic plots for A027-A029; no bit/event classifier."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

import diagonal_platform as platform

SERIES = platform.SERIES
REPO = platform.REPO
RUNS = SERIES / "runs"
TASK = SERIES / "analysis" / "cb-carry-buffer-all-20261009"
PLOTS = SERIES / "plots"
RUNS_EXPECTED = tuple(item[0] for item in platform.CB_CARRY_BUFFER_ALL_RUN_MATRIX)
BASELINES = {
    "A027_FULL_CB_CHAIN_ALL_CLOCK": "A025_CARRY_CB_D1_ALL_CLOCK",
    "A028_FULL_CB_CHAIN_PAPER_CLOCK": "A026_CARRY_CB_D1_PAPER_CLOCK",
}
COMMON_D1_SIGNALS = (
    "V(DOUT_D0)", "V(T1_I_D0)", "V(C_D0)", "V(S_D0)",
    "P(B_J11|XT1_D0)", "V(B_J11|XT1_D0)",
    "V(DOUT_D1)", "P(BJ1|XCB_D1_L2)", "V(BJ1|XCB_D1_L2)",
    "V(CARRY_CB_IN_D1)", "I(V_CARRY_IN_D1)",
    "P(BJ1|XCB_CARRY_D1)", "V(BJ1|XCB_CARRY_D1)",
    "P(BJ2|XCB_CARRY_D1)", "V(BJ2|XCB_CARRY_D1)",
    "V(CARRY_CB_OUT_D1)", "I(V_CBU_B_D1)", "V(CBU_JOIN_D1)",
    "I(V_CBU_A_D1)", "V(T1_I_D1)", "I(V_T1_LINK_D1)",
    "P(B_J11|XT1_D1)", "V(B_J11|XT1_D1)", "V(S_D1)", "V(C_D1)", "V(CLK_D1)",
)
THEORY = {
    "A027_FULL_CB_CHAIN_ALL_CLOCK": {"diagonal_population": [1,2,3,4,3,2,1], "stage_inputs": [1,2,4,6,6,5,3],
                                      "carry": [0,1,2,3,3,2,1], "product": 225,
                                      "bits_lsb_to_msb": [1,0,0,0,0,1,1,1]},
    "A028_FULL_CB_CHAIN_PAPER_CLOCK": {"diagonal_population": [1,1,1,3,1,1,1], "stage_inputs": [1,1,1,3,2,2,2],
                                       "carry": [0,0,0,1,1,1,1], "product": 143,
                                       "bits_lsb_to_msb": [1,1,1,1,0,0,0,1]},
    "A029_FULL_CB_CHAIN_3X3_CLOCK": {"diagonal_population": [1,2,1,0,0,0,0], "stage_inputs": [1,2,2,1,0,0,0],
                                     "carry": [0,1,1,0,0,0,0], "product": 9,
                                     "bits_lsb_to_msb": [1,0,0,1,0,0,0,0]},
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def jnew(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite analysis table: {path}")
    if not rows:
        raise RuntimeError(f"analysis table is empty: {path}")
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                          if isinstance(value, (dict, list)) else value
                          for key, value in row.items()} for row in rows)


def _run_identity(run_id: str) -> dict[str, Any]:
    run_dir = RUNS / run_id
    raw = run_dir / "raw.csv"
    result, qa, raw_qa, metrics, probes, plot_qa = (
        jread(run_dir / name) for name in
        ("result.json", "qa.json", "chain_qa.json", "metrics.json", "probe_manifest.json", "plot_qa.json"))
    digest = sha(raw)
    if (result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
            result.get("raw_sha256") != digest or qa.get("status") != "PASS" or
            qa.get("raw_sha256_before_analysis") != digest or qa.get("raw_sha256_after_analysis") != digest or
            raw_qa.get("status") != "PASS" or raw_qa.get("raw_sha256_after_analysis") != digest or
            metrics.get("raw_sha256") != digest or plot_qa.get("status") != "PASS" or
            plot_qa.get("raw_sha256_after") != digest):
        raise RuntimeError(f"run QA/raw identity failure: {run_id}")
    for page in plot_qa.get("pages", []):
        page_path = SERIES / page["path"]
        if not page_path.is_file() or sha(page_path) != page.get("sha256"):
            raise RuntimeError(f"standalone HTML hash mismatch: {run_id}/{page.get('path')}")
    return {"run_id": run_id, "run_dir": run_dir, "raw": raw, "raw_sha256": digest,
            "raw_bytes": raw.stat().st_size, "result": result, "qa": qa, "raw_qa": raw_qa,
            "metrics": metrics, "probes": probes, "plot_qa": plot_qa,
            "case": jread(run_dir / "case_manifest.json")["case"]}


def _indexes(metrics: dict[str, Any]) -> tuple[dict, dict, dict]:
    return (
        {(row["signal"], row["window"]): row for row in metrics["waveforms"]},
        {(row["signal"], row["window"]): row for row in metrics["currents"]},
        {(row["phase_signal"], row["window"]): row for row in metrics["same_jj_phase_voltage"]},
    )


def _metric(indexes: tuple[dict, dict, dict], signal: str, window: str) -> dict[str, Any] | None:
    kind_index = 2 if signal.startswith("P(") else 1 if signal.startswith("I(") else 0
    return indexes[kind_index].get((signal, window))


def _common_pair_plot(name: str, run_a: dict[str, Any], run_b: dict[str, Any],
                      signals: list[str]) -> dict[str, Any]:
    target = PLOTS / "comparison" / name
    if target.exists():
        raise FileExistsError(f"refusing to overwrite comparison page: {target}")
    plotter = platform._plotter_module()
    times_by_run, frames, sections, qa_runs = [], [], [], []
    for run in (run_a, run_b):
        before = sha(run["raw"])
        times, columns, _header = platform.read_raw(run["raw"], set(signals))
        times_by_run.append(times)
        frame = pd.DataFrame({"time": times, **{signal: list(columns[signal]) for signal in signals}})
        fig = plotter.seperate_combined_layout(frame, SimpleNamespace(subset=signals, jump="2pi"))
        fig.update_layout(title=f"{run['run_id']} — D1 common-boundary comparison",
                          template="plotly_dark", autosize=True, width=None)
        div = fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True})
        if "Plotly.newPlot" not in div or '"responsive": true' not in div or "staticPlot" in div:
            raise RuntimeError(f"classic comparison plot QA failure: {name}/{run['run_id']}")
        sections.append(f"<section><h2>{html.escape(run['run_id'])}</h2>"
                        f"<p>Raw SHA-256: <code>{run['raw_sha256']}</code>; samples: {len(times)}</p>{div}</section>")
        after = sha(run["raw"])
        if before != after:
            raise RuntimeError(f"raw changed during plot generation: {run['run_id']}")
        qa_runs.append({"run_id": run["run_id"], "raw_sha256_before": before,
                        "raw_sha256_after": after, "sample_count": len(times),
                        "signals": signals, "native_stored_grid": True})
    grid_equal = times_by_run[0] == times_by_run[1]
    asset = Path(os.path.relpath(platform.PLOTLY_ASSET, target.parent)).as_posix()
    doc = ("<!doctype html><html><head><meta charset=\"utf-8\"><style>html,body,main{width:100%;margin:0;padding:0;}"
           "body{background:#111;color:#eee;overflow-x:hidden;}main{width:100%;max-width:none;}section{padding:8px 2%;}"
           f"</style><script src=\"{html.escape(asset)}\"></script></head><body><main><h1>{html.escape(name)}</h1>"
           "<p>Classic josim-plot2 sep_comb/dark/-j 2pi; same D1 signal schema, native raw samples, no interpolation. "
           "Phase turns are navigation arithmetic only, not event counts.</p>"
           f"<p>Exact grids equal: {str(grid_equal).lower()}.</p>" + "\n".join(sections) + "</main></body></html>\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, encoding="utf-8")
    if doc.count(asset) != 1 or "Plotly.newPlot" not in doc:
        raise RuntimeError(f"comparison HTML/shared asset check failed: {target}")
    return {"path": target.relative_to(SERIES).as_posix(), "sha256": sha(target), "status": "PASS",
            "renderer": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi",
            "shared_plotly_asset": asset, "shared_plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
            "signals": signals, "runs": qa_runs, "exact_stored_grid_equal": grid_equal,
            "interpolation_or_resampling": False}


def _build_analysis() -> dict[str, Any]:
    if any((TASK / name).exists() for name in (
            "FULL_CB_CHAIN_SUMMARY.json", "FULL_CB_CHAIN_STAGE_METRICS.csv",
            "FULL_CB_CHAIN_JJ_PHASE_AREA.csv", "FULL_CB_CHAIN_TIMING.csv",
            "FULL_CB_CHAIN_COMPARISON.csv", "RESULT_BRIEF.md", "EVIDENCE_MANIFEST.md",
            "RAW_ANALYSIS_HANDOFF_MANIFEST.json")):
        raise RuntimeError("full-chain analysis outputs already exist; refusing overwrite")
    run_records = list(platform.CB_CARRY_BUFFER_ALL_RUN_MATRIX)
    run_ids = [item[0] for item in run_records]
    runs = {run_id: _run_identity(run_id) for run_id in run_ids}
    for run_id, *_ in run_records:
        current_hash = sha(runs[run_id]["raw"])
        if current_hash != runs[run_id]["raw_sha256"]:
            raise RuntimeError(f"raw changed before table generation: {run_id}")

    metric_indexes = {run_id: _indexes(runs[run_id]["metrics"]) for run_id in run_ids}
    stage_rows, jj_rows, timing_rows, output_rows, signal_rows = [], [], [], [], []
    for run_id, preset, rows, cols, pop in run_records:
        run = runs[run_id]
        theory = THEORY[run_id]
        indexes = metric_indexes[run_id]
        for junction in run["metrics"]["same_jj_phase_voltage"]:
            jj_rows.append({"run_id": run_id, "case": preset, "raw_sha256": run["raw_sha256"], **junction})
        for timing in run["metrics"]["stage_timing_descriptors"]:
            timing_rows.append({"run_id": run_id, "case": preset, "raw_sha256": run["raw_sha256"],
                                "descriptor_type": "T1_STAGE", **timing})
        timing_rows.append({"run_id": run_id, "case": preset, "raw_sha256": run["raw_sha256"],
                            "descriptor_type": "DFF", **run["metrics"]["dff_timing_descriptor"]})
        for signal in run["probes"]["signals"]:
            label = signal["label"]
            for window in platform.CHAIN_WINDOWS_PS:
                metric = _metric(indexes, label, window)
                if metric is None:
                    continue
                signal_rows.append({"run_id": run_id, "case": preset, "raw_sha256": run["raw_sha256"],
                                    "label": label, "group": signal.get("group"), "window": window,
                                    "unit": metric.get("unit"),
                                    **{key: value for key, value in metric.items()
                                       if key not in {"signal", "phase_signal", "voltage_signal", "group", "window", "unit"}}})
        for index, diagonal in enumerate(platform.DIAGONALS):
            refs = {"diagonal_population_reference": theory["diagonal_population"][index],
                    "stage_inputs_reference": theory["stage_inputs"][index],
                    "carry_reference": theory["carry"][index]}
            for window in platform.CHAIN_WINDOWS_PS:
                stage = {"run_id": run_id, "case": preset, "raw_sha256": run["raw_sha256"],
                         "stage": diagonal, "window": window, **refs}
                labels = [f"V(DOUT_{diagonal})", f"V(T1_I_{diagonal})", f"V(S_{diagonal})", f"V(C_{diagonal})"]
                if index:
                    labels.extend((f"V(C_{diagonal[:1]}{index-1})", f"V(CARRY_CB_IN_{index})",
                                   f"V(CARRY_CB_OUT_{index})", f"V(CBU_JOIN_{index})",
                                   f"I(V_CBU_A_D{index})", f"I(V_CARRY_IN_D{index})",
                                   f"I(V_CBU_B_D{index})", f"I(V_T1_LINK_D{index})",
                                   f"P(BJ1|XCB_CARRY_D{index})", f"V(BJ1|XCB_CARRY_D{index})",
                                   f"P(BJ2|XCB_CARRY_D{index})", f"V(BJ2|XCB_CARRY_D{index})"))
                else:
                    labels.extend(("V(T1_I_D0)", "V(D0_JTL_IN_1)", "V(D0_JTL_OUT_1)", "I(V_T1_LINK_D0)"))
                for label in labels:
                    record = _metric(indexes, label, window)
                    if record is None:
                        continue
                    prefix = label.replace("(", "").replace(")", "").replace("|", "_").replace("-", "_")
                    for key, value in record.items():
                        if key in {"signal", "phase_signal", "voltage_signal", "window", "unit", "group"}:
                            continue
                        stage[f"{prefix}_{key}"] = value
                stage_rows.append(stage)
        for bit in [*(f"V(S_D{index})" for index in range(7)), "V(DFF_O)"]:
            for window in platform.CHAIN_WINDOWS_PS:
                record = _metric(indexes, bit, window)
                if record:
                    output_rows.append({"run_id": run_id, "case": preset, "raw_sha256": run["raw_sha256"],
                                        "theoretical_product_reference": theory["product"],
                                        "theoretical_bits_lsb_to_msb_reference": theory["bits"],
                                        "signal": bit, "window": window,
                                        "signed_area_phi0_arithmetic": record["signed_area_phi0_arithmetic"],
                                        "min_v": record["min_v"], "max_v": record["max_v"],
                                        "time_of_max_ps": record["time_of_max_s"]*1e12,
                                        "bit_decode": "NOT_PERFORMED"})

    compare_plots, compare_rows, grid_checks = [], [], {}
    pairs = (("A025_CARRY_CB_D1_ALL_CLOCK", "A027_FULL_CB_CHAIN_ALL_CLOCK", "A025_A027_D1_COMMON.html"),
             ("A026_CARRY_CB_D1_PAPER_CLOCK", "A028_FULL_CB_CHAIN_PAPER_CLOCK", "A026_A028_D1_COMMON.html"))
    for baseline_id, full_id, page_name in pairs:
        base_times, _, _ = platform.read_raw(runs[baseline_id]["raw"], set(COMMON_D1_SIGNALS))
        full_times, _, _ = platform.read_raw(runs[full_id]["raw"], set(COMMON_D1_SIGNALS))
        exact_grid = base_times == full_times
        grid_checks[page_name] = {"baseline": baseline_id, "full_chain": full_id,
                                  "exact_stored_grid_equal": exact_grid,
                                  "sample_count": [len(base_times), len(full_times)]}
        for label in COMMON_D1_SIGNALS:
            for window in platform.CHAIN_WINDOWS_PS:
                for role, rid in (("baseline", baseline_id), ("full_chain", full_id)):
                    rec = _metric(metric_indexes[rid], label, window)
                    if rec is None:
                        raise RuntimeError(f"D1 comparison metric absent: {rid}/{label}/{window}")
                    compare_rows.append({"comparison_page": page_name, "role": role, "run_id": rid,
                                         "raw_sha256": runs[rid]["raw_sha256"], "signal": label,
                                         "window": window, "unit": rec.get("unit"),
                                         "exact_grid_equal": exact_grid,
                                         **{key: val for key,val in rec.items()
                                            if key not in {"signal","phase_signal","voltage_signal","window","unit","group"}}})
        compare_plots.append(_common_pair_plot(page_name, runs[baseline_id], runs[full_id],
                                               list(COMMON_D1_SIGNALS)))

    for run_id in run_ids:
        if sha(runs[run_id]["raw"]) != runs[run_id]["raw_sha256"]:
            raise RuntimeError(f"raw changed during analysis: {run_id}")

    _write_csv(TASK / "FULL_CB_CHAIN_STAGE_METRICS.csv", stage_rows)
    _write_csv(TASK / "FULL_CB_CHAIN_JJ_PHASE_AREA.csv", jj_rows)
    _write_csv(TASK / "FULL_CB_CHAIN_TIMING.csv", timing_rows)
    _write_csv(TASK / "FULL_CB_CHAIN_SIGNAL_METRICS.csv", signal_rows)
    _write_csv(TASK / "FULL_CB_CHAIN_OUTPUT_METRICS.csv", output_rows)
    _write_csv(TASK / "FULL_CB_CHAIN_COMPARISON.csv", compare_rows)
    raw_records = {run_id: {"path": runs[run_id]["raw"].relative_to(SERIES).as_posix(),
                            "sha256": runs[run_id]["raw_sha256"], "bytes": runs[run_id]["raw_bytes"],
                            "sample_count": runs[run_id]["raw_qa"]["sample_count"],
                            "time_range_s": [runs[run_id]["raw_qa"]["time_start_s"],
                                             runs[run_id]["raw_qa"]["time_end_s"]],
                            "dt_min_s": runs[run_id]["raw_qa"]["dt_min_s"],
                            "dt_max_s": runs[run_id]["raw_qa"]["dt_max_s"],
                            "artifact_status": "VALID", "mechanical_qa": "PASS"}
                   for run_id in run_ids}
    summary = {"schema": "bvm-4x4-cb-carry-buffer-all-results-v1", "status": "PASS",
               "batch_id": BATCH_ID, "physical_solve_count": 3,
               "run_ids": run_ids, "raw_by_run": raw_records,
               "theoretical_vectors_reference_only": THEORY,
               "registered_windows_ps": {key:list(value) for key,value in platform.CHAIN_WINDOWS_PS.items()},
               "triplet_grid_checks": grid_checks,
               "comparison_plots": compare_plots,
               "stage_metrics_path": (TASK/"FULL_CB_CHAIN_STAGE_METRICS.csv").relative_to(SERIES).as_posix(),
               "jj_phase_area_path": (TASK/"FULL_CB_CHAIN_JJ_PHASE_AREA.csv").relative_to(SERIES).as_posix(),
               "timing_path": (TASK/"FULL_CB_CHAIN_TIMING.csv").relative_to(SERIES).as_posix(),
               "signal_metrics_path": (TASK/"FULL_CB_CHAIN_SIGNAL_METRICS.csv").relative_to(SERIES).as_posix(),
               "output_metrics_path": (TASK/"FULL_CB_CHAIN_OUTPUT_METRICS.csv").relative_to(SERIES).as_posix(),
               "comparison_table_path": (TASK/"FULL_CB_CHAIN_COMPARISON.csv").relative_to(SERIES).as_posix(),
               "phase_units": "raw radians; delta/(2*pi) navigation only",
               "integration": "actual stored timestamp rows; half-open windows; trapezoid; no interpolation",
               "bit_decode": "NOT_PERFORMED", "event_classifier": None,
               "sfq_count_inference": "NOT_PERFORMED", "scientific_interpretation_performed": False,
               "timestep_convergence": "UNKNOWN_NOT_RUN", "automatic_follow_up": False,
               "next_action": "STOP_AWAITING_USER_REVIEW"}
    jnew(TASK / "FULL_CB_CHAIN_SUMMARY.json", summary)
    brief = ["# A027-A029 full CB-only carry chain — mechanical evidence", "",
             f"- Batch: `{BATCH_ID}`; status: `PASS`; solves: 3; scientific interpretation: `NOT PERFORMED`.",
             "- Each D1-D6 input uses two measured branches, with only the previous T1 Carry passing through the added canonical CB_0928; JOIN connects directly to the current T1 input.",
             "- Artifact, raw, mechanical QA and classic plot QA passed for all three cases.",
             "- Theory vectors in the tables are references only. No bit decode, event count, or success verdict is assigned.",
             "- Same-JJ phase/voltage records use actual timestamps, exact half-open windows, and raw phase in radians.",
             "- Clock comparison uses the measured V(CLK_Dk)/V(CLK_DFF) peak and descriptive last-input lobe candidates only.",
             "- Time-step convergence: `UNKNOWN`; no new settings or follow-up solves authorized.", "",
             "| Run | Product reference | Raw bytes | Raw SHA-256 | samples | QA |",
             "|---|---:|---:|---|---:|---|"]
    for run_id, *_ in run_records:
        rr=raw_records[run_id]
        brief.append(f"| {run_id} | {THEORY[run_id]['product']} | {rr['bytes']} | `{rr['sha256']}` | {rr['sample_count']} | PASS |")
    brief.extend(["", "Tables: `FULL_CB_CHAIN_STAGE_METRICS.csv`, `FULL_CB_CHAIN_JJ_PHASE_AREA.csv`, `FULL_CB_CHAIN_TIMING.csv`, `FULL_CB_CHAIN_SIGNAL_METRICS.csv`, `FULL_CB_CHAIN_OUTPUT_METRICS.csv`, `FULL_CB_CHAIN_COMPARISON.csv`.",
                  "Plots: eight classic pages per run (full overview, carry propagation, D1-D6 focus) plus A025/A027 and A026/A028 D1 comparisons. HTML is local and excluded from ZIPs.",
                  "No CB isolation, SFQ count, bit-decode, or multiplier-success conclusion is made."])
    (TASK / "RESULT_BRIEF.md").write_text("\n".join(brief)+"\n",encoding="utf-8")
    evidence = ["# Evidence manifest", "", "This batch is governed by `docs/EXPERIMENT_CONTRACT.md`.",
                "", "| Run | Raw path | SHA-256 | Bytes | QA |", "|---|---|---|---:|---|"]
    for run_id in run_ids:
        rr=raw_records[run_id]
        evidence.append(f"| {run_id} | `{rr['path']}` | `{rr['sha256']}` | {rr['bytes']} | PASS |")
    evidence.extend(["", "Prior A001-A026 raw is referenced by exact hashes in the DELTA; not duplicated.",
                     "HTML remains local. Scientific interpretation is NOT PERFORMED; follow-up is NONE."])
    (TASK / "EVIDENCE_MANIFEST.md").write_text("\n".join(evidence)+"\n",encoding="utf-8")
    handoff = {"schema":"bvm-raw-analysis-handoff-v1", "analysis_id":"bvm-4x4-cb-carry-buffer-all-20261009",
               "analysis_scope":{"source_runs":run_ids,"read_only_raw":True,"solver_authorized":False,
                                 "raw_mutation":False,"circuit_parameter_or_timing_change":False,
                                 "windows_ps":{key:list(value) for key,value in platform.CHAIN_WINDOWS_PS.items()}},
               "raw_by_run":raw_records,"transformations":[],
               "visualization":{"renderer":"scripts/josim-plot2.py","layout":"sep_comb/dark/-j 2pi",
                                "html_local_only":True,"files":[page for run_id in run_ids
                                    for page in runs[run_id]["plot_qa"].get("pages",[])] + compare_plots},
               "scientific_interpretation_performed":False}
    jnew(TASK / "RAW_ANALYSIS_HANDOFF_MANIFEST.json", handoff)
    if any(sha(runs[run_id]["raw"]) != runs[run_id]["raw_sha256"] for run_id in run_ids):
        raise RuntimeError("raw changed after analysis or plotting")
    return {"status":"PASS","run_ids":run_ids,"physical_solve_count":3,
            "raw_sha256_by_run":{run_id:runs[run_id]["raw_sha256"] for run_id in run_ids},
            "triplet_grid_checks":grid_checks,"scientific_interpretation_performed":False}


def main() -> int:
    if sys.argv[1:] != ["--write"]:
        print("usage: analyze_cb_carry_buffer_all.py --write", file=sys.stderr)
        return 2
    try:
        result = _build_analysis()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(f"ANALYSIS_FAILURE_RAW_PRESERVED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
