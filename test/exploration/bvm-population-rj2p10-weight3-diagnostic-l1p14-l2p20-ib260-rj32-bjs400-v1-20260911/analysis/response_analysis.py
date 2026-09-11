#!/usr/bin/env python3
"""Organize raw-first RJ2=10/0111 diagnostic measurements and comparisons.

The response oracle is used only as a mechanical navigation aid.  This module
keeps raw waveform metrics, windows, signal directions and the evidence ceiling
explicit so that the later scientific review can inspect the CSV authority.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(EXP / "analysis"))
from bvmtools.phase import continuous_unwrap, window_indices  # noqa: E402
from bvmtools.raw import read_csv  # noqa: E402
from population_oracle import generalized_response_oracle  # noqa: E402
from prepare_diagnostic import FIXED, MASK, REFERENCE_CASES, RUN_ID, sha256  # noqa: E402


PHI0 = 2.067833848e-15
SOURCE_WINDOW = (110e-12, 114.5e-12)
WINDOWS = {
    "READ": (110e-12, 121e-12),
    "POST_READ_121_126": (121e-12, 126e-12),
    "POST_READ_121_130": (121e-12, 130e-12),
    "EXTENDED_110_140": (110e-12, 140e-12),
    "FINAL_110_200": (110e-12, 200e-12),
}
SOURCE_SUBWINDOWS = {"SOURCE_121_124": (121e-12, 124e-12), "SOURCE_121_126": (121e-12, 126e-12)}
REQUIRED_SIGNALS = (
    "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
    "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
    "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)",
    "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)",
    "V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "I(LIN|XBQ1)",
    "I(L1|XBQ1)", "I(L2|XBQ1)",
)
RESPONSE_SIGNALS = (
    "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ1|XBQ1)", "V(BJ2|XBQ1)",
    "I(BJ1|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)",
    *(f"V(JTL{stage}_OUT)" for stage in range(1, 7)), "I(R_TERM)",
)
SOURCE_SIGNALS = ("V(COMMON_SL)", "I(B_JSL8)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)")
FOCUS_SIGNALS = tuple(dict.fromkeys((*RESPONSE_SIGNALS, *SOURCE_SIGNALS)))
PHASE_LABELS = ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", *(f"P(B01|XJTL1_{stage})" for stage in range(1, 7)))
VOLTAGE_LABELS = ("V(QBOUT)", *(f"V(JTL{stage}_OUT)" for stage in range(1, 7)))


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


CASE_MATRIX = ((10, "0001"), (10, "0011"), (10, "0111"), (11, "0011"), (11, "0111"), (12, "0011"), (12, "0111"))


def case_dir(rj2: int, mask: str) -> Path:
    if rj2 == 10 and mask == "0111":
        return EXP / "runs" / RUN_ID
    return EXP / f"references/rj2p{rj2}" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P{rj2}_{mask}"


def raw_path(rj2: int, mask: str) -> Path:
    return case_dir(rj2, mask) / "raw.csv"


def trace_for(rj2: int, mask: str) -> Any:
    return read_csv(raw_path(rj2, mask))


def trap(times: tuple[float, ...], values: tuple[float, ...]) -> float | None:
    if len(times) < 2 or len(times) != len(values):
        return None
    return sum((values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]) for index in range(len(values) - 1))


def raw_window_metric(trace: Any, label: str, window: tuple[float, float]) -> dict[str, Any]:
    indexes = tuple(window_indices(trace.time, *window))
    values = tuple(float(trace.column(label)[index]) for index in indexes)
    if not values:
        return {"status": "UNKNOWN", "label": label, "window_ps": [window[0] * 1e12, window[1] * 1e12], "sample_count": 0}
    crossings: list[dict[str, float]] = []
    for left, right in zip(indexes, indexes[1:]):
        left_value, right_value = float(trace.column(label)[left]), float(trace.column(label)[right])
        if left_value == 0.0 or right_value == 0.0 or (left_value < 0.0 < right_value) or (left_value > 0.0 > right_value):
            crossings.append({"left_time_ps": trace.time[left] * 1e12, "right_time_ps": trace.time[right] * 1e12})
    area = trap(tuple(trace.time[index] for index in indexes), values)
    is_phase = label.startswith("P(")
    unit = "rad" if is_phase else ("A" if label.startswith("I(") else "V")
    area_unit = f"{unit}_s"
    return {"status": "DERIVED", "label": label, "window_ps": [window[0] * 1e12, window[1] * 1e12], "sample_count": len(indexes), "unit": unit, "area_unit": area_unit, "raw_first": values[0], "raw_last": values[-1], "raw_min": min(values), "raw_max": max(values), "peak_abs": max(abs(value) for value in values), "signed_area": area, "zero_crossing_sample_brackets_ps": crossings, "actual_time_column_used": True, "interpolation": False}


def phase_navigation(trace: Any) -> dict[str, Any]:
    return generalized_response_oracle(trace)


def control_guardrail(trace: Any) -> dict[str, Any]:
    baseline = tuple(window_indices(trace.time, 61e-12, 70e-12))
    origin = tuple(window_indices(trace.time, 70e-12, 110e-12))
    if not baseline or not origin:
        return {"status": "UNKNOWN", "reason": "control windows have no samples", "baseline_ps": [61.0, 70.0], "window_ps": [70.0, 110.0]}
    markers: dict[str, int | None] = {}
    labels = {"BJ1": "P(BJ1|XBQ1)", "BJ2": "P(BJ2|XBQ1)", **{f"JTL{stage}": f"P(B01|XJTL1_{stage})" for stage in range(1, 7)}}
    for name, label in labels.items():
        phase = continuous_unwrap(tuple(trace.column(label)))
        reference = phase[baseline[0]]
        markers[name] = next((index for index in origin if (phase[index] - reference) / (2.0 * math.pi) >= 0.5), None)
    direct_support: dict[str, bool] = {}
    for label in VOLTAGE_LABELS:
        values = [abs(float(trace.column(label)[index])) for index in origin]
        direct_support[label] = bool(values) and max(values) > 0.0
    terminal_area = raw_window_metric(trace, "V(JTL6_OUT)", (70e-12, 110e-12))["signed_area"]
    complete = all(value is not None for value in markers.values()) and all(direct_support.values()) and terminal_area is not None
    return {"status": "CONTROL_GUARDRAIL_FAILURE" if complete else "CLEAN", "baseline_ps": [61.0, 70.0], "window_ps": [70.0, 110.0], "phase_markers_sample_index": markers, "direct_voltage_support": direct_support, "terminal_area_V_s": terminal_area, "rule": "no complete control-origin downstream progression", "not_sfq_count": True}


def source_metrics(trace: Any) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for name, window in {"SOURCE_110_114P5": SOURCE_WINDOW, **SOURCE_SUBWINDOWS}.items():
        metrics[name] = {label: raw_window_metric(trace, label, window) for label in SOURCE_SIGNALS}
    metrics["closed_loop_quantity_notice"] = "I(B_JSL8) is post-switch closed-loop current; do not interpret it as independent BVM source amplitude."
    return metrics


def response_focus(oracle: dict[str, Any], trace: Any, focus: str) -> dict[str, Any]:
    records = oracle["response_records"]
    result: dict[str, Any] = {"focus": focus, "responses": []}
    for response_index in range(1, 5):
        record = records[response_index - 1]
        window_metrics = {name: {label: raw_window_metric(trace, label, window) for label in FOCUS_SIGNALS} for name, window in WINDOWS.items() if name in {"READ", "POST_READ_121_126", "POST_READ_121_130", "EXTENDED_110_140"}}
        result["responses"].append({"response_index": response_index, "complete_candidate": record["complete"], "phase_landmark_times_ps": record["phase_landmark_times_ps"], "downstream_voltage_peak_times_ps": record["downstream_voltage_peak_times_ps"], "checks": record["checks"], "window_metrics": window_metrics})
    if focus == "weight2_second":
        result["second_response_relative_to_read_end_ps"] = {"phase_latest_ps": max((value for value in result["responses"][1]["phase_landmark_times_ps"].values() if value is not None), default=None), "downstream_latest_ps": max((value for value in result["responses"][1]["downstream_voltage_peak_times_ps"].values() if value is not None), default=None), "read_end_ps": 121.0}
    if focus == "weight3_fourth":
        result["fourth_post_read_121_130ps"] = {"phase": result["responses"][3]["phase_landmark_times_ps"], "downstream": result["responses"][3]["downstream_voltage_peak_times_ps"], "terminal": result["responses"][3]["downstream_voltage_peak_times_ps"].get("terminal"), "window": "[121,130)ps"}
    if focus == "weight4_fourth":
        result["fourth_response_summary"] = result["responses"][3]
    return result


def case_record(rj2: int, mask: str) -> dict[str, Any]:
    trace = trace_for(rj2, mask)
    required_missing = [label for label in REQUIRED_SIGNALS if label not in trace.headers]
    qa = trace.qa()
    raw_valid = not required_missing and trace.sample_count == 1999 and trace.time[0] == 0.0 and trace.time[-1] == 1.999e-10 and qa["strictly_increasing_time"] and qa["nan_inf_status"] == "PASS"
    oracle = phase_navigation(trace)
    focus = "weight2_second" if mask == "0011" else ("weight3_fourth" if mask == "0111" else ("weight4_fourth" if mask == "1111" else "weight1_baseline"))
    return {"case_id": f"RJ2P{rj2}_{mask}", "rj2_ohm": rj2, "mask": mask, "active_bvms": [f"BVM{index}" for index, bit in enumerate(mask, 1) if bit == "1"], "hamming_weight": mask.count("1"), "raw_path": str(raw_path(rj2, mask).relative_to(REPO)), "raw_sha256": sha256(raw_path(rj2, mask)), "sample_count": trace.sample_count, "time_grid_ps": [trace.time[0] * 1e12, trace.time[-1] * 1e12], "dt_min_ps": min(trace.dt) * 1e12, "dt_max_ps": max(trace.dt) * 1e12, "required_signal_missing": required_missing, "artifact_validity": "VALID" if raw_valid else "INVALID", "control": control_guardrail(trace), "oracle_status": oracle["status"], "complete_response_count_candidate": oracle["complete_response_count"], "response_records": oracle["response_records"], "voltage_signal_cluster_counts": oracle["voltage_signal_cluster_counts"], "terminal_pulse_analysis": oracle["terminal_pulse_analysis"], "source_metrics": source_metrics(trace), "window_metrics": {name: {label: raw_window_metric(trace, label, window) for label in REQUIRED_SIGNALS} for name, window in WINDOWS.items()}, "response_focus": response_focus(oracle, trace, focus), "raw_is_scientific_authority": True, "mechanical_oracle_is_subordinate": True, "not_sfq_count": True, "scientific_interpretation_performed": False}


COMPARISON_SIGNALS = ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(BJ1|XBQ1)", "V(BJ2|XBQ1)", "I(BJ1|XBQ1)", "I(BJ2|XBQ1)", "V(QBOUT)", *(f"V(JTL{stage}_OUT)" for stage in range(1, 7)), "I(R_TERM)", "I(B_JSL8)", "V(QBIN)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)")


def comparison_values(trace: Any, label: str, indexes: tuple[int, ...]) -> tuple[float, ...]:
    values = tuple(trace.column(label))
    if label.startswith("P("):
        values = continuous_unwrap(values)
    return tuple(float(values[index]) for index in indexes)


def pair_comparison(left_rj2: int, right_rj2: int, left_mask: str, right_mask: str | None = None) -> dict[str, Any]:
    right_mask = left_mask if right_mask is None else right_mask
    left = trace_for(left_rj2, left_mask)
    right = trace_for(right_rj2, right_mask)
    same_grid = tuple(left.time) == tuple(right.time)
    windows: dict[str, Any] = {}
    if same_grid:
        for name, window in WINDOWS.items():
            indexes = tuple(window_indices(left.time, *window))
            values: dict[str, Any] = {}
            for label in COMPARISON_SIGNALS:
                left_values = comparison_values(left, label, indexes)
                right_values = comparison_values(right, label, indexes)
                delta = tuple(a - b for a, b in zip(left_values, right_values))
                values[label] = {"max_abs_difference": max((abs(value) for value in delta), default=None), "signed_area_difference": (trap(tuple(left.time[index] for index in indexes), left_values) or 0.0) - (trap(tuple(right.time[index] for index in indexes), right_values) or 0.0), "left_window": raw_window_metric(left, label, window), "right_window": raw_window_metric(right, label, window), "pointwise_window_permitted": True}
            windows[name] = values
    return {"left_case": f"RJ2P{left_rj2}_{left_mask}", "right_case": f"RJ2P{right_rj2}_{right_mask}", "same_time_grid": same_grid, "same_protocol_window": True, "windows": windows, "comparison_semantics": "descriptive same-time raw waveform comparison; not an event-count or SFQ proof", "scientific_interpretation_performed": False}


def weight3_comparison() -> dict[str, Any]:
    pairwise = {f"RJ2P{left}_VS_RJ2P{right}": pair_comparison(left, right, "0111") for left, right in ((10, 11), (11, 12), (10, 12))}
    return {"comparison_id": "RJ2P10_P11_P12_WEIGHT3", "mask": "0111", "cases": ["RJ2P10_0111", "RJ2P11_0111", "RJ2P12_0111"], "pairwise": pairwise, "scientific_interpretation_performed": False}


def weight2_vs_weight3_comparison() -> dict[str, Any]:
    return {"comparison_id": "RJ2P10_WEIGHT2_VS_WEIGHT3", "rj2p10_weight2_case": "RJ2P10_0011", "rj2p10_weight3_case": "RJ2P10_0111", "pairwise": pair_comparison(10, 10, "0011", "0111"), "scientific_interpretation_performed": False}


def outcome_category(case: dict[str, Any]) -> str:
    if case["control"]["status"] != "CLEAN":
        return "CONTROL_GUARDRAIL_FAILURE_RECORDED"
    count = case["complete_response_count_candidate"]
    if count == 3:
        return "RJ2P10_WEIGHT3_THREE_RESPONSE_CANDIDATE"
    if count == 4:
        return "RJ2P10_WEIGHT3_FOURTH_RESPONSE_PERSISTS"
    return "RJ2P10_WEIGHT3_MULTIPLICITY_AMBIGUOUS"


def main() -> int:
    execution_path = EXP / "qa/execution_summary.json"
    if not execution_path.is_file():
        raise RuntimeError("execution summary is missing; run physical cases before analysis")
    execution = json.loads(execution_path.read_text(encoding="utf-8"))
    if execution.get("status") != "PASS" or execution.get("exact_new_physical_solve_count") != 1 or execution.get("reference_case_count") != 6 or execution.get("unauthorized_extra_solves") != 0:
        raise RuntimeError("execution is not exact 1-new/6-reference PASS")
    records: dict[str, dict[str, Any]] = {}
    raw_failures: list[str] = []
    for rj2, mask in ((10, "0111"), *REFERENCE_CASES):
        record = case_record(rj2, mask)
        records[record["case_id"]] = record
        if record["artifact_validity"] != "VALID":
            raw_failures.append(f"invalid raw artifact: {record['case_id']}")
    new_case = records["RJ2P10_0111"]
    reference_records = {key: value for key, value in records.items() if key != "RJ2P10_0111"}
    comparisons = {"RJ2P10_P11_P12_WEIGHT3": weight3_comparison(), "RJ2P10_WEIGHT2_VS_WEIGHT3": weight2_vs_weight3_comparison()}
    control_failures = [] if new_case["control"]["status"] == "CLEAN" else [new_case["case_id"]]
    outcome = outcome_category(new_case)
    raw_qa = {"schema": "bjs400-rj2p10-weight3-raw-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not raw_failures else "FAIL", "artifact_validity": "VALID" if not raw_failures else "INVALID", "new_case_count": 1, "reference_case_count": 6, "raw_files_modified": 0, "cases": {key: {"raw_path": value["raw_path"], "sha256": value["raw_sha256"], "sample_count": value["sample_count"], "artifact_validity": value["artifact_validity"], "required_signal_missing": value["required_signal_missing"]} for key, value in records.items()}, "failures": raw_failures, "scientific_interpretation_performed": False}
    control_qa = {"schema": "bjs400-rj2p10-weight3-control-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if new_case["control"]["status"] == "CLEAN" else "FAIL", "new_case": {"status": new_case["control"]["status"], "window_ps": new_case["control"].get("window_ps"), "markers": new_case["control"].get("phase_markers_sample_index")}, "control_failure_cases": [] if new_case["control"]["status"] == "CLEAN" else [new_case["case_id"]], "action": "record raw evidence; no parameter tuning or follow-up solve", "scientific_interpretation_performed": False}
    response_qa = {"schema": "bjs400-rj2p10-weight3-response-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not raw_failures else "FAIL", "raw_scientific_authority": True, "mechanical_checker_subordinate": True, "outcome_category_from_recorded_evidence": outcome, "new_case_response_candidates": {"0111": new_case["complete_response_count_candidate"]}, "reference_response_candidates": {key.removeprefix("RJ2P"): value["complete_response_count_candidate"] for key, value in reference_records.items()}, "fourth_focus_mask": "0111", "weight2_boundary_reference": "RJ2P10_0011", "comparisons": comparisons, "not_sfq_count": True, "scientific_interpretation_performed": False, "failures": raw_failures}
    protocol = {"schema": "bjs400-rj2p10-weight3-protocol-audit-v1", "status": "PASS" if execution.get("run_order") == [RUN_ID] and execution.get("unauthorized_extra_solves") == 0 and not raw_failures else "FAIL", "registered_new_run_id": RUN_ID, "execution_run_order": execution.get("run_order"), "exact_new_physical_solve_count": execution.get("exact_new_physical_solve_count"), "reference_case_count": 6, "only_mask_delta_from_RJ2P10_0011": True, "raw_files_modified": 0, "no_follow_up": True, "scientific_interpretation_performed": False}
    provenance = {"schema": "bjs400-rj2p10-weight3-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "authority": "raw waveform files; current Git repository and latest Drive canonical handoffs", "source_packages": {"rj2p10": {"sha256": "84e1a8654aa16baf2fe81f96f9cdc4ce8af6efbeb5f617a12c8123b8b13a9bde", "bytes": 10106003}, "rj2p11": {"sha256": "785be4b1d92d9eeea4e3dfa044a70ac55cf47d7a6f2feea860f4b1c3d79566af", "bytes": 10555946}, "rj2p12": {"sha256": "3ceba168be95b7e48cbb77ccb13d4f4133893cb39813c025b7d4a3f631a09dff", "bytes": 130901740}}, "solver_sha256": "48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2", "runs": records, "new_case": new_case, "reference_cases": reference_records, "raw_files_modified": 0, "scientific_interpretation_performed": False}
    transformations = {"schema": "bjs400-rj2p10-weight3-transformation-registry-v1", "raw_immutable": True, "raw_scientific_authority": True, "transformations": [{"name": "actual_grid_window_metrics", "operation": "direct raw-column extrema, stored-sample zero-crossing brackets and trapezoid over CSV time", "not_event_count": True}, {"name": "continuous_phase_navigation", "operation": "continuous unwrap(raw P radians)/(2*pi) from FINAL baseline [101,110)ps", "not_sfq_count": True}, {"name": "multi_evidence_response_navigation", "operation": "cumulative phase landmarks plus direct voltage clusters, ordered JTL and terminal valleys", "not_sfq_count": True}, {"name": "rj2_weight3_comparison", "operation": "same-time descriptive comparisons for RJ2=10/11/12 mask 0111 and RJ2=10 mask 0011 vs 0111", "not_event_count": True}]}
    mechanical = {"schema": "bjs400-rj2p10-weight3-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not raw_failures else "FAIL", "artifact_validity": "VALID" if not raw_failures else "INVALID", "fixed_working_point": {**FIXED, "BJS_area": 4, "BJS_Ic_uA": 400}, "canonical_timestep_ps": 0.1, "cases": records, "comparisons": comparisons, "control_failure_cases": control_qa["control_failure_cases"], "outcome_category_from_recorded_evidence": outcome, "raw_scientific_authority": True, "mechanical_checker_subordinate": True, "raw_files_modified": 0, "scientific_interpretation_performed": False, "interpretation_ceiling": "raw review required; no phase/area/current/pulse/response candidate is an SFQ count"}
    for path, value in ((EXP / "qa/raw_qa.json", raw_qa), (EXP / "qa/control_qa.json", control_qa), (EXP / "qa/response_qa.json", response_qa), (EXP / "qa/protocol_audit.json", protocol), (EXP / "qa/provenance.json", provenance), (EXP / "qa/transformation_registry.json", transformations), (EXP / "mechanical_summary.json", mechanical)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    deck_qa = json.loads((EXP / "analysis/preflight.json").read_text(encoding="utf-8"))["deck_checks"]
    (EXP / "qa/deck_diff_qa.json").write_text(json.dumps({**deck_qa, "schema": "bjs400-rj2p10-weight3-deck-diff-qa-v1", "scientific_interpretation_performed": False}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# RJ2=10 weight-3 diagnostic raw-oriented review", "", "Scientific interpretation: `NOT_PERFORMED`.", "", f"Recorded bounded outcome category: `{outcome}`.", "", "| case | response candidates | control | terminal segmentation |", "|:---|---:|:---|:---|"]
    for key, value in records.items():
        lines.append(f"| {key} | {value['complete_response_count_candidate']} | {value['control']['status']} | {value['terminal_pulse_analysis']['status']} |")
    lines.extend(["", "The new RJ2=10/0111 case has dedicated first/second/third/fourth navigation, [121,130)ps fourth-candidate records and source/receiver state metrics. The weight-3 RJ2=10/11/12 comparison and same-RJ2 weight-2-vs-weight-3 comparison are stored in `mechanical_summary.json`.", "", "All phase values remain raw radians in the source CSV. Phase navigation, voltage clusters, current/voltage areas, L1 crossings, terminal pulse-local areas and response candidates are supporting evidence and are not SFQ counts. Raw waveform review remains authoritative over any mechanical category.", ""])
    (EXP / "analysis/DIAGNOSTIC_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    (EXP / "analysis/REVIEW.md").write_text("\n".join(["# RJ2=10 weight-3 diagnostic evidence review", "", "This is a raw-oriented evidence handoff. Scientific interpretation is `NOT_PERFORMED`.", "", "- Artifact/raw validity and exact protocol execution are recorded separately from the bounded outcome category.", "- RJ2=10/11/12 reference files are comparison-only immutable evidence.", "- Same-time comparisons use the declared windows and actual CSV time grid.", "- No response candidate, phase turn, terminal area or current/voltage metric is an SFQ count.", ""]), encoding="utf-8")
    print(json.dumps({"status": mechanical["status"], "outcome_category": outcome, "new_response_candidates": {"0111": new_case["complete_response_count_candidate"]}, "reference_response_candidates": {key: value["complete_response_count_candidate"] for key, value in reference_records.items()}, "control_failure_cases": control_qa["control_failure_cases"], "raw_files_modified": 0, "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2))
    return 0 if mechanical["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
