#!/usr/bin/env python3
"""Independent direct-CSV numerical and adversarial review.

This file intentionally does not import the population analyzer or its oracle.
The detector below receives only a time vector and raw columns.  Mask weight
is inspected only after the detector has produced its bounded classifications.
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
MASKS = ("0001", "0011", "0111")
NEW_RUN = "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P10_0111"
REFERENCE_CASES = ((10, "0001"), (10, "0011"), (11, "0011"), (11, "0111"), (12, "0011"), (12, "0111"))
ACTIVE_BY_MASK = {
    mask: tuple(index for index, bit in enumerate(mask, 1) if bit == "1")
    for mask in MASKS
}
PHI0 = 2.067833848e-15
MAX_RESPONSES = 4
FINAL_BASELINE = (101e-12, 110e-12)
FINAL_WINDOW = (110e-12, 200e-12)
CONTROL_BASELINE = (61e-12, 70e-12)
CONTROL_WINDOW = (70e-12, 110e-12)
CLUSTER_GAP = 2.5e-12
VOLTAGE_LABELS = (
    "V(BJ1|XBQ1)",
    "V(BJ2|XBQ1)",
    "V(QBOUT)",
    *(f"V(JTL{stage}_OUT)" for stage in range(1, 7)),
)
PHASE_LABELS = (
    "P(BJ1|XBQ1)",
    "P(BJ2|XBQ1)",
    *(f"P(B01|XJTL1_{stage})" for stage in range(1, 7)),
)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def raw_path(rj2: int, mask: str) -> Path:
    if rj2 == 10 and mask == "0111":
        return EXP / "runs" / NEW_RUN / "raw.csv"
    return EXP / f"references/rj2p{rj2}" / f"ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P{rj2}_{mask}" / "raw.csv"


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


def indexes(times: list[float], window: tuple[float, float]) -> list[int]:
    start, end = window
    return [index for index, value in enumerate(times) if start <= value < end]


def trap(times: list[float], values: list[float]) -> float | None:
    if len(times) < 2 or len(times) != len(values):
        return None
    return sum(
        (values[index] + values[index + 1])
        * 0.5
        * (times[index + 1] - times[index])
        for index in range(len(values) - 1)
    )


def integrate(times: list[float], values: list[float], window: tuple[float, float]) -> float | None:
    selected = indexes(times, window)
    return trap([times[index] for index in selected], [values[index] for index in selected])


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    output = [values[0]]
    for previous, current in zip(values, values[1:]):
        delta = current - previous
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi
        output.append(output[-1] + delta)
    return output


def phase_landmarks(times: list[float], columns: dict[str, list[float]], label: str) -> dict[str, Any]:
    baseline = indexes(times, FINAL_BASELINE)
    origin = indexes(times, FINAL_WINDOW)
    if not baseline or not origin:
        return {"landmarks": {str(index): None for index in range(1, MAX_RESPONSES + 1)}}
    continuous = unwrap(columns[label])
    reference = continuous[baseline[0]]
    landmarks: dict[str, Any] = {}
    for response_index in range(1, MAX_RESPONSES + 1):
        threshold = response_index - 0.5
        sample = next(
            (
                index
                for index in origin
                if (continuous[index] - reference) / (2.0 * math.pi) >= threshold
            ),
            None,
        )
        landmarks[str(response_index)] = {
            "sample_index": sample,
            "time_ps": times[sample] * 1e12 if sample is not None else None,
        }
    return {"landmarks": landmarks, "max_relative_turns": max((continuous[index] - reference) / (2.0 * math.pi) for index in origin)}


def voltage_clusters(times: list[float], columns: dict[str, list[float]], label: str) -> dict[str, Any]:
    baseline = indexes(times, FINAL_BASELINE)
    origin = indexes(times, FINAL_WINDOW)
    values = columns[label]
    if not baseline or not origin:
        return {"cluster_count": 0, "clusters": [], "status": "UNKNOWN"}
    center = statistics.median(values[index] for index in baseline)
    mad = statistics.median(abs(values[index] - center) for index in baseline)
    peak = max(values[index] - center for index in origin)
    threshold = max(0.35 * peak, min(5.5 * 1.4826 * mad, 0.8 * peak))
    peaks = [
        index
        for index in origin
        if values[index] - center >= threshold
        and index > 0
        and index + 1 < len(values)
        and values[index] >= values[index - 1]
        and values[index] > values[index + 1]
    ]
    groups: list[list[int]] = []
    valleys: list[dict[str, Any]] = []
    for peak_index in peaks:
        if not groups:
            groups.append([peak_index])
            continue
        previous = groups[-1][-1]
        valley = min(range(previous, peak_index + 1), key=lambda index: values[index] - center)
        split = times[peak_index] - times[previous] > CLUSTER_GAP and values[valley] - center <= threshold
        valleys.append({"valley_time_ps": times[valley] * 1e12, "split": split})
        if split:
            groups.append([peak_index])
        else:
            groups[-1].append(peak_index)
    clusters: list[dict[str, Any]] = []
    for cluster_index, group in enumerate(groups, 1):
        left, right = group[0], group[-1]
        while left > origin[0] and values[left - 1] - center > threshold:
            left -= 1
        while right < origin[-1] and values[right + 1] - center > threshold:
            right += 1
        peak_index = max(range(left, right + 1), key=lambda index: values[index])
        area = trap(times[left : right + 1], values[left : right + 1])
        clusters.append(
            {
                "cluster_index": cluster_index,
                "peak_sample_index": peak_index,
                "peak_time_ps": times[peak_index] * 1e12,
                "left_boundary_sample_index": left,
                "right_boundary_sample_index": right,
                "signed_area_over_phi0": area / PHI0 if area is not None else None,
            }
        )
    return {
        "status": "DERIVED" if len(clusters) <= MAX_RESPONSES else "AMBIGUOUS_CLUSTER_COUNT",
        "baseline_center_V": center,
        "threshold_V": threshold,
        "cluster_count": len(clusters),
        "clusters": clusters,
        "valleys": valleys,
    }


def terminal_pulses(times: list[float], terminal: dict[str, Any], columns: dict[str, list[float]]) -> dict[str, Any]:
    origin = indexes(times, FINAL_WINDOW)
    values = columns["V(JTL6_OUT)"]
    clusters = terminal.get("clusters", [])
    total = integrate(times, values, FINAL_WINDOW)
    if not clusters:
        return {"status": "NO_RESPONSE_CLUSTER", "pulse_count": 0, "pulses": [], "total_area_over_phi0": None}
    if len(clusters) == 1:
        return {"status": "ONE_RESPONSE_CLUSTER", "pulse_count": 1, "pulses": [{"peak_time_ps": clusters[0]["peak_time_ps"], "signed_area_over_phi0": total / PHI0 if total is not None else None}], "total_area_over_phi0": total / PHI0 if total is not None else None}
    valleys: list[int] = []
    peaks = [cluster["peak_sample_index"] for cluster in clusters]
    for left, right in zip(peaks, peaks[1:]):
        valley = min(range(left, right + 1), key=lambda index: values[index])
        if times[right] - times[left] <= CLUSTER_GAP or values[valley] - terminal["baseline_center_V"] > terminal["threshold_V"]:
            return {"status": "AMBIGUOUS_VALLEY", "pulse_count": len(clusters), "pulses": [], "total_area_over_phi0": total / PHI0 if total is not None else None}
        valleys.append(valley)
    boundaries = [origin[0], *valleys, origin[-1]]
    pulses = []
    for index, cluster in enumerate(clusters):
        left, right = boundaries[index], boundaries[index + 1]
        area = trap(times[left : right + 1], values[left : right + 1])
        pulses.append({"peak_time_ps": cluster["peak_time_ps"], "signed_area_over_phi0": area / PHI0 if area is not None else None})
    return {"status": f"{len(clusters)}_SEPARATED_PULSES", "pulse_count": len(clusters), "pulses": pulses, "total_area_over_phi0": total / PHI0 if total is not None else None}


def ordered(values: list[float | None]) -> bool:
    return all(value is not None for value in values) and all(left < right for left, right in zip(values, values[1:]))


def oracle(times: list[float], columns: dict[str, list[float]]) -> dict[str, Any]:
    phase = {label: phase_landmarks(times, columns, label) for label in PHASE_LABELS}
    voltage = {label: voltage_clusters(times, columns, label) for label in VOLTAGE_LABELS}
    terminal = terminal_pulses(times, voltage["V(JTL6_OUT)"], columns)
    responses = []
    for response_index in range(1, MAX_RESPONSES + 1):
        phase_times = [
            phase["P(BJ1|XBQ1)"]["landmarks"][str(response_index)]["time_ps"] if phase["P(BJ1|XBQ1)"]["landmarks"][str(response_index)] else None,
            phase["P(BJ2|XBQ1)"]["landmarks"][str(response_index)]["time_ps"] if phase["P(BJ2|XBQ1)"]["landmarks"][str(response_index)] else None,
            *[phase[f"P(B01|XJTL1_{stage})"]["landmarks"][str(response_index)]["time_ps"] if phase[f"P(B01|XJTL1_{stage})"]["landmarks"][str(response_index)] else None for stage in range(1, 7)],
        ]
        pulse_times = []
        for label in ("V(QBOUT)", *(f"V(JTL{stage}_OUT)" for stage in range(1, 7))):
            clusters = voltage[label]["clusters"]
            pulse_times.append(clusters[response_index - 1]["peak_time_ps"] if len(clusters) >= response_index else None)
        terminal_time = terminal["pulses"][response_index - 1]["peak_time_ps"] if len(terminal["pulses"]) >= response_index else None
        checks = {
            "phase_ordered_BJ1_BJ2_JTL1_to_JTL6": ordered(phase_times),
            "voltage_clusters_present": all(record["cluster_count"] >= response_index for record in voltage.values()),
            "voltage_ordered_QBOUT_JTL1_to_JTL6": ordered(pulse_times),
            "terminal_pulse_present": terminal_time is not None,
            "terminal_corresponds_to_JTL6": terminal_time is not None and terminal_time == pulse_times[-1],
        }
        responses.append({"response_index": response_index, "complete": all(checks.values()), "checks": checks, "phase_times_ps": phase_times, "downstream_peak_times_ps": pulse_times, "terminal_time_ps": terminal_time})
    count = 0
    for record in responses:
        if not record["complete"]:
            break
        count = record["response_index"]
    return {"status": "BOUNDED_RESULT" if count else "NO_COMPLETE_RESPONSE_CANDIDATE", "complete_response_count": count, "responses": responses, "cluster_counts": {label: record["cluster_count"] for label, record in voltage.items()}, "terminal": terminal, "hamming_weight_used_as_oracle_input": False}


def control_status(times: list[float], columns: dict[str, list[float]]) -> str:
    baseline = indexes(times, CONTROL_BASELINE)
    origin = indexes(times, CONTROL_WINDOW)
    if not baseline or not origin:
        return "UNKNOWN"
    markers: list[int | None] = []
    for label in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)", *(f"P(B01|XJTL1_{stage})" for stage in range(1, 7))):
        continuous = unwrap(columns[label])
        reference = continuous[baseline[0]]
        markers.append(next((index for index in origin if (continuous[index] - reference) / (2.0 * math.pi) >= 0.5), None))
    direct = all(max(abs(columns[label][index]) for index in origin) > 0.0 for label in ("V(QBOUT)", *(f"V(JTL{stage}_OUT)" for stage in range(1, 7))))
    terminal_area = integrate(times, columns["V(JTL6_OUT)"], CONTROL_WINDOW)
    return "CONTROL_GUARDRAIL_FAILURE" if all(marker is not None for marker in markers) and direct and terminal_area is not None else "CLEAN"


def main() -> int:
    failures: list[str] = []
    execution = json.loads((EXP / "qa/execution_summary.json").read_text(encoding="utf-8"))
    recorded = json.loads((EXP / "mechanical_summary.json").read_text(encoding="utf-8"))
    references = json.loads((EXP / "REFERENCE_MANIFEST.json").read_text(encoding="utf-8"))
    records: dict[str, Any] = {}
    for rj2, mask in ((10, "0111"), *REFERENCE_CASES):
        case_id = f"RJ2P{rj2}_{mask}"
        path = raw_path(rj2, mask)
        if not path.is_file():
            failures.append(f"missing raw: {case_id}")
            continue
        header, times, columns = read_raw(path)
        if len(times) != 1999 or times[0] != 0.0 or times[-1] != 1.999e-10 or any(right <= left for left, right in zip(times, times[1:])):
            failures.append(f"time grid mismatch: {case_id}")
        required = set(VOLTAGE_LABELS) | set(PHASE_LABELS)
        if not required.issubset(header):
            failures.append(f"required signal missing: {case_id}")
            continue
        raw_hash = sha256(path)
        if rj2 != 10 or mask != "0111":
            if raw_hash != references["references"][case_id]["artifacts"]["raw.csv"]["sha256"]:
                failures.append(f"reference raw hash mismatch: {case_id}")
        checked = oracle(times, columns)
        control = control_status(times, columns)
        primary = recorded["cases"].get(case_id, {})
        short_cluster_counts = {"BJ1": checked["cluster_counts"]["V(BJ1|XBQ1)"], "BJ2": checked["cluster_counts"]["V(BJ2|XBQ1)"], "QBOUT": checked["cluster_counts"]["V(QBOUT)"], **{f"JTL{stage}": checked["cluster_counts"][f"V(JTL{stage}_OUT)"] for stage in range(1, 7)}}
        if checked["complete_response_count"] != primary.get("complete_response_count_candidate") or checked["status"] != primary.get("oracle_status") or control != primary.get("control", {}).get("status"):
            failures.append(f"primary/independent mismatch: {case_id}")
        if short_cluster_counts != primary.get("voltage_signal_cluster_counts"):
            failures.append(f"cluster count mismatch: {case_id}")
        records[case_id] = {"rj2_ohm": rj2, "mask": mask, "active_bvms_from_mask": [f"BVM{index}" for index, bit in enumerate(mask, 1) if bit == "1"], "hamming_weight_observed_after_oracle": mask.count("1"), "raw_sha256": raw_hash, "sample_count": len(times), "control_status": control, "oracle_status": checked["status"], "oracle_count": checked["complete_response_count"], "hamming_weight_used_as_oracle_input": checked["hamming_weight_used_as_oracle_input"], "cluster_counts": checked["cluster_counts"], "terminal": checked["terminal"], "response_records": checked["responses"]}
    if execution.get("status") != "PASS" or execution.get("solver_solve_invocations") != 1 or execution.get("exact_new_physical_solve_count") != 1 or execution.get("reference_case_count") != 6 or execution.get("unauthorized_extra_solves") != 0 or execution.get("run_order") != [NEW_RUN]:
        failures.append("execution exactness guard failed")
    independent_source = (EXP / "analysis/independent_diagnostic_review.py").read_text(encoding="utf-8")
    oracle_signature = next((line.strip() for line in independent_source.splitlines() if line.startswith("def oracle(")), "")
    no_weight_input = oracle_signature == "def oracle(times: list[float], columns: dict[str, list[float]]) -> dict[str, Any]:"
    target = records.get("RJ2P10_0111", {})
    primary_outcome = recorded.get("outcome_category_from_recorded_evidence")
    adversarial = {
        "mask_semantics_b3b2b1b0": target.get("active_bvms_from_mask") == ["BVM2", "BVM3", "BVM4"],
        "generalized_detector_no_hamming_weight_input": all(record.get("hamming_weight_used_as_oracle_input") is False for record in records.values()) and no_weight_input,
        "rj2p10_weight2_reference_not_false_two_response": records.get("RJ2P10_0011", {}).get("oracle_count") == 1 and len(records.get("RJ2P10_0011", {}).get("response_records", [])) == 4 and records["RJ2P10_0011"]["response_records"][1]["complete"] is False,
        "0111_fourth_post_read_explicitly_checked": len(target.get("response_records", [])) == 4 and "phase_ordered_BJ1_BJ2_JTL1_to_JTL6" in target.get("response_records", [{}, {}, {}, {}])[3].get("checks", {}),
        "rj2p11_and_rj2p12_weight3_references_present": all(key in records for key in ("RJ2P11_0011", "RJ2P11_0111", "RJ2P12_0011", "RJ2P12_0111")),
        "terminal_clusters_and_jtl_order_checked": all(all("voltage_ordered_QBOUT_JTL1_to_JTL6" in response.get("checks", {}) for response in record.get("response_records", [])) for record in records.values()),
    }
    failures.extend(f"adversarial probe failed: {name}" for name, value in adversarial.items() if value is not True)
    result = {"schema": "bjs400-rj2p10-weight3-independent-review-v1", "experiment_id": EXP.name, "created_at_local": now(), "status": "PASS" if not failures else "FAIL", "review_type": "stdlib-only direct raw CSV recheck; no import of primary analyzer or oracle", "cases_checked": len(records), "records": records, "adversarial_probes": adversarial, "primary_recorded_outcome_category": primary_outcome, "new_case_response_candidate": target.get("oracle_count"), "reference_case_response_candidates": {key: value.get("oracle_count") for key, value in records.items() if key != "RJ2P10_0111"}, "raw_files_modified": 0, "scientific_interpretation_performed": False, "failures": failures}
    (EXP / "qa/independent_review.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    review_lines = [
        "# Independent population numerical/adversarial review",
        "",
        f"Review status: `{result['status']}`.",
        "",
        "The reviewer read raw CSV files directly and independently recomputed cumulative phase landmarks, adaptive stored-sample voltage clusters, terminal valley segmentation and ordered QBOUT→JTL1→...→JTL6 progression. It did not import the primary population analyzer or oracle.",
        "",
        f"- Cases checked: {len(records)}; new physical solver invocations checked: {execution.get('solver_solve_invocations')}; comparison references checked: 6.",
        f"- Recorded outcome category (not final scientific interpretation): `{primary_outcome}`.",
        f"- Adversarial probes: `{adversarial}`.",
        "- Hamming weight is inspected only after the detector produces response classifications.",
        "- Phase landmarks, voltage areas, terminal pulse areas and response candidates are not SFQ counts.",
        "",
    ]
    (EXP / "analysis/REVIEW.md").write_text("\n".join(review_lines), encoding="utf-8")
    print(json.dumps({"status": result["status"], "cases_checked": len(records), "recorded_outcome_category": primary_outcome, "new_response_candidate": target.get("oracle_count"), "adversarial_probes": adversarial, "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
