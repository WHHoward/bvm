#!/usr/bin/env python3
"""Aggregate the five preregistered R1c B_OUT-bias analysis points."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POINTS = [
    ("diff-a010-b006-r100", 6.0),
    ("diff-a010-b007-r100", 7.0),
    ("diff-a010-b008-r100", 8.0),
    ("diff-a010-b009-r100", 9.0),
    ("diff-a010-b010-r100", 10.0),
]
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]


def load(point: str):
    primary = json.loads((ROOT / "analysis" / f"{point}-analysis.json").read_text())
    cross = json.loads((ROOT / "analysis" / f"{point}-crosscheck.json").read_text())
    return primary, cross


def largest(case: dict, branch: str, window: str = "output_analysis") -> dict:
    return case["output"][window]["largest_abs_segment"] or {
        "phase_abs_turns": 0.0,
        "phase_delta_turns": 0.0,
        "same_junction_voltage_area_turns": 0.0,
        "area_minus_phase_turns": 0.0,
        "start_time_ps": None,
        "end_time_ps": None,
    }


def trigger_largest(case: dict) -> dict:
    return case["trigger"]["trigger_analysis"]["largest_abs_segment"] or {
        "phase_abs_turns": 0.0,
        "phase_delta_turns": 0.0,
        "same_junction_voltage_area_turns": 0.0,
        "area_minus_phase_turns": 0.0,
        "start_time_ps": None,
        "end_time_ps": None,
    }


def signal(case: dict, key: str) -> dict:
    return case["output_branch"]["signals"][key]


def point_row(point: str, bias: float, primary: dict, cross: dict) -> dict:
    cases = primary["cases"]
    read1 = cases["read1"]
    read0 = cases["read0"]
    c1 = cases["logical1-read0-control"]
    c0 = cases["logical0-read0-control"]
    out1 = largest(read1, "output")
    out0 = largest(read0, "output")
    c1_out = largest(c1, "output", "control_full")
    c0_out = largest(c0, "output", "control_full")
    c1_range = c1["output"]["control_full"]["trajectory"]["unwrapped_phase_range_turns"]
    c0_range = c0["output"]["control_full"]["trajectory"]["unwrapped_phase_range_turns"]
    trig1 = trigger_largest(read1)
    trig0 = trigger_largest(read0)
    cross_ok = cross["all_comparisons_pass"]
    controls_complete = c1["output"]["control_full"]["complete_2pi"] or c0[
        "output"
    ]["control_full"]["complete_2pi"]
    return {
        "point_id": point,
        "bias_uA": bias,
        "bias_fraction_of_ic": bias / 10.0,
        "read1_bout_phase_turns": out1["phase_abs_turns"],
        "read1_bout_phase_delta_turns": out1["phase_delta_turns"],
        "read1_bout_voltage_area_turns": out1["same_junction_voltage_area_turns"],
        "read1_bout_area_minus_phase_turns": out1["area_minus_phase_turns"],
        "read1_bout_segment_ps": [out1["start_time_ps"], out1["end_time_ps"]],
        "read0_bout_phase_turns": out0["phase_abs_turns"],
        "read0_bout_phase_delta_turns": out0["phase_delta_turns"],
        "read0_bout_voltage_area_turns": out0["same_junction_voltage_area_turns"],
        "read0_bout_area_minus_phase_turns": out0["area_minus_phase_turns"],
        "read0_bout_segment_ps": [out0["start_time_ps"], out0["end_time_ps"]],
        "logical1_control_bout_phase_turns": c1_out["phase_abs_turns"],
        "logical0_control_bout_phase_turns": c0_out["phase_abs_turns"],
        "logical1_control_bout_phase_range_turns": c1_range,
        "logical0_control_bout_phase_range_turns": c0_range,
        "read1_bout_complete": read1["output"]["qualifying_read_output"],
        "read0_bout_complete": read0["output"]["qualifying_read_output"],
        "controls_bout_complete": controls_complete,
        "read1_bout_voltage_peak_uV": signal(read1, "V(B_OUT|XTRIG)")["abs_peak"] * 1e6,
        "read0_bout_voltage_peak_uV": signal(read0, "V(B_OUT|XTRIG)")["abs_peak"] * 1e6,
        "read1_bout_current_peak_uA": signal(read1, "I(B_OUT|XTRIG)")["abs_peak"] * 1e6,
        "read0_bout_current_peak_uA": signal(read0, "I(B_OUT|XTRIG)")["abs_peak"] * 1e6,
        "read1_btrig_phase_turns": trig1["phase_abs_turns"],
        "read1_btrig_voltage_area_turns": trig1["same_junction_voltage_area_turns"],
        "read0_btrig_phase_turns": trig0["phase_abs_turns"],
        "read0_btrig_voltage_area_turns": trig0["same_junction_voltage_area_turns"],
        "btrig_guard": primary["verdict_components"]["btrig_guard"],
        "read1_secondary_voltage_uV": read1["secondary"]["V(N_SEC|XTRIG)"][
            "activity_abs_deviation_peak"
        ]
        * 1e6,
        "read0_secondary_voltage_uV": read0["secondary"]["V(N_SEC|XTRIG)"][
            "activity_abs_deviation_peak"
        ]
        * 1e6,
        "read1_secondary_return_current_uA": read1["secondary"][
            "I(R_SEC_LOAD|XTRIG)"
        ]["activity_abs_deviation_peak"]
        * 1e6,
        "read0_secondary_return_current_uA": read0["secondary"][
            "I(R_SEC_LOAD|XTRIG)"
        ]["activity_abs_deviation_peak"]
        * 1e6,
        "secondary_read1_over_read0_voltage": read1["secondary"][
            "V(N_SEC|XTRIG)"
        ]["activity_abs_deviation_peak"]
        / read0["secondary"]["V(N_SEC|XTRIG)"]["activity_abs_deviation_peak"],
        "secondary_read1_over_read0_current": read1["secondary"][
            "I(R_SEC_LOAD|XTRIG)"
        ]["activity_abs_deviation_peak"]
        / read0["secondary"]["I(R_SEC_LOAD|XTRIG)"]["activity_abs_deviation_peak"],
        "storage_sign_guard": primary["storage_guard"]["pass"],
        "artifact_valid": primary["verdict_components"]["artifact_valid"],
        "independent_crosscheck": cross_ok,
        "control_free_running": max(c1_range, c0_range) >= 1.0,
    }


def main() -> None:
    rows = []
    points_data = {}
    for point, bias in POINTS:
        primary, cross = load(point)
        row = point_row(point, bias, primary, cross)
        rows.append(row)
        points_data[point] = {"primary": primary, "crosscheck": cross}

    bias_window = [
        row["bias_uA"]
        for row in rows
        if row["read1_bout_complete"]
        and not row["read0_bout_complete"]
        and not row["controls_bout_complete"]
    ]
    all_artifact_valid = all(row["artifact_valid"] for row in rows)
    all_crosschecks = all(row["independent_crosscheck"] for row in rows)
    all_btrig = all(row["btrig_guard"] for row in rows)
    all_storage = all(row["storage_sign_guard"] for row in rows)
    read1_peak = max(rows, key=lambda row: row["read1_bout_phase_turns"])
    read1_low = min(rows, key=lambda row: row["read1_bout_phase_turns"])
    read0_peak = max(rows, key=lambda row: row["read0_bout_phase_turns"])
    dt_values = [
        case["qa"]["dt_min_ps"]
        for data in points_data.values()
        for case in data["primary"]["cases"].values()
    ] + [
        case["qa"]["dt_max_ps"]
        for data in points_data.values()
        for case in data["primary"]["cases"].values()
    ]
    row_counts = [
        case["qa"]["rows"]
        for data in points_data.values()
        for case in data["primary"]["cases"].values()
    ]
    summary = {
        "document_type": "r1c_bias_margin_aggregate",
        "analysis_version": "r1c-bias-aggregate-1",
        "criterion": {
            "complete_event": "monotonic same-JJ B_OUT segment >=1.0 turn with same-segment voltage area residual <=0.05 turn and start <=130 ps",
            "not_used_as_event_oracle": ["I_above_Ic", "voltage_peak", "phase_range_alone"],
            "local_event_boundary": "B_OUT local JJ evidence is not downstream SFQ delivery",
        },
        "matrix": {
            "points": len(rows),
            "cases_per_point": len(CASES),
            "total_cases": len(rows) * len(CASES),
            "row_counts": sorted(set(row_counts)),
            "dt_min_ps": min(dt_values),
            "dt_max_ps": max(dt_values),
        },
        "comparison": rows,
        "bias_window_points_uA": bias_window,
        "guards": {
            "artifact_valid_all_points": all_artifact_valid,
            "independent_crosscheck_all_points": all_crosschecks,
            "btrig_guard_all_points": all_btrig,
            "storage_sign_guard_all_points": all_storage,
        },
        "q1": {
            "answer": "NO_MONOTONIC_ACTIVATION_GAIN_OBSERVED",
            "read1_max_phase_turns": read1_peak["read1_bout_phase_turns"],
            "read1_max_at_bias_uA": read1_peak["bias_uA"],
            "read1_min_phase_turns": read1_low["read1_bout_phase_turns"],
            "read1_min_at_bias_uA": read1_low["bias_uA"],
            "read0_max_phase_turns": read0_peak["read0_bout_phase_turns"],
            "read0_max_at_bias_uA": read0_peak["bias_uA"],
            "basis": "All five read1 phase/area segments remain sub-turn; read1 activity is largest at 6 uA and smallest at 10 uA in this bounded matrix.",
        },
        "q2": {
            "answer": "NO_BIAS_WINDOW_OBSERVED_IN_TESTED_RANGE",
            "qualifying_bias_points_uA": bias_window,
            "basis": "No tested point has a complete read1 B_OUT segment, so the requested read1-complete/read0-incomplete window is absent.",
        },
        "q3": {
            "answer": "NOT_UNIQUELY_SEPARATED; A_OR_C_REMAIN_PLAUSIBLE",
            "basis": "The secondary remains state-dependent and B_TRIG remains guarded, but no bias point completes B_OUT. Bias-only evidence does not distinguish insufficient transferred energy from loaded damping dynamics; the fixed-area operating point is also not shown to have a successful activation window.",
        },
        "result": "R1c_FAIL_NO_COMPLETE_BOUT_IN_BOUNDED_BIAS_MATRIX",
    }
    out = ROOT / "analysis" / "bias-summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print("bias | read1_turn | read0_turn | read1_area | read0_area | read1_complete | read0_complete | controls_complete")
    for row in rows:
        print(
            f"{row['bias_uA']:4.0f} | {row['read1_bout_phase_turns']:.9f} | "
            f"{row['read0_bout_phase_turns']:.9f} | "
            f"{row['read1_bout_voltage_area_turns']:.9f} | "
            f"{row['read0_bout_voltage_area_turns']:.9f} | "
            f"{row['read1_bout_complete']} | {row['read0_bout_complete']} | "
            f"{row['controls_bout_complete']}"
        )
    print("artifact_valid_all_points=" + str(all_artifact_valid))
    print("independent_crosscheck_all_points=" + str(all_crosschecks))
    print("btrig_guard_all_points=" + str(all_btrig))
    print("storage_sign_guard_all_points=" + str(all_storage))
    print("bias_window_points_uA=" + repr(bias_window))
    print("result=" + summary["result"])


if __name__ == "__main__":
    main()
