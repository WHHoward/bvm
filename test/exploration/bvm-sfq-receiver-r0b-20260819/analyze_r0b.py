#!/usr/bin/env python3
"""Independent R0b raw-CSV analysis.

The complete-trigger criterion is deliberately based on the same B_TRIG
junction's raw phase trajectory and voltage.  A current sample above Ic or a
voltage peak is never treated as a switching event.  Phase is stored in raw
radians, then unwrapped continuously before monotonic segments are found.
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
OPERATING_POINTS = [
    {"id": "a050-b15", "area": 0.50, "bias_uA": 15.0, "ic_uA": 50.0, "rn_ohm": 32.0, "r0_ohm": 320.0, "c_fF": 35.0},
    {"id": "a050-b20", "area": 0.50, "bias_uA": 20.0, "ic_uA": 50.0, "rn_ohm": 32.0, "r0_ohm": 320.0, "c_fF": 35.0},
    {"id": "a045-b20", "area": 0.45, "bias_uA": 20.0, "ic_uA": 45.0, "rn_ohm": 16.0 / 0.45, "r0_ohm": 160.0 / 0.45, "c_fF": 0.07 * 1000.0 * 0.45},
    {"id": "a040-b20", "area": 0.40, "bias_uA": 20.0, "ic_uA": 40.0, "rn_ohm": 16.0 / 0.40, "r0_ohm": 160.0 / 0.40, "c_fF": 0.07 * 1000.0 * 0.40},
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
    "TRIGGER_ANALYSIS": (94.0, 170.0),
    "POST": (130.0, 170.0),
    "POST_EARLY": (130.0, 140.0),
    "POST_LATE": (160.0, 170.0),
    "CONTROL_FULL": (20.0, 170.0),
    "STORAGE_POST": (140.0, 150.0),
}
PHASE_KEY = "P(B_TRIG|XTRIG)"
VOLTAGE_KEY = "V(B_TRIG|XTRIG)"
REQUIRED = [
    "time",
    PHASE_KEY,
    VOLTAGE_KEY,
    "I(B_TRIG|XTRIG)",
    "I(R_IN|XTRIG)",
    "I(I_TRIG_BIAS|XTRIG)",
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


def med(rows, key):
    return statistics.median(row[key] for row in rows)


def extrema(rows, key):
    low = min(rows, key=lambda row: row[key])
    high = max(rows, key=lambda row: row[key])
    abs_peak = max(rows, key=lambda row: abs(row[key]))
    return {
        "min": low[key],
        "min_time_ps": low["_time_ps"],
        "max": high[key],
        "max_time_ps": high["_time_ps"],
        "abs_peak": abs_peak[key],
        "abs_peak_time_ps": abs_peak["_time_ps"],
    }


def trapezoid_area(rows, key):
    return sum(
        0.5 * (left[key] + right[key]) * (right["time"] - left["time"])
        for left, right in zip(rows, rows[1:])
    )


def unwrap_phase(rows):
    """Add a continuous unwrapped phase without changing the raw P column."""
    if not rows:
        return
    rows[0]["_unwrapped_phase_rad"] = rows[0][PHASE_KEY]
    for previous, current in zip(rows, rows[1:]):
        delta = current[PHASE_KEY] - previous[PHASE_KEY]
        while delta > math.pi:
            delta -= PI2
        while delta < -math.pi:
            delta += PI2
        current["_unwrapped_phase_rad"] = previous["_unwrapped_phase_rad"] + delta


def phase_sample(row):
    return {
        "time_ps": row["_time_ps"],
        "raw_phase_rad": row[PHASE_KEY],
        "unwrapped_phase_rad": row["_unwrapped_phase_rad"],
        "voltage_V": row[VOLTAGE_KEY],
    }


def monotonic_segments(rows):
    """Return strict sign-consistent phase segments over the supplied rows.

    A zero adjacent delta is retained in the current segment.  When the sign
    changes, the turning-point row belongs to both neighboring segments so
    each segment's phase delta and voltage area share the same endpoints.
    """
    if len(rows) < 2:
        return []
    deltas = [
        right["_unwrapped_phase_rad"] - left["_unwrapped_phase_rad"]
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
        delta_rad = right["_unwrapped_phase_rad"] - left["_unwrapped_phase_rad"]
        area_wb = trapezoid_area(rows[segment_start: segment_end + 1], VOLTAGE_KEY)
        segments.append(
            {
                "start_index": segment_start,
                "end_index": segment_end,
                "start_time_ps": left["_time_ps"],
                "end_time_ps": right["_time_ps"],
                "direction": "increasing" if segment_direction > 0 else "decreasing",
                "direction_sign": segment_direction,
                "raw_phase_start_rad": left[PHASE_KEY],
                "raw_phase_end_rad": right[PHASE_KEY],
                "unwrapped_phase_start_rad": left["_unwrapped_phase_rad"],
                "unwrapped_phase_end_rad": right["_unwrapped_phase_rad"],
                "phase_delta_rad": delta_rad,
                "phase_delta_turns": delta_rad / PI2,
                "phase_abs_turns": abs(delta_rad) / PI2,
                "same_junction_voltage_area_Wb": area_wb,
                "same_junction_voltage_area_turns": area_wb / PHI0_WB,
                "area_minus_phase_turns": area_wb / PHI0_WB - delta_rad / PI2,
                "rows": segment_end - segment_start + 1,
                "complete_2pi": abs(delta_rad) >= PI2,
                "endpoint_samples": {
                    "start": phase_sample(left),
                    "end": phase_sample(right),
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


def trajectory_summary(rows):
    if not rows:
        return {"rows": 0, "samples_first": [], "samples_last": [], "turning_points": []}
    turning = []
    for left, middle, right in zip(rows, rows[1:], rows[2:]):
        before = middle["_unwrapped_phase_rad"] - left["_unwrapped_phase_rad"]
        after = right["_unwrapped_phase_rad"] - middle["_unwrapped_phase_rad"]
        if before * after < 0.0:
            turning.append(phase_sample(middle))
    return {
        "rows": len(rows),
        "time_start_ps": rows[0]["_time_ps"],
        "time_end_ps": rows[-1]["_time_ps"],
        "raw_phase_start_rad": rows[0][PHASE_KEY],
        "raw_phase_end_rad": rows[-1][PHASE_KEY],
        "raw_phase_min_rad": min(row[PHASE_KEY] for row in rows),
        "raw_phase_max_rad": max(row[PHASE_KEY] for row in rows),
        "unwrapped_phase_start_rad": rows[0]["_unwrapped_phase_rad"],
        "unwrapped_phase_end_rad": rows[-1]["_unwrapped_phase_rad"],
        "unwrapped_phase_min_rad": min(row["_unwrapped_phase_rad"] for row in rows),
        "unwrapped_phase_max_rad": max(row["_unwrapped_phase_rad"] for row in rows),
        "turning_points": turning,
        "samples_first": [phase_sample(row) for row in rows[:5]],
        "samples_last": [phase_sample(row) for row in rows[-5:]],
    }


def segment_result(rows):
    segments = monotonic_segments(rows)
    complete = [segment for segment in segments if segment["complete_2pi"]]
    largest = max(segments, key=lambda segment: segment["phase_abs_turns"], default=None)
    return {
        "trajectory": trajectory_summary(rows),
        "segments": segments,
        "segment_count": len(segments),
        "complete_2pi_segments": complete,
        "complete_2pi": bool(complete),
        "largest_abs_segment": largest,
        "largest_abs_segment_turns": largest["phase_abs_turns"] if largest else 0.0,
    }


def phase_window_result(rows, interval):
    part = select(rows, interval)
    if not part:
        return {"interval_ps": list(interval), "rows": 0, "segments": [], "complete_2pi": False}
    raw = [row[PHASE_KEY] for row in part]
    unwrapped = [row["_unwrapped_phase_rad"] for row in part]
    result = segment_result(part)
    result.update(
        {
            "interval_ps": list(interval),
            "rows": len(part),
            "raw_phase_range_rad": max(raw) - min(raw),
            "raw_phase_range_turns": (max(raw) - min(raw)) / PI2,
            "unwrapped_phase_range_rad": max(unwrapped) - min(unwrapped),
            "unwrapped_phase_range_turns": (max(unwrapped) - min(unwrapped)) / PI2,
            "endpoint_delta_rad": unwrapped[-1] - unwrapped[0],
            "endpoint_delta_turns": (unwrapped[-1] - unwrapped[0]) / PI2,
            "same_junction_voltage_area_Wb": trapezoid_area(part, VOLTAGE_KEY),
            "same_junction_voltage_area_turns": trapezoid_area(part, VOLTAGE_KEY) / PHI0_WB,
            "same_junction_voltage_abs_peak_uV": 1e6 * extrema(part, VOLTAGE_KEY)["abs_peak"],
            "same_junction_voltage_abs_peak_time_ps": extrema(part, VOLTAGE_KEY)["abs_peak_time_ps"],
        }
    )
    return result


def signal_window_result(rows, interval, keys):
    part = select(rows, interval)
    return {
        "interval_ps": list(interval),
        "rows": len(part),
        "signals": {
            key: {
                "median": med(part, key),
                **extrema(part, key),
            }
            for key in keys
        }
        if part
        else {},
    }


def summarize_case(op, case_id, logical_state, read_kind):
    path = ROOT / "raw" / op["id"] / case_id / "run-01.csv"
    fields, rows = load_csv(path)
    missing = [key for key in REQUIRED if key not in fields]
    times = [row["_time_ps"] for row in rows]
    finite = all(
        math.isfinite(value) for row in rows for key, value in row.items() if key != "_time_ps"
    )
    increasing = all(right > left for left, right in zip(times, times[1:]))
    dts = [right - left for left, right in zip(times, times[1:])]
    unwrap_phase(rows)
    activity = select(rows, WINDOWS["READ_ACTIVITY"])
    trigger_window = select(rows, WINDOWS["TRIGGER_ANALYSIS"])
    storage_post = select(rows, WINDOWS["STORAGE_POST"])
    pre = select(rows, WINDOWS["PRE"])
    readout_keys = [
        "P(B_JS1|XBVM1)",
        "P(B_JS2|XBVM1)",
        "V(B_JS1|XBVM1)",
        "V(B_JS2|XBVM1)",
    ]
    source_keys = ["V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "I(L_PSL|XBVM1)"]
    current_keys = ["I(B_TRIG|XTRIG)", "I(R_IN|XTRIG)", "I(I_TRIG_BIAS|XTRIG)"]

    phase = {
        "activity": phase_window_result(rows, WINDOWS["READ_ACTIVITY"]),
        "trigger_analysis": phase_window_result(rows, WINDOWS["TRIGGER_ANALYSIS"]),
        "post": phase_window_result(rows, WINDOWS["POST"]),
        "post_early": phase_window_result(rows, WINDOWS["POST_EARLY"]),
        "post_late": phase_window_result(rows, WINDOWS["POST_LATE"]),
        "control_full": phase_window_result(rows, WINDOWS["CONTROL_FULL"]),
    }
    qualifying = [
        segment
        for segment in phase["trigger_analysis"]["segments"]
        if segment["complete_2pi"] and segment["start_time_ps"] <= WINDOWS["READ_ACTIVITY"][1]
    ]
    phase["qualifying_read_trigger_segments"] = qualifying
    phase["qualifying_read_trigger"] = bool(qualifying)

    storage = {}
    if pre and storage_post:
        for key in ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"]:
            delta = med(storage_post, key) - med(pre, key)
            storage[key] = {
                "pre_median_rad": med(pre, key),
                "post_median_rad": med(storage_post, key),
                "post_minus_pre_rad": delta,
                "post_minus_pre_turns": delta / PI2,
            }

    effective = [
        row["I(R_IN|XTRIG)"] + row["I(I_TRIG_BIAS|XTRIG)"]
        for row in activity
    ]
    source = signal_window_result(rows, WINDOWS["READ_ACTIVITY"], source_keys)
    currents = signal_window_result(rows, WINDOWS["READ_ACTIVITY"], current_keys)
    post_receiver = signal_window_result(
        rows,
        WINDOWS["POST"],
        [PHASE_KEY, VOLTAGE_KEY, "I(B_TRIG|XTRIG)", "I(R_IN|XTRIG)", "I(I_TRIG_BIAS|XTRIG)"],
    )
    source["effective_drive_positive_peak_uA"] = 1e6 * max(effective) if effective else None
    source["effective_drive_signed_peak_uA"] = 1e6 * max(effective, key=abs) if effective else None

    return {
        "case_id": case_id,
        "logical_state": logical_state,
        "read_kind": read_kind,
        "operating_point": op,
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
        "phase": phase,
        "same_junction": {
            "phase_probe": PHASE_KEY,
            "voltage_probe": VOLTAGE_KEY,
            "direction": "B_TRIG N_TRIG -> 0",
            "criterion": "complete_2pi requires one monotonic unwrapped phase segment with abs(delta)>=2*pi; voltage area is reported for that same segment",
        },
        "source_and_receiver": {
            "signals": source,
            "currents": currents,
            "post_receiver": post_receiver,
            "post_receiver_early": signal_window_result(
                rows, WINDOWS["POST_EARLY"], [VOLTAGE_KEY, "I(R_IN|XTRIG)"]
            ),
            "post_receiver_late": signal_window_result(
                rows, WINDOWS["POST_LATE"], [VOLTAGE_KEY, "I(R_IN|XTRIG)"]
            ),
        },
        "storage": storage,
        "readout": {
            key: signal_window_result(rows, WINDOWS["READ_ACTIVITY"], [key])
            for key in readout_keys
        },
    }


def main():
    operating_points = []
    for op in OPERATING_POINTS:
        cases = {}
        for case_id, logical_state, read_kind in CASES:
            path = ROOT / "raw" / op["id"] / case_id / "run-01.csv"
            if not path.exists():
                continue
            cases[case_id] = summarize_case(op, case_id, logical_state, read_kind)
        if not cases:
            continue
        operating_points.append(
            {
                "id": op["id"],
                "parameters": op,
                "matched_case_count": len(cases),
                "matched_matrix_complete": len(cases) == len(CASES),
                "cases": cases,
            }
        )

    result = {
        "document_type": "r0b_raw_analysis",
        "analysis_version": "r0b-segment-1",
        "phi0_Wb": PHI0_WB,
        "metric_boundary": "P is raw radians; continuous phase is unwrapped from adjacent raw samples; turns=delta_rad/(2*pi); same-JJ voltage area uses actual CSV time; no SFQ count is inferred.",
        "windows_ps": WINDOWS,
        "complete_trigger_rule": "at least one monotonic segment in TRIGGER_ANALYSIS starting no later than 130 ps with abs(unwrapped phase delta)>=2*pi; its same-segment voltage area must be reported; I>Ic and voltage peak are not switching criteria",
        "operating_points": operating_points,
    }
    out = ROOT / "analysis" / "r0b-analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    for op in operating_points:
        for case in op["cases"].values():
            largest = case["phase"]["trigger_analysis"]["largest_abs_segment_turns"]
            qualifying = len(case["phase"]["qualifying_read_trigger_segments"])
            print(f"{op['id']} {case['case_id']}: largest_trigger_segment={largest:.9g} turns, qualifying_complete={qualifying}")


if __name__ == "__main__":
    main()
