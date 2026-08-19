#!/usr/bin/env python3
"""Primary raw-CSV analysis for the R1a series-pickup Exploration."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PHI0_WB = 2.067833848e-15
TWO_PI = 2.0 * math.pi
POINT = {
    "id": "l020-k080",
    "l_tx_pH": 0.20,
    "l_sec_pH": 2.0,
    "coupling_k": 0.80,
    "r_sec_load_ohm": 12.0,
    "area": 0.50,
    "trigger_bias_uA": 15.0,
    "trigger_ic_uA": 50.0,
    "trigger_rn_ohm": 32.0,
    "trigger_r0_ohm": 320.0,
    "trigger_c_fF": 35.0,
}
CASES = [
    ("read1", 1, "canonical_positive"),
    ("read0", 0, "canonical_positive"),
    ("logical1-read0-control", 1, "zero_control"),
    ("logical0-read0-control", 0, "zero_control"),
]
WINDOWS = {
    "PRE": (80.0, 90.0),
    "READ_ACTIVITY": (94.0, 130.0),
    "TRIGGER_ANALYSIS": (94.0, 170.0),
    "POST": (130.0, 170.0),
    "CONTROL_FULL": (20.0, 170.0),
    "STORAGE_POST": (140.0, 150.0),
}
TRIGGER_PHASE = "P(B_TRIG|XTRIG)"
TRIGGER_VOLTAGE = "V(B_TRIG|XTRIG)"
SECONDARY_VOLTAGE = "V(N_SEC|XTRIG)"
SECONDARY_LOAD_CURRENT = "I(R_SEC_LOAD|XTRIG)"
SECONDARY_COIL_CURRENT = "I(L_SEC|XTRIG)"
REQUIRED = [
    "time",
    TRIGGER_PHASE,
    TRIGGER_VOLTAGE,
    "I(B_TRIG|XTRIG)",
    "I(R_IN|XTRIG)",
    "I(L_TX|XTRIG)",
    "I(I_TRIG_BIAS|XTRIG)",
    "V(N_PICK|XTRIG)",
    "V(N_TRIG|XTRIG)",
    SECONDARY_VOLTAGE,
    SECONDARY_COIL_CURRENT,
    SECONDARY_LOAD_CURRENT,
    "V(SL1)",
    "V(N6|XBVM1)",
    "I(L_SL|XBVM1)",
    "I(L_PSL|XBVM1)",
    "P(B_JM1|XBVM1)",
    "V(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "V(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "V(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
    "V(B_JS2|XBVM1)",
    "I(L_S1|XBVM1)",
    "I(L_S2|XBVM1)",
    "I(L_S3|XBVM1)",
    "I(L_M3|XBVM1)",
    "I(I_WL1)",
    "I(I_BL1)",
    "I(I_SE1)",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv(path: Path):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = []
        for raw in reader:
            row = {key: float(value) for key, value in raw.items()}
            row["_time_ps"] = row["time"] * 1e12
            rows.append(row)
    return fields, rows


def select(rows, interval):
    lo, hi = interval
    return [row for row in rows if lo <= row["_time_ps"] <= hi]


def median(rows, key):
    return statistics.median(row[key] for row in rows)


def extrema(rows, key):
    low = min(rows, key=lambda row: row[key])
    high = max(rows, key=lambda row: row[key])
    absolute = max(rows, key=lambda row: abs(row[key]))
    return {
        "min": low[key],
        "min_time_ps": low["_time_ps"],
        "max": high[key],
        "max_time_ps": high["_time_ps"],
        "abs_peak": absolute[key],
        "abs_peak_time_ps": absolute["_time_ps"],
        "median": median(rows, key),
    }


def trapezoid_area(rows, key):
    return sum(
        0.5 * (left[key] + right[key]) * (right["time"] - left["time"])
        for left, right in zip(rows, rows[1:])
    )


def unwrap_phase(rows):
    if not rows:
        return
    rows[0]["_phase_unwrapped"] = rows[0][TRIGGER_PHASE]
    for previous, current in zip(rows, rows[1:]):
        delta = current[TRIGGER_PHASE] - previous[TRIGGER_PHASE]
        while delta > math.pi:
            delta -= TWO_PI
        while delta < -math.pi:
            delta += TWO_PI
        current["_phase_unwrapped"] = previous["_phase_unwrapped"] + delta


def phase_sample(row):
    return {
        "time_ps": row["_time_ps"],
        "raw_phase_rad": row[TRIGGER_PHASE],
        "unwrapped_phase_rad": row["_phase_unwrapped"],
        "voltage_V": row[TRIGGER_VOLTAGE],
    }


def monotonic_segments(rows):
    if len(rows) < 2:
        return []
    deltas = [
        right["_phase_unwrapped"] - left["_phase_unwrapped"]
        for left, right in zip(rows, rows[1:])
    ]
    start = 0
    direction = None
    segments = []

    def append_segment(end, sign):
        if end <= start or sign is None:
            return
        left = rows[start]
        right = rows[end]
        delta_rad = right["_phase_unwrapped"] - left["_phase_unwrapped"]
        delta_turns = delta_rad / TWO_PI
        area_turns = trapezoid_area(rows[start : end + 1], TRIGGER_VOLTAGE) / PHI0_WB
        abs_turns = abs(delta_turns)
        segments.append(
            {
                "start_time_ps": left["_time_ps"],
                "end_time_ps": right["_time_ps"],
                "direction": "increasing" if sign > 0 else "decreasing",
                "direction_sign": sign,
                "raw_phase_start_rad": left[TRIGGER_PHASE],
                "raw_phase_end_rad": right[TRIGGER_PHASE],
                "unwrapped_phase_start_rad": left["_phase_unwrapped"],
                "unwrapped_phase_end_rad": right["_phase_unwrapped"],
                "phase_delta_rad": delta_rad,
                "phase_delta_turns": delta_turns,
                "phase_abs_turns": abs_turns,
                "same_junction_voltage_area_Wb": trapezoid_area(rows[start : end + 1], TRIGGER_VOLTAGE),
                "same_junction_voltage_area_turns": area_turns,
                "area_minus_phase_turns": area_turns - delta_turns,
                "area_consistent_0p05_turns": abs(area_turns - delta_turns) <= 0.05,
                "complete_2pi": abs_turns >= 1.0,
                "complete_turn_units": int(math.floor(abs_turns + 1e-9)),
                "rows": end - start + 1,
                "endpoint_samples": {"start": phase_sample(left), "end": phase_sample(right)},
            }
        )

    for index, delta in enumerate(deltas):
        sign = 1 if delta > 0.0 else -1 if delta < 0.0 else 0
        if sign == 0:
            continue
        if direction is None:
            direction = sign
        elif sign != direction:
            append_segment(index, direction)
            start = index
            direction = sign
    append_segment(len(rows) - 1, direction)
    return segments


def phase_window_result(rows, interval):
    part = select(rows, interval)
    if not part:
        return {"interval_ps": list(interval), "rows": 0, "segments": [], "complete_2pi": False, "complete_turn_units": 0}
    segments = monotonic_segments(part)
    raw = [row[TRIGGER_PHASE] for row in part]
    unwrapped = [row["_phase_unwrapped"] for row in part]
    complete = [segment for segment in segments if segment["complete_2pi"]]
    return {
        "interval_ps": list(interval),
        "rows": len(part),
        "trajectory": {
            "raw_phase_start_rad": part[0][TRIGGER_PHASE],
            "raw_phase_end_rad": part[-1][TRIGGER_PHASE],
            "raw_phase_min_rad": min(raw),
            "raw_phase_max_rad": max(raw),
            "unwrapped_phase_start_rad": part[0]["_phase_unwrapped"],
            "unwrapped_phase_end_rad": part[-1]["_phase_unwrapped"],
            "unwrapped_phase_min_rad": min(unwrapped),
            "unwrapped_phase_max_rad": max(unwrapped),
            "unwrapped_phase_range_turns": (max(unwrapped) - min(unwrapped)) / TWO_PI,
            "samples_first": [phase_sample(row) for row in part[:5]],
            "samples_last": [phase_sample(row) for row in part[-5:]],
        },
        "segments": segments,
        "complete_segments": complete,
        "complete_2pi": bool(complete),
        "complete_turn_units": sum(segment["complete_turn_units"] for segment in segments),
        "largest_abs_segment": max(segments, key=lambda segment: segment["phase_abs_turns"], default=None),
        "largest_abs_segment_turns": max((segment["phase_abs_turns"] for segment in segments), default=0.0),
    }


def signal_window_result(rows, interval, keys):
    part = select(rows, interval)
    return {
        "interval_ps": list(interval),
        "rows": len(part),
        "signals": {key: extrema(part, key) for key in keys} if part else {},
    }


def secondary_amplitude(rows, key):
    pre = select(rows, WINDOWS["PRE"])
    activity = select(rows, WINDOWS["READ_ACTIVITY"])
    baseline = median(pre, key) if pre else 0.0
    deviations = [abs(row[key] - baseline) for row in activity]
    return {
        "key": key,
        "pre_median": baseline,
        "activity_abs_deviation_peak": max(deviations, default=0.0),
        "activity_abs_deviation_peak_time_ps": activity[deviations.index(max(deviations))]["_time_ps"] if deviations else None,
        "pre_stats": signal_window_result(rows, WINDOWS["PRE"], [key]),
        "activity_stats": signal_window_result(rows, WINDOWS["READ_ACTIVITY"], [key]),
    }


def summarize_case(case_id, logical_state, read_kind):
    path = ROOT / "raw" / POINT["id"] / case_id / "run-01.csv"
    fields, rows = load_csv(path)
    missing = [key for key in REQUIRED if key not in fields]
    times = [row["_time_ps"] for row in rows]
    dts = [right - left for left, right in zip(times, times[1:])]
    increasing = all(right > left for left, right in zip(times, times[1:]))
    finite = all(math.isfinite(value) for row in rows for key, value in row.items() if key != "_time_ps")
    unwrap_phase(rows)

    trigger = {
        "read_activity": phase_window_result(rows, WINDOWS["READ_ACTIVITY"]),
        "trigger_analysis": phase_window_result(rows, WINDOWS["TRIGGER_ANALYSIS"]),
        "post": phase_window_result(rows, WINDOWS["POST"]),
        "control_full": phase_window_result(rows, WINDOWS["CONTROL_FULL"]),
    }
    qualifying = [
        segment
        for segment in trigger["trigger_analysis"]["segments"]
        if segment["complete_2pi"] and segment["start_time_ps"] <= WINDOWS["READ_ACTIVITY"][1]
    ]
    trigger["qualifying_read_trigger_segments"] = qualifying
    trigger["qualifying_read_trigger"] = bool(qualifying)

    secondary = {
        key: secondary_amplitude(rows, key)
        for key in [SECONDARY_VOLTAGE, SECONDARY_LOAD_CURRENT, SECONDARY_COIL_CURRENT]
    }
    storage = {}
    pre = select(rows, WINDOWS["PRE"])
    post = select(rows, WINDOWS["STORAGE_POST"])
    if pre and post:
        for key in ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"]:
            delta = median(post, key) - median(pre, key)
            storage[key] = {
                "pre_median_rad": median(pre, key),
                "post_median_rad": median(post, key),
                "post_minus_pre_rad": delta,
                "post_minus_pre_turns": delta / TWO_PI,
            }

    source_keys = ["V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "I(L_PSL|XBVM1)"]
    pickup_keys = ["I(R_IN|XTRIG)", "I(L_TX|XTRIG)", "I(I_TRIG_BIAS|XTRIG)", "V(N_PICK|XTRIG)", "V(N_TRIG|XTRIG)"]
    readout_keys = ["P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)", "V(B_JS1|XBVM1)", "V(B_JS2|XBVM1)"]
    return {
        "case_id": case_id,
        "logical_state": logical_state,
        "read_kind": read_kind,
        "operating_point": POINT,
        "csv": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "qa": {
            "rows": len(rows),
            "time_start_ps": times[0] if times else None,
            "time_end_ps": times[-1] if times else None,
            "dt_min_ps": min(dts) if dts else None,
            "dt_max_ps": max(dts) if dts else None,
            "strictly_increasing_time": increasing,
            "all_finite": finite,
            "missing_columns": missing,
            "artifact_valid": bool(rows) and not missing and increasing and finite,
        },
        "trigger": trigger,
        "secondary": secondary,
        "pickup": signal_window_result(rows, WINDOWS["READ_ACTIVITY"], pickup_keys),
        "source": signal_window_result(rows, WINDOWS["READ_ACTIVITY"], source_keys),
        "storage": storage,
        "readout": {key: signal_window_result(rows, WINDOWS["READ_ACTIVITY"], [key]) for key in readout_keys},
        "same_junction": {
            "phase_probe": TRIGGER_PHASE,
            "voltage_probe": TRIGGER_VOLTAGE,
            "direction": "B_TRIG N_TRIG -> 0",
            "criterion": "continuous adjacent-sample phase segments and same-segment B_TRIG voltage area",
        },
    }


def build_secondary_criterion(cases):
    read1 = cases["read1"]
    read0 = cases["read0"]
    c1 = cases["logical1-read0-control"]
    c0 = cases["logical0-read0-control"]
    outcomes = {}
    for key, threshold in [(SECONDARY_VOLTAGE, 10e-6), (SECONDARY_LOAD_CURRENT, 1e-6)]:
        a1 = read1["secondary"][key]["activity_abs_deviation_peak"]
        a0 = read0["secondary"][key]["activity_abs_deviation_peak"]
        ac1 = c1["secondary"][key]["activity_abs_deviation_peak"]
        ac0 = c0["secondary"][key]["activity_abs_deviation_peak"]
        outcomes[key] = {
            "read1_amplitude": a1,
            "read0_amplitude": a0,
            "logical1_control_amplitude": ac1,
            "logical0_control_amplitude": ac0,
            "threshold_native_units": threshold,
            "read1_above_absolute_threshold": a1 >= threshold,
            "read1_at_least_2x_read0": a1 >= 2.0 * a0,
            "read1_at_least_5x_controls": a1 >= 5.0 * max(ac1, ac0),
            "pass": a1 >= threshold and a1 >= 2.0 * a0 and a1 >= 5.0 * max(ac1, ac0),
        }
    return outcomes


def main():
    cases = {}
    for case_id, logical_state, read_kind in CASES:
        path = ROOT / "raw" / POINT["id"] / case_id / "run-01.csv"
        if path.exists():
            cases[case_id] = summarize_case(case_id, logical_state, read_kind)
    secondary_criterion = build_secondary_criterion(cases) if len(cases) == len(CASES) else {}
    read1_trigger = cases.get("read1", {}).get("trigger", {}).get("qualifying_read_trigger", False)
    read0_trigger = cases.get("read0", {}).get("trigger", {}).get("qualifying_read_trigger", True)
    control_triggers = [
        cases.get(case_id, {}).get("trigger", {}).get("control_full", {}).get("complete_2pi", True)
        for case_id in ["logical1-read0-control", "logical0-read0-control"]
    ]
    secondary_pass = bool(secondary_criterion) and all(item["pass"] for item in secondary_criterion.values())
    result = {
        "document_type": "r1a_raw_analysis",
        "analysis_version": "r1a-series-pickup-1",
        "phi0_Wb": PHI0_WB,
        "metric_boundary": "P(B_TRIG) is raw radians; turns=delta/(2*pi); same-JJ voltage area uses actual CSV time and B_TRIG endpoints; secondary amplitudes are passive-signal extraction metrics, not event counts.",
        "point": POINT,
        "windows_ps": WINDOWS,
        "criterion": {
            "trigger": "read1 qualifying complete B_TRIG segment; read0/control no qualifying complete segment",
            "secondary": "V(N_SEC) >=10 uV and I(R_SEC_LOAD) >=1 uA in read1, each >=2x read0 and >=5x both controls",
        },
        "matched_case_count": len(cases),
        "matched_matrix_complete": len(cases) == len(CASES),
        "secondary_criterion": secondary_criterion,
        "verdict_components": {
            "artifact_valid": len(cases) == len(CASES) and all(case["qa"]["artifact_valid"] for case in cases.values()),
            "read1_trigger_complete": read1_trigger,
            "read0_trigger_noncomplete": not read0_trigger,
            "controls_trigger_noncomplete": not any(control_triggers),
            "secondary_state_dependent": secondary_pass,
        },
        "cases": cases,
    }
    out = ROOT / "analysis" / "r1a-analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    for case in cases.values():
        largest = case["trigger"]["trigger_analysis"]["largest_abs_segment_turns"]
        v_amp = case["secondary"][SECONDARY_VOLTAGE]["activity_abs_deviation_peak"]
        i_amp = case["secondary"][SECONDARY_LOAD_CURRENT]["activity_abs_deviation_peak"]
        print(f"{case['case_id']}: trigger_largest={largest:.9g} turns, Vsec_amp={v_amp:.9g} V, Isec_amp={i_amp:.9g} A")
    if secondary_criterion:
        for key, outcome in secondary_criterion.items():
            print(f"secondary {key}: pass={outcome['pass']} read1={outcome['read1_amplitude']:.9g} read0={outcome['read0_amplitude']:.9g}")


if __name__ == "__main__":
    main()
