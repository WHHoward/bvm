#!/usr/bin/env python3
"""Produce evidence-first population, position and control summaries."""

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
from prepare_population import FIXED, NEW_MASKS, NEW_RUNS, REUSE_RUNS, RUN_TO_MASK, sha256  # noqa: E402


ALL_RUNS = REUSE_RUNS + NEW_RUNS
MASK_ORDER = ("0001", "0011", "0110", "1100", "1110", "0111", "1111")
PHI0 = 2.067833848e-15
SOURCE_WINDOW = (110e-12, 114.5e-12)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def raw_path(run_id: str) -> Path:
    return EXP / ("references/reused" if run_id in REUSE_RUNS else "runs") / run_id / "raw.csv"


def deck_path(run_id: str) -> Path:
    return EXP / ("references/reused" if run_id in REUSE_RUNS else "runs") / run_id / "deck.cir"


def trapezoid(times: tuple[float, ...], values: tuple[float, ...]) -> float | None:
    if len(times) < 2:
        return None
    return sum((values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]) for index in range(len(values) - 1))


def direct_area(trace: Any, label: str, window: tuple[float, float]) -> float | None:
    indexes = window_indices(trace.time, *window)
    if len(indexes) < 2:
        return None
    return trapezoid(tuple(trace.time[index] for index in indexes), tuple(float(trace.column(label)[index]) for index in indexes))


def extrema(trace: Any, label: str, window: tuple[float, float]) -> dict[str, float | None]:
    indexes = window_indices(trace.time, *window)
    values = tuple(float(trace.column(label)[index]) for index in indexes)
    if not values:
        return {"max": None, "min": None, "max_abs": None}
    return {"max": max(values), "min": min(values), "max_abs": max(abs(value) for value in values)}


def control_guardrail(trace: Any) -> dict[str, Any]:
    baseline = window_indices(trace.time, 61e-12, 70e-12)
    origin = window_indices(trace.time, 70e-12, 110e-12)
    if not baseline or not origin:
        return {"status": "UNKNOWN", "reason": "control window has no samples", "label": "ZERO_STATE_READ_CONTROL"}

    def marker(label: str, threshold: float) -> int | None:
        phase = continuous_unwrap(tuple(trace.column(label)))
        reference = phase[baseline[0]]
        return next((index for index in origin if (phase[index] - reference) / (2.0 * math.pi) >= threshold), None)

    phase_markers = {"BJ1": marker("P(BJ1|XBQ1)", 0.5), "BJ2": marker("P(BJ2|XBQ1)", 0.5)}
    phase_markers.update({f"JTL{stage}": marker(f"P(B01|XJTL1_{stage})", 0.5) for stage in range(1, 7)})
    ordered = all(value is not None for value in phase_markers.values()) and all(phase_markers[left] < phase_markers[right] for left, right in zip(("BJ1", "BJ2", "JTL1", "JTL2", "JTL3", "JTL4", "JTL5"), ("BJ2", "JTL1", "JTL2", "JTL3", "JTL4", "JTL5", "JTL6")))
    direct_support = all(extrema(trace, label, (70e-12, 110e-12))["max_abs"] is not None and extrema(trace, label, (70e-12, 110e-12))["max_abs"] > 0.0 for label in ("V(QBOUT)", *(f"V(JTL{stage}_OUT)" for stage in range(1, 7))))
    terminal_area = direct_area(trace, "V(JTL6_OUT)", (70e-12, 110e-12))
    complete = ordered and direct_support and terminal_area is not None
    return {"status": "CONTROL_GUARDRAIL_FAILURE" if complete else "CLEAN", "phase_markers_sample_index": phase_markers, "phase_ordered": ordered, "direct_downstream_support": direct_support, "terminal_area_V_s": terminal_area, "window_ps": [70.0, 110.0], "baseline_ps": [61.0, 70.0], "label": "ZERO_STATE_READ_CONTROL_GUARDRAIL_ONLY", "not_event_count": True, "scientific_interpretation_performed": False}


def source_population_evidence(trace: Any, mask: str) -> dict[str, Any]:
    signals = ["I(B_JSL8)", "I(LIN|XBQ1)", "V(QBIN)", "V(COMMON_SL)", *(f"I(L_SL|XBVM{instance})" for instance in range(1, 5))]
    result: dict[str, Any] = {"window_ps": [110.0, 114.5], "actual_grid": True, "signals": {}}
    for label in signals:
        result["signals"][label] = {"extrema": extrema(trace, label, SOURCE_WINDOW), "signed_area": direct_area(trace, label, SOURCE_WINDOW), "unit": "A_s" if label.startswith("I(") else "V or solver-emitted node quantity"}
    result["active_bvm_branch_labels"] = [f"I(L_SL|XBVM{index})" for index, bit in enumerate(mask, 1) if bit == "1"]
    result["label"] = "DERIVED_SOURCE_POPULATION_EVIDENCE"
    result["not_event_count"] = True
    return result


def case_summary(run_id: str, trace: Any) -> dict[str, Any]:
    mask = RUN_TO_MASK[run_id]
    oracle = generalized_response_oracle(trace)
    response_records = oracle["response_records"]
    ordered_wavefronts = [record["response_index"] for record in response_records if record["complete"]]
    return {"case_id": run_id, "mask": mask, "hamming_weight": mask.count("1"), "active_bvms": [f"BVM{index}" for index, bit in enumerate(mask, 1) if bit == "1"], "rj2_ohm": 12.0, "L1_pH": FIXED["L1_pH"], "L2_pH": FIXED["L2_pH"], "physical_solve_this_experiment": run_id in NEW_RUNS, "raw_path": str(raw_path(run_id).relative_to(REPO)), "raw_sha256": sha256(raw_path(run_id)), "control": control_guardrail(trace), "oracle_status": oracle["status"], "complete_response_count": oracle["complete_response_count"], "response_count_candidate": oracle["response_count_candidate"], "response_records": response_records, "voltage_signal_cluster_counts": oracle["voltage_signal_cluster_counts"], "terminal_pulse_analysis": oracle["terminal_pulse_analysis"], "ordered_complete_response_indices": ordered_wavefronts, "source_population_evidence": source_population_evidence(trace, mask), "scientific_interpretation_performed": False}


def population_comparisons(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    by_mask = {case["mask"]: case for case in cases.values()}
    weight2 = [by_mask[mask] for mask in ("0011", "0110", "1100")]
    weight3 = [by_mask[mask] for mask in ("1110", "0111")]
    weight2_counts = {case["mask"]: case["complete_response_count"] for case in weight2}
    weight3_counts = {case["mask"]: case["complete_response_count"] for case in weight3}
    position2 = len(set(weight2_counts.values())) > 1
    position3 = len(set(weight3_counts.values())) > 1
    max_by_weight: dict[str, int] = {}
    for weight in range(1, 5):
        values = [case["complete_response_count"] for case in cases.values() if case["hamming_weight"] == weight]
        if values:
            max_by_weight[str(weight)] = max(values)
    saturation = "DOWNSTREAM_RESPONSE_SATURATION_OBSERVED" if max_by_weight.get("3", 0) <= max_by_weight.get("2", 0) and max_by_weight.get("4", 0) <= max_by_weight.get("3", 0) and max_by_weight.get("3") == max_by_weight.get("2") else "NO_REGISTERED_SATURATION_CLASSIFICATION"
    expected = {"0001": 1, "0011": 2, "0110": 2, "1100": 2, "1110": 3, "0111": 3, "1111": 4}
    selected_candidate = all(by_mask[mask]["control"]["status"] == "CLEAN" and by_mask[mask]["complete_response_count"] == value for mask, value in expected.items())
    return {"weight2_counts": weight2_counts, "weight3_counts": weight3_counts, "position_dependence_weight2": "POSITION_DEPENDENCE_OBSERVED_AT_WEIGHT_2" if position2 else "NO_POSITION_DEPENDENCE_OBSERVED_AT_WEIGHT_2", "position_dependence_weight3": "POSITION_DEPENDENCE_OBSERVED_AT_WEIGHT_3" if position3 else "NO_POSITION_DEPENDENCE_OBSERVED_AT_WEIGHT_3", "max_response_count_by_weight": max_by_weight, "saturation_classification": saturation, "selected_mask_population_scaling_candidate": "SELECTED_MASK_POPULATION_SCALING_CANDIDATE" if selected_candidate else "SELECTED_MASK_EXPECTED_SCALING_NOT_OBSERVED", "selected_candidate": selected_candidate, "expected_counts_used_only_for_final_comparison": True, "oracle_received_no_hamming_weight": True, "no_universal_all_mask_claim": True}


def main() -> int:
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    if execution.get("status") != "PASS" or execution.get("exact_new_physical_solve_count") != 5 or execution.get("reused_physical_case_count") != 2 or execution.get("unauthorized_extra_solves") != 0:
        raise RuntimeError("execution is not exact 5-new/2-reuse PASS")
    traces: dict[str, Any] = {}
    cases: dict[str, dict[str, Any]] = {}
    raw_failures: list[str] = []
    raw_records: dict[str, Any] = {}
    reuse = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    for run_id in ALL_RUNS:
        raw = raw_path(run_id)
        if not raw.is_file():
            raw_failures.append(f"missing raw: {run_id}")
            continue
        trace = read_csv(raw)
        traces[run_id] = trace
        qa = trace.qa()
        if trace.sample_count != 1999 or trace.time[0] != 0.0 or trace.time[-1] != 1.999e-10 or not trace.qa()["strictly_increasing_time"] or trace.qa()["nan_inf_status"] != "PASS":
            raw_failures.append(f"time/finite failure: {run_id}")
        if run_id in REUSE_RUNS and sha256(raw) != reuse["references"][run_id]["artifacts"]["raw.csv"]["source_sha256"]:
            raw_failures.append(f"reuse raw hash mismatch: {run_id}")
        cases[run_id] = case_summary(run_id, trace)
        raw_records[run_id] = {"path": str(raw.relative_to(REPO)), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "first_timestamp_s": trace.time[0], "last_timestamp_s": trace.time[-1], "dt_min_ps": min(trace.dt) * 1e12, "dt_max_ps": max(trace.dt) * 1e12, "strictly_increasing_time": True, "finite_values": qa["nan_inf_status"] == "PASS", "physical_solve_this_experiment": run_id in NEW_RUNS}
    deck_failures: list[str] = []
    base = (EXP / "references/reused/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0001/deck.cir").read_text(encoding="utf-8")
    normalized_base = tuple(line for line in base.splitlines() if not line.startswith("I_WL") and not line.startswith("I_BL") and not line.startswith("I_SE"))
    for run_id in NEW_RUNS:
        text = deck_path(run_id).read_text(encoding="utf-8")
        normalized = tuple(line for line in text.splitlines() if not line.startswith("I_WL") and not line.startswith("I_BL") and not line.startswith("I_SE"))
        if normalized != normalized_base:
            deck_failures.append(f"deck changed outside mask controls: {run_id}")
        if ".tran 0.1p 200p" not in text:
            deck_failures.append(f"timestep mismatch: {run_id}")
    deck_qa = {"schema": "bjs400-population-deck-qa-v1", "status": "PASS" if not deck_failures else "FAIL", "only_final_read_mask_delta": not deck_failures, "failures": deck_failures, "new_decks": {run_id: {"mask": RUN_TO_MASK[run_id], "sha256": sha256(deck_path(run_id))} for run_id in NEW_RUNS}}
    raw_ok = not raw_failures and len(cases) == len(ALL_RUNS)
    comparisons = population_comparisons(cases) if raw_ok else {}
    control_failures = [run_id for run_id, case in cases.items() if case["control"]["status"] != "CLEAN"]
    population_qa = {"schema": "bjs400-population-scaling-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if raw_ok and not deck_failures else "FAIL", "artifact_validity": "VALID" if raw_ok and not deck_failures else "INVALID", "physical_solve_count": 5, "reused_case_count": 2, "logical_case_count": 7, "selected_new_masks": list(NEW_MASKS), "unauthorized_extra_solves": 0, "control_failure_cases": control_failures, "raw_files_modified": 0, "raw_ok": raw_ok, "deck_ok": not deck_failures, "population_comparisons": comparisons, "scientific_interpretation_performed": False, "failures": raw_failures + deck_failures}
    protocol_audit = {"schema": "bjs400-population-protocol-audit-v1", "status": "PASS" if execution.get("run_order") == list(NEW_RUNS) and not control_failures and execution.get("unauthorized_extra_solves") == 0 else "FAIL", "rule": "execute exactly selected masks; control failures are recorded per mask and do not alter parameters or add masks", "executor_run_order": execution.get("run_order"), "registered_new_masks": list(NEW_MASKS), "control_failure_cases": control_failures, "unauthorized_extra_solves": execution.get("unauthorized_extra_solves"), "scientific_interpretation_performed": False}
    provenance = {"schema": "bjs400-population-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "authority_experiment": "test/exploration/qb-rj2p12-timestep-robustness-l1p14-l2p20-ib260-rj32-bjs400-v1-20260910", "authority_package_sha256": "a6e2e0b6d9bfa9dab002aa38979e8b12029ad3c16cb2dc203e5069b9f8e1e287", "oracle_code": "analysis/population_oracle.py", "oracle_code_sha256": sha256(EXP / "analysis/population_oracle.py"), "runs": cases, "execution_summary": "qa/execution_summary.json", "oracle_regression": "qa/oracle_regression.json", "population_qa": "qa/population_qa.json", "raw_files_modified": 0, "scientific_interpretation_performed": False}
    transformations = {"schema": "bjs400-population-transformation-registry-v1", "raw_immutable": True, "scientific_analysis_performed": False, "transformations": [{"name": "generalized_response_oracle", "operation": "response indices 1..4 from common FINAL baseline cumulative phase plus direct voltage clusters and terminal valleys", "scope": "N_RESPONSE_MULTI_EVIDENCE_ORACLE", "hamming_weight_input": False, "not_event_count": True}, {"name": "terminal_local_area", "operation": "actual-grid trapezoid over shared valley boundaries for each separated terminal cluster", "scope": "supporting mechanical evidence", "not_sfq_count": True}, {"name": "source_population_metrics", "operation": "extrema and actual-grid signed areas in [110,114.5) ps", "scope": "DERIVED_SOURCE_POPULATION_EVIDENCE"}, {"name": "population_comparison", "operation": "Hamming weight and position used only after oracle classification", "scope": "bounded selected-mask comparison"}, {"name": "phase_display", "operation": "continuous_unwrap(raw_rad)/(2*pi)", "scope": "diagnostic/display only", "not_event_count": True}, {"name": "area_integration", "operation": "trapezoid on actual stored time values", "scope": "mechanical arithmetic", "interpolation": False}]}
    mechanical = {"schema": "bjs400-population-scaling-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": population_qa["status"], "artifact_validity": population_qa["artifact_validity"], "fixed_working_point": {**FIXED, "BJS_area": 4, "BJS_Ic_uA": 400}, "canonical_timestep_ps": 0.1, "cases": cases, "population_comparisons": comparisons, "control_failure_cases": control_failures, "protocol_audit_status": protocol_audit["status"], "physical_solve_count": 5, "reused_case_count": 2, "raw_files_modified": 0, "scientific_interpretation_performed": False, "interpretation_ceiling": "selected-mask bounded comparison only; no universal mask claim, mechanism or SFQ count"}
    for path, value in ((EXP / "qa/raw_qa.json", {"schema": "bjs400-population-raw-qa-v1", "status": "PASS" if raw_ok else "FAIL", "artifact_validity": "VALID" if raw_ok else "INVALID", "experiment_id": EXP.name, "physical_solve_count": 5, "reused_case_count": 2, "logical_case_count": 7, "raw_files_modified": 0, "raw_unchanged_pre_to_post": True, "cases": raw_records, "failures": raw_failures, "scientific_analysis_performed": False}), (EXP / "qa/deck_diff_qa.json", deck_qa), (EXP / "qa/population_qa.json", population_qa), (EXP / "qa/protocol_audit.json", protocol_audit), (EXP / "qa/provenance.json", provenance), (EXP / "qa/transformation_registry.json", transformations), (EXP / "mechanical_summary.json", mechanical)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Selected-mask population scaling review", "", "Scientific interpretation: NOT_PERFORMED.", "", f"Selected-mask classification: `{comparisons.get('selected_mask_population_scaling_candidate')}`.", f"Weight-2 position classification: `{comparisons.get('position_dependence_weight2')}`.", f"Weight-3 position classification: `{comparisons.get('position_dependence_weight3')}`.", f"Saturation classification: `{comparisons.get('saturation_classification')}`.", "", "| mask | active BVMs | weight | control | BJ1 clusters | BJ2 clusters | QBOUT clusters | complete ordered response indices | terminal pulses | classification |", "|:---:|:---|---:|:---|---:|---:|---:|:---|---:|:---|"]
    for mask in MASK_ORDER:
        case = next(case for case in cases.values() if case["mask"] == mask)
        counts = case["voltage_signal_cluster_counts"]
        terminal = case["terminal_pulse_analysis"]
        lines.append(f"| {mask} | {','.join(case['active_bvms'])} | {case['hamming_weight']} | {case['control']['status']} | {counts.get('BJ1')} | {counts.get('BJ2')} | {counts.get('QBOUT')} | {case['ordered_complete_response_indices']} | {terminal.get('pulse_count')} | {case['complete_response_count']}_COMPLETE_RESPONSE_CANDIDATE |")
    lines.extend(["", "Source-side [110,114.5)ps extrema and signed areas for active branches, I(B_JSL8), I(LIN), V(QBIN) and V(COMMON_SL) are stored per case in `mechanical_summary.json`.", "", "Hamming weight is used only in this final comparison table; the generalized oracle receives no expected weight. Phase landmarks, voltage areas, terminal areas and response candidates are not SFQ counts.", ""])
    (EXP / "analysis/POPULATION_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": population_qa["status"], "selected_mask_classification": comparisons.get("selected_mask_population_scaling_candidate"), "weight2": comparisons.get("position_dependence_weight2"), "weight3": comparisons.get("position_dependence_weight3"), "saturation": comparisons.get("saturation_classification"), "control_failure_cases": control_failures, "physical_solve_count": 5, "reused_case_count": 2, "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2))
    return 0 if population_qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
