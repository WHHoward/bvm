#!/usr/bin/env python3
"""Primary raw-CSV analysis for the R2-B B_OUT local damping Exploration."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_ID = "run-01"
PHI0_WB = 2.067833848e-15
TWO_PI = 2.0 * math.pi
POINT_ID = os.environ.get("POINT_ID", "k095-r100")

RDAMP_OHM = float(os.environ.get("RDAMP_OHM", "100.0"))
COUPLING_K = 0.95
_RN_OUT = 160.0
_REFF = _RN_OUT * RDAMP_OHM / (_RN_OUT + RDAMP_OHM)
_BETA_C = (
    2.0 * math.pi * 10e-6 * _REFF * _REFF * 7e-15 / PHI0_WB
)

POINT = {
    "id": POINT_ID,
    "trigger_area": 0.50,
    "trigger_bias_uA": 15.0,
    "trigger_ic_uA": 50.0,
    "trigger_rn_ohm": 32.0,
    "trigger_r0_ohm": 320.0,
    "trigger_c_fF": 35.0,
    "l_tx_pH": 0.20,
    "l_sec_pH": 2.0,
    "coupling_k": COUPLING_K,
    "r_sec_load_ohm": 12.0,
    "output_area": 0.10,
    "output_bias_uA": 7.0,
    "output_ic_uA": 10.0,
    "output_rn_ohm": 160.0,
    "output_r0_ohm": 1600.0,
    "output_c_fF": 7.0,
    "output_r_damp_ohm": RDAMP_OHM,
    "output_reff_ohm": _REFF,
    "output_beta_c_reff": _BETA_C,
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
    "OUTPUT_ANALYSIS": (94.0, 170.0),
    "POST": (130.0, 170.0),
    "CONTROL_FULL": (20.0, 170.0),
    "STORAGE_POST": (140.0, 150.0),
}
TRIG_PHASE = "P(B_TRIG|XTRIG)"
TRIG_VOLTAGE = "V(B_TRIG|XTRIG)"
OUT_PHASE = "P(B_OUT|XTRIG)"
OUT_VOLTAGE = "V(B_OUT|XTRIG)"
SECONDARY_VOLTAGE = "V(N_SEC|XTRIG)"
SECONDARY_LOAD_CURRENT = "I(R_SEC_LOAD|XTRIG)"
SECONDARY_COIL_CURRENT = "I(L_SEC|XTRIG)"
REQUIRED = [
    "time",
    TRIG_PHASE,
    TRIG_VOLTAGE,
    "I(B_TRIG|XTRIG)",
    "I(R_IN|XTRIG)",
    "I(L_TX|XTRIG)",
    "I(I_TRIG_BIAS|XTRIG)",
    "V(N_PICK|XTRIG)",
    "V(N_TRIG|XTRIG)",
    OUT_PHASE,
    OUT_VOLTAGE,
    "I(B_OUT|XTRIG)",
    "I(I_OUT_BIAS|XTRIG)",
    "I(R_OUT_DAMP|XTRIG)",
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


def unwrap_phase(rows, phase_key, state_key):
    if not rows:
        return
    rows[0][state_key] = rows[0][phase_key]
    for previous, current in zip(rows, rows[1:]):
        delta = current[phase_key] - previous[phase_key]
        while delta > math.pi:
            delta -= TWO_PI
        while delta < -math.pi:
            delta += TWO_PI
        current[state_key] = previous[state_key] + delta


def phase_sample(row, phase_key, voltage_key, state_key):
    return {
        "time_ps": row["_time_ps"],
        "raw_phase_rad": row[phase_key],
        "unwrapped_phase_rad": row[state_key],
        "voltage_V": row[voltage_key],
    }


def monotonic_segments(rows, phase_key, voltage_key, state_key):
    if len(rows) < 2:
        return []
    deltas = [
        right[state_key] - left[state_key]
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
        delta_rad = right[state_key] - left[state_key]
        delta_turns = delta_rad / TWO_PI
        same_rows = rows[start : end + 1]
        area_wb = trapezoid_area(same_rows, voltage_key)
        area_turns = area_wb / PHI0_WB
        abs_turns = abs(delta_turns)
        segments.append(
            {
                "start_time_ps": left["_time_ps"],
                "end_time_ps": right["_time_ps"],
                "direction": "increasing" if sign > 0 else "decreasing",
                "direction_sign": sign,
                "raw_phase_start_rad": left[phase_key],
                "raw_phase_end_rad": right[phase_key],
                "unwrapped_phase_start_rad": left[state_key],
                "unwrapped_phase_end_rad": right[state_key],
                "phase_delta_rad": delta_rad,
                "phase_delta_turns": delta_turns,
                "phase_abs_turns": abs_turns,
                "same_junction_voltage_area_Wb": area_wb,
                "same_junction_voltage_area_turns": area_turns,
                "area_minus_phase_turns": area_turns - delta_turns,
                "area_consistent_0p05_turns": abs(area_turns - delta_turns) <= 0.05,
                "complete_2pi": abs_turns >= 1.0,
                "complete_turn_units": int(math.floor(abs_turns + 1e-9)),
                "rows": end - start + 1,
                "endpoint_samples": {
                    "start": phase_sample(left, phase_key, voltage_key, state_key),
                    "end": phase_sample(right, phase_key, voltage_key, state_key),
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
            append_segment(index, direction)
            start = index
            direction = sign
    append_segment(len(rows) - 1, direction)
    return segments


def phase_window_result(rows, interval, phase_key, voltage_key, state_key):
    part = select(rows, interval)
    if not part:
        return {
            "interval_ps": list(interval),
            "rows": 0,
            "segments": [],
            "complete_segments": [],
            "complete_2pi": False,
            "complete_turn_units": 0,
        }
    segments = monotonic_segments(part, phase_key, voltage_key, state_key)
    raw = [row[phase_key] for row in part]
    unwrapped = [row[state_key] for row in part]
    complete = [segment for segment in segments if segment["complete_2pi"]]
    return {
        "interval_ps": list(interval),
        "rows": len(part),
        "trajectory": {
            "raw_phase_start_rad": part[0][phase_key],
            "raw_phase_end_rad": part[-1][phase_key],
            "raw_phase_min_rad": min(raw),
            "raw_phase_max_rad": max(raw),
            "unwrapped_phase_start_rad": part[0][state_key],
            "unwrapped_phase_end_rad": part[-1][state_key],
            "unwrapped_phase_min_rad": min(unwrapped),
            "unwrapped_phase_max_rad": max(unwrapped),
            "unwrapped_phase_range_turns": (max(unwrapped) - min(unwrapped)) / TWO_PI,
            "samples_first": [
                phase_sample(row, phase_key, voltage_key, state_key)
                for row in part[:5]
            ],
            "samples_last": [
                phase_sample(row, phase_key, voltage_key, state_key)
                for row in part[-5:]
            ],
        },
        "segments": segments,
        "complete_segments": complete,
        "complete_2pi": bool(complete),
        "complete_turn_units": sum(segment["complete_turn_units"] for segment in segments),
        "largest_abs_segment": max(
            segments, key=lambda segment: segment["phase_abs_turns"], default=None
        ),
        "largest_abs_segment_turns": max(
            (segment["phase_abs_turns"] for segment in segments), default=0.0
        ),
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
    peak = max(deviations, default=0.0)
    return {
        "key": key,
        "pre_median": baseline,
        "activity_abs_deviation_peak": peak,
        "activity_abs_deviation_peak_time_ps": (
            activity[deviations.index(peak)]["_time_ps"] if deviations else None
        ),
        "pre_stats": signal_window_result(rows, WINDOWS["PRE"], [key]),
        "activity_stats": signal_window_result(rows, WINDOWS["READ_ACTIVITY"], [key]),
    }


def qualifying(phase_result, latest_start_ps=130.0):
    return [
        segment
        for segment in phase_result["segments"]
        if segment["complete_2pi"]
        and segment["start_time_ps"] <= latest_start_ps
        and segment["area_consistent_0p05_turns"]
    ]


def summarize_case(case_id, logical_state, read_kind):
    path = ROOT / "raw" / POINT["id"] / case_id / f"{RUN_ID}.csv"
    fields, rows = load_csv(path)
    missing = [key for key in REQUIRED if key not in fields]
    times = [row["_time_ps"] for row in rows]
    dts = [right - left for left, right in zip(times, times[1:])]
    increasing = all(right > left for left, right in zip(times, times[1:]))
    finite = all(
        math.isfinite(value)
        for row in rows
        for key, value in row.items()
        if key != "_time_ps"
    )
    unwrap_phase(rows, TRIG_PHASE, "_btrig_unwrapped")
    unwrap_phase(rows, OUT_PHASE, "_bout_unwrapped")

    trigger_analysis = phase_window_result(
        rows, WINDOWS["TRIGGER_ANALYSIS"], TRIG_PHASE, TRIG_VOLTAGE, "_btrig_unwrapped"
    )
    trigger = {
        "read_activity": phase_window_result(
            rows, WINDOWS["READ_ACTIVITY"], TRIG_PHASE, TRIG_VOLTAGE, "_btrig_unwrapped"
        ),
        "trigger_analysis": trigger_analysis,
        "post": phase_window_result(
            rows, WINDOWS["POST"], TRIG_PHASE, TRIG_VOLTAGE, "_btrig_unwrapped"
        ),
        "control_full": phase_window_result(
            rows, WINDOWS["CONTROL_FULL"], TRIG_PHASE, TRIG_VOLTAGE, "_btrig_unwrapped"
        ),
        "qualifying_read_trigger_segments": qualifying(trigger_analysis),
    }
    trigger["qualifying_read_trigger"] = bool(trigger["qualifying_read_trigger_segments"])

    output_analysis = phase_window_result(
        rows, WINDOWS["OUTPUT_ANALYSIS"], OUT_PHASE, OUT_VOLTAGE, "_bout_unwrapped"
    )
    output = {
        "read_activity": phase_window_result(
            rows, WINDOWS["READ_ACTIVITY"], OUT_PHASE, OUT_VOLTAGE, "_bout_unwrapped"
        ),
        "output_analysis": output_analysis,
        "post": phase_window_result(
            rows, WINDOWS["POST"], OUT_PHASE, OUT_VOLTAGE, "_bout_unwrapped"
        ),
        "control_full": phase_window_result(
            rows, WINDOWS["CONTROL_FULL"], OUT_PHASE, OUT_VOLTAGE, "_bout_unwrapped"
        ),
        "qualifying_read_output_segments": qualifying(output_analysis),
    }
    output["qualifying_read_output"] = bool(output["qualifying_read_output_segments"])

    secondary = {
        key: secondary_amplitude(rows, key)
        for key in [
            SECONDARY_VOLTAGE,
            SECONDARY_LOAD_CURRENT,
            SECONDARY_COIL_CURRENT,
        ]
    }
    storage = {}
    pre = select(rows, WINDOWS["PRE"])
    post = select(rows, WINDOWS["STORAGE_POST"])
    if pre and post:
        for key in ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"]:
            pre_median = median(pre, key)
            post_median = median(post, key)
            delta = post_median - pre_median
            storage[key] = {
                "pre_median_rad": pre_median,
                "post_median_rad": post_median,
                "post_minus_pre_rad": delta,
                "post_minus_pre_turns": delta / TWO_PI,
            }

    source_keys = ["V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "I(L_PSL|XBVM1)"]
    pickup_keys = [
        "I(R_IN|XTRIG)",
        "I(L_TX|XTRIG)",
        "I(I_TRIG_BIAS|XTRIG)",
        "V(N_PICK|XTRIG)",
        "V(N_TRIG|XTRIG)",
    ]
    output_branch_keys = [
        "I(B_OUT|XTRIG)",
        "I(I_OUT_BIAS|XTRIG)",
        "I(R_OUT_DAMP|XTRIG)",
        OUT_VOLTAGE,
    ]
    readout_keys = [
        "P(B_JS1|XBVM1)",
        "P(B_JS2|XBVM1)",
        "V(B_JS1|XBVM1)",
        "V(B_JS2|XBVM1)",
    ]
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
        "output": output,
        "secondary": secondary,
        "pickup": signal_window_result(rows, WINDOWS["READ_ACTIVITY"], pickup_keys),
        "output_branch": signal_window_result(
            rows, WINDOWS["READ_ACTIVITY"], output_branch_keys
        ),
        "source": signal_window_result(rows, WINDOWS["READ_ACTIVITY"], source_keys),
        "storage": storage,
        "readout": {
            key: signal_window_result(rows, WINDOWS["READ_ACTIVITY"], [key])
            for key in readout_keys
        },
        "same_junction": {
            "trigger": {
                "phase_probe": TRIG_PHASE,
                "voltage_probe": TRIG_VOLTAGE,
                "direction": "B_TRIG N_TRIG -> 0",
            },
            "output": {
                "phase_probe": OUT_PHASE,
                "voltage_probe": OUT_VOLTAGE,
                "direction": "B_OUT N_SEC -> 0",
            },
            "criterion": "continuous adjacent-sample phase segments and same-segment direct JJ voltage area",
        },
    }


def build_secondary_guard(cases):
    read1 = cases["read1"]
    read0 = cases["read0"]
    c1 = cases["logical1-read0-control"]
    c0 = cases["logical0-read0-control"]
    outcomes = {}
    for key in [SECONDARY_VOLTAGE, SECONDARY_LOAD_CURRENT]:
        a1 = read1["secondary"][key]["activity_abs_deviation_peak"]
        a0 = read0["secondary"][key]["activity_abs_deviation_peak"]
        ac1 = c1["secondary"][key]["activity_abs_deviation_peak"]
        ac0 = c0["secondary"][key]["activity_abs_deviation_peak"]
        outcomes[key] = {
            "read1_amplitude": a1,
            "read0_amplitude": a0,
            "logical1_control_amplitude": ac1,
            "logical0_control_amplitude": ac0,
            "read1_over_read0": a1 / a0 if a0 else None,
            "read1_over_max_control": a1 / max(ac1, ac0) if max(ac1, ac0) else None,
            "read1_at_least_2x_read0": a1 >= 2.0 * a0,
            "read1_at_least_5x_controls": a1 >= 5.0 * max(ac1, ac0),
            "pass": a1 >= 2.0 * a0 and a1 >= 5.0 * max(ac1, ac0),
        }
    return outcomes


def storage_sign_guard(cases):
    signs = {}
    for case_id, expected in [
        ("read1", 1),
        ("read0", -1),
        ("logical1-read0-control", 1),
        ("logical0-read0-control", -1),
    ]:
        storage = cases[case_id]["storage"]
        signs[case_id] = {
            key: (value["post_median_rad"] * expected > 0)
            for key, value in storage.items()
        }
    return {
        "by_case": signs,
        "pass": all(all(values.values()) for values in signs.values()),
    }


def main():
    cases = {}
    for case_id, logical_state, read_kind in CASES:
        path = ROOT / "raw" / POINT["id"] / case_id / f"{RUN_ID}.csv"
        if path.exists():
            cases[case_id] = summarize_case(case_id, logical_state, read_kind)

    matrix_complete = len(cases) == len(CASES)
    if matrix_complete:
        secondary_guard = build_secondary_guard(cases)
        storage_guard = storage_sign_guard(cases)
    else:
        secondary_guard = {}
        storage_guard = {"pass": False}

    read1 = cases.get("read1", {})
    read0 = cases.get("read0", {})
    read1_trigger = read1.get("trigger", {}).get("qualifying_read_trigger", False)
    read0_trigger = read0.get("trigger", {}).get("qualifying_read_trigger", True)
    control_trigger_complete = [
        cases.get(case_id, {}).get("trigger", {}).get("control_full", {}).get(
            "complete_2pi", True
        )
        for case_id in ["logical1-read0-control", "logical0-read0-control"]
    ]
    read1_output = read1.get("output", {}).get("qualifying_read_output", False)
    read0_output = read0.get("output", {}).get("qualifying_read_output", True)
    control_output_complete = [
        cases.get(case_id, {}).get("output", {}).get("control_full", {}).get(
            "complete_2pi", True
        )
        for case_id in ["logical1-read0-control", "logical0-read0-control"]
    ]
    artifact_valid = matrix_complete and all(
        case["qa"]["artifact_valid"] for case in cases.values()
    )
    trigger_guard = read1_trigger and not read0_trigger and not any(control_trigger_complete)
    output_guard = read1_output and not read0_output and not any(control_output_complete)
    result = {
        "document_type": "r2a_coupling_point_raw_analysis",
        "analysis_version": "r2a-output-coupling-1",
        "phi0_Wb": PHI0_WB,
        "metric_boundary": (
            "P(B_TRIG) and P(B_OUT) are raw radians; turns=delta/(2*pi); "
            "same-JJ voltage areas use actual CSV time and exact segment endpoints; "
            "current and voltage peaks are activity diagnostics, not event counts."
        ),
        "point": POINT,
        "windows_ps": WINDOWS,
        "criterion": {
            "output": "read1 complete B_OUT segment with same-segment area consistency; read0/control none",
            "trigger_guard": "read1 complete B_TRIG; read0/control non-complete",
            "secondary_guard": "read1 secondary remains at least 2x read0 and 5x controls",
            "storage_guard": "JM1/JM2 post signs remain logical-state distinct",
        },
        "matched_case_count": len(cases),
        "matched_matrix_complete": matrix_complete,
        "secondary_guard": secondary_guard,
        "storage_guard": storage_guard,
        "verdict_components": {
            "artifact_valid": artifact_valid,
            "read1_output_complete": read1_output,
            "read0_output_noncomplete": not read0_output,
            "controls_output_noncomplete": not any(control_output_complete),
            "btrig_guard": trigger_guard,
            "secondary_state_dependent_after_loading": bool(
                secondary_guard
            )
            and all(item["pass"] for item in secondary_guard.values()),
            "storage_logical_signs": storage_guard.get("pass", False),
        },
        "cases": cases,
    }
    result["verdict_components"]["r2a_point_pass"] = all(
        result["verdict_components"].values()
    )
    output_name = os.environ.get(
        "ANALYSIS_OUTPUT", f"analysis/{POINT_ID}-analysis.json"
    )
    out = ROOT / output_name
    out.write_text(json.dumps(result, indent=2) + "\n")

    for case in cases.values():
        trig = case["trigger"]["trigger_analysis"]["largest_abs_segment_turns"]
        out_seg = case["output"]["output_analysis"]["largest_abs_segment_turns"]
        out_complete = case["output"]["qualifying_read_output"]
        v_amp = case["secondary"][SECONDARY_VOLTAGE][
            "activity_abs_deviation_peak"
        ]
        i_amp = case["secondary"][SECONDARY_LOAD_CURRENT][
            "activity_abs_deviation_peak"
        ]
        print(
            f"{case['case_id']}: BTRIG_largest={trig:.9g} turns, "
            f"BOUT_largest={out_seg:.9g} turns, BOUT_complete={out_complete}, "
            f"Vsec_amp={v_amp:.9g} V, Isec_amp={i_amp:.9g} A"
        )
    print("artifact_valid=" + str(artifact_valid))
    print("btrig_guard=" + str(trigger_guard))
    print("output_guard=" + str(output_guard))
    print("r2a_point_pass=" + str(result["verdict_components"]["r2a_point_pass"]))


if __name__ == "__main__":
    main()
