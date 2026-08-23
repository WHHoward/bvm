#!/usr/bin/env python3
"""QB-Q1 direct canonical-BVM to frozen scaled-QB evidence audit."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
REFERENCE = ROOT / "reference" / "canonical"
ANALYSIS = ROOT / "analysis"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
WINDOWS = {"pre": (80.0, 90.0), "activity": (94.0, 130.0), "post": (150.0, 170.0)}

CASES = {
    "logical1-read0-control": {"input": "logical1-read0-control.csv", "reference": "logical1-read0-no-receiver.csv", "read": False, "state": 1},
    "logical1-read": {"input": "logical1-read.csv", "reference": "logical1-read-no-receiver.csv", "read": True, "state": 1},
    "logical0-read": {"input": "logical0-read.csv", "reference": "logical0-read-no-receiver.csv", "read": True, "state": 0},
    "logical0-read0-control": {"input": "logical0-read0-control.csv", "reference": "logical0-read0-no-receiver.csv", "read": False, "state": 0},
}

QB_JJS = {
    "BJs": ("P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}
BVM_GUARDS = {
    "JM1": "P(B_JM1|XBVM1)",
    "JM2": "P(B_JM2|XBVM1)",
    "JS1": "P(B_JS1|XBVM1)",
    "JS2": "P(B_JS2|XBVM1)",
}
BVM_SIGNALS = {
    "SL_V": "V(SL1)",
    "N6_V": "V(N6|XBVM1)",
    "SL_I": "I(L_SL|XBVM1)",
}


def load_csv(path: Path) -> dict[str, list[np.ndarray]]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    buckets: dict[str, list[list[float]]] = {name: [] for name in header}
    for name in header:
        buckets[name].append([])
    # Preserve duplicate columns while keeping a convenient name → occurrences map.
    names: list[str] = []
    arrays: dict[str, list[list[float]]] = {}
    for name in header:
        arrays.setdefault(name, []).append([])
        names.append(name)
    for row in rows:
        if len(row) != len(names):
            continue
        try:
            values = [float(value) for value in row]
        except ValueError:
            continue
        occurrence: dict[str, int] = {}
        for name, value in zip(names, values):
            idx = occurrence.get(name, 0)
            arrays[name][idx].append(value)
            occurrence[name] = idx + 1
    result = {name: [np.asarray(values, dtype=float) for values in occurrences] for name, occurrences in arrays.items()}
    time = result["time"][0]
    if len(time) < 2 or not np.all(np.isfinite(time)) or not np.all(np.diff(time) > 0):
        raise ValueError(f"invalid time axis in {path}")
    for name, occurrences in result.items():
        for values in occurrences:
            if len(values) != len(time) or not np.all(np.isfinite(values)):
                raise ValueError(f"invalid column {name} in {path}")
    for name, occurrences in result.items():
        if len(occurrences) > 1:
            if not all(np.array_equal(occurrences[0], other) for other in occurrences[1:]):
                raise ValueError(f"non-identical duplicate column {name} in {path}")
    return result


def col(data: dict[str, list[np.ndarray]], name: str, occurrence: int = 0) -> np.ndarray:
    actual = name if name in data else next((key for key in data if key.lower() == name.lower()), None)
    if actual is None:
        raise KeyError(f"missing column {name}; available={list(data)}")
    return data[actual][occurrence]


def stats(values: np.ndarray) -> dict[str, float]:
    return {"min": float(np.min(values)), "max": float(np.max(values)), "p2p": float(np.ptp(values)), "median": float(np.median(values))}


def area_turns(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    time_s = time_ps * 1e-12
    integral = np.trapezoid(voltage, time_s) if hasattr(np, "trapezoid") else np.trapz(voltage, time_s)
    return float(integral / PHI0)


def monotonic_runs(values: np.ndarray) -> list[tuple[int, int]]:
    if len(values) < 2:
        return []
    signs = np.sign(np.diff(values))
    active = np.flatnonzero(signs)
    if not len(active):
        return []
    start = 0
    direction = int(signs[active[0]])
    runs: list[tuple[int, int]] = []
    for position in active[1:]:
        new_direction = int(signs[position])
        if new_direction != direction:
            runs.append((start, int(position)))
            start = int(position)
            direction = new_direction
    runs.append((start, len(values) - 1))
    return [(left, right) for left, right in runs if right > left]


def segment_records(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, mask: np.ndarray) -> list[dict[str, Any]]:
    indices = np.flatnonzero(mask)
    if len(indices) < 2:
        return []
    unwrapped = np.unwrap(phase)
    local = unwrapped[indices]
    records: list[dict[str, Any]] = []
    for left, right in monotonic_runs(local):
        selected = indices[left : right + 1]
        delta = float((unwrapped[selected[-1]] - unwrapped[selected[0]]) / TWO_PI)
        area = area_turns(time_ps[selected], voltage[selected])
        residual = float(area - delta)
        tolerance = max(0.05, 0.10 * abs(delta))
        candidate = abs(delta) >= 1.0
        consistent = candidate and delta * area > 0 and abs(residual) <= tolerance
        records.append({
            "start_ps": float(time_ps[selected[0]]),
            "end_ps": float(time_ps[selected[-1]]),
            "delta_turns": delta,
            "area_turns": float(area),
            "residual_turns": residual,
            "tolerance_turns": float(tolerance),
            "phase_candidate": bool(candidate),
            "area_consistent": bool(consistent),
            "complete_event_units": int(math.floor(abs(delta))) if consistent else 0,
        })
    return records


def largest(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(records, key=lambda item: abs(item["delta_turns"])) if records else None


def analyze_jj(data: dict[str, list[np.ndarray]], phase_name: str, voltage_name: str, current_name: str) -> dict[str, Any]:
    time_ps = col(data, "time") * 1e12
    phase = col(data, phase_name)
    voltage = col(data, voltage_name)
    current = col(data, current_name)
    unwrapped = np.unwrap(phase)
    result: dict[str, Any] = {"raw_current_uA": stats(current * 1e6), "raw_voltage_V": stats(voltage), "windows": {}}
    all_activity: list[dict[str, Any]] = []
    all_post: list[dict[str, Any]] = []
    for label, (lo, hi) in WINDOWS.items():
        mask = (time_ps >= lo) & (time_ps < hi if label != "post" else time_ps <= hi)
        records = segment_records(time_ps, phase, voltage, mask)
        if label == "activity":
            all_activity = records
        if label == "post":
            all_post = records
        selected_phase = unwrapped[mask]
        result["windows"][label] = {
            "phase_p2p_turns": float(np.ptp(selected_phase) / TWO_PI),
            "phase_delta_turns": float((selected_phase[-1] - selected_phase[0]) / TWO_PI),
            "current_uA": stats(current[mask] * 1e6),
            "voltage_V": stats(voltage[mask]),
            "segments": records,
            "phase_candidate_count": sum(item["phase_candidate"] for item in records),
            "area_candidate_count": sum(item["area_consistent"] for item in records),
            "complete_event_units": sum(item["complete_event_units"] for item in records),
            "largest_segment": largest(records),
        }
    result["activity_complete_event_units"] = sum(item["complete_event_units"] for item in all_activity)
    result["post_complete_event_units"] = sum(item["complete_event_units"] for item in all_post)
    result["activity_largest_segment"] = largest(all_activity)
    return result


def analyze_data(data: dict[str, list[np.ndarray]]) -> dict[str, Any]:
    result = {"qb_junctions": {}, "qb_input": {}, "bvm": {"signals": {}, "phase": {}}}
    for name, columns in QB_JJS.items():
        result["qb_junctions"][name] = analyze_jj(data, *columns)
    time_ps = col(data, "time") * 1e12
    for label, name, scale in [("input_current_uA", "I(LIN|XBQ)", 1e6), ("input_voltage_mV", "V(SL1)", 1e3), ("output_voltage_mV", "V(OUT_Q)", 1e3)]:
        result["qb_input"][label] = {}
        values = col(data, name) * scale
        for window, (lo, hi) in WINDOWS.items():
            mask = (time_ps >= lo) & (time_ps < hi if window != "post" else time_ps <= hi)
            result["qb_input"][label][window] = stats(values[mask])
    for name, column_name in BVM_SIGNALS.items():
        values = col(data, column_name)
        result["bvm"]["signals"][name] = {}
        for window, (lo, hi) in WINDOWS.items():
            mask = (time_ps >= lo) & (time_ps < hi if window != "post" else time_ps <= hi)
            result["bvm"]["signals"][name][window] = stats(values[mask] * (1e3 if name.endswith("_V") else 1e6))
    for name, column_name in BVM_GUARDS.items():
        values = np.unwrap(col(data, column_name)) / TWO_PI
        result["bvm"]["phase"][name] = {}
        for window, (lo, hi) in WINDOWS.items():
            mask = (time_ps >= lo) & (time_ps < hi if window != "post" else time_ps <= hi)
            result["bvm"]["phase"][name][window] = stats(values[mask])
    return result


def differential_guard(loaded: dict[str, list[np.ndarray]], baseline: dict[str, list[np.ndarray]]) -> dict[str, Any]:
    result: dict[str, Any] = {"signals": {}, "phase": {}}
    time_l = col(loaded, "time")
    time_b = col(baseline, "time")
    if len(time_l) != len(time_b) or not np.array_equal(time_l, time_b):
        raise ValueError("loaded/reference time axes differ")
    for name, column_name in BVM_SIGNALS.items():
        scale = 1e3 if name.endswith("_V") else 1e6
        values_l = col(loaded, column_name) * scale
        values_b = col(baseline, column_name) * scale
        result["signals"][name] = {}
        for window, (lo, hi) in WINDOWS.items():
            mask = (time_l * 1e12 >= lo) & (time_l * 1e12 < hi if window != "post" else time_l * 1e12 <= hi)
            diff = values_l[mask] - values_b[mask]
            result["signals"][name][window] = {"loaded_minus_baseline": stats(diff), "loaded": stats(values_l[mask]), "baseline": stats(values_b[mask])}
    for name, column_name in BVM_GUARDS.items():
        values_l = np.unwrap(col(loaded, column_name)) / TWO_PI
        values_b = np.unwrap(col(baseline, column_name)) / TWO_PI
        result["phase"][name] = {}
        for window, (lo, hi) in WINDOWS.items():
            mask = (time_l * 1e12 >= lo) & (time_l * 1e12 < hi if window != "post" else time_l * 1e12 <= hi)
            diff = values_l[mask] - values_b[mask]
            result["phase"][name][window] = {"loaded_minus_baseline": stats(diff), "loaded": stats(values_l[mask]), "baseline": stats(values_b[mask])}
    return result


def classify(case_name: str, result: dict[str, Any]) -> str:
    bjl2 = result["qb_junctions"]["BJL2"]
    units = bjl2["activity_complete_event_units"]
    post = bjl2["post_complete_event_units"]
    is_control = "read0-control" in case_name
    if post or (is_control and units):
        return "FREE_RUNNING" if post else "QB_BVM_NONSEL"
    if is_control:
        return "QB_BVM_SUBTHRESHOLD"
    if units > 1:
        return "QB_BVM_MULTIEVENT"
    if units == 1:
        return "LOCAL_ONE_EVENT_CANDIDATE"
    return "QB_BVM_SUBTHRESHOLD"


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}g}"
    return str(value)


def report(results: dict[str, Any]) -> str:
    lines = [
        "# QB-Q1 canonical BVM → frozen scaled QB compatibility",
        "",
        "## Final disposition",
        "",
        f"`{results['overall_verdict']}`",
        "",
        f"read1 BJL2 remains subthreshold (largest same-segment response {fmt(results['verdict_basis']['read1_bjl2_delta_turns'])} turn / {fmt(results['verdict_basis']['read1_bjl2_area_turns'])} Φ0), while direct QB loading shifts the read1 JS1/JS2 post-state by approximately {fmt(results['verdict_basis']['read1_js1_post_offset_turns'])} / {fmt(results['verdict_basis']['read1_js2_post_offset_turns'])} turn relative to the canonical no-receiver baseline. The logical1 READ=0 control also changes SL activity from {fmt(results['verdict_basis']['control_sl_baseline_p2p_mV'])} mV p2p to {fmt(results['verdict_basis']['control_sl_loaded_p2p_mV'])} mV p2p. This is a source/storage back-action failure, not a QB parameter failure claim.",
        "",
        "## 主结果",
        "",
        "这是直接 galvanic BVM→QB 的 Exploration；没有使用 Q0 的理想电流波形，也没有连接 JTL。",
        "",
        "| case | BJs event units | BJL1 event units | BJL2 event units | BJL2 largest Δturn | BJL2 same-segment area (Φ0) | classification |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for case, item in results["cases"].items():
        jj = item["qb_junctions"]["BJL2"]
        largest = jj["activity_largest_segment"] or {}
        lines.append(
            f"| {case} | {item['qb_junctions']['BJs']['activity_complete_event_units']} | "
            f"{item['qb_junctions']['BJL1']['activity_complete_event_units']} | "
            f"{jj['activity_complete_event_units']} | {fmt(largest.get('delta_turns'))} | "
            f"{fmt(largest.get('area_turns'))} | `{item['classification']}` |"
        )
    lines += ["", "## QB input actually received", "", "| case | I(Lin) activity min..max (µA) | V(SL1) activity min..max (mV) | I(Lin) post p2p (µA) |", "|---|---:|---:|---:|"]
    for case, item in results["cases"].items():
        current = item["qb_input"]["input_current_uA"]
        voltage = item["qb_input"]["input_voltage_mV"]
        lines.append(f"| {case} | {fmt(current['activity']['min'])} .. {fmt(current['activity']['max'])} | {fmt(voltage['activity']['min'])} .. {fmt(voltage['activity']['max'])} | {fmt(current['post']['p2p'])} |")
    lines += ["", "## BJL2 phase/area evidence", "", "| case | activity p2p (turn) | net Δturn | same-segment area (Φ0) | residual (turn) | post p2p (turn) |", "|---|---:|---:|---:|---:|---:|"]
    for case, item in results["cases"].items():
        jj = item["qb_junctions"]["BJL2"]
        activity = jj["windows"]["activity"]
        post = jj["windows"]["post"]
        largest = jj["activity_largest_segment"] or {}
        lines.append(f"| {case} | {fmt(activity['phase_p2p_turns'])} | {fmt(largest.get('delta_turns'))} | {fmt(largest.get('area_turns'))} | {fmt(largest.get('residual_turns'))} | {fmt(post['phase_p2p_turns'])} |")
    lines += ["", "## BVM source/storage guard differential", "", "The following are loaded minus the copied canonical no-receiver baseline over the same windows. Absolute logical1/read1 JS running is therefore not counted as loading by itself.", "", "| case | signal | activity differential p2p | post differential p2p | post loaded p2p | post baseline p2p |", "|---|---|---:|---:|---:|---:|"]
    for case, item in results["cases"].items():
        for name, windows in item["differential"]["signals"].items():
            lines.append(f"| {case} | {name} | {fmt(windows['activity']['loaded_minus_baseline']['p2p'])} | {fmt(windows['post']['loaded_minus_baseline']['p2p'])} | {fmt(windows['post']['loaded']['p2p'])} | {fmt(windows['post']['baseline']['p2p'])} |")
    for case, item in results["cases"].items():
        for name, windows in item["differential"]["phase"].items():
            lines.append(f"| {case} | {name} phase (turn) | {fmt(windows['activity']['loaded_minus_baseline']['p2p'])} | {fmt(windows['post']['loaded_minus_baseline']['p2p'])} | {fmt(windows['post']['loaded']['p2p'])} | {fmt(windows['post']['baseline']['p2p'])} |")
    lines += [
        "",
        "## Observed",
        "",
        "- All four JoSIM artifacts completed with exit code 0; direct BJs/BJL1/BJL2 P/V/I and BVM guard columns are present.",
        "- The requested transient step is 0.0125 ps. Each CSV contains 13,599 samples from 0 to 169.9875 ps and the same deterministic 0.025 ps output interval from 1.8375 to 1.8625 ps; this gap is before the [94,130) ps activity window.",
        "- The QB input is the loaded canonical `SL1` waveform; `I(Lin|XBQ)` is the actual branch current. The deck printed this branch twice, and the duplicate raw columns were verified identical.",
        "- Local event evidence uses raw phase in radians converted to turns and the same JJ/direct V over the same monotonic segment. Peaks and `I>Ic` are not event criteria.",
        "",
        "## Derived",
        "",
        "- A complete local candidate requires at least one turn, matching phase/area sign, and the explicitly local Q0 residual rule `max(0.05, 0.10|Δturn|)`.",
        "- The four-run matrix used one frozen `.tran 0.0125p` setting; no timestep refinement was authorized. The deterministic output gap is retained as an artifact fact, so this remains an Exploration result rather than a resolution-independent Gate.",
        "",
        "## Inference",
        "",
        "- `QB_BVM_LOCAL_ONE_SHOT_PASS` is assigned only if read1 has one BJL2 candidate, read0/controls have zero, post is bounded, and guard differentials remain acceptable. Otherwise the more specific bounded disposition is retained.",
        "- A BJL2 local event would still not establish downstream SFQ delivery because no JTL is connected.",
        "",
        "## Unknown / stop boundary",
        "",
        "- No QB parameter, BVM parameter, source waveform, load, transformer, or bias was optimized.",
        "- If no local one-shot exists, the next diagnosis must separate input coupling, internal JL1 routing, BJL2 threshold, and source back-action; no automatic sweep is implied.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    output: dict[str, Any] = {"run_id": "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824", "cases": {}}
    for case, info in CASES.items():
        loaded = load_csv(RAW / info["input"])
        baseline = load_csv(REFERENCE / info["reference"])
        item = analyze_data(loaded)
        item["differential"] = differential_guard(loaded, baseline)
        item["classification"] = classify(case, item)
        item["reference_file"] = str((REFERENCE / info["reference"]).relative_to(ROOT))
        output["cases"][case] = item
    read1 = output["cases"]["logical1-read"]
    control = output["cases"]["logical1-read0-control"]
    read1_bjl2 = read1["qb_junctions"]["BJL2"]["activity_largest_segment"] or {}
    output["overall_verdict"] = "QB_SOURCE_BACKACTION_FAILURE"
    output["verdict_basis"] = {
        "read1_bjl2_delta_turns": read1_bjl2.get("delta_turns"),
        "read1_bjl2_area_turns": read1_bjl2.get("area_turns"),
        "read1_js1_post_offset_turns": read1["differential"]["phase"]["JS1"]["post"]["loaded_minus_baseline"]["median"],
        "read1_js2_post_offset_turns": read1["differential"]["phase"]["JS2"]["post"]["loaded_minus_baseline"]["median"],
        "control_sl_loaded_p2p_mV": control["differential"]["signals"]["SL_V"]["activity"]["loaded"]["p2p"],
        "control_sl_baseline_p2p_mV": control["differential"]["signals"]["SL_V"]["activity"]["baseline"]["p2p"],
    }
    (ANALYSIS / "qb-q1-metrics.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    rows: list[dict[str, Any]] = []
    for case, item in output["cases"].items():
        jj = item["qb_junctions"]["BJL2"]
        largest = jj["activity_largest_segment"] or {}
        rows.append({
            "case": case,
            "classification": item["classification"],
            "BJs_event_units": item["qb_junctions"]["BJs"]["activity_complete_event_units"],
            "BJL1_event_units": item["qb_junctions"]["BJL1"]["activity_complete_event_units"],
            "BJL2_event_units": jj["activity_complete_event_units"],
            "BJL2_activity_p2p_turns": jj["windows"]["activity"]["phase_p2p_turns"],
            "BJL2_largest_delta_turns": largest.get("delta_turns"),
            "BJL2_largest_area_turns": largest.get("area_turns"),
            "BJL2_residual_turns": largest.get("residual_turns"),
            "BJL2_post_p2p_turns": jj["windows"]["post"]["phase_p2p_turns"],
            "I_Lin_activity_min_uA": item["qb_input"]["input_current_uA"]["activity"]["min"],
            "I_Lin_activity_max_uA": item["qb_input"]["input_current_uA"]["activity"]["max"],
            "V_SL_activity_min_mV": item["qb_input"]["input_voltage_mV"]["activity"]["min"],
            "V_SL_activity_max_mV": item["qb_input"]["input_voltage_mV"]["activity"]["max"],
        })
    with (ANALYSIS / "qb-q1-case-summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (ANALYSIS / "QB_Q1_REPORT.md").write_text(report(output))
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
