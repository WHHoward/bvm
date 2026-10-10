#!/usr/bin/env python3
"""Registered arithmetic and classic common-signal comparisons for A040/A041."""

from __future__ import annotations

import csv
import hashlib
import html
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import diagonal_platform as platform

SERIES = platform.SERIES
REPO = platform.REPO
RUNS = platform.RUNS
PLOTS = platform.PLOTS
TASK = platform.CARRY_D3_TIMING_ANALYSIS
BASE_RUN = "A036_PRE_CB_SJTL_ALL_200"
RUN_IDS = (BASE_RUN, "A040_D3_PRE_CB_SJTL_0_ALL_200", "A041_D3_PRE_CB_SJTL_2_ALL_200")
WINDOWS = ("ARRAY_FINAL_READ", "PRE_CLOCK", "BEFORE_CLOCK", "CLOCK_EDGE", "POST_CLOCK", "TOTAL")
OUTPUTS = (
    "D3_CARRY_TIMING_SIGNAL_METRICS.csv",
    "D3_CARRY_TIMING_SAME_JJ_PHASE_AREA.csv",
    "D3_CARRY_TIMING_STAGE_METRICS.csv",
    "D3_CARRY_TIMING_SUMMARY.json",
    "D3_CARRY_TIMING_SUMMARY.md",
    "D3_CARRY_TIMING_VISUALIZATION_QA.json",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite analysis table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _load_run(run_id: str) -> dict[str, Any]:
    run_dir = RUNS / run_id
    raw = run_dir / "raw.csv"
    digest = sha(raw)
    result, qa, chain_qa, plot_qa, metrics, probe, case_manifest = (
        json.loads((run_dir / name).read_text(encoding="utf-8"))
        for name in ("result.json", "qa.json", "chain_qa.json", "plot_qa.json",
                     "metrics.json", "probe_manifest.json", "case_manifest.json"))
    if (result.get("run_id") != run_id or result.get("raw_sha256") != digest or
            result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
            qa.get("status") != "PASS" or qa.get("raw_sha256_before_analysis") != digest or
            qa.get("raw_sha256_after_analysis") != digest or chain_qa.get("status") != "PASS" or
            chain_qa.get("raw_sha256_after_analysis") != digest or plot_qa.get("status") != "PASS" or
            metrics.get("raw_sha256") != digest):
        raise RuntimeError(f"run identity or QA is not valid for immutable raw: {run_id}")
    if sha(raw) != digest:
        raise RuntimeError(f"raw changed during QA read: {run_id}")
    wave = {(row["signal"], row["window"]): row for row in metrics["waveforms"]}
    current = {(row["signal"], row["window"]): row for row in metrics["currents"]}
    phase = {(row["phase_signal"], row["window"]): row for row in metrics["same_jj_phase_voltage"]}
    return {"run_id": run_id, "run_dir": run_dir, "raw": raw, "raw_sha256": digest,
            "raw_bytes": raw.stat().st_size, "result": result, "qa": qa, "chain_qa": chain_qa,
            "plot_qa": plot_qa, "metrics": metrics, "probe": probe, "case": case_manifest["case"],
            "wave": wave, "current": current, "phase": phase}


def _phase_fields(run: dict[str, Any], signal: str, window: str, prefix: str) -> dict[str, Any]:
    row = run["phase"].get((signal, window), {})
    fields = ("phase_delta_rad", "positive_phase_variation_rad_navigation",
              "negative_phase_variation_rad_navigation", "phase_delta_rad_over_2pi_navigation",
              "positive_phase_variation_turns_navigation", "negative_phase_variation_turns_navigation",
              "voltage_area_v_s_same_jj_same_rows", "voltage_area_phi0_arithmetic",
              "phase_minus_area_turn_arithmetic", "sample_count", "interpolation_or_resampling")
    return {f"{prefix}_{field}": row.get(field) for field in fields}


def _signal_rows(run: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    waveform_rows = []
    current_rows = []
    for item in run["probe"]["signals"]:
        label = item["label"]
        if label.startswith("V("):
            for window in WINDOWS:
                record = run["wave"].get((label, window))
                if record:
                    waveform_rows.append({"run_id": run["run_id"], "raw_sha256": run["raw_sha256"],
                                          "signal": label, "group": item["group"], "window": window,
                                          **record})
        elif label.startswith("I("):
            for window in WINDOWS:
                record = run["current"].get((label, window))
                if record:
                    current_rows.append({"run_id": run["run_id"], "raw_sha256": run["raw_sha256"],
                                         "signal": label, "group": item["group"], "window": window,
                                         **record})
    return waveform_rows, current_rows


def _stage_rows(run: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    array_sjtl = run["case"]["SJTL_COUNT_D3"].split(",")
    carry_counts = platform._carry_sjtl_spec(run["case"])["counts_by_stage"]
    for stage_index in range(1, 7):
        stage = f"D{stage_index}"
        array_cb = f"XCB_{stage}_L{len(platform.DIAGONALS[stage])}"
        carry_cb = f"XCB_CARRY_{stage}"
        t1 = f"XT1_{stage}"
        prev = f"XT1_D{stage_index-1}"
        for window in WINDOWS:
            row: dict[str, Any] = {"run_id": run["run_id"], "raw_sha256": run["raw_sha256"],
                                   "stage": stage, "window": window,
                                   "carry_sjtl_position": run["case"]["CARRY_SJTL_POSITION"],
                                   "carry_sjtl_count": carry_counts[stage_index],
                                   "dout_join_voltage_is_source_mixed": True}
            row.update(_phase_fields(run, f"P(BJ1|{array_cb})", window, "array_cb_bj1"))
            row.update(_phase_fields(run, f"P(BJ2|{array_cb})", window, "array_cb_bj2"))
            row.update(_phase_fields(run, f"P(B_J11|{prev})", window, "previous_t1_carry_jj"))
            row.update(_phase_fields(run, f"P(BJ1|{carry_cb})", window, "carry_cb_bj1"))
            row.update(_phase_fields(run, f"P(BJ2|{carry_cb})", window, "carry_cb_bj2"))
            row.update(_phase_fields(run, f"P(B_J1|{t1})", window, "t1_input_jj"))
            row.update(_phase_fields(run, f"P(B_J11|{t1})", window, "t1_carry_jj"))
            for signal, key in ((f"V(C_D{stage_index-1})", "previous_carry"),
                                (f"V(CARRY_CB_IN_{stage})", "carry_cb_input"),
                                (f"V(CARRY_CB_OUT_{stage})", "carry_cb_output"),
                                (f"V(CBU_JOIN_{stage})", "join_voltage"),
                                (f"V(T1_I_{stage})", "t1_input_voltage"),
                                (f"V(S_{stage})", "sum_voltage"),
                                (f"V(C_{stage})", "carry_voltage")):
                data = run["wave"].get((signal, window), {})
                row[f"{key}_signed_area_v_s"] = data.get("signed_area_v_s")
                row[f"{key}_area_phi0_arithmetic"] = data.get("signed_area_phi0_arithmetic")
                row[f"{key}_time_of_max_s"] = data.get("time_of_max_s")
            for signal, key in ((f"I(V_CBU_A_D{stage_index})", "array_dout_branch"),
                                (f"I(V_CARRY_IN_D{stage_index})", "carry_input_branch"),
                                (f"I(V_CBU_B_D{stage_index})", "carry_to_join_branch"),
                                (f"I(V_T1_LINK_D{stage_index})", "t1_input_link")):
                data = run["current"].get((signal, window), {})
                row[f"{key}_charge_c"] = data.get("charge_c")
                row[f"{key}_min_a"] = data.get("min_a")
                row[f"{key}_max_a"] = data.get("max_a")
            for serial in range(1, carry_counts[stage_index] + 1):
                instance = platform._carry_sjtl_instance(stage_index, serial)
                row.update(_phase_fields(run, f"P(BJ1|{instance})", window, f"carry_sjtl_{serial}_bj1"))
            if stage_index == 6:
                for signal, key in (("V(DFF_IN)", "dff_input"), ("V(DFF_O)", "dff_output")):
                    data = run["wave"].get((signal, window), {})
                    row[f"{key}_signed_area_v_s"] = data.get("signed_area_v_s")
                    row[f"{key}_area_phi0_arithmetic"] = data.get("signed_area_phi0_arithmetic")
                for jj in ("B1", "B2", "B7"):
                    row.update(_phase_fields(run, f"P({jj}|XDFF)", window, f"dff_{jj.lower()}"))
            # Array internal topology is frozen; record its configured count vector.
            row["array_sjtl_count_vector_d3"] = ",".join(array_sjtl)
            rows.append(row)
    return rows


def _comparison_page(filename: str, title: str, signals: list[str], runs: dict[str, dict[str, Any]],
                    run_ids: tuple[str, ...] = RUN_IDS) -> dict[str, Any]:
    import pandas as pd

    target = PLOTS / "comparison" / filename
    if target.exists():
        raise FileExistsError(f"refusing to overwrite comparison page: {target}")
    plotter = platform._plotter_module()
    asset = Path(__import__("os").path.relpath(platform.PLOTLY_ASSET, target.parent)).as_posix()
    sections = []
    run_qa = []
    for run_id in run_ids:
        run = runs[run_id]
        before = sha(run["raw"])
        available = {item["label"] for item in run["probe"]["signals"]}
        if not set(signals).issubset(available):
            raise RuntimeError(f"comparison signal schema differs for {run_id}: {sorted(set(signals)-available)}")
        times, columns, _ = platform.read_raw(run["raw"], set(signals), exact_header=False)
        frame = pd.DataFrame({"time": times, **{signal: list(columns[signal]) for signal in signals}})
        fig = plotter.seperate_combined_layout(frame, SimpleNamespace(subset=signals, jump="2pi"))
        fig.update_layout(title=f"{run_id} — native stored grid", template="plotly_dark")
        sections.append("<section><h2>" + html.escape(run_id) + "</h2>" +
                        fig.to_html(full_html=False, include_plotlyjs=False,
                                    config={"responsive": True}) + "</section>")
        after = sha(run["raw"])
        if before != after or before != run["raw_sha256"]:
            raise RuntimeError(f"raw changed during comparison plotting: {run_id}")
        run_qa.append({"run_id": run_id, "raw_sha256_before": before, "raw_sha256_after": after,
                       "sample_count": len(times), "signals": signals,
                       "native_stored_grid": True, "interpolation_or_resampling": False})
    body = ("<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<script src=\"{html.escape(asset)}\"></script></head><body><main style=\"width:100%;max-width:none;margin:0 auto\">"
            f"<h1>{html.escape(title)}</h1><p>Classic josim-plot2.py sep_comb/dark/-j 2pi. "
            "Same preregistered signal schema; each run uses native timestamps with no interpolation or resampling. "
            "P(...) is radians; phase/2pi is navigation only.</p>" + "\n".join(sections) + "</main></body></html>\n")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    text = target.read_text(encoding="utf-8")
    if "Plotly.newPlot" not in text or text.count(asset) != 1 or '"responsive": true' not in text:
        raise RuntimeError(f"comparison HTML QA failed: {target}")
    return {"path": target.relative_to(SERIES).as_posix(), "sha256": sha(target),
            "raw_sha256_by_run": {run_id: runs[run_id]["raw_sha256"] for run_id in run_ids},
            "signals": signals, "renderer": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi",
            "shared_plotly_asset": asset, "shared_plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
            "html_embeds_plotly_js": False, "responsive": True,
            "native_stored_grids": True, "interpolation_or_resampling": False, "runs": run_qa}


def analyze() -> dict[str, Any]:
    target_paths = [TASK / name for name in OUTPUTS]
    for target in target_paths:
        if target.exists():
            raise FileExistsError(f"refusing to overwrite analysis result: {target}")
    runs = {run_id: _load_run(run_id) for run_id in RUN_IDS}
    baseline_sha = json.loads((RUNS / BASE_RUN / "metadata.json").read_text(encoding="utf-8"))["raw_sha256"]
    if runs[BASE_RUN]["raw_sha256"] != baseline_sha:
        raise RuntimeError("A036 raw SHA does not match its immutable metadata")

    signal_rows: list[dict[str, Any]] = []
    same_jj_rows: list[dict[str, Any]] = []
    stage_rows: list[dict[str, Any]] = []
    for run in runs.values():
        wave, currents = _signal_rows(run)
        signal_rows.extend(wave)
        signal_rows.extend(currents)
        for row in run["metrics"]["same_jj_phase_voltage"]:
            same_jj_rows.append({"run_id": run["run_id"], "raw_sha256": run["raw_sha256"], **row})
        stage_rows.extend(_stage_rows(run))
    _write_csv_new(TASK / OUTPUTS[0], signal_rows)
    _write_csv_new(TASK / OUTPUTS[1], same_jj_rows)
    _write_csv_new(TASK / OUTPUTS[2], stage_rows)

    focus = ["V(DOUT_D3)", "I(V_CBU_A_D3)",
             "P(BJ1|XCB_D3_L4)", "V(BJ1|XCB_D3_L4)",
             "P(BJ2|XCB_D3_L4)", "V(BJ2|XCB_D3_L4)",
             "V(C_D2)", "P(B_J11|XT1_D2)", "V(B_J11|XT1_D2)",
             "I(V_CARRY_IN_D3)", "P(BJ1|XCB_CARRY_D3)", "V(BJ1|XCB_CARRY_D3)",
             "P(BJ2|XCB_CARRY_D3)", "V(BJ2|XCB_CARRY_D3)",
             "V(CARRY_CB_IN_D3)", "V(CARRY_CB_OUT_D3)", "I(V_CBU_B_D3)",
             "V(CBU_JOIN_D3)", "I(V_T1_LINK_D3)", "V(T1_I_D3)",
             "P(B_J1|XT1_D3)", "V(B_J1|XT1_D3)",
             "P(B_J11|XT1_D3)", "V(B_J11|XT1_D3)", "V(CLK_D3)", "V(S_D3)", "V(C_D3)"]
    extended_jjs = [signal for jj in ("B_J1", "B_J2", "B_J9", "B_J10", "B_J11")
                    for signal in (f"P({jj}|XT1_D3)", f"V({jj}|XT1_D3)")]
    carry = ["V(C_D2)", "P(B_J11|XT1_D2)", "V(B_J11|XT1_D2)",
             "I(V_CARRY_IN_D3)", "P(BJ1|XCB_CARRY_D3)", "V(BJ1|XCB_CARRY_D3)",
             "P(BJ2|XCB_CARRY_D3)", "V(BJ2|XCB_CARRY_D3)",
             "V(CARRY_CB_IN_D3)", "V(CARRY_CB_OUT_D3)", "I(V_CBU_B_D3)",
             "V(CBU_JOIN_D3)", "V(T1_I_D3)", "I(V_T1_LINK_D3)"]
    full_chain = [*(f"V(DOUT_D{i})" for i in range(7)),
                  *(f"V(CBU_JOIN_D{i})" for i in range(1, 7)),
                  *(f"V(T1_I_D{i})" for i in range(7)),
                  *(f"V(S_D{i})" for i in range(7)),
                  *(f"V(C_D{i})" for i in range(7)), "V(DFF_IN)", "V(DFF_O)"]
    final = [*(f"V(S_D{i})" for i in range(7)), *(f"V(C_D{i})" for i in range(7)),
             "V(DFF_IN)", "V(CLK_DFF)", "V(DFF_O)", "I(V_DFF_DATA)"]
    compare_specs = (
        ("A036_A040_A041_D3_FOCUS.html", "A036 / A040 / A041 — D3 focus", focus),
        ("A040_A041_D3_EXTENDED_JJ.html", "A040 / A041 — D3 five-JJ focus (A036 lacks four probes)", extended_jjs),
        ("A036_A040_A041_D3_CARRY_PATH.html", "A036 / A040 / A041 — D3 Carry path and JOIN", carry),
        ("A036_A040_A041_FULL_CHAIN.html", "A036 / A040 / A041 — D0-D6 chain boundaries", full_chain),
        ("A036_A040_A041_OUTPUTS_DFF.html", "A036 / A040 / A041 — Sum / Carry / DFF boundaries", final),
    )
    comparison_qa = [_comparison_page(filename, title, signals, runs,
                                      ("A040_D3_PRE_CB_SJTL_0_ALL_200", "A041_D3_PRE_CB_SJTL_2_ALL_200")
                                      if filename == "A040_A041_D3_EXTENDED_JJ.html" else RUN_IDS)
                     for filename, title, signals in compare_specs]
    for run in runs.values():
        if sha(run["raw"]) != run["raw_sha256"]:
            raise RuntimeError(f"raw hash changed during analysis: {run['run_id']}")
    summary = {"schema": "bvm4x4-d3-carry-timing-summary-v1",
               "batch_id": platform.CARRY_D3_TIMING_BATCH_ID,
               "status": "MECHANICAL_QA_PASS_AWAITING_USER_REVIEW",
               "runs": [{"run_id": run_id, "raw_path": (runs[run_id]["raw"].relative_to(SERIES).as_posix()),
                         "raw_sha256": runs[run_id]["raw_sha256"], "raw_bytes": runs[run_id]["raw_bytes"],
                         "sample_count": runs[run_id]["qa"]["sample_count"],
                         "time_range_s": runs[run_id]["qa"]["time_range_s"],
                         "qa_status": runs[run_id]["qa"]["status"],
                         "carry_sjtl_count_by_stage": runs[run_id]["case"].get("CARRY_SJTL_COUNT_BY_STAGE", "")}
                        for run_id in RUN_IDS],
               "windows": json.loads((TASK / "METRIC_SPEC.json").read_text(encoding="utf-8"))["windows"],
               "tables": {"signal_metrics": (TASK / OUTPUTS[0]).relative_to(SERIES).as_posix(),
                          "same_jj_phase_area": (TASK / OUTPUTS[1]).relative_to(SERIES).as_posix(),
                          "stage_metrics": (TASK / OUTPUTS[2]).relative_to(SERIES).as_posix()},
               "comparison_pages": comparison_qa,
               "phase_unit": "raw radians; turns=rad/(2*pi) navigation only",
               "integration": "actual stored timestamp grid; trapezoid; no interpolation or resampling",
               "shared_dout_voltage": "DOUT/JOIN shared boundary; not an array-only event count",
               "event_classification_performed": False, "scientific_interpretation_performed": False,
               "automatic_follow_up": False}
    (TASK / OUTPUTS[3]).write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = ["# D3 Carry timing A040/A041 — evidence-only summary", "",
          "- Physical solve count: 2 new solves; A036 is a read-only baseline reference.",
          "- Mechanical QA only; scientific interpretation and event/SFQ classification: NOT PERFORMED.",
          "- DOUT and JOIN share a node; DOUT voltage is not treated as an array-only event count.",
          "- `P(...)` is raw radians; phase/2π is navigation arithmetic only.", "",
          "| Run | D3 Carry sJTL count | Raw bytes | Samples | Raw SHA-256 | QA |",
          "|---|---:|---:|---:|---|---|"]
    for run_id in RUN_IDS:
        run = runs[run_id]
        md.append(f"| {run_id} | {platform._carry_sjtl_count_at(run['case'], 3)} | {run['raw_bytes']} | "
                  f"{run['qa']['sample_count']} | `{run['raw_sha256']}` | {run['qa']['status']} |")
    md.extend(["", "## Registered arithmetic", "",
               "See the stage and same-JJ tables for exact-window P/V cross-checks, branch-current arithmetic, "
               "output areas, and stored-grid time descriptors. No pulse count, mechanism, or product-bit verdict "
               "is assigned by this report.", "", "## Visualizations", ""])
    md.extend(f"- {Path(item['path']).name}: `{item['sha256']}`" for item in comparison_qa)
    (TASK / OUTPUTS[4]).write_text("\n".join(md) + "\n", encoding="utf-8")
    viz_qa = {"schema": "bvm4x4-d3-carry-timing-visualization-qa-v1", "status": "PASS",
              "raw_sha256_by_run": {run_id: runs[run_id]["raw_sha256"] for run_id in RUN_IDS},
              "comparison_pages": comparison_qa,
              "standalone_run_pages": [{"run_id": run_id, "pages": runs[run_id]["plot_qa"]["pages"],
                                         "raw_sha256": runs[run_id]["raw_sha256"]}
                                        for run_id in RUN_IDS[1:]],
              "renderer": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi",
              "html_package_policy": "exclude HTML from evidence ZIP; keep local",
              "scientific_interpretation_performed": False}
    (TASK / OUTPUTS[5]).write_text(json.dumps(viz_qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(analyze(), ensure_ascii=False, indent=2))
