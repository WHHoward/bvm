#!/usr/bin/env python3
"""Raw evidence analysis for the R1 one-shot Exploration.

The event decision is local to B_OUT.  It uses the raw phase trajectory,
continuous adjacent-sample unwrapping, monotonic segments, and a voltage
integral over the exact same B_OUT segment.  Current and voltage peaks are
reported as context only; neither is an event counter.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PHI0_WB = 2.067833848e-15
PI2 = 2.0 * math.pi
POINTS = [
    {
        "id": "a050-b15",
        "area": 0.50,
        "trigger_bias_uA": 15.0,
        "trigger_ic_uA": 50.0,
        "trigger_rn_ohm": 32.0,
        "trigger_r0_ohm": 320.0,
        "trigger_c_fF": 35.0,
        "output_bias_uA": 35.0,
        "output_ic_uA": 50.0,
        "output_rn_ohm": 32.0,
        "r_q_ohm": 15.0,
    },
    {
        "id": "a050-b15-rq100",
        "area": 0.50,
        "trigger_bias_uA": 15.0,
        "trigger_ic_uA": 50.0,
        "trigger_rn_ohm": 32.0,
        "trigger_r0_ohm": 320.0,
        "trigger_c_fF": 35.0,
        "output_bias_uA": 35.0,
        "output_ic_uA": 50.0,
        "output_rn_ohm": 32.0,
        "r_q_ohm": 100.0,
    },
    {
        "id": "a050-b15-rq1k",
        "area": 0.50,
        "trigger_bias_uA": 15.0,
        "trigger_ic_uA": 50.0,
        "trigger_rn_ohm": 32.0,
        "trigger_r0_ohm": 320.0,
        "trigger_c_fF": 35.0,
        "output_bias_uA": 35.0,
        "output_ic_uA": 50.0,
        "output_rn_ohm": 32.0,
        "r_q_ohm": 1000.0,
    },
    {
        "id": "a050-b15-lq10",
        "area": 0.50,
        "trigger_bias_uA": 15.0,
        "trigger_ic_uA": 50.0,
        "trigger_rn_ohm": 32.0,
        "trigger_r0_ohm": 320.0,
        "trigger_c_fF": 35.0,
        "output_bias_uA": 35.0,
        "output_ic_uA": 50.0,
        "output_rn_ohm": 32.0,
        "l_q_pH": 10.0,
        "r_q_ohm": 15.0,
    },
]
CASES = [
    ("read1", 1, "canonical_positive"),
    ("read0", 0, "canonical_positive"),
    ("logical1-read0-control", 1, "zero_control"),
    ("logical0-read0-control", 0, "zero_control"),
]
WINDOWS = {
    "PRE": (80.0, 90.0),
    "READ_ACTIVITY": (94.0, 130.0),
    "TRIGGER_ANALYSIS": (94.0, 200.0),
    "OUTPUT_ANALYSIS": (20.0, 200.0),
    "READ_OUTPUT_WINDOW": (94.0, 140.0),
    "POST": (140.0, 200.0),
    "POST_EARLY": (140.0, 160.0),
    "POST_LATE": (180.0, 200.0),
    "CONTROL_FULL": (20.0, 200.0),
    "STORAGE_POST": (160.0, 180.0),
}
TRIGGER_PHASE = "P(B_TRIG|XTRIG)"
TRIGGER_VOLTAGE = "V(B_TRIG|XTRIG)"
OUTPUT_PHASE = "P(B_OUT|XTRIG)"
OUTPUT_VOLTAGE = "V(B_OUT|XTRIG)"
REQUIRED = [
    "time",
    TRIGGER_PHASE,
    TRIGGER_VOLTAGE,
    "I(B_TRIG|XTRIG)",
    "I(R_IN|XTRIG)",
    "I(I_TRIG_BIAS|XTRIG)",
    "I(L_Q|XTRIG)",
    "I(R_Q|XTRIG)",
    OUTPUT_PHASE,
    OUTPUT_VOLTAGE,
    "I(B_OUT|XTRIG)",
    "I(L_SEC|XTRIG)",
    "I(R_OUT_DAMP|XTRIG)",
    "I(R_LOAD|XTRIG)",
    "I(I_OUT_BIAS|XTRIG)",
    "V(OUT_PORT|XTRIG)",
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


def percentile_abs(rows, key, percentile):
    values = sorted(abs(row[key]) for row in rows)
    if not values:
        return None
    index = min(len(values) - 1, max(0, int(math.ceil(percentile * len(values))) - 1))
    return values[index]


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
        "abs_p95": percentile_abs(rows, key, 0.95),
    }


def trapezoid_area(rows, key):
    return sum(
        0.5 * (left[key] + right[key]) * (right["time"] - left["time"])
        for left, right in zip(rows, rows[1:])
    )


def unwrap_phase(rows, key):
    """Unwrap adjacent raw phase samples while retaining the raw column."""
    if not rows:
        return
    rows[0][f"_{key}_unwrapped"] = rows[0][key]
    internal_key = f"_{key}_unwrapped"
    for previous, current in zip(rows, rows[1:]):
        delta = current[key] - previous[key]
        while delta > math.pi:
            delta -= PI2
        while delta < -math.pi:
            delta += PI2
        current[internal_key] = previous[internal_key] + delta


def phase_sample(row, phase_key, voltage_key):
    return {
        "time_ps": row["_time_ps"],
        "raw_phase_rad": row[phase_key],
        "unwrapped_phase_rad": row[f"_{phase_key}_unwrapped"],
        "voltage_V": row[voltage_key],
    }


def monotonic_segments(rows, phase_key, voltage_key):
    """Return sign-consistent continuous phase segments."""
    if len(rows) < 2:
        return []
    internal_key = f"_{phase_key}_unwrapped"
    deltas = [
        right[internal_key] - left[internal_key]
        for left, right in zip(rows, rows[1:])
    ]
    start = 0
    direction = None
    segments = []

    def append_segment(segment_start, segment_end, segment_direction):
        if segment_end <= segment_start or segment_direction is None:
            return
        left = rows[segment_start]
        right = rows[segment_end]
        delta_rad = right[internal_key] - left[internal_key]
        phase_turns = delta_rad / PI2
        area_turns = trapezoid_area(rows[segment_start : segment_end + 1], voltage_key) / PHI0_WB
        abs_turns = abs(phase_turns)
        complete_units = int(math.floor(abs_turns + 1e-9))
        segments.append(
            {
                "start_index": segment_start,
                "end_index": segment_end,
                "start_time_ps": left["_time_ps"],
                "end_time_ps": right["_time_ps"],
                "direction": "increasing" if segment_direction > 0 else "decreasing",
                "direction_sign": segment_direction,
                "raw_phase_start_rad": left[phase_key],
                "raw_phase_end_rad": right[phase_key],
                "unwrapped_phase_start_rad": left[internal_key],
                "unwrapped_phase_end_rad": right[internal_key],
                "phase_delta_rad": delta_rad,
                "phase_delta_turns": phase_turns,
                "phase_abs_turns": abs_turns,
                "same_junction_voltage_area_Wb": trapezoid_area(rows[segment_start : segment_end + 1], voltage_key),
                "same_junction_voltage_area_turns": area_turns,
                "area_minus_phase_turns": area_turns - phase_turns,
                "area_consistent_0p05_turns": abs(area_turns - phase_turns) <= 0.05,
                "complete_units": complete_units,
                "complete_2pi": complete_units >= 1,
                "rows": segment_end - segment_start + 1,
                "endpoint_samples": {
                    "start": phase_sample(left, phase_key, voltage_key),
                    "end": phase_sample(right, phase_key, voltage_key),
                },
            }
        )

    for index, delta in enumerate(deltas):
        sign = 1 if delta > 0.0 else -1 if delta < 0.0 else 0
        if sign == 0:
            continue
        if direction is None:
            direction = sign
        elif sign != direction:
            append_segment(start, index, direction)
            start = index
            direction = sign
    append_segment(start, len(rows) - 1, direction)
    return segments


def trajectory_summary(rows, phase_key, voltage_key):
    if not rows:
        return {"rows": 0, "samples_first": [], "samples_last": [], "turning_points": []}
    internal_key = f"_{phase_key}_unwrapped"
    turning = []
    for left, middle, right in zip(rows, rows[1:], rows[2:]):
        before = middle[internal_key] - left[internal_key]
        after = right[internal_key] - middle[internal_key]
        if before * after < 0.0:
            turning.append(phase_sample(middle, phase_key, voltage_key))
    return {
        "rows": len(rows),
        "time_start_ps": rows[0]["_time_ps"],
        "time_end_ps": rows[-1]["_time_ps"],
        "raw_phase_start_rad": rows[0][phase_key],
        "raw_phase_end_rad": rows[-1][phase_key],
        "raw_phase_min_rad": min(row[phase_key] for row in rows),
        "raw_phase_max_rad": max(row[phase_key] for row in rows),
        "unwrapped_phase_start_rad": rows[0][internal_key],
        "unwrapped_phase_end_rad": rows[-1][internal_key],
        "unwrapped_phase_min_rad": min(row[internal_key] for row in rows),
        "unwrapped_phase_max_rad": max(row[internal_key] for row in rows),
        "turning_points": turning,
        "samples_first": [phase_sample(row, phase_key, voltage_key) for row in rows[:5]],
        "samples_last": [phase_sample(row, phase_key, voltage_key) for row in rows[-5:]],
    }


def phase_window_result(rows, interval, phase_key, voltage_key):
    part = select(rows, interval)
    if not part:
        return {
            "interval_ps": list(interval),
            "rows": 0,
            "segments": [],
            "complete_transition_units": 0,
            "complete_2pi": False,
        }
    phase_segments = monotonic_segments(part, phase_key, voltage_key)
    complete_units = sum(segment["complete_units"] for segment in phase_segments)
    raw = [row[phase_key] for row in part]
    unwrapped = [row[f"_{phase_key}_unwrapped"] for row in part]
    return {
        "interval_ps": list(interval),
        "rows": len(part),
        "trajectory": trajectory_summary(part, phase_key, voltage_key),
        "segments": phase_segments,
        "segment_count": len(phase_segments),
        "complete_transition_units": complete_units,
        "complete_2pi": complete_units >= 1,
        "largest_abs_segment": max(phase_segments, key=lambda item: item["phase_abs_turns"], default=None),
        "largest_abs_segment_turns": max(
            (segment["phase_abs_turns"] for segment in phase_segments), default=0.0
        ),
        "raw_phase_range_rad": max(raw) - min(raw),
        "raw_phase_range_turns": (max(raw) - min(raw)) / PI2,
        "unwrapped_phase_range_rad": max(unwrapped) - min(unwrapped),
        "unwrapped_phase_range_turns": (max(unwrapped) - min(unwrapped)) / PI2,
        "endpoint_delta_rad": unwrapped[-1] - unwrapped[0],
        "endpoint_delta_turns": (unwrapped[-1] - unwrapped[0]) / PI2,
        "same_junction_voltage_area_Wb": trapezoid_area(part, voltage_key),
        "same_junction_voltage_area_turns": trapezoid_area(part, voltage_key) / PHI0_WB,
        "same_junction_voltage_abs_peak_uV": 1e6 * extrema(part, voltage_key)["abs_peak"],
        "same_junction_voltage_abs_peak_time_ps": extrema(part, voltage_key)["abs_peak_time_ps"],
    }


def signal_window_result(rows, interval, keys):
    part = select(rows, interval)
    return {
        "interval_ps": list(interval),
        "rows": len(part),
        "signals": {
            key: {"median": median(part, key), **extrema(part, key)} for key in keys
        }
        if part
        else {},
    }


def summarize_case(point, case_id, logical_state, read_kind):
    path = ROOT / "raw" / point["id"] / case_id / "run-01.csv"
    fields, rows = load_csv(path)
    missing = [key for key in REQUIRED if key not in fields]
    times = [row["_time_ps"] for row in rows]
    dts = [right - left for left, right in zip(times, times[1:])]
    finite = all(
        math.isfinite(value) for row in rows for key, value in row.items() if key != "_time_ps"
    )
    increasing = all(right > left for left, right in zip(times, times[1:]))
    unwrap_phase(rows, TRIGGER_PHASE)
    unwrap_phase(rows, OUTPUT_PHASE)

    trigger = {
        "read_activity": phase_window_result(rows, WINDOWS["READ_ACTIVITY"], TRIGGER_PHASE, TRIGGER_VOLTAGE),
        "trigger_analysis": phase_window_result(rows, WINDOWS["TRIGGER_ANALYSIS"], TRIGGER_PHASE, TRIGGER_VOLTAGE),
        "post": phase_window_result(rows, WINDOWS["POST"], TRIGGER_PHASE, TRIGGER_VOLTAGE),
    }
    output = {
        "output_analysis": phase_window_result(rows, WINDOWS["OUTPUT_ANALYSIS"], OUTPUT_PHASE, OUTPUT_VOLTAGE),
        "read_output_window": phase_window_result(rows, WINDOWS["READ_OUTPUT_WINDOW"], OUTPUT_PHASE, OUTPUT_VOLTAGE),
        "post": phase_window_result(rows, WINDOWS["POST"], OUTPUT_PHASE, OUTPUT_VOLTAGE),
        "post_early": phase_window_result(rows, WINDOWS["POST_EARLY"], OUTPUT_PHASE, OUTPUT_VOLTAGE),
        "post_late": phase_window_result(rows, WINDOWS["POST_LATE"], OUTPUT_PHASE, OUTPUT_VOLTAGE),
        "control_full": phase_window_result(rows, WINDOWS["CONTROL_FULL"], OUTPUT_PHASE, OUTPUT_VOLTAGE),
    }
    all_output_segments = output["output_analysis"]["segments"]
    qualifying = [
        segment
        for segment in all_output_segments
        if segment["complete_units"] >= 1
        and WINDOWS["READ_OUTPUT_WINDOW"][0] <= segment["start_time_ps"] <= WINDOWS["READ_OUTPUT_WINDOW"][1]
    ]
    output["read_triggered_complete_segments"] = qualifying
    output["read_triggered_complete_units"] = sum(segment["complete_units"] for segment in qualifying)
    output["one_shot_candidate"] = (
        output["output_analysis"]["complete_transition_units"] == 1
        and output["read_triggered_complete_units"] == 1
        and len(qualifying) == 1
        and qualifying[0]["area_consistent_0p05_turns"]
        and output["post"]["complete_transition_units"] == 0
    )
    output["area_consistency"] = [
        {
            "start_time_ps": segment["start_time_ps"],
            "end_time_ps": segment["end_time_ps"],
            "phase_delta_turns": segment["phase_delta_turns"],
            "same_junction_voltage_area_turns": segment["same_junction_voltage_area_turns"],
            "area_minus_phase_turns": segment["area_minus_phase_turns"],
            "pass_0p05_turns": segment["area_consistent_0p05_turns"],
        }
        for segment in qualifying
    ]

    pre = select(rows, WINDOWS["PRE"])
    storage_post = select(rows, WINDOWS["STORAGE_POST"])
    storage = {}
    if pre and storage_post:
        for key in ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"]:
            delta = median(storage_post, key) - median(pre, key)
            storage[key] = {
                "pre_median_rad": median(pre, key),
                "post_median_rad": median(storage_post, key),
                "post_minus_pre_rad": delta,
                "post_minus_pre_turns": delta / PI2,
            }

    source_keys = ["V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "I(L_PSL|XBVM1)"]
    trigger_current_keys = [
        TRIGGER_PHASE,
        TRIGGER_VOLTAGE,
        "I(B_TRIG|XTRIG)",
        "I(R_IN|XTRIG)",
        "I(I_TRIG_BIAS|XTRIG)",
        "I(L_Q|XTRIG)",
        "I(R_Q|XTRIG)",
    ]
    output_current_keys = [
        OUTPUT_PHASE,
        OUTPUT_VOLTAGE,
        "I(B_OUT|XTRIG)",
        "I(L_SEC|XTRIG)",
        "I(R_OUT_DAMP|XTRIG)",
        "I(R_LOAD|XTRIG)",
        "I(I_OUT_BIAS|XTRIG)",
        "V(OUT_PORT|XTRIG)",
    ]
    readout_keys = [
        "P(B_JS1|XBVM1)",
        "P(B_JS2|XBVM1)",
        "V(B_JS1|XBVM1)",
        "V(B_JS2|XBVM1)",
    ]
    activity = select(rows, WINDOWS["READ_ACTIVITY"])
    effective_drive = [row["I(R_IN|XTRIG)"] + row["I(I_TRIG_BIAS|XTRIG)"] for row in activity]
    post_output = signal_window_result(
        rows,
        WINDOWS["POST"],
        [OUTPUT_PHASE, OUTPUT_VOLTAGE, "I(B_OUT|XTRIG)", "I(L_SEC|XTRIG)", "I(R_LOAD|XTRIG)", "V(OUT_PORT|XTRIG)"],
    )

    return {
        "case_id": case_id,
        "logical_state": logical_state,
        "read_kind": read_kind,
        "operating_point": point,
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
        "output": output,
        "same_junction_probes": {
            "trigger_phase": TRIGGER_PHASE,
            "trigger_voltage": TRIGGER_VOLTAGE,
            "output_phase": OUTPUT_PHASE,
            "output_voltage": OUTPUT_VOLTAGE,
            "direction": "B_TRIG N_TRIG->0; B_OUT N_OUT->N_SEC",
            "criterion": "monotonic continuous phase segments plus same-segment voltage area; no peak/current shortcut",
        },
        "source_and_currents": {
            "source": signal_window_result(rows, WINDOWS["READ_ACTIVITY"], source_keys),
            "trigger": signal_window_result(rows, WINDOWS["READ_ACTIVITY"], trigger_current_keys),
            "output": signal_window_result(rows, WINDOWS["READ_ACTIVITY"], output_current_keys),
            "output_post": post_output,
            "output_post_early": signal_window_result(rows, WINDOWS["POST_EARLY"], output_current_keys),
            "output_post_late": signal_window_result(rows, WINDOWS["POST_LATE"], output_current_keys),
            "effective_trigger_drive_signed_peak_uA": 1e6 * max(effective_drive, key=abs) if effective_drive else None,
            "effective_trigger_drive_positive_peak_uA": 1e6 * max(effective_drive) if effective_drive else None,
        },
        "storage": storage,
        "readout": {
            key: signal_window_result(rows, WINDOWS["READ_ACTIVITY"], [key]) for key in readout_keys
        },
    }


def main():
    operating_points = []
    for point in POINTS:
        cases = {}
        for case_id, logical_state, read_kind in CASES:
            path = ROOT / "raw" / point["id"] / case_id / "run-01.csv"
            if path.exists():
                cases[case_id] = summarize_case(point, case_id, logical_state, read_kind)
        if cases:
            operating_points.append(
                {
                    "id": point["id"],
                    "parameters": point,
                    "matched_case_count": len(cases),
                    "matched_matrix_complete": len(cases) == len(CASES),
                    "cases": cases,
                }
            )
    result = {
        "document_type": "r1_raw_analysis",
        "analysis_version": "r1-segment-units-1",
        "phi0_Wb": PHI0_WB,
        "metric_boundary": "P is raw radians; unwrapped phase is continuous adjacent-sample reconstruction; turns=delta/(2*pi); same-JJ voltage area uses actual CSV time; complete units=floor(abs(monotonic delta turns)); no SFQ count is inferred.",
        "windows_ps": WINDOWS,
        "criterion": {
            "output_one_shot": "exactly one complete transition unit in OUTPUT_ANALYSIS, its segment starts in READ_OUTPUT_WINDOW, same-segment area residual <=0.05 turns, and POST contains zero complete units",
            "controls": "zero complete output units over CONTROL_FULL",
            "trigger": "B_TRIG segments are reported but not required to be one-shot",
        },
        "operating_points": operating_points,
    }
    out = ROOT / "analysis" / "r1-analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    for operating_point in operating_points:
        for case in operating_point["cases"].values():
            trigger_units = case["trigger"]["trigger_analysis"]["complete_transition_units"]
            output_units = case["output"]["output_analysis"]["complete_transition_units"]
            largest = case["output"]["output_analysis"]["largest_abs_segment_turns"]
            print(
                f"{operating_point['id']} {case['case_id']}: trigger_units={trigger_units}, "
                f"output_units={output_units}, output_largest_segment={largest:.9g} turns, "
                f"one_shot_candidate={case['output']['one_shot_candidate']}"
            )


if __name__ == "__main__":
    main()
