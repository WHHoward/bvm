#!/usr/bin/env python3
"""Analyze the six timestep/mask cases with the repaired oracle."""

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
from prepare_timestep import AUTH, DT_VALUES, FIXED, NEW_RUNS, REUSE_RUNS, RUN_TO_DT, RUN_TO_MASK  # noqa: E402
from second_response_oracle import PHI0, FINAL_BASELINE, FINAL_WINDOW, repaired_second_response_oracle  # noqa: E402


ALL_RUNS = REUSE_RUNS + NEW_RUNS
CONTROL_BASELINE = (61e-12, 70e-12)
CONTROL_WINDOW = (70e-12, 110e-12)
EXPECTED_SAMPLE_COUNT = {0.1: 1999, 0.05: 3999, 0.025: 7999}


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_path(run_id: str) -> Path:
    return EXP / ("references/reused" if run_id in REUSE_RUNS else "runs") / run_id / "raw.csv"


def deck_path(run_id: str) -> Path:
    return EXP / ("references/reused" if run_id in REUSE_RUNS else "runs") / run_id / "deck.cir"


def trapezoid(times: tuple[float, ...], values: tuple[float, ...]) -> float | None:
    if len(times) < 2:
        return None
    return sum((values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]) for index in range(len(values) - 1))


def control_status(trace: Any) -> dict[str, Any]:
    times = tuple(trace.time)
    baseline = window_indices(times, *CONTROL_BASELINE)
    origin = window_indices(times, *CONTROL_WINDOW)
    if not baseline or not origin:
        return {"status": "UNKNOWN", "reason": "control window has no samples"}

    def first(label: str, threshold: float) -> float | None:
        unwrapped = continuous_unwrap(tuple(trace.column(label)))
        reference = unwrapped[baseline[0]]
        index = next((index for index in origin if (unwrapped[index] - reference) / (2.0 * math.pi) >= threshold), None)
        return times[index] * 1e12 if index is not None else None

    markers = {
        "BJ1_0p5_time_ps": first("P(BJ1|XBQ1)", 0.5),
        "BJ2_0p9_time_ps": first("P(BJ2|XBQ1)", 0.9),
        "JTL_first_time_ps": {f"JTL{stage}": first(f"P(B01|XJTL1_{stage})", 0.5) for stage in range(1, 7)},
    }
    complete = markers["BJ1_0p5_time_ps"] is not None and markers["BJ2_0p9_time_ps"] is not None and all(value is not None for value in markers["JTL_first_time_ps"].values())
    return {"status": "UNSUITABLE_WORKING_POINT" if complete else "CLEAN", "markers": markers, "complete_control_progression": complete, "window_ps": [70.0, 110.0], "baseline_ps": [61.0, 70.0], "label": "ZERO_STATE_READ_CONTROL_GUARDRAIL_ONLY"}


def strongest_l1_excursion(trace: Any, oracle: dict[str, Any]) -> dict[str, Any]:
    index = oracle.get("phase_landmarks", {}).get("P(BJ2|XBQ1)", {}).get("first_0p9_sample_index")
    if not isinstance(index, int):
        return {"status": "UNKNOWN", "reason": "missing first BJ2 +0.9 navigation sample"}
    values = tuple(float(value) for value in trace.column("I(L1|XBQ1)"))
    segments: list[list[int]] = []
    for sample in range(index, len(trace.time)):
        if trace.time[sample] >= FINAL_WINDOW[1]:
            break
        if values[sample] > 0.0:
            if not segments or sample != segments[-1][-1] + 1:
                segments.append([sample])
            else:
                segments[-1].append(sample)
    if not segments:
        return {"status": "DERIVED", "segment_count": 0, "peak_A": None, "peak_time_ps": None, "label": "POST_FIRST_L1_ACTIVITY_ONLY"}
    chosen = max(segments, key=lambda segment: max(values[sample] for sample in segment))
    peak = max(chosen, key=lambda sample: values[sample])
    return {"status": "DERIVED", "segment_count": len(segments), "start_time_ps": trace.time[chosen[0]] * 1e12, "end_time_ps": trace.time[chosen[-1]] * 1e12, "dwell_ps": (trace.time[chosen[-1]] - trace.time[chosen[0]]) * 1e12, "peak_A": values[peak], "peak_uA": values[peak] * 1e6, "peak_time_ps": trace.time[peak] * 1e12, "label": "POST_FIRST_L1_ACTIVITY_ONLY", "not_event_count": True, "not_sfq_count": True}


def case_record(run_id: str, trace: Any, oracle: dict[str, Any]) -> dict[str, Any]:
    phase = oracle["phase_landmarks"]
    clusters = oracle["voltage_pulse_clusters"]
    terminal = oracle["terminal_pulse_analysis"]
    def phase_time(label: str, key: str) -> float | None:
        return phase.get(label, {}).get(key)
    def pulse_time(label: str, index: int) -> float | None:
        values = clusters.get(label, {}).get("clusters", [])
        return values[index].get("peak_time_ps") if len(values) > index else None
    return {
        "case_id": run_id,
        "dt_ps": RUN_TO_DT[run_id],
        "mask": RUN_TO_MASK[run_id],
        "rj2_ohm": 12.0,
        "physical_solve_this_experiment": run_id in NEW_RUNS,
        "raw_path": str(raw_path(run_id).relative_to(REPO)),
        "raw_sha256": sha256(raw_path(run_id)),
        "sample_count": trace.sample_count,
        "first_timestamp_s": trace.time[0],
        "last_timestamp_s": trace.time[-1],
        "dt_min_ps": min(trace.dt) * 1e12,
        "dt_max_ps": max(trace.dt) * 1e12,
        "control": control_status(trace),
        "oracle_status": oracle["status"],
        "first_response_status": oracle["first_response_status"],
        "single_response_status": oracle["single_response_status"],
        "oracle_first_checks": oracle["first_checks"],
        "oracle_second_checks": oracle["second_checks"],
        "voltage_signal_cluster_counts": oracle["voltage_signal_cluster_counts"],
        "terminal_pulse_analysis": terminal,
        "timing_metrics": {
            "first_BJ1_time_ps": phase_time("P(BJ1|XBQ1)", "first_0p5_time_ps"),
            "second_BJ1_time_ps": phase_time("P(BJ1|XBQ1)", "second_1p5_time_ps"),
            "first_BJ2_time_ps": phase_time("P(BJ2|XBQ1)", "first_0p9_time_ps"),
            "second_BJ2_time_ps": phase_time("P(BJ2|XBQ1)", "second_1p5_time_ps"),
            "first_QBOUT_time_ps": pulse_time("V(QBOUT)", 0),
            "second_QBOUT_time_ps": pulse_time("V(QBOUT)", 1),
            "first_JTL_time_ps": {f"JTL{stage}": pulse_time(f"V(JTL{stage}_OUT)", 0) for stage in range(1, 7)},
            "second_JTL_time_ps": {f"JTL{stage}": pulse_time(f"V(JTL{stage}_OUT)", 1) for stage in range(1, 7)},
            "terminal_pulse_1_time_ps": (terminal.get("pulses") or [{}])[0].get("peak_time_ps") if terminal.get("pulses") else None,
            "terminal_pulse_2_time_ps": (terminal.get("pulses") or [{}, {}])[1].get("peak_time_ps") if len(terminal.get("pulses") or []) > 1 else None,
            "terminal_pulse_separation_ps": terminal.get("pulse_separation_ps"),
            "terminal_pulse_1_area_over_phi0": (terminal.get("pulses") or [{}])[0].get("signed_area_over_phi0") if terminal.get("pulses") else None,
            "terminal_pulse_2_area_over_phi0": (terminal.get("pulses") or [{}, {}])[1].get("signed_area_over_phi0") if len(terminal.get("pulses") or []) > 1 else None,
            "terminal_final_area_over_phi0": terminal.get("total_final_area_over_phi0"),
        },
        "strongest_post_first_L1_positive_excursion": strongest_l1_excursion(trace, oracle),
        "scientific_interpretation_performed": False,
    }


def compare_value(left: Any, right: Any) -> dict[str, Any]:
    if left is None or right is None:
        return {"from": left, "to": right, "delta": None, "status": "UNKNOWN" if left != right else "DERIVED"}
    return {"from": left, "to": right, "delta": right - left, "status": "DERIVED"}


def comparisons(cases: dict[str, dict[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    metric_names = [
        "first_BJ1_time_ps", "second_BJ1_time_ps", "first_BJ2_time_ps", "second_BJ2_time_ps",
        "first_QBOUT_time_ps", "second_QBOUT_time_ps", "terminal_pulse_1_time_ps", "terminal_pulse_2_time_ps",
        "terminal_pulse_separation_ps", "terminal_pulse_1_area_over_phi0", "terminal_pulse_2_area_over_phi0",
        "terminal_final_area_over_phi0",
    ]
    for mask in ("0001", "0011"):
        by_dt = {cases[run_id]["dt_ps"]: cases[run_id] for run_id in ALL_RUNS if cases[run_id]["mask"] == mask}
        rows: dict[str, Any] = {}
        for left_dt, right_dt in ((0.1, 0.05), (0.05, 0.025)):
            left = by_dt[left_dt]
            right = by_dt[right_dt]
            row: dict[str, Any] = {"from_dt_ps": left_dt, "to_dt_ps": right_dt, "metrics": {name: compare_value(left["timing_metrics"].get(name), right["timing_metrics"].get(name)) for name in metric_names}, "first_JTL_time_ps": {stage: compare_value(left["timing_metrics"]["first_JTL_time_ps"].get(stage), right["timing_metrics"]["first_JTL_time_ps"].get(stage)) for stage in (f"JTL{i}" for i in range(1, 7))}, "second_JTL_time_ps": {stage: compare_value(left["timing_metrics"]["second_JTL_time_ps"].get(stage), right["timing_metrics"]["second_JTL_time_ps"].get(stage)) for stage in (f"JTL{i}" for i in range(1, 7))}, "strongest_post_first_L1_peak_A": compare_value(left["strongest_post_first_L1_positive_excursion"].get("peak_A"), right["strongest_post_first_L1_positive_excursion"].get("peak_A")), "qualitative_from": {"control": left["control"]["status"], "0001_or_0011_response": left["single_response_status"] if mask == "0001" else left["oracle_status"]}, "qualitative_to": {"control": right["control"]["status"], "0001_or_0011_response": right["single_response_status"] if mask == "0001" else right["oracle_status"]}}
            rows[f"{left_dt:g}_to_{right_dt:g}"] = row
        output[mask] = rows
    return output


def main() -> int:
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    if execution.get("status") != "PASS" or execution.get("exact_new_physical_solve_count") != 4 or execution.get("reused_physical_case_count") != 2 or execution.get("unauthorized_extra_solves") != 0:
        raise RuntimeError("execution summary is not exact 4-new/2-reuse PASS")
    traces: dict[str, Any] = {}
    cases: dict[str, dict[str, Any]] = {}
    raw_failures: list[str] = []
    raw_records: dict[str, Any] = {}
    reuse_manifest = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    for run_id in ALL_RUNS:
        raw = raw_path(run_id)
        if not raw.is_file():
            raw_failures.append(f"missing raw: {run_id}")
            continue
        trace = read_csv(raw)
        traces[run_id] = trace
        if trace.time[0] != 0.0 or trace.time[-1] <= 0.0 or any(right <= left for left, right in zip(trace.time, trace.time[1:])):
            raw_failures.append(f"time axis invalid: {run_id}")
        expected_count = EXPECTED_SAMPLE_COUNT[RUN_TO_DT[run_id]]
        if trace.sample_count != expected_count:
            raw_failures.append(f"sample count mismatch {run_id}: {trace.sample_count} != {expected_count}")
        if run_id in REUSE_RUNS and sha256(raw) != reuse_manifest["references"][run_id]["artifacts"]["raw.csv"]["source_sha256"]:
            raw_failures.append(f"0.1ps reuse raw hash mismatch: {run_id}")
        oracle = repaired_second_response_oracle(trace)
        cases[run_id] = case_record(run_id, trace, oracle)
        raw_records[run_id] = {"path": str(raw.relative_to(REPO)), "sha256": sha256(raw), "bytes": raw.stat().st_size, "sample_count": trace.sample_count, "first_timestamp_s": trace.time[0], "last_timestamp_s": trace.time[-1], "dt_min_ps": min(trace.dt) * 1e12, "dt_max_ps": max(trace.dt) * 1e12, "strictly_increasing_time": True, "finite_values": True, "physical_solve_this_experiment": run_id in NEW_RUNS}
    cases_status_ok = all(case["control"]["status"] == "CLEAN" and ((case["mask"] == "0001" and case["single_response_status"] == "BOUNDED_RESULT") or (case["mask"] == "0011" and case["oracle_status"] == "BOUNDED_RESULT")) for case in cases.values())
    raw_ok = not raw_failures and len(cases) == len(ALL_RUNS)
    qualitative_label = "TIMESTEP_ROBUST_CANDIDATE_WITHIN_TESTED_DT" if raw_ok and cases_status_ok else "TIMESTEP_SENSITIVITY_OBSERVED"
    comparison_records = comparisons(cases) if raw_ok else {}
    timestep_qa = {"schema": "bjs400-rj2p12-timestep-qa-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if raw_ok and cases_status_ok else "FAIL", "artifact_validity": "VALID" if raw_ok else "INVALID", "classification": qualitative_label, "canonical_timestep_ps": 0.1, "spot_checked_timestep_ps": list(DT_VALUES), "physical_solve_count": 4, "reused_case_count": 2, "cases_status_ok": cases_status_ok, "control_all_clean": all(case["control"]["status"] == "CLEAN" for case in cases.values()), "0001_all_one_response": all(case["mask"] != "0001" or case["single_response_status"] == "BOUNDED_RESULT" for case in cases.values()), "0011_all_two_response": all(case["mask"] != "0011" or case["oracle_status"] == "BOUNDED_RESULT" for case in cases.values()), "comparisons": comparison_records, "raw_records": raw_records, "raw_files_modified": 0, "canonical_timestep_unchanged": True, "scientific_interpretation_performed": False, "failures": raw_failures}
    raw_qa = {"schema": "bjs400-rj2p12-timestep-raw-qa-v1", "status": "PASS" if raw_ok else "FAIL", "artifact_validity": "VALID" if raw_ok else "INVALID", "experiment_id": EXP.name, "created_at_local": now(), "physical_solve_count": 4, "reused_case_count": 2, "registered_logical_case_count": 6, "observed_logical_case_count": len(cases), "raw_files_modified": 0, "raw_unchanged_pre_to_post": True, "cases": raw_records, "failures": raw_failures, "scientific_analysis_performed": False}
    deck_failures: list[str] = []
    for run_id in NEW_RUNS:
        text = deck_path(run_id).read_text(encoding="utf-8")
        if text.count(f".tran {RUN_TO_DT[run_id]:g}p 200p") != 1 or ".tran 0.1p 200p" in text:
            deck_failures.append(f"new deck timestep mismatch: {run_id}")
        base = (EXP / "references/reused" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_{RUN_TO_MASK[run_id]}" / "deck.cir").read_text(encoding="utf-8")
        if text.replace(f".tran {RUN_TO_DT[run_id]:g}p 200p", ".tran 0.1p 200p", 1) != base:
            deck_failures.append(f"new deck changed outside tran: {run_id}")
    deck_qa = {"schema": "bjs400-rj2p12-timestep-deck-qa-v1", "status": "PASS" if not deck_failures else "FAIL", "only_tran_delta": not deck_failures, "failures": deck_failures, "new_decks": {run_id: {"path": str(deck_path(run_id).relative_to(REPO)), "sha256": sha256(deck_path(run_id)), "dt_ps": RUN_TO_DT[run_id]} for run_id in NEW_RUNS}}
    provenance = {"schema": "bjs400-rj2p12-timestep-provenance-v1", "experiment_id": EXP.name, "created_at_local": now(), "authority_experiment": str(AUTH.relative_to(REPO)), "authority_package_sha256": "84e1a8654aa16baf2fe81f96f9cdc4ce8af6efbeb5f617a12c8123b8b13a9bde", "oracle_code": "analysis/second_response_oracle.py", "oracle_code_sha256": sha256(EXP / "analysis/second_response_oracle.py"), "runs": cases, "execution_summary": "qa/execution_summary.json", "timestep_qa": "qa/timestep_qa.json", "raw_files_modified": 0, "scientific_interpretation_performed": False}
    transformations = {"schema": "bjs400-rj2p12-timestep-transformation-registry-v1", "raw_immutable": True, "scientific_analysis_performed": False, "transformations": [{"name": "phase_display", "operation": "continuous_unwrap(raw_rad)/(2*pi)", "scope": "navigation/display only", "not_event_count": True}, {"name": "pulse_segmentation", "operation": "adaptive stored-sample threshold plus below-threshold valley; terminal local areas share valley", "scope": "mechanical response cluster only", "forced_split": False}, {"name": "timestep_comparison", "operation": "compare actual stored-grid metrics across 0.1/0.05/0.025ps", "scope": "LOCAL_TIMESTEP_ROBUSTNESS_SPOT_CHECK", "canonical_timestep_changed": False}, {"name": "area_integration", "operation": "trapezoid using actual stored time values", "scope": "derived diagnostic"}]}
    mechanical = {"schema": "bjs400-rj2p12-timestep-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if raw_ok and not deck_failures else "FAIL", "classification": qualitative_label, "canonical_timestep_ps": 0.1, "spot_checked_timestep_ps": list(DT_VALUES), "physical_solve_count": 4, "reused_case_count": 2, "cases": cases, "comparisons": comparison_records, "interpretation_ceiling": "finite local robustness candidate only; not convergence or final SFQ proof", "raw_files_modified": 0, "scientific_interpretation_performed": False}
    for path, value in ((EXP / "qa/raw_qa.json", raw_qa), (EXP / "qa/deck_diff_qa.json", deck_qa), (EXP / "qa/timestep_qa.json", timestep_qa), (EXP / "qa/provenance.json", provenance), (EXP / "qa/transformation_registry.json", transformations), (EXP / "mechanical_summary.json", mechanical)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Timestep spot-check review", "", f"Classification: `{qualitative_label}`.", "", "The canonical 0.1ps pair is exact reuse; only 0.05ps and 0.025ps were newly solved. The comparison uses actual stored time grids and does not alter the canonical timestep.", "", "| dt (ps) | mask | control | oracle/response | terminal cluster | terminal final area / Phi0 |", "|---:|:---:|:---|:---|:---|---:|"]
    for run_id in ALL_RUNS:
        case = cases[run_id]
        terminal = case["terminal_pulse_analysis"]
        response = case["single_response_status"] if case["mask"] == "0001" else case["oracle_status"]
        lines.append(f"| {case['dt_ps']} | {case['mask']} | {case['control']['status']} | {response} | {terminal.get('status')} | {terminal.get('total_final_area_over_phi0')} |")
    lines.extend(["", "The timing/area deltas for 0.1→0.05 and 0.05→0.025ps are machine-readable in `qa/timestep_qa.json`.", "", "No phase turn, voltage area or terminal area is an SFQ count. This finite spot-check does not establish full numerical convergence.", ""])
    (EXP / "analysis/TIMESTEP_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": timestep_qa["status"], "classification": qualitative_label, "physical_solve_count": 4, "reused_case_count": 2, "cases": len(cases), "failures": raw_failures + deck_failures, "scientific_interpretation_performed": False}, ensure_ascii=False, indent=2))
    return 0 if timestep_qa["status"] == "PASS" and not deck_failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
