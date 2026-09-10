#!/usr/bin/env python3
"""Independent stdlib-only review of the timestep spot-check.

The reviewer reads CSV files directly and reimplements the repaired oracle;
it does not import ``timestep_analysis.py`` or the shared oracle module.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
REUSE_RUNS = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0100_0011")
NEW_RUNS = ("ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0050_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0050_0011", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0025_0001", "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0025_0011")
ALL_RUNS = REUSE_RUNS + NEW_RUNS
DT_BY_RUN = {run_id: 0.1 for run_id in REUSE_RUNS}
DT_BY_RUN.update({"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0050_0001": 0.05, "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0050_0011": 0.05, "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0025_0001": 0.025, "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_DT0025_0011": 0.025})
MASK_BY_RUN = {run_id: run_id.rsplit("_", 1)[1] for run_id in ALL_RUNS}
EXPECTED_COUNTS = {0.1: 1999, 0.05: 3999, 0.025: 7999}
PHI0 = 2.067833848e-15
VOLTAGE_SIGNALS = ("V(BJ1|XBQ1)", "V(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)")
PHASE_SIGNALS = ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "P(B01|XJTL1_1)", "P(B01|XJTL1_2)", "P(B01|XJTL1_3)", "P(B01|XJTL1_4)", "P(B01|XJTL1_5)", "P(B01|XJTL1_6)")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_path(run_id: str) -> Path:
    return EXP / ("references/reused" if run_id in REUSE_RUNS else "runs") / run_id / "raw.csv"


def read_raw(path: Path) -> tuple[list[str], list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)
    columns = {name: [] for name in header}
    for row in rows:
        if len(row) != len(header):
            raise ValueError(f"row width mismatch: {path}")
        for name, value in zip(header, row):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError(f"nonfinite value: {path}")
            columns[name].append(number)
    return header, columns["time"], columns


def indexes(times: list[float], start: float, end: float) -> list[int]:
    return [index for index, value in enumerate(times) if start <= value < end]


def trapezoid(times: list[float], values: list[float]) -> float | None:
    if len(times) < 2:
        return None
    return sum((values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]) for index in range(len(values) - 1))


def integrate(times: list[float], values: list[float], start: float, end: float) -> float | None:
    selected = indexes(times, start, end)
    return trapezoid([times[index] for index in selected], [values[index] for index in selected])


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    for previous, current in zip(values, values[1:]):
        delta = current - previous
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi
        result.append(result[-1] + delta)
    return result


def phase_landmarks(times: list[float], columns: dict[str, list[float]], label: str) -> dict[str, Any]:
    base = indexes(times, 101e-12, 110e-12)
    origin = indexes(times, 110e-12, 200e-12)
    if not base or not origin:
        return {"first_0p5_time_ps": None, "first_0p9_time_ps": None, "second_1p5_time_ps": None}
    continuous = unwrap(columns[label])
    reference = continuous[base[0]]
    def find(threshold: float) -> int | None:
        return next((index for index in origin if (continuous[index] - reference) / (2.0 * math.pi) >= threshold), None)
    first, regen, second = find(0.5), find(0.9), find(1.5)
    return {"first_0p5_time_ps": times[first] * 1e12 if first is not None else None, "first_0p9_time_ps": times[regen] * 1e12 if regen is not None else None, "first_0p9_index": regen, "second_1p5_time_ps": times[second] * 1e12 if second is not None else None}


def voltage_clusters(times: list[float], columns: dict[str, list[float]], label: str) -> dict[str, Any]:
    base = indexes(times, 101e-12, 110e-12)
    origin = indexes(times, 110e-12, 200e-12)
    values = columns[label]
    center = statistics.median(values[index] for index in base)
    mad = statistics.median(abs(values[index] - center) for index in base)
    threshold = max(5.5 * 1.4826 * mad, 0.35 * max(values[index] - center for index in origin))
    peaks = [index for index in origin if values[index] - center >= threshold and index > 0 and index + 1 < len(values) and values[index] >= values[index - 1] and values[index] > values[index + 1]]
    groups: list[list[int]] = []
    valleys: list[dict[str, Any]] = []
    for index in peaks:
        if not groups:
            groups.append([index])
            continue
        previous = groups[-1][-1]
        valley = min(range(previous, index + 1), key=lambda candidate: values[candidate] - center)
        split = times[index] - times[previous] > 2.5e-12 and values[valley] - center <= threshold
        valleys.append({"valley_time_ps": times[valley] * 1e12, "valley_value_V": values[valley] - center, "split": split})
        if split:
            groups.append([index])
        else:
            groups[-1].append(index)
    clusters = []
    for number, group in enumerate(groups, 1):
        left, right = group[0], group[-1]
        while left > origin[0] and values[left - 1] - center > threshold:
            left -= 1
        while right < origin[-1] and values[right + 1] - center > threshold:
            right += 1
        peak = max(range(left, right + 1), key=lambda candidate: values[candidate])
        clusters.append({"cluster_index": number, "peak_sample_index": peak, "peak_time_ps": times[peak] * 1e12, "peak_voltage_V": values[peak], "signed_area_V_s": integrate(times, values, times[left], times[right] + (times[1] - times[0]))})
    return {"baseline_center_V": center, "threshold_V": threshold, "valley_records": valleys, "cluster_count": len(clusters), "clusters": clusters}


def terminal_pulses(times: list[float], columns: dict[str, list[float]], terminal: dict[str, Any]) -> dict[str, Any]:
    origin = indexes(times, 110e-12, 200e-12)
    values = columns["V(JTL6_OUT)"]
    total = integrate(times, values, 110e-12, 200e-12)
    clusters = terminal["clusters"]
    base = {"total_final_area_over_phi0": total / PHI0 if total is not None else None, "not_population_count": True}
    if len(clusters) == 1:
        return {**base, "status": "ONE_RESPONSE_CLUSTER", "pulse_count": 1}
    if len(clusters) != 2:
        return {**base, "status": "AMBIGUOUS_CLUSTER_COUNT", "pulse_count": len(clusters)}
    first, second = clusters[0]["peak_sample_index"], clusters[1]["peak_sample_index"]
    valley = min(range(first, second + 1), key=lambda index: values[index])
    if values[valley] - terminal["baseline_center_V"] > terminal["threshold_V"]:
        return {**base, "status": "AMBIGUOUS_VALLEY", "pulse_count": 2}
    first_area = trapezoid(times[origin[0]:valley + 1], values[origin[0]:valley + 1])
    second_area = trapezoid(times[valley:origin[-1] + 1], values[valley:origin[-1] + 1])
    return {**base, "status": "TWO_SEPARATED_PULSES", "pulse_count": 2, "pulse_separation_ps": times[second] * 1e12 - times[first] * 1e12, "pulses": [{"peak_time_ps": clusters[0]["peak_time_ps"], "signed_area_over_phi0": first_area / PHI0}, {"peak_time_ps": clusters[1]["peak_time_ps"], "signed_area_over_phi0": second_area / PHI0}]}


def oracle(times: list[float], columns: dict[str, list[float]]) -> dict[str, Any]:
    phases = {label: phase_landmarks(times, columns, label) for label in PHASE_SIGNALS}
    first = [phases["P(BJ1|XBQ1)"]["first_0p5_time_ps"], phases["P(BJ2|XBQ1)"]["first_0p5_time_ps"], *(phases[f"P(B01|XJTL1_{stage})"]["first_0p5_time_ps"] for stage in range(1, 7))]
    second = [phases["P(BJ1|XBQ1)"]["second_1p5_time_ps"], phases["P(BJ2|XBQ1)"]["second_1p5_time_ps"], *(phases[f"P(B01|XJTL1_{stage})"]["second_1p5_time_ps"] for stage in range(1, 7))]
    clusters = {label: voltage_clusters(times, columns, label) for label in VOLTAGE_SIGNALS}
    terminal = terminal_pulses(times, columns, clusters["V(JTL6_OUT)"])
    def ct(label: str, index: int) -> float | None:
        values = clusters[label]["clusters"]
        return values[index]["peak_time_ps"] if len(values) > index else None
    first_downstream = [ct("V(QBOUT)", 0)] + [ct(f"V(JTL{stage}_OUT)", 0) for stage in range(1, 7)]
    second_downstream = [ct("V(QBOUT)", 1)] + [ct(f"V(JTL{stage}_OUT)", 1) for stage in range(1, 7)]
    ordered = lambda values: all(value is not None for value in values) and all(left < right for left, right in zip(values, values[1:]))
    first_checks = {"first_phase_ordered": ordered(first), "first_voltage_cluster_present": all(value["cluster_count"] >= 1 for value in clusters.values()), "first_downstream_voltage_ordered": ordered(first_downstream), "first_terminal_present": terminal["pulse_count"] >= 1}
    second_checks = {"second_phase_ordered": ordered(second), "two_voltage_clusters": all(value["cluster_count"] == 2 for value in clusters.values()), "second_downstream_voltage_ordered": ordered(second_downstream), "two_terminal_pulses": terminal["status"] == "TWO_SEPARATED_PULSES"}
    return {"status": "BOUNDED_RESULT" if all(second_checks.values()) else "NO_SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE", "first_response_status": "BOUNDED_RESULT" if all(first_checks.values()) else "NO_FIRST_COMPLETE_RESPONSE_CANDIDATE", "single_response_status": "BOUNDED_RESULT" if all(first_checks.values()) and all(value["cluster_count"] == 1 for value in clusters.values()) and terminal["status"] == "ONE_RESPONSE_CLUSTER" else "NO_SINGLE_COMPLETE_RESPONSE_CANDIDATE", "first_checks": first_checks, "second_checks": second_checks, "second_progression_times_ps": second, "cluster_counts": {label: value["cluster_count"] for label, value in clusters.items()}, "terminal": terminal}


def control_clean(times: list[float], columns: dict[str, list[float]]) -> str:
    base = indexes(times, 61e-12, 70e-12)
    origin = indexes(times, 70e-12, 110e-12)
    if not base or not origin:
        return "UNKNOWN"
    markers = []
    for label, threshold in (("P(BJ1|XBQ1)", 0.5), ("P(BJ2|XBQ1)", 0.9)):
        continuous = unwrap(columns[label]); ref = continuous[base[0]]
        markers.append(next((index for index in origin if (continuous[index] - ref) / (2 * math.pi) >= threshold), None))
    for stage in range(1, 7):
        continuous = unwrap(columns[f"P(B01|XJTL1_{stage})"]); ref = continuous[base[0]]
        markers.append(next((index for index in origin if (continuous[index] - ref) / (2 * math.pi) >= 0.5), None))
    return "UNSUITABLE_WORKING_POINT" if all(index is not None for index in markers) else "CLEAN"


def main() -> int:
    analysis = json.loads((EXP / "mechanical_summary.json").read_text(encoding="utf-8"))
    recorded_qa = json.loads((EXP / "qa/timestep_qa.json").read_text(encoding="utf-8"))
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    reuse = json.loads((EXP / "REUSED_REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    failures: list[str] = []
    records: dict[str, Any] = {}
    for run_id in ALL_RUNS:
        path = raw_path(run_id)
        if not path.is_file():
            failures.append(f"missing raw: {run_id}")
            continue
        header, times, columns = read_raw(path)
        if len(times) != EXPECTED_COUNTS[DT_BY_RUN[run_id]] or any(right <= left for left, right in zip(times, times[1:])):
            failures.append(f"time grid mismatch: {run_id}")
        raw_hash = sha256(path)
        if run_id in REUSE_RUNS and raw_hash != reuse["references"][run_id]["artifacts"]["raw.csv"]["source_sha256"]:
            failures.append(f"reuse raw hash mismatch: {run_id}")
        checked = oracle(times, columns)
        control = control_clean(times, columns)
        recorded = analysis["cases"][run_id]
        if checked["status"] != recorded["oracle_status"] or checked["first_response_status"] != recorded["first_response_status"] or checked["single_response_status"] != recorded["single_response_status"] or control != recorded["control"]["status"]:
            failures.append(f"independent oracle/status mismatch: {run_id}")
        records[run_id] = {"dt_ps": DT_BY_RUN[run_id], "mask": MASK_BY_RUN[run_id], "raw_sha256": raw_hash, "sample_count": len(times), "control_status": control, "oracle_status": checked["status"], "first_response_status": checked["first_response_status"], "single_response_status": checked["single_response_status"], "second_checks": checked["second_checks"], "second_progression_times_ps": checked["second_progression_times_ps"], "cluster_counts": checked["cluster_counts"], "terminal": checked["terminal"]}
    if execution.get("solver_solve_invocations") != 4 or execution.get("reused_physical_case_count") != 2 or execution.get("unauthorized_extra_solves") != 0:
        failures.append("execution count/extra-solve guard failed")
    expected_robust = all(record["control_status"] == "CLEAN" and ((record["mask"] == "0001" and record["single_response_status"] == "BOUNDED_RESULT") or (record["mask"] == "0011" and record["oracle_status"] == "BOUNDED_RESULT")) for record in records.values())
    adversarial = {
        "canonical_0p1_0001_not_two": records.get(REUSE_RUNS[0], {}).get("single_response_status") == "BOUNDED_RESULT" and records.get(REUSE_RUNS[0], {}).get("oracle_status") != "BOUNDED_RESULT" and records.get(REUSE_RUNS[0], {}).get("terminal", {}).get("status") == "ONE_RESPONSE_CLUSTER",
        "canonical_0p1_0011_two_explained": records.get(REUSE_RUNS[1], {}).get("oracle_status") == "BOUNDED_RESULT" and all((records.get(REUSE_RUNS[1], {}).get("second_checks") or {}).values()) and records.get(REUSE_RUNS[1], {}).get("terminal", {}).get("status") == "TWO_SEPARATED_PULSES",
        "all_finer_cases_preserve_qualitative_class": expected_robust,
    }
    for name, value in adversarial.items():
        if value is not True:
            failures.append(f"adversarial timestep probe failed: {name}")
    result = {"schema": "bjs400-rj2p12-timestep-independent-review-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "review_type": "stdlib-only direct raw recheck plus independent repaired-oracle implementation", "cases_checked": len(records), "records": records, "adversarial_probes": adversarial, "recorded_classification": recorded_qa.get("classification"), "independent_qualitative_classification": "TIMESTEP_ROBUST_CANDIDATE_WITHIN_TESTED_DT" if expected_robust else "TIMESTEP_SENSITIVITY_OBSERVED", "raw_immutable_check": recorded_qa.get("raw_files_modified") == 0, "scientific_interpretation_performed": False, "failures": failures}
    (EXP / "qa/independent_review.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = ["# Independent timestep numerical/adversarial review", "", f"Review status: `{result['status']}`.", "", "This review read the raw CSV files directly and independently reimplemented the FINAL-baseline phase landmarks, voltage-cluster valley rule and terminal pulse segmentation; it did not import the primary timestep analyzer or oracle module.", "", f"- Cases checked: {len(records)}; new physical solves checked from execution summary: {execution.get('solver_solve_invocations')}; exact 0.1ps reuse cases: {len(REUSE_RUNS)}.", f"- Independent qualitative classification: `{result['independent_qualitative_classification']}`.", f"- Adversarial probes: `{adversarial}`.", "- The canonical 0.1ps timestep remains the project standard; finer values are a local spot-check only.", "", "No phase turn, voltage area or terminal area is an SFQ count. A finite timestep classification is not a convergence theorem or final physical proof.", ""]
    (EXP / "analysis/REVIEW.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": result["status"], "cases_checked": len(records), "independent_qualitative_classification": result["independent_qualitative_classification"], "adversarial_probes": adversarial, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
