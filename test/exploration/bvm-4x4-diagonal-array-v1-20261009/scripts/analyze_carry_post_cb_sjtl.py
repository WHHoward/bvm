#!/usr/bin/env python3
"""Mechanical raw QA and descriptive summaries for A030-A033; never invokes JoSIM."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import diagonal_platform as platform

SERIES = platform.SERIES
REPO = platform.REPO
RUNS = platform.RUNS
PLOTS = platform.PLOTS
TASK = platform.CARRY_POST_CB_SJTL_ANALYSIS
SUMMARY = TASK / "CARRY_POST_CB_SJTL_SUMMARY.json"
SIGNALS_CSV = TASK / "CARRY_POST_CB_SJTL_SIGNAL_METRICS.csv"
PHASE_CSV = TASK / "CARRY_POST_CB_SJTL_SAME_JJ_PHASE_AREA.csv"
STAGE_CSV = TASK / "CARRY_POST_CB_SJTL_STAGE_METRICS.csv"
COMPARISON_CSV = TASK / "CARRY_POST_CB_SJTL_COMPARISON.csv"
PLOT_QA = TASK / "CARRY_POST_CB_SJTL_VISUALIZATION_QA.json"
SUMMARY_MD = TASK / "CARRY_POST_CB_SJTL_SUMMARY.md"
WINDOWS = ("ARRAY_FINAL_READ", "PRE_CLOCK", "BEFORE_CLOCK", "CLOCK_EDGE", "POST_CLOCK", "TOTAL")
RUNS_EXPECTED = tuple(item[0] for item in platform.CARRY_POST_CB_SJTL_RUN_MATRIX)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def jread(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_new(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite analysis artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _csv_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite analysis table: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def _windows(clock_start_ps: float) -> dict[str, tuple[float, float]]:
    return {"ARRAY_FINAL_READ": (110.0, 121.0),
            "PRE_CLOCK": (121.0, clock_start_ps),
            "BEFORE_CLOCK": (0.0, clock_start_ps),
            "CLOCK_EDGE": (clock_start_ps, clock_start_ps + 5.0),
            "POST_CLOCK": (clock_start_ps + 5.0, 300.0),
            "TOTAL": (0.0, 300.0)}


def _probe_lookup(probe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["label"]: item for item in probe["signals"]}


def _measure_run(run_id: str) -> dict[str, Any]:
    run_dir = RUNS / run_id
    raw = run_dir / "raw.csv"
    result = jread(run_dir / "result.json")
    run_qa = jread(run_dir / "qa.json")
    chain_qa = jread(run_dir / "chain_qa.json")
    probe = jread(run_dir / "probe_manifest.json")
    case_manifest = jread(run_dir / "case_manifest.json")
    runner_metrics = jread(run_dir / "metrics.json")
    before = sha(raw)
    if (result.get("run_id") != run_id or result.get("raw_sha256") != before or
            result.get("artifact_status") != "VALID" or run_qa.get("status") != "PASS" or
            chain_qa.get("status") != "PASS" or chain_qa.get("raw_sha256_after_analysis") != before):
        raise RuntimeError(f"run identity/QA/raw SHA mismatch: {run_id}")
    case_post_count = int(case_manifest.get("case", {}).get("CARRY_POST_CB_SJTL_COUNT", "0"))
    probe_post_count = int(probe.get("carry_post_cb_sjtl_count", 0))
    if case_post_count not in {0, 1} or probe_post_count != case_post_count:
        raise RuntimeError(f"post-CB-sJTL configuration/probe identity mismatch: {run_id}")

    labels = {item["label"] for item in probe["signals"]}
    times, columns, header = platform.read_raw(raw, labels, exact_header=True)
    after = sha(raw)
    if before != after:
        raise RuntimeError(f"raw changed during mechanical analysis: {run_id}")
    if len(times) < 2 or any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"raw time grid is not strictly increasing: {run_id}")
    dt = [right-left for left, right in zip(times, times[1:])]
    clock_ps = float(platform._time_ps(case_manifest["case"]["T1_CHAIN_CLK_START"]))
    windows_ps = _windows(clock_ps)
    windows = {}
    indices = {}
    for name in WINDOWS:
        idx = platform._window_indices(times, name, windows_ps)
        if len(idx) < 2:
            raise RuntimeError(f"fewer than two stored samples in {run_id} / {name}")
        indices[name] = idx
        windows[name] = {"start_ps": windows_ps[name][0], "end_ps": windows_ps[name][1],
                         "boundary_rule": "[start,end)", "sample_count": len(idx),
                         "first_stored_s": times[idx[0]], "last_stored_s": times[idx[-1]]}

    descriptors = _probe_lookup(probe)
    waveform_rows: list[dict[str, Any]] = []
    current_rows: list[dict[str, Any]] = []
    phase_rows: list[dict[str, Any]] = []
    wave_index: dict[tuple[str, str], dict[str, Any]] = {}
    phase_index: dict[tuple[str, str], dict[str, Any]] = {}
    for label, meta in descriptors.items():
        if label.startswith("V("):
            values = columns[label]
            is_shared_dout = label.startswith("V(DOUT_D") and label != "V(DOUT_D0)"
            for window, idx in indices.items():
                hi = max(idx, key=lambda i: values[i])
                lo = min(idx, key=lambda i: values[i])
                area = platform._trapz(times, values, idx)
                row = {"run_id": run_id, "signal": label, "group": meta.get("group"), "window": window,
                       "min_v": values[lo], "max_v": values[hi], "peak_to_peak_v": values[hi]-values[lo],
                       "time_of_min_ps": times[lo]*1e12, "time_of_max_ps": times[hi]*1e12,
                       "signed_area_v_s": area, "signed_area_phi0_arithmetic": area/platform.PHI0,
                       "interpolation_or_resampling": False,
                       "measurement_semantics": meta.get("measurement_semantics")}
                if is_shared_dout:
                    row["shared_node_voltage_not_array_only"] = True
                    row["event_count_interpretation"] = "NOT_PERFORMED"
                if (not is_shared_dout and
                        (label.startswith("V(CBU_") or label.startswith("V(CARRY_") or
                         label.startswith("V(T1_I_") or label.startswith("V(C_") or
                         label.startswith("V(S_") or label.startswith("V(DFF_") or
                         label.startswith("V(CLK_"))):
                    row["descriptive_lobe_candidates"] = platform._voltage_lobe_candidates(times, values, idx)
                waveform_rows.append(row)
                wave_index[(label, window)] = row
        elif label.startswith("I("):
            values = columns[label]
            for window, idx in indices.items():
                hi = max(idx, key=lambda i: values[i])
                lo = min(idx, key=lambda i: values[i])
                charge = platform._trapz(times, values, idx)
                row = {"run_id": run_id, "signal": label, "group": meta.get("group"), "window": window,
                       "min_a": values[lo], "max_a": values[hi], "peak_to_peak_a": values[hi]-values[lo],
                       "time_of_min_ps": times[lo]*1e12, "time_of_max_ps": times[hi]*1e12,
                       "charge_c": charge, "direction": meta.get("direction", "JoSIM element-reference direction"),
                       "interpolation_or_resampling": False}
                current_rows.append(row)
        elif label.startswith("P("):
            voltage_label = "V(" + label[2:]
            if voltage_label not in columns:
                raise RuntimeError(f"same-JJ voltage counterpart missing: {label} -> {voltage_label}")
            phase = platform._unwrap(columns[label])
            voltage = columns[voltage_label]
            for window, idx in indices.items():
                delta = phase[idx[-1]]-phase[idx[0]]
                area = platform._trapz(times, voltage, idx)
                row = {"run_id": run_id, "phase_signal": label, "voltage_signal": voltage_label,
                       "group": meta.get("group"), "window": window, "sample_count": len(idx),
                       "phase_delta_rad": delta,
                       "phase_delta_rad_over_2pi_navigation": delta/(2*math.pi),
                       "voltage_area_v_s_same_jj_same_rows": area,
                       "voltage_area_phi0_arithmetic": area/platform.PHI0,
                       "phase_minus_area_turn_arithmetic": delta/(2*math.pi)-area/platform.PHI0,
                       "interpolation_or_resampling": False}
                phase_rows.append(row)
                phase_index[(label, window)] = row

    if before != sha(raw):
        raise RuntimeError(f"raw changed at end of summary analysis: {run_id}")
    raw_qa = {"status": "PASS", "raw_sha256": before, "raw_sha256_after_analysis": after,
              "sample_count": len(times), "header_count": len(header),
              "time_start_s": times[0], "time_end_s": times[-1],
              "dt_min_s": min(dt), "dt_max_s": max(dt), "strictly_monotonic": True,
              "probe_count": len(labels), "windows": windows,
              "interpolation_or_resampling": False}
    return {"run_id": run_id, "raw_sha256": before, "raw_bytes": raw.stat().st_size,
            "case": case_manifest["case"], "stimulus": case_manifest["stimulus"],
            "topology": case_manifest["effective_topology"], "result": result, "qa": run_qa,
            "chain_qa": chain_qa, "raw_qa": raw_qa, "probe": probe,
            "stage_timing_descriptors": runner_metrics.get("stage_timing_descriptors", []),
            "dff_timing_descriptor": runner_metrics.get("dff_timing_descriptor", {}),
            "waveforms": waveform_rows, "currents": current_rows, "phase_area": phase_rows,
            "wave_index": wave_index, "current_index": {(r["signal"], r["window"]): r for r in current_rows},
            "phase_index": phase_index}


def _stage_rows(run: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    wave = run["wave_index"]
    current = run["current_index"]
    phase = run["phase_index"]

    def p(signal: str, window: str, field: str) -> Any:
        return phase.get((signal, window), {}).get(field)

    def v(signal: str, window: str, field: str) -> Any:
        return wave.get((signal, window), {}).get(field)

    def i(signal: str, window: str, field: str) -> Any:
        return current.get((signal, window), {}).get(field)

    def candidate_times(signal: str, window: str) -> list[float]:
        record = wave.get((signal, window), {})
        candidates = record.get("descriptive_lobe_candidates", {}).get("candidates", [])
        return [float(item["time_ps"]) for item in candidates]

    for index in range(1, 7):
        d = f"D{index}"
        last_cb = f"XCB_{d}_L{len(platform.DIAGONALS[d])}"
        carry_cb = f"XCB_CARRY_{d}"
        carry_sjtl = f"XSJTL_CARRY_{d}"
        t1 = f"XT1_{d}"
        for window in WINDOWS:
            cb_peak = v(f"V(CARRY_CB_OUT_{d})", window, "time_of_max_ps")
            sjtl_peak = v(f"V(CARRY_SJTL_OUT_{d})", window, "time_of_max_ps")
            row = {"run_id": run["run_id"], "raw_sha256": run["raw_sha256"], "stage": d, "window": window,
                   "array_cb_bj1_phase_delta_rad": p(f"P(BJ1|{last_cb})", window, "phase_delta_rad"),
                   "array_cb_bj1_voltage_area_v_s": p(f"P(BJ1|{last_cb})", window, "voltage_area_v_s_same_jj_same_rows"),
                   "array_cb_bj1_voltage_area_phi0_arithmetic": p(f"P(BJ1|{last_cb})", window, "voltage_area_phi0_arithmetic"),
                   "array_cb_bj2_phase_delta_rad": p(f"P(BJ2|{last_cb})", window, "phase_delta_rad"),
                   "array_cb_bj2_voltage_area_v_s": p(f"P(BJ2|{last_cb})", window, "voltage_area_v_s_same_jj_same_rows"),
                   "dout_to_join_branch_charge_c": i(f"I(V_CBU_A_{index})", window, "charge_c"),
                   "previous_t1_c_voltage_max_v": v(f"V(C_{index-1})", window, "max_v"),
                   "previous_t1_c_voltage_max_time_ps": v(f"V(C_{index-1})", window, "time_of_max_ps"),
                   "carry_cb_bj1_phase_delta_rad": p(f"P(BJ1|{carry_cb})", window, "phase_delta_rad"),
                   "carry_cb_bj1_voltage_area_v_s": p(f"P(BJ1|{carry_cb})", window, "voltage_area_v_s_same_jj_same_rows"),
                   "carry_cb_bj1_voltage_area_phi0_arithmetic": p(f"P(BJ1|{carry_cb})", window, "voltage_area_phi0_arithmetic"),
                   "carry_cb_bj2_phase_delta_rad": p(f"P(BJ2|{carry_cb})", window, "phase_delta_rad"),
                   "carry_cb_bj2_voltage_area_v_s": p(f"P(BJ2|{carry_cb})", window, "voltage_area_v_s_same_jj_same_rows"),
                   "carry_cb_out_voltage_max_time_ps": cb_peak,
                   "carry_sjtl_bj1_phase_delta_rad": p(f"P(BJ1|{carry_sjtl})", window, "phase_delta_rad"),
                   "carry_sjtl_bj1_voltage_area_v_s": p(f"P(BJ1|{carry_sjtl})", window, "voltage_area_v_s_same_jj_same_rows"),
                   "carry_sjtl_bj1_voltage_area_phi0_arithmetic": p(f"P(BJ1|{carry_sjtl})", window, "voltage_area_phi0_arithmetic"),
                   "carry_sjtl_out_voltage_max_time_ps": sjtl_peak,
                   "carry_cb_to_sjtl_positive_max_time_offset_ps": (sjtl_peak-cb_peak)
                       if sjtl_peak is not None and cb_peak is not None else None,
                   "carry_sjtl_input_current_charge_c": i(f"I(V_CARRY_SJTL_IN_{index})", window, "charge_c"),
                   "carry_sjtl_output_current_charge_c": i(f"I(V_CBU_B_{index})", window, "charge_c"),
                   "join_shared_voltage_signed_area_phi0_arithmetic": v(f"V(CBU_JOIN_{d})", window, "signed_area_phi0_arithmetic"),
                   "join_shared_voltage_lobe_candidate_times_ps_json": json.dumps(candidate_times(f"V(CBU_JOIN_{d})", window)),
                   "join_shared_voltage_adjacent_candidate_intervals_ps_json": json.dumps([
                       right-left for left, right in zip(candidate_times(f"V(CBU_JOIN_{d})", window),
                                                         candidate_times(f"V(CBU_JOIN_{d})", window)[1:])]),
                   "join_candidate_semantics": "descriptive extrema of mixed DOUT/Carry JOIN voltage only; not event or SFQ count",
                   "join_from_t1_input_link_current_charge_c": i(f"I(V_T1_LINK_{index})", window, "charge_c"),
                   "t1_bj1_phase_delta_rad": p(f"P(B_J1|{t1})", window, "phase_delta_rad"),
                   "t1_bj1_voltage_area_v_s": p(f"P(B_J1|{t1})", window, "voltage_area_v_s_same_jj_same_rows"),
                   "t1_bj1_voltage_area_phi0_arithmetic": p(f"P(B_J1|{t1})", window, "voltage_area_phi0_arithmetic"),
                   "t1_bj11_phase_delta_rad": p(f"P(B_J11|{t1})", window, "phase_delta_rad"),
                   "t1_bj11_voltage_area_v_s": p(f"P(B_J11|{t1})", window, "voltage_area_v_s_same_jj_same_rows"),
                   "t1_input_voltage_max_time_ps": v(f"V(T1_I_{d})", window, "time_of_max_ps"),
                   "sum_voltage_area_phi0_arithmetic": v(f"V(S_{d})", window, "signed_area_phi0_arithmetic"),
                   "carry_voltage_area_phi0_arithmetic": v(f"V(C_{d})", window, "signed_area_phi0_arithmetic"),
                   "clock_voltage_max_time_ps": v(f"V(CLK_{d})", window, "time_of_max_ps"),
                   "shared_node_area_is_not_array_event_count": True}
            rows.append(row)
    return rows


def _comparison_rows(runs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    pairs = (("A027_FULL_CB_CHAIN_ALL_CLOCK", "A030_CARRY_POST_CB_SJTL_ALL_200"),
             ("A027_FULL_CB_CHAIN_ALL_CLOCK", "A031_CARRY_POST_CB_SJTL_ALL_210"),
             ("A028_FULL_CB_CHAIN_PAPER_CLOCK", "A032_CARRY_POST_CB_SJTL_PAPER_210"),
             ("A029_FULL_CB_CHAIN_3X3_CLOCK", "A033_CARRY_POST_CB_SJTL_3X3_210"))
    rows = []
    signals = ("V(CARRY_CB_OUT_D2)", "V(CARRY_SJTL_OUT_D2)", "V(CBU_JOIN_D2)",
               "V(T1_I_D2)", "V(S_D2)", "V(C_D2)", "V(DFF_IN)", "V(DFF_O)",
               "I(V_CBU_A_D2)", "I(V_CARRY_SJTL_IN_D2)", "I(V_CBU_B_D2)",
               "P(BJ1|XCB_CARRY_D2)", "P(BJ2|XCB_CARRY_D2)",
               "P(BJ1|XSJTL_CARRY_D2)", "P(B_J1|XT1_D2)", "P(B_J11|XT1_D2)")
    for baseline_id, candidate_id in pairs:
        base, candidate = runs[baseline_id], runs[candidate_id]
        for signal in signals:
            phase_signal = signal.startswith("P(")
            for window in WINDOWS:
                if phase_signal:
                    left = base["phase_index"].get((signal, window), {})
                    right = candidate["phase_index"].get((signal, window), {})
                    for field in ("phase_delta_rad", "voltage_area_v_s_same_jj_same_rows",
                                  "voltage_area_phi0_arithmetic", "phase_minus_area_turn_arithmetic"):
                        rows.append({"baseline_run": baseline_id, "candidate_run": candidate_id,
                                     "signal": signal, "window": window, "metric": field,
                                     "baseline_value": left.get(field), "candidate_value": right.get(field),
                                     "candidate_minus_baseline": (right.get(field)-left.get(field))
                                        if isinstance(left.get(field), (int, float)) and isinstance(right.get(field), (int, float)) else None,
                                     "unit": "rad" if field == "phase_delta_rad" else
                                            "V*s" if field == "voltage_area_v_s_same_jj_same_rows" else
                                            "Phi0 arithmetic"})
                elif signal.startswith("V("):
                    left = base["wave_index"].get((signal, window), {})
                    right = candidate["wave_index"].get((signal, window), {})
                    for field in ("min_v", "max_v", "time_of_min_ps", "time_of_max_ps",
                                  "signed_area_v_s", "signed_area_phi0_arithmetic"):
                        rows.append({"baseline_run": baseline_id, "candidate_run": candidate_id,
                                     "signal": signal, "window": window, "metric": field,
                                     "baseline_value": left.get(field), "candidate_value": right.get(field),
                                     "candidate_minus_baseline": (right.get(field)-left.get(field))
                                        if isinstance(left.get(field), (int, float)) and isinstance(right.get(field), (int, float)) else None,
                                     "unit": "ps" if field.endswith("_ps") else
                                            "V" if field.endswith("_v") else "V*s/Phi0 arithmetic"})
                else:
                    left = base["current_index"].get((signal, window), {})
                    right = candidate["current_index"].get((signal, window), {})
                    for field in ("min_a", "max_a", "time_of_min_ps", "time_of_max_ps", "charge_c"):
                        rows.append({"baseline_run": baseline_id, "candidate_run": candidate_id,
                                     "signal": signal, "window": window, "metric": field,
                                     "baseline_value": left.get(field), "candidate_value": right.get(field),
                                     "candidate_minus_baseline": (right.get(field)-left.get(field))
                                        if isinstance(left.get(field), (int, float)) and isinstance(right.get(field), (int, float)) else None,
                                     "unit": "ps" if field.endswith("_ps") else "A" if field.endswith("_a") else "C"})
    return rows


def _comparison_page(filename: str, title: str, run_ids: tuple[str, ...], signals: list[str],
                     run_data: dict[str, dict[str, Any]]) -> dict[str, Any]:
    import pandas as pd
    from diagonal_platform import _plotter_module

    target = PLOTS / "comparison" / filename
    if target.exists():
        raise FileExistsError(f"refusing to overwrite comparison page {target}")
    plotter = _plotter_module()
    figures = []
    records = []
    for run_id in run_ids:
        raw = RUNS / run_id / "raw.csv"
        before = sha(raw)
        if before != run_data[run_id]["raw_sha256"]:
            raise RuntimeError(f"comparison raw identity mismatch: {run_id}")
        available = {item["label"] for item in run_data[run_id]["probe"]["signals"]}
        run_signals = [signal for signal in signals if signal in available]
        if not run_signals:
            raise RuntimeError(f"comparison page has no available registered signals for {run_id}")
        times, columns, _ = platform.read_raw(raw, set(run_signals), exact_header=False)
        frame = pd.DataFrame({"time": times, **{signal: list(columns[signal]) for signal in run_signals}})
        fig = plotter.seperate_combined_layout(frame, SimpleNamespace(subset=run_signals, jump="2pi"))
        fig.update_layout(title=f"{run_id} — native stored time grid", title_font_size=20, template="plotly_dark")
        figures.append("<section><h2>" + html.escape(run_id) + "</h2>" +
                       fig.to_html(full_html=False, include_plotlyjs=False, config={"responsive": True}) + "</section>")
        after = sha(raw)
        if after != before:
            raise RuntimeError(f"raw changed during comparison page generation: {run_id}")
        records.append({"run_id": run_id, "raw_path": raw.relative_to(SERIES).as_posix(),
                        "raw_sha256_before": before, "raw_sha256_after": after,
                        "sample_count": len(times), "signals": run_signals,
                        "requested_signals_absent_in_run": sorted(set(signals)-set(run_signals)),
                        "native_stored_grid": True, "interpolation_or_resampling": False})
    target.parent.mkdir(parents=True, exist_ok=True)
    asset = Path(__import__("os").path.relpath(platform.PLOTLY_ASSET, target.parent)).as_posix()
    content = ("<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
               f"<script src=\"{html.escape(asset)}\"></script></head><body><main style=\"width:100%;max-width:none;margin:0 auto\">"
               f"<h1>{html.escape(title)}</h1><p>Classic josim-plot2 sep_comb/dark/-j 2pi. Each run is rendered on its own actual stored grid; no interpolation or resampling. DOUT/JOIN voltage is not an array-only event count.</p>"
               + "\n".join(figures) + "</main></body></html>\n")
    target.write_text(content, encoding="utf-8")
    page = {"path": target.relative_to(SERIES).as_posix(), "sha256": sha(target),
            "status": "PASS", "renderer": "scripts/josim-plot2.py",
            "layout": "sep_comb/dark/-j 2pi", "signals": signals, "runs": records,
            "shared_plotly_asset": asset, "shared_plotly_asset_sha256": sha(platform.PLOTLY_ASSET),
            "plotly_js_embedded_once": False, "responsive": True,
            "interpolation_or_resampling": False}
    html_text = target.read_text(encoding="utf-8")
    if "Plotly.newPlot" not in html_text or html_text.count(asset) != 1 or '"responsive": true' not in html_text:
        raise RuntimeError(f"comparison HTML QA failed: {target}")
    return page


def analyze_batch() -> dict[str, Any]:
    if [item[0] for item in platform.CARRY_POST_CB_SJTL_RUN_MATRIX] != list(RUNS_EXPECTED):
        raise RuntimeError("analysis run order differs from the registered A030-A033 matrix")
    comparison_paths = (PLOTS / "comparison" / "A027_A030_A031_D2_CARRY_CLOCK_COMPARISON.html",
                        PLOTS / "comparison" / "A028_A032_PAPER_REGRESSION.html",
                        PLOTS / "comparison" / "A029_A033_3X3_REGRESSION.html")
    for path in (SUMMARY, SIGNALS_CSV, PHASE_CSV, STAGE_CSV, COMPARISON_CSV, PLOT_QA, SUMMARY_MD,
                 *comparison_paths):
        if path.exists():
            raise FileExistsError(f"refusing to overwrite analysis output: {path}")
    baseline_ids = ("A027_FULL_CB_CHAIN_ALL_CLOCK", "A028_FULL_CB_CHAIN_PAPER_CLOCK",
                    "A029_FULL_CB_CHAIN_3X3_CLOCK")
    baselines = {run_id: _measure_run(run_id) for run_id in baseline_ids}
    runs = {run_id: _measure_run(run_id) for run_id in RUNS_EXPECTED}
    comparison_data = {**baselines, **runs}
    signal_rows = [row for run_id in RUNS_EXPECTED for row in runs[run_id]["waveforms"] + runs[run_id]["currents"]]
    phase_rows = [row for run_id in RUNS_EXPECTED for row in runs[run_id]["phase_area"]]
    stage_rows = [row for run_id in RUNS_EXPECTED for row in _stage_rows(runs[run_id])]
    comparison_rows = _comparison_rows(comparison_data)

    all_run_ids = ("A027_FULL_CB_CHAIN_ALL_CLOCK", "A030_CARRY_POST_CB_SJTL_ALL_200",
                   "A031_CARRY_POST_CB_SJTL_ALL_210")
    d2_focus_signals = ["V(CARRY_CB_OUT_D2)", "V(CARRY_SJTL_OUT_D2)", "I(V_CARRY_SJTL_IN_D2)",
                        "I(V_CBU_A_D2)", "I(V_CBU_B_D2)", "V(CBU_JOIN_D2)",
                        "P(BJ1|XCB_CARRY_D2)", "V(BJ1|XCB_CARRY_D2)",
                        "P(BJ2|XCB_CARRY_D2)", "V(BJ2|XCB_CARRY_D2)",
                        "P(BJ1|XSJTL_CARRY_D2)", "V(BJ1|XSJTL_CARRY_D2)",
                        "V(T1_I_D2)", "P(B_J1|XT1_D2)", "V(B_J1|XT1_D2)",
                        "P(B_J11|XT1_D2)", "V(B_J11|XT1_D2)", "V(S_D2)", "V(C_D2)",
                        "V(CLK_D2)", "V(DFF_IN)", "V(CLK_DFF)", "V(DFF_O)"]
    product_signals = [*(f"V(S_D{index})" for index in range(7)),
                       *(f"V(C_D{index})" for index in range(7)),
                       "V(DFF_IN)", "V(CLK_DFF)", "V(DFF_O)"]
    pages = [
        _comparison_page("A027_A030_A031_D2_CARRY_CLOCK_COMPARISON.html",
                         "A027 / A030 / A031 — D2 Carry CB + sJTL + T1 + global clock",
                         all_run_ids, d2_focus_signals, comparison_data),
        _comparison_page("A028_A032_PAPER_REGRESSION.html",
                         "A028 / A032 — 11×13 registered paper case vs post-CB sJTL at 210 ps",
                         ("A028_FULL_CB_CHAIN_PAPER_CLOCK", "A032_CARRY_POST_CB_SJTL_PAPER_210"),
                         product_signals, comparison_data),
        _comparison_page("A029_A033_3X3_REGRESSION.html",
                         "A029 / A033 — 3×3 registered low-load case vs post-CB sJTL at 210 ps",
                         ("A029_FULL_CB_CHAIN_3X3_CLOCK", "A033_CARRY_POST_CB_SJTL_3X3_210"),
                         product_signals, comparison_data),
    ]
    _csv_new(SIGNALS_CSV, signal_rows)
    _csv_new(PHASE_CSV, phase_rows)
    _csv_new(STAGE_CSV, stage_rows)
    _csv_new(COMPARISON_CSV, comparison_rows)

    run_records = []
    for run_id in RUNS_EXPECTED:
        data = runs[run_id]
        run_records.append({"run_id": run_id, "case": data["case"],
                            "reference_run": next(row[-1] for row in platform.CARRY_POST_CB_SJTL_RUN_MATRIX
                                                  if row[0] == run_id),
                            "raw_path": (RUNS / run_id / "raw.csv").relative_to(SERIES).as_posix(),
                            "raw_sha256": data["raw_sha256"], "raw_bytes": data["raw_bytes"],
                            "sample_count": data["raw_qa"]["sample_count"],
                            "time_range_s": [data["raw_qa"]["time_start_s"], data["raw_qa"]["time_end_s"]],
                            "dt_min_s": data["raw_qa"]["dt_min_s"], "dt_max_s": data["raw_qa"]["dt_max_s"],
                            "artifact_status": data["result"].get("artifact_status"),
                            "qa_status": data["qa"].get("status"), "chain_qa_status": data["chain_qa"].get("status"),
                            "same_jj_count": len(data["phase_area"]),
                            "stage_timing_descriptors": data["stage_timing_descriptors"],
                            "dff_timing_descriptor": data["dff_timing_descriptor"],
                            "scientific_interpretation_performed": False})
    summary = {"schema": "bvm4x4-carry-post-cb-sjtl-summary-v1", "status": "PASS",
               "batch_id": platform.CARRY_POST_CB_SJTL_BATCH_ID,
               "analysis_type": "mechanical raw-derived evidence; no physics verdict",
               "physical_solve_count": 4, "runs": run_records,
               "baseline_references": {run_id: {"raw_path": (RUNS/run_id/"raw.csv").relative_to(SERIES).as_posix(),
                                                   "raw_sha256": baselines[run_id]["raw_sha256"],
                                                   "raw_bytes": baselines[run_id]["raw_bytes"],
                                                   "physical_solve_count": 0}
                                        for run_id in baseline_ids},
               "registered_windows_ps_by_run": {
                   run_id: {name: list(_windows(float(runs[run_id]["case"]["T1_CHAIN_CLK_START"].removesuffix("p")))[name])
                            for name in WINDOWS} for run_id in RUNS_EXPECTED},
               "clock_start_ps_by_run": {run_id: float(runs[run_id]["case"]["T1_CHAIN_CLK_START"].removesuffix("p"))
                                         for run_id in RUNS_EXPECTED},
               "theoretical_vectors_reference_only": {
                   "A030_CARRY_POST_CB_SJTL_ALL_200": {"product": 225, "bits_lsb_to_msb": [1,0,0,0,0,1,1,1]},
                   "A031_CARRY_POST_CB_SJTL_ALL_210": {"product": 225, "bits_lsb_to_msb": [1,0,0,0,0,1,1,1]},
                   "A032_CARRY_POST_CB_SJTL_PAPER_210": {"product": 143, "bits_lsb_to_msb": [1,1,1,1,0,0,0,1]},
                   "A033_CARRY_POST_CB_SJTL_3X3_210": {"product": 9, "bits_lsb_to_msb": [1,0,0,1,0,0,0,0]}},
               "tables": {"signals": SIGNALS_CSV.relative_to(SERIES).as_posix(),
                          "same_jj_phase_area": PHASE_CSV.relative_to(SERIES).as_posix(),
                          "stage_metrics": STAGE_CSV.relative_to(SERIES).as_posix(),
                          "comparison": COMPARISON_CSV.relative_to(SERIES).as_posix()},
               "comparison_pages": pages,
               "shared_dout_join_voltage_semantics": runs[RUNS_EXPECTED[0]]["probe"].get("shared_dout_join_voltage_semantics"),
               "phase_units": "raw radians; phase delta/(2*pi) navigation arithmetic only",
               "integration": "actual stored timestamps; trapezoid; exact half-open windows; no interpolation/resampling",
               "dout_voltage_area_as_array_event_count": "NOT_USED",
               "event_classifier": None, "sfq_count_inference": "NOT_PERFORMED", "bit_decode": "NOT_PERFORMED",
               "timestep_convergence": "UNKNOWN_NOT_RUN", "scientific_interpretation_performed": False,
               "automatic_follow_up": False, "next_action": "STOP_AWAITING_USER_AND_CHATGPT_REVIEW"}
    _write_new(SUMMARY, json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    plot_qa = {"schema": "bvm4x4-carry-post-cb-sjtl-visualization-qa-v1", "status": "PASS",
               "run_pages_per_case": 4, "comparison_page_count": len(pages), "comparison_pages": pages,
               "renderer": "scripts/josim-plot2.py", "layout": "sep_comb/dark/-j 2pi",
               "html_in_package": False, "shared_plotly_js": platform.PLOTLY_ASSET.relative_to(REPO).as_posix(),
               "raw_modified": False, "scientific_interpretation_performed": False}
    _write_new(PLOT_QA, json.dumps(plot_qa, ensure_ascii=False, indent=2) + "\n")
    lines = ["# Carry CB + canonical sJTL batch — mechanical evidence brief", "",
             "- Status: `PASS / AWAITING_SCIENTIFIC_REVIEW`; physical solves: 4; scientific interpretation: `NOT_PERFORMED`.",
             "- D1-D6 topology: previous T1 Carry → canonical CB_0928 → one canonical sJTL_0923 → JOIN with array DOUT → T1 input.",
             "- `V(DOUT_Dk)` shares the sensed zero-volt boundary with JOIN; no DOUT voltage area is presented as an array-only pulse/event count.",
             "- Raw phase remains radians. Phase/area values and descriptive extrema are registered actual-grid arithmetic, not SFQ or bit counts.", "",
             "| Run | Reference | Raw bytes | Raw SHA-256 | QA |", "|---|---|---:|---|---|"]
    for item in run_records:
        lines.append(f"| {item['run_id']} | {item['reference_run']} | {item['raw_bytes']} | `{item['raw_sha256']}` | {item['qa_status']} |")
    lines.extend(["", "Mechanical detail:", "",
                  f"- [Stage boundaries](<{STAGE_CSV}>)", f"- [Same-JJ phase/area](<{PHASE_CSV}>)",
                  f"- [Waveform/current metrics](<{SIGNALS_CSV}>)", f"- [Matched arithmetic deltas](<{COMPARISON_CSV}>)",
                  "- HTML files remain local under `plots/`; no physical interpretation or follow-up is authorized.", ""])
    _write_new(SUMMARY_MD, "\n".join(lines))
    return summary


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analyze", action="store_true", required=True)
    args = parser.parse_args()
    result = analyze_batch()
    print(json.dumps({"status": result["status"], "run_count": len(result["runs"]),
                      "physical_solve_count": result["physical_solve_count"],
                      "summary_sha256": sha(SUMMARY), "scientific_interpretation_performed": False}, indent=2))
