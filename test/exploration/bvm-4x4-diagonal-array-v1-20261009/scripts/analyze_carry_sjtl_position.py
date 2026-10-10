#!/usr/bin/env python3
"""Raw-identity checks, registered arithmetic tables, and classic local plots for A034-A039."""

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
TASK = platform.CARRY_SJTL_POSITION_ANALYSIS
WINDOWS = ("ARRAY_FINAL_READ", "PRE_CLOCK", "BEFORE_CLOCK", "CLOCK_EDGE", "POST_CLOCK", "TOTAL")
RUN_IDS = tuple(item[0] for item in platform.CARRY_SJTL_POSITION_RUN_MATRIX)
ANALYSIS_FILES = (
    "CARRY_SJTL_POSITION_SUMMARY.json", "CARRY_SJTL_POSITION_SUMMARY.md",
    "CARRY_SJTL_POSITION_SIGNAL_METRICS.csv", "CARRY_SJTL_POSITION_SAME_JJ_PHASE_AREA.csv",
    "CARRY_SJTL_POSITION_STAGE_METRICS.csv", "CARRY_SJTL_POSITION_COMPARISON.csv",
    "CARRY_SJTL_POSITION_VISUALIZATION_QA.json",
)
BASE_RAW_SHA = {
    "A027_FULL_CB_CHAIN_ALL_CLOCK": "939e6024928be84df809532ecd8b716b815a9b96ea498324fc5c30b712100e46",
    "A028_FULL_CB_CHAIN_PAPER_CLOCK": "59ba22b2c31bd04993989c16a7c37d1e5bb904c078ef9db979657de81e604701",
    "A029_FULL_CB_CHAIN_3X3_CLOCK": "d943765ab3e47c1607ab3c29ff08a1088f2444dfd8a3266e9670a1d75d24ac0f",
    "A030_CARRY_POST_CB_SJTL_ALL_200": "027bb32757c1b426b2876ad2d694b6560cea58e6d54a733fd821408538ae166b",
    "A031_CARRY_POST_CB_SJTL_ALL_210": "c796e9b13024720fc1f5e3268e4174b4064343ab83a57bed3967ac4ed2c3dddf",
    "A032_CARRY_POST_CB_SJTL_PAPER_210": "439e9444964adf59043d11b39808c33fcd4f29d63d45835af4fa8cb5333546b5",
    "A033_CARRY_POST_CB_SJTL_3X3_210": "d4ed238cf7f7b113bb2e32c94b904d027ad5cf2c443502ae5183f3c4d3b1383c",
}
BASELINE_IDS = tuple(BASE_RAW_SHA.keys())


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_new(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite analysis artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")


def _csv_new(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _load_run(run_id: str, expected_sha: str | None = None) -> dict[str, Any]:
    run_dir = RUNS / run_id
    raw = run_dir / "raw.csv"
    before = sha(raw)
    if expected_sha and before != expected_sha:
        raise RuntimeError(f"raw SHA mismatch; refusing derived analysis: {run_id}")
    result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
    qa = json.loads((run_dir / "qa.json").read_text(encoding="utf-8"))
    chain_qa = json.loads((run_dir / "chain_qa.json").read_text(encoding="utf-8"))
    metrics = json.loads((run_dir / "metrics.json").read_text(encoding="utf-8"))
    probe = json.loads((run_dir / "probe_manifest.json").read_text(encoding="utf-8"))
    case_manifest = json.loads((run_dir / "case_manifest.json").read_text(encoding="utf-8"))
    plot_qa = json.loads((run_dir / "plot_qa.json").read_text(encoding="utf-8"))
    if (result.get("run_id") != run_id or result.get("raw_sha256") != before or
            result.get("artifact_status") != "VALID" or result.get("physical_solve_count") != 1 or
            qa.get("status") != "PASS" or chain_qa.get("status") != "PASS" or
            chain_qa.get("raw_sha256_after_analysis") != before or metrics.get("raw_sha256") != before):
        raise RuntimeError(f"run identity/QA/raw immutability mismatch: {run_id}")
    after = sha(raw)
    if after != before:
        raise RuntimeError(f"raw changed while reading QA artifacts: {run_id}")
    return {"run_id": run_id, "run_dir": run_dir, "raw_path": raw,
            "raw_sha256": before, "raw_bytes": raw.stat().st_size, "result": result,
            "qa": qa, "chain_qa": chain_qa, "metrics": metrics, "probe": probe,
            "plot_qa": plot_qa, "case_manifest": case_manifest}


def _indexes(run: dict[str, Any]) -> tuple[dict, dict, dict]:
    metrics = run["metrics"]
    wave = {(row["signal"], row["window"]): row for row in metrics["waveforms"]}
    current = {(row["signal"], row["window"]): row for row in metrics["currents"]}
    phase = {(row["phase_signal"], row["window"]): row for row in metrics["same_jj_phase_voltage"]}
    return wave, current, phase


def _value(index: dict, signal: str, window: str, field: str) -> Any:
    return index.get((signal, window), {}).get(field)


def _phase_fields(phase: dict, signal: str, window: str, prefix: str) -> dict[str, Any]:
    row = phase.get((signal, window), {})
    return {f"{prefix}_{field}": row.get(field) for field in (
        "phase_delta_rad", "phase_delta_rad_over_2pi_navigation",
        "positive_phase_variation_rad_navigation", "negative_phase_variation_rad_navigation",
        "positive_phase_variation_turns_navigation", "negative_phase_variation_turns_navigation",
        "voltage_area_v_s_same_jj_same_rows", "voltage_area_phi0_arithmetic",
        "phase_minus_area_turn_arithmetic")}


def _stage_rows(run: dict[str, Any]) -> list[dict[str, Any]]:
    wave, current, phase = _indexes(run)
    case = run["case_manifest"]["case"]
    sjtl_stages = platform._carry_sjtl_stages(case)
    sjtl_position = platform._carry_sjtl_position(case)
    rows: list[dict[str, Any]] = []
    for index in range(1, 7):
        diag = f"D{index}"
        array_cb = f"XCB_{diag}_L{len(platform.DIAGONALS[diag])}"
        carry_cb = f"XCB_CARRY_{diag}"
        t1 = f"XT1_{diag}"
        previous_t1 = f"XT1_D{index-1}"
        sjtl = f"XSJTL_CARRY_D{index}"
        for window in WINDOWS:
            row: dict[str, Any] = {"run_id": run["run_id"], "raw_sha256": run["raw_sha256"],
                                   "stage": diag, "window": window,
                                   "carry_sjtl_position": sjtl_position if index in sjtl_stages else "NONE",
                                   "carry_sjtl_instantiated": index in sjtl_stages,
                                   "dout_join_voltage_is_source_mixed": True}
            row.update(_phase_fields(phase, f"P(BJ1|{array_cb})", window, "array_cb_bj1"))
            row.update(_phase_fields(phase, f"P(BJ2|{array_cb})", window, "array_cb_bj2"))
            row.update(_phase_fields(phase, f"P(BJ11|{previous_t1})", window, "previous_t1_c_jj"))
            row.update(_phase_fields(phase, f"P(BJ1|{carry_cb})", window, "carry_cb_bj1"))
            row.update(_phase_fields(phase, f"P(BJ2|{carry_cb})", window, "carry_cb_bj2"))
            row.update(_phase_fields(phase, f"P(B_J1|{t1})", window, "t1_input_jj"))
            row.update(_phase_fields(phase, f"P(B_J11|{t1})", window, "t1_carry_jj"))
            row.update({
                "array_dout_branch_current_min_a": _value(current, f"I(V_CBU_A_D{index})", window, "min_a"),
                "array_dout_branch_current_max_a": _value(current, f"I(V_CBU_A_D{index})", window, "max_a"),
                "array_dout_branch_current_charge_c": _value(current, f"I(V_CBU_A_D{index})", window, "charge_c"),
                "previous_c_voltage_area_v_s": _value(wave, f"V(C_D{index-1})", window, "signed_area_v_s"),
                "carry_cb_input_voltage_area_v_s": _value(wave, f"V(CARRY_CB_IN_D{index})", window, "signed_area_v_s"),
                "carry_cb_output_voltage_area_v_s": _value(wave, f"V(CARRY_CB_OUT_D{index})", window, "signed_area_v_s"),
                "carry_cb_output_peak_time_s": _value(wave, f"V(CARRY_CB_OUT_D{index})", window, "time_of_max_s"),
                "join_voltage_signed_area_phi0_arithmetic": _value(wave, f"V(CBU_JOIN_D{index})", window, "signed_area_phi0_arithmetic"),
                "join_array_branch_current_charge_c": _value(current, f"I(V_CBU_A_D{index})", window, "charge_c"),
                "join_carry_branch_current_charge_c": _value(current, f"I(V_CBU_B_D{index})", window, "charge_c"),
                "t1_input_link_current_charge_c": _value(current, f"I(V_T1_LINK_D{index})", window, "charge_c"),
                "t1_input_voltage_area_v_s": _value(wave, f"V(T1_I_{diag})", window, "signed_area_v_s"),
                "sum_voltage_signed_area_phi0_arithmetic": _value(wave, f"V(S_{diag})", window, "signed_area_phi0_arithmetic"),
                "carry_voltage_signed_area_phi0_arithmetic": _value(wave, f"V(C_{diag})", window, "signed_area_phi0_arithmetic"),
                "t1_clock_peak_time_s": _value(wave, f"V(CLK_{diag})", window, "time_of_max_s"),
                "clock_start_configured": case["T1_CHAIN_CLK_START"],
            })
            if index in sjtl_stages:
                sjtl_sensor = (f"I(V_CARRY_SJTL_IN_D{index})" if sjtl_position == "POST_CB"
                               else f"I(V_CARRY_SJTL_OUT_D{index})")
                row.update(_phase_fields(phase, f"P(BJ1|{sjtl})", window, "carry_sjtl_bj1"))
                row.update({"carry_sjtl_input_voltage_area_v_s": _value(wave, f"V(CARRY_SJTL_IN_D{index})", window, "signed_area_v_s"),
                            "carry_sjtl_output_voltage_area_v_s": _value(wave, f"V(CARRY_SJTL_OUT_D{index})", window, "signed_area_v_s"),
                            "carry_sjtl_branch_current_charge_c": _value(current, sjtl_sensor, window, "charge_c"),
                            "carry_sjtl_branch_current_signal": sjtl_sensor})
            if index == 6:
                row["dff_input_voltage_area_v_s"] = _value(wave, "V(DFF_IN)", window, "signed_area_v_s")
                row["dff_output_voltage_area_v_s"] = _value(wave, "V(DFF_O)", window, "signed_area_v_s")
                row.update(_phase_fields(phase, "P(B1|XDFF)", window, "dff_b1"))
                row.update(_phase_fields(phase, "P(B2|XDFF)", window, "dff_b2"))
                row.update(_phase_fields(phase, "P(B7|XDFF)", window, "dff_b7"))
            rows.append(row)
    return rows


def _comparison_page(filename: str, title: str, run_ids: tuple[str, ...], signals: list[str],
                     run_data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    import pandas as pd

    target = PLOTS / "comparison" / filename
    if target.exists():
        raise FileExistsError(f"refusing to overwrite comparison page {target}")
    plotter = platform._plotter_module()
    chunks: list[str] = []
    records = []
    for run_id in run_ids:
        run = run_data[run_id]
        before = sha(run["raw_path"])
        if before != run["raw_sha256"]:
            raise RuntimeError(f"comparison raw identity mismatch: {run_id}")
        available = {item["label"] for item in run["probe"]["signals"]}
        selected = [signal for signal in signals if signal in available]
        if not selected:
            raise RuntimeError(f"no registered comparison probes present for {run_id}")
        times, columns, _ = platform.read_raw(run["raw_path"], set(selected), exact_header=False)
        frame = pd.DataFrame({"time": times, **{signal: list(columns[signal]) for signal in selected}})
        fig = plotter.seperate_combined_layout(frame, SimpleNamespace(subset=selected, jump="2pi"))
        fig.update_layout(title=f"{run_id} — native stored grid", title_font_size=20, template="plotly_dark")
        chunks.append("<section><h2>" + html.escape(run_id) + "</h2>" +
                      fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True}) + "</section>")
        after = sha(run["raw_path"])
        if before != after:
            raise RuntimeError(f"raw changed while plotting comparison: {run_id}")
        records.append({"run_id": run_id, "raw_sha256_before": before, "raw_sha256_after": after,
                        "sample_count": len(times), "signals": selected,
                        "signals_absent": sorted(set(signals) - set(selected)),
                        "native_stored_grid": True, "interpolation_or_resampling": False})
    target.parent.mkdir(parents=True, exist_ok=True)
    asset = Path(__import__("os").path.relpath(platform.PLOTLY_ASSET, target.parent)).as_posix()
    body = ("<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<script src=\"{html.escape(asset)}\"></script></head><body><main style=\"width:100%;max-width:none;margin:0 auto\">"
            f"<h1>{html.escape(title)}</h1><p>Classic josim-plot2.py sep_comb/dark/-j 2pi; each run uses its actual stored grid; no interpolation/resampling. Shared DOUT/JOIN voltage is not an array-only event count.</p>"
            + "\n".join(chunks) + "</main></body></html>\n")
    target.write_text(body, encoding="utf-8")
    text = target.read_text(encoding="utf-8")
    if "Plotly.newPlot" not in text or text.count(asset) != 1 or '"responsive": true' not in text:
        raise RuntimeError(f"comparison HTML QA failed: {target}")
    return {"path": target.relative_to(SERIES).as_posix(), "sha256": sha(target), "status": "PASS",
            "renderer": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi",
            "signals": signals, "runs": records, "shared_plotly_asset": asset,
            "shared_plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
            "plotly_js_embedded_once": False, "responsive": True,
            "interpolation_or_resampling": False}


def analyze_batch() -> dict[str, Any]:
    if tuple(item[0] for item in platform.CARRY_SJTL_POSITION_RUN_MATRIX) != RUN_IDS:
        raise RuntimeError("registered A034-A039 matrix changed")
    output_paths = [TASK / name for name in ANALYSIS_FILES]
    compare_specs = [
        ("A027_A030_A034_D2_POST_ALL.html", "A027 / A030 / A034 — D2 local POST-CB comparison",
         ("A027_FULL_CB_CHAIN_ALL_CLOCK", "A030_CARRY_POST_CB_SJTL_ALL_200", "A034_D2_ONLY_POST_CB_SJTL_ALL_200")),
        ("A028_A032_A035_D2_POST_PAPER.html", "A028 / A032 / A035 — paper-mask D2 local POST-CB comparison",
         ("A028_FULL_CB_CHAIN_PAPER_CLOCK", "A032_CARRY_POST_CB_SJTL_PAPER_210", "A035_D2_ONLY_POST_CB_SJTL_PAPER_200")),
        ("A030_A036_PRE_POST_ALL_200.html", "A030 / A036 — all-input POST-CB vs PRE-CB at 200 ps",
         ("A030_CARRY_POST_CB_SJTL_ALL_200", "A036_PRE_CB_SJTL_ALL_200")),
        ("A031_A037_PRE_POST_ALL_210.html", "A031 / A037 — all-input POST-CB vs PRE-CB at 210 ps",
         ("A031_CARRY_POST_CB_SJTL_ALL_210", "A037_PRE_CB_SJTL_ALL_210")),
        ("A032_A038_PRE_POST_PAPER_210.html", "A032 / A038 — paper-mask POST-CB vs PRE-CB at 210 ps",
         ("A032_CARRY_POST_CB_SJTL_PAPER_210", "A038_PRE_CB_SJTL_PAPER_210")),
        ("A033_A039_PRE_POST_3X3_210.html", "A033 / A039 — 3x3 POST-CB vs PRE-CB at 210 ps",
         ("A033_CARRY_POST_CB_SJTL_3X3_210", "A039_PRE_CB_SJTL_3X3_210")),
        ("A036_A037_CLOCK_200_210.html", "A036 / A037 — PRE-CB all-input, 200 ps vs 210 ps clock start",
         ("A036_PRE_CB_SJTL_ALL_200", "A037_PRE_CB_SJTL_ALL_210")),
    ]
    compare_paths = [PLOTS / "comparison" / name for name, _title, _ids in compare_specs]
    for path in (*output_paths, *compare_paths):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite analysis output: {path}")

    data: dict[str, dict[str, Any]] = {}
    for run_id, expected in BASE_RAW_SHA.items():
        data[run_id] = _load_run(run_id, expected)
    for run_id in RUN_IDS:
        data[run_id] = _load_run(run_id)
    for matrix in platform.CARRY_SJTL_POSITION_RUN_MATRIX:
        run_id, preset, rows, cols, clock, position, mask, _ref = matrix
        case = data[run_id]["case_manifest"]["case"]
        if (case["CASE"] != preset or case["ROW_BITS"] != rows or case["COL_BITS"] != cols or
                case["T1_CHAIN_CLK_START"] != clock or case["CARRY_SJTL_POSITION"] != position or
                case["CARRY_SJTL_STAGE_MASK"] != mask):
            raise RuntimeError(f"post-run effective config does not match registration: {run_id}")

    signal_rows: list[dict[str, Any]] = []
    phase_rows: list[dict[str, Any]] = []
    stage_rows: list[dict[str, Any]] = []
    run_records = []
    for run_id in RUN_IDS:
        run = data[run_id]
        signal_rows.extend({"run_id": run_id, "raw_sha256": run["raw_sha256"], **row}
                           for row in run["metrics"]["waveforms"] + run["metrics"]["currents"])
        phase_rows.extend({"run_id": run_id, "raw_sha256": run["raw_sha256"], **row}
                          for row in run["metrics"]["same_jj_phase_voltage"])
        stage_rows.extend(_stage_rows(run))
        plot_pages = run["plot_qa"].get("pages", [])
        run_records.append({"run_id": run_id, "case": run["result"]["case"],
                            "reference_run": next(item[-1] for item in platform.CARRY_SJTL_POSITION_RUN_MATRIX
                                                   if item[0] == run_id),
                            "configuration": {key: run["case_manifest"]["case"].get(key) for key in
                                              ("ROW_BITS", "COL_BITS", "CARRY_SJTL_POSITION",
                                               "CARRY_SJTL_STAGE_MASK", "T1_CHAIN_CLK_START")},
                            "raw_path": run["raw_path"].relative_to(SERIES).as_posix(),
                            "raw_sha256": run["raw_sha256"], "raw_bytes": run["raw_bytes"],
                            "sample_count": run["chain_qa"]["sample_count"],
                            "time_range_s": [run["chain_qa"]["time_start_s"], run["chain_qa"]["time_end_s"]],
                            "dt_min_s": run["chain_qa"]["dt_min_s"], "dt_max_s": run["chain_qa"]["dt_max_s"],
                            "artifact_status": run["result"]["artifact_status"], "qa_status": run["qa"]["status"],
                            "chain_qa_status": run["chain_qa"]["status"],
                            "probe_count": run["probe"]["signal_count"], "local_html_pages": plot_pages,
                            "solver": run["result"].get("solver_exit_code"),
                            "scientific_interpretation_performed": False})

    compare_signals = ["V(DOUT_D2)", "I(V_CBU_A_D2)", "V(C_D1)", "V(CARRY_CB_IN_D2)",
                       "V(CARRY_CB_OUT_D2)", "V(CARRY_SJTL_IN_D2)", "V(CARRY_SJTL_OUT_D2)",
                       "I(V_CARRY_SJTL_IN_D2)", "I(V_CARRY_SJTL_OUT_D2)", "P(BJ1|XCB_CARRY_D2)",
                       "V(BJ1|XCB_CARRY_D2)", "P(BJ2|XCB_CARRY_D2)", "V(BJ2|XCB_CARRY_D2)",
                       "P(BJ1|XSJTL_CARRY_D2)", "V(BJ1|XSJTL_CARRY_D2)", "V(CBU_JOIN_D2)",
                       "I(V_CBU_B_D2)", "I(V_T1_LINK_D2)", "V(T1_I_D2)",
                       "P(B_J1|XT1_D2)", "V(B_J1|XT1_D2)", "P(B_J11|XT1_D2)", "V(B_J11|XT1_D2)",
                       "V(S_D2)", "V(C_D2)", "V(DFF_IN)", "V(DFF_O)"]
    output_signals = [*(f"V(S_D{i})" for i in range(7)), *(f"V(C_D{i})" for i in range(7)),
                      "V(DFF_IN)", "V(DFF_O)"]
    clock_signals = [*(f"V(CLK_D{i})" for i in range(7)), "V(CLK_DFF)", *output_signals]
    comparisons = []
    for filename, title, ids in compare_specs:
        signals = clock_signals if filename.startswith("A036_A037") else compare_signals
        comparisons.append(_comparison_page(filename, title, ids, signals, data))

    comparison_rows = []
    pairs = [(item[-1], item[0]) for item in platform.CARRY_SJTL_POSITION_RUN_MATRIX]
    for baseline_id, candidate_id in pairs:
        left_wave, left_current, left_phase = _indexes(data[baseline_id])
        right_wave, right_current, right_phase = _indexes(data[candidate_id])
        signals = sorted({signal for signal, _window in set(left_wave) | set(right_wave) |
                          set(left_current) | set(right_current) | set(left_phase) | set(right_phase)})
        for signal in signals:
            for window in WINDOWS:
                if signal.startswith("P("):
                    left, right = left_phase.get((signal, window), {}), right_phase.get((signal, window), {})
                    fields = ("phase_delta_rad", "voltage_area_v_s_same_jj_same_rows",
                              "voltage_area_phi0_arithmetic", "phase_minus_area_turn_arithmetic",
                              "positive_phase_variation_rad_navigation", "negative_phase_variation_rad_navigation")
                elif signal.startswith("V("):
                    left, right = left_wave.get((signal, window), {}), right_wave.get((signal, window), {})
                    fields = ("min_v", "max_v", "time_of_min_s", "time_of_max_s", "signed_area_v_s",
                              "signed_area_phi0_arithmetic")
                else:
                    left, right = left_current.get((signal, window), {}), right_current.get((signal, window), {})
                    fields = ("min_a", "max_a", "peak_to_peak_a", "charge_c")
                for field in fields:
                    a, b = left.get(field), right.get(field)
                    comparison_rows.append({"baseline_run": baseline_id, "candidate_run": candidate_id,
                                            "signal": signal, "window": window, "metric": field,
                                            "baseline_value": a, "candidate_value": b,
                                            "candidate_minus_baseline": b-a
                                                if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None,
                                            "comparison_interpolation_or_resampling": False,
                                            "scientific_interpretation_performed": False})

    for name in ANALYSIS_FILES:
        path = TASK / name
        if path.exists():
            raise FileExistsError(f"analysis output collision: {path}")
    _csv_new(TASK / "CARRY_SJTL_POSITION_SIGNAL_METRICS.csv", signal_rows)
    _csv_new(TASK / "CARRY_SJTL_POSITION_SAME_JJ_PHASE_AREA.csv", phase_rows)
    _csv_new(TASK / "CARRY_SJTL_POSITION_STAGE_METRICS.csv", stage_rows)
    _csv_new(TASK / "CARRY_SJTL_POSITION_COMPARISON.csv", comparison_rows)
    summary = {"schema": "bvm4x4-carry-sjtl-position-summary-v1", "status": "MECHANICAL_QA_PASS",
               "batch_id": platform.CARRY_SJTL_POSITION_BATCH_ID,
               "physical_solve_count": 6, "runs": run_records,
               "baseline_references": {run_id: {"raw_path": data[run_id]["raw_path"].relative_to(SERIES).as_posix(),
                                                  "raw_sha256": data[run_id]["raw_sha256"],
                                                  "raw_bytes": data[run_id]["raw_bytes"],
                                                  "physical_solve_count": 0} for run_id in BASELINE_IDS},
               "windows": {run_id: data[run_id]["metrics"]["windows"] for run_id in RUN_IDS},
               "comparison_pairs": [{"baseline": left, "candidate": right} for left, right in pairs],
               "comparison_pages": comparisons,
               "tables": {"signals": (TASK / "CARRY_SJTL_POSITION_SIGNAL_METRICS.csv").relative_to(SERIES).as_posix(),
                          "same_jj_phase_area": (TASK / "CARRY_SJTL_POSITION_SAME_JJ_PHASE_AREA.csv").relative_to(SERIES).as_posix(),
                          "stage_metrics": (TASK / "CARRY_SJTL_POSITION_STAGE_METRICS.csv").relative_to(SERIES).as_posix(),
                          "comparisons": (TASK / "CARRY_SJTL_POSITION_COMPARISON.csv").relative_to(SERIES).as_posix()},
               "shared_dout_join_voltage": "source-mixed boundary; not an array-only event count",
               "phase_raw_units": "radians; /2pi navigation only",
               "integration": "actual stored timestamp rows, trapezoid, half-open windows, no interpolation",
               "event_classifier": None, "SFQ_count": "NOT_PERFORMED", "product_bit_decode": "NOT_PERFORMED",
               "physical_interpretation": "NOT_PERFORMED", "automatic_follow_up": False,
               "next_action": "STOP_AWAITING_USER_AND_CHATGPT_REVIEW"}
    _write_new(TASK / "CARRY_SJTL_POSITION_SUMMARY.json", json.dumps(summary, ensure_ascii=False, indent=2))
    lines = ["# Carry sJTL placement — mechanical evidence handoff", "",
             "- Status: `MECHANICAL_QA_PASS`; physical solves: 6; scientific interpretation: `NOT_PERFORMED`.",
             "- Raw files are immutable and all post-analysis SHA-256 values match their run manifests.",
             "- DOUT/JOIN voltages are mixed boundary signals and are not counted as array-only events.",
             "- JJ phase remains radians; same-JJ voltage integrals use the same stored rows/window. Positive/negative phase variation is descriptive arithmetic only.",
             "- No event classifier, bit decoder, parameter tuning, or follow-up solve was run.", "",
             "| Run | Position/mask | Clock | Raw bytes | Raw SHA-256 | QA |", "|---|---|---:|---:|---|---|"]
    for item in run_records:
        cfg = item["configuration"]
        lines.append(f"| {item['run_id']} | {cfg['CARRY_SJTL_POSITION']} / {cfg['CARRY_SJTL_STAGE_MASK']} | {cfg['T1_CHAIN_CLK_START']} | {item['raw_bytes']} | `{item['raw_sha256']}` | {item['qa_status']} |")
    lines.extend(["", "The stage and comparison CSVs report registered arithmetic only. No physical mechanism or success classification is assigned.", ""])
    _write_new(TASK / "CARRY_SJTL_POSITION_SUMMARY.md", "\n".join(lines))
    plot_qa = {"schema": "bvm4x4-carry-sjtl-position-visualization-qa-v1", "status": "PASS",
               "run_page_count": sum(len(item["local_html_pages"]) for item in run_records),
               "comparison_page_count": len(comparisons), "comparison_pages": comparisons,
               "renderer": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi",
               "shared_plotly_js": platform.PLOTLY_ASSET.relative_to(REPO).as_posix(),
               "html_in_package": False, "raw_modified": False,
               "interpolation_or_resampling": False, "scientific_interpretation_performed": False}
    _write_new(TASK / "CARRY_SJTL_POSITION_VISUALIZATION_QA.json", json.dumps(plot_qa, ensure_ascii=False, indent=2))
    return {"status": "MECHANICAL_QA_PASS", "summary_path": summary["tables"]["stage_metrics"],
            "physical_solve_count": 6, "raw_count": len(RUN_IDS), "comparison_page_count": len(comparisons),
            "scientific_interpretation_performed": False}


if __name__ == "__main__":
    raise SystemExit(0 if analyze_batch()["status"] == "MECHANICAL_QA_PASS" else 1)
