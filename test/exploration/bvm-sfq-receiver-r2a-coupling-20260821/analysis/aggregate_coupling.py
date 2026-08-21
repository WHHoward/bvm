#!/usr/bin/env python3
"""Aggregate the preregistered R2-A mutual-coupling points."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POINTS = [
    ("diff-a010-b007-k060", 0.60, 0.3794733),
    ("diff-a010-b007-k070", 0.70, 0.4427189),
    ("diff-a010-b007-k080", 0.80, 0.5059644),
    ("diff-a010-b007-k090", 0.90, 0.5692099),
    ("diff-a010-b007-k095", 0.95, 0.6008327),
]
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]
VSEC = "V(N_SEC|XTRIG)"
ISEC = "I(R_SEC_LOAD|XTRIG)"


def load(point: str):
    primary = json.loads((ROOT / "analysis" / f"{point}-analysis.json").read_text())
    cross = json.loads((ROOT / "analysis" / f"{point}-crosscheck.json").read_text())
    return primary, cross


def empty_segment() -> dict:
    return {
        "phase_abs_turns": 0.0,
        "phase_delta_turns": 0.0,
        "same_junction_voltage_area_turns": 0.0,
        "area_minus_phase_turns": 0.0,
        "start_time_ps": None,
        "end_time_ps": None,
    }


def largest(case: dict, window: str = "output_analysis") -> dict:
    return case["output"][window]["largest_abs_segment"] or empty_segment()


def trig_largest(case: dict) -> dict:
    return case["trigger"]["trigger_analysis"]["largest_abs_segment"] or empty_segment()


def signal(case: dict, key: str) -> dict:
    return case["output_branch"]["signals"][key]


def row(point: str, coupling: float, mutual: float, primary: dict, cross: dict) -> dict:
    cases = primary["cases"]
    read1 = cases["read1"]
    read0 = cases["read0"]
    control1 = cases["logical1-read0-control"]
    control0 = cases["logical0-read0-control"]
    out1 = largest(read1)
    out0 = largest(read0)
    c1 = largest(control1, "control_full")
    c0 = largest(control0, "control_full")
    c1_range = control1["output"]["control_full"]["trajectory"][
        "unwrapped_phase_range_turns"
    ]
    c0_range = control0["output"]["control_full"]["trajectory"][
        "unwrapped_phase_range_turns"
    ]
    trig1 = trig_largest(read1)
    trig0 = trig_largest(read0)
    controls_complete = control1["output"]["control_full"]["complete_2pi"] or control0[
        "output"
    ]["control_full"]["complete_2pi"]
    return {
        "point_id": point,
        "coupling_K": coupling,
        "mutual_M_pH": mutual,
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
        "logical1_control_bout_phase_turns": c1["phase_abs_turns"],
        "logical0_control_bout_phase_turns": c0["phase_abs_turns"],
        "logical1_control_bout_phase_range_turns": c1_range,
        "logical0_control_bout_phase_range_turns": c0_range,
        "read1_bout_complete": read1["output"]["qualifying_read_output"],
        "read0_bout_complete": read0["output"]["qualifying_read_output"],
        "controls_bout_complete": controls_complete,
        "controls_free_running": max(c1_range, c0_range) >= 1.0,
        "read1_bout_voltage_peak_uV": signal(read1, "V(B_OUT|XTRIG)")["abs_peak"] * 1e6,
        "read0_bout_voltage_peak_uV": signal(read0, "V(B_OUT|XTRIG)")["abs_peak"] * 1e6,
        "read1_bout_current_peak_uA": signal(read1, "I(B_OUT|XTRIG)")["abs_peak"] * 1e6,
        "read0_bout_current_peak_uA": signal(read0, "I(B_OUT|XTRIG)")["abs_peak"] * 1e6,
        "read1_btrig_phase_turns": trig1["phase_abs_turns"],
        "read1_btrig_voltage_area_turns": trig1["same_junction_voltage_area_turns"],
        "read0_btrig_phase_turns": trig0["phase_abs_turns"],
        "read0_btrig_voltage_area_turns": trig0["same_junction_voltage_area_turns"],
        "btrig_guard": primary["verdict_components"]["btrig_guard"],
        "read1_secondary_voltage_uV": read1["secondary"][VSEC][
            "activity_abs_deviation_peak"
        ]
        * 1e6,
        "read0_secondary_voltage_uV": read0["secondary"][VSEC][
            "activity_abs_deviation_peak"
        ]
        * 1e6,
        "read1_secondary_return_current_uA": read1["secondary"][ISEC][
            "activity_abs_deviation_peak"
        ]
        * 1e6,
        "read0_secondary_return_current_uA": read0["secondary"][ISEC][
            "activity_abs_deviation_peak"
        ]
        * 1e6,
        "secondary_read1_over_read0_voltage": read1["secondary"][VSEC][
            "activity_abs_deviation_peak"
        ]
        / read0["secondary"][VSEC]["activity_abs_deviation_peak"],
        "secondary_read1_over_read0_current": read1["secondary"][ISEC][
            "activity_abs_deviation_peak"
        ]
        / read0["secondary"][ISEC]["activity_abs_deviation_peak"],
        "storage_sign_guard": primary["storage_guard"]["pass"],
        "artifact_valid": primary["verdict_components"]["artifact_valid"],
        "independent_crosscheck": cross["all_comparisons_pass"],
    }


def main() -> None:
    rows = []
    details = {}
    for point, coupling, mutual in POINTS:
        primary, cross = load(point)
        rows.append(row(point, coupling, mutual, primary, cross))
        details[point] = {"primary": primary, "crosscheck": cross}

    window = [
        item["coupling_K"]
        for item in rows
        if item["read1_bout_complete"]
        and not item["read0_bout_complete"]
        and not item["controls_bout_complete"]
    ]
    artifact_valid = all(item["artifact_valid"] for item in rows)
    crosscheck_valid = all(item["independent_crosscheck"] for item in rows)
    btrig_guard = all(item["btrig_guard"] for item in rows)
    storage_guard = all(item["storage_sign_guard"] for item in rows)
    read1_peak = max(rows, key=lambda item: item["read1_bout_phase_turns"])
    read1_low = min(rows, key=lambda item: item["read1_bout_phase_turns"])
    secondary_v_first = rows[0]["read1_secondary_voltage_uV"]
    secondary_v_last = rows[-1]["read1_secondary_voltage_uV"]
    secondary_i_first = rows[0]["read1_secondary_return_current_uA"]
    secondary_i_last = rows[-1]["read1_secondary_return_current_uA"]
    dt_values = [
        case["qa"][key]
        for data in details.values()
        for case in data["primary"]["cases"].values()
        for key in ["dt_min_ps", "dt_max_ps"]
    ]
    row_counts = [
        case["qa"]["rows"]
        for data in details.values()
        for case in data["primary"]["cases"].values()
    ]
    if window:
        result = "R2A_PASS_BOUNDED_INPUT_TRANSFER_WINDOW"
    elif artifact_valid and crosscheck_valid:
        result = "R2A_FAIL_NO_COMPLETE_BOUT_IN_BOUNDED_K_MATRIX"
    else:
        result = "R2A_INVALID_ARTIFACT_OR_CROSSCHECK"
    summary = {
        "document_type": "r2a_coupling_aggregate",
        "analysis_version": "r2a-coupling-aggregate-1",
        "criterion": {
            "complete_event": "monotonic same-JJ B_OUT segment >=1.0 turn, start <=130 ps, same-segment area residual <=0.05 turn",
            "not_event_oracles": ["I_above_Ic", "voltage_peak", "phase_range_alone"],
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
        "coupling_window_points": window,
        "guards": {
            "artifact_valid_all_points": artifact_valid,
            "independent_crosscheck_all_points": crosscheck_valid,
            "btrig_guard_all_points": btrig_guard,
            "storage_sign_guard_all_points": storage_guard,
            "control_free_running_any_point": any(item["controls_free_running"] for item in rows),
        },
        "q1": {
            "answer": "K_EFFECT_ON_BOUT_RECORDED",
            "read1_max_phase_turns": read1_peak["read1_bout_phase_turns"],
            "read1_max_at_K": read1_peak["coupling_K"],
            "read1_min_phase_turns": read1_low["read1_bout_phase_turns"],
            "read1_min_at_K": read1_low["coupling_K"],
            "read1_secondary_voltage_first_uV": secondary_v_first,
            "read1_secondary_voltage_last_uV": secondary_v_last,
            "read1_secondary_current_first_uA": secondary_i_first,
            "read1_secondary_current_last_uA": secondary_i_last,
            "basis": "Compare the monotonicity and scale of secondary transfer and B_OUT phase/area across the five K points; no current-only event rule is used.",
        },
        "q2": {
            "answer": "NO_BOUNDED_READ1_COMPLETE_WINDOW" if not window else "BOUNDED_WINDOW_OBSERVED",
            "coupling_window_points": window,
        },
        "interpretation": {
            "case_A_H1_input_margin": "supported only if increased K produces a corresponding B_OUT approach to a complete phase/area segment; see comparison table",
            "case_B_H2_dynamic_limit": "supported if secondary transfer increases substantially while B_OUT remains sub-turn",
            "unknown": "This K-only matrix does not independently vary damping or receiver topology.",
        },
        "result": result,
    }
    out = ROOT / "analysis" / "coupling-summary.json"
    out.write_text(json.dumps(summary, indent=2) + "\n")
    print("K | M_pH | read1_BOUT_turn | read1_area | read0_BOUT_turn | read0_area | read1_complete | read0_complete")
    for item in rows:
        print(
            f"{item['coupling_K']:.2f} | {item['mutual_M_pH']:.7f} | "
            f"{item['read1_bout_phase_turns']:.9f} | "
            f"{item['read1_bout_voltage_area_turns']:.9f} | "
            f"{item['read0_bout_phase_turns']:.9f} | "
            f"{item['read0_bout_voltage_area_turns']:.9f} | "
            f"{item['read1_bout_complete']} | {item['read0_bout_complete']}"
        )
    print("artifact_valid_all_points=" + str(artifact_valid))
    print("independent_crosscheck_all_points=" + str(crosscheck_valid))
    print("btrig_guard_all_points=" + str(btrig_guard))
    print("storage_sign_guard_all_points=" + str(storage_guard))
    print("control_free_running_any_point=" + str(any(item["controls_free_running"] for item in rows)))
    print("coupling_window_points=" + repr(window))
    print("result=" + result)


if __name__ == "__main__":
    main()
