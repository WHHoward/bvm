#!/usr/bin/env python3
"""Generalized N-response mechanical oracle for selected BVM masks.

The detector derives a response count from evidence.  It never receives or
uses Hamming weight, mask position or an expected population count.
"""

from __future__ import annotations

import math
import statistics
from collections import OrderedDict
from typing import Any


PHI0 = 2.067833848e-15
MAX_RESPONSES = 4
FINAL_BASELINE = (101e-12, 110e-12)
FINAL_WINDOW = (110e-12, 200e-12)
CLUSTER_GAP_S = 2.5e-12
BASELINE_NOISE_MULTIPLIER = 5.5
PEAK_FRACTION = 0.35
NOISE_CAP_FRACTION = 0.8
PHASE_LABELS = OrderedDict(
    [
        ("BJ1", "P(BJ1|XBQ1)"),
        ("BJ2", "P(BJ2|XBQ1)"),
        *[(f"JTL{stage}", f"P(B01|XJTL1_{stage})") for stage in range(1, 7)],
    ]
)
VOLTAGE_LABELS = OrderedDict(
    [
        ("BJ1", "V(BJ1|XBQ1)"),
        ("BJ2", "V(BJ2|XBQ1)"),
        ("QBOUT", "V(QBOUT)"),
        *[(f"JTL{stage}", f"V(JTL{stage}_OUT)") for stage in range(1, 7)],
    ]
)
RESPONSE_VOLTAGE_LABELS = tuple(VOLTAGE_LABELS.values())


def _indices(times: tuple[float, ...], start: float, end: float) -> tuple[int, ...]:
    return tuple(index for index, value in enumerate(times) if start <= value < end)


def _trap(times: tuple[float, ...], values: tuple[float, ...]) -> float | None:
    if len(times) < 2 or len(times) != len(values):
        return None
    return sum((values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]) for index in range(len(values) - 1))


def _unwrap(values: tuple[float, ...]) -> tuple[float, ...]:
    if not values:
        return ()
    output = [values[0]]
    for previous, current in zip(values, values[1:]):
        delta = current - previous
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi
        output.append(output[-1] + delta)
    return tuple(output)


def _column(trace: Any, label: str) -> tuple[float, ...]:
    return tuple(float(value) for value in trace.column(label))


def phase_landmarks(trace: Any, label: str) -> dict[str, Any]:
    times = tuple(trace.time)
    baseline = _indices(times, *FINAL_BASELINE)
    origin = _indices(times, *FINAL_WINDOW)
    if not baseline or not origin:
        return {"status": "UNKNOWN", "label": label, "landmarks": {str(k): None for k in range(1, MAX_RESPONSES + 1)}}
    continuous = _unwrap(_column(trace, label))
    reference = continuous[baseline[0]]
    landmarks: dict[str, Any] = OrderedDict()
    for response_index in range(1, MAX_RESPONSES + 1):
        threshold = response_index - 0.5
        sample = next((index for index in origin if (continuous[index] - reference) / (2.0 * math.pi) >= threshold), None)
        landmarks[str(response_index)] = {
            "threshold_turns": threshold,
            "sample_index": sample,
            "time_ps": times[sample] * 1e12 if sample is not None else None,
            "navigation_only": True,
        }
    first_0p9 = next((index for index in origin if (continuous[index] - reference) / (2.0 * math.pi) >= 0.9), None)
    return {
        "status": "DERIVED",
        "label": label,
        "raw_unit": "rad",
        "display_unit": "turns",
        "conversion": "continuous_unwrap(raw_rad)/(2*pi)",
        "baseline_window_ps": [101.0, 110.0],
        "origin_window_ps": [110.0, 200.0],
        "baseline_reference_time_ps": times[baseline[0]] * 1e12,
        "landmarks": landmarks,
        "first_0p9_sample_index": first_0p9,
        "first_0p9_time_ps": times[first_0p9] * 1e12 if first_0p9 is not None else None,
        "max_relative_turns": max((continuous[index] - reference) / (2.0 * math.pi) for index in origin),
        "final_relative_turns": (continuous[origin[-1]] - reference) / (2.0 * math.pi),
        "not_event_count": True,
        "not_sfq_count": True,
    }


def voltage_clusters(trace: Any, label: str) -> dict[str, Any]:
    times = tuple(trace.time)
    values = _column(trace, label)
    baseline = _indices(times, *FINAL_BASELINE)
    origin = _indices(times, *FINAL_WINDOW)
    if not baseline or not origin:
        return {"status": "UNKNOWN", "label": label, "clusters": [], "cluster_count": 0}
    baseline_values = tuple(values[index] for index in baseline)
    center = statistics.median(baseline_values)
    mad = statistics.median(abs(value - center) for value in baseline_values)
    robust_noise = 1.4826 * mad
    peak_positive = max(values[index] - center for index in origin)
    raw_noise_threshold = BASELINE_NOISE_MULTIPLIER * robust_noise
    threshold = max(PEAK_FRACTION * peak_positive, min(raw_noise_threshold, NOISE_CAP_FRACTION * peak_positive))
    peaks = [
        index for index in origin
        if values[index] - center >= threshold
        and index > 0
        and index + 1 < len(values)
        and values[index] >= values[index - 1]
        and values[index] > values[index + 1]
    ]
    groups: list[list[int]] = []
    valleys: list[dict[str, Any]] = []
    for index in peaks:
        if not groups:
            groups.append([index])
            continue
        previous = groups[-1][-1]
        valley = min(range(previous, index + 1), key=lambda candidate: values[candidate] - center)
        split = times[index] - times[previous] > CLUSTER_GAP_S and values[valley] - center <= threshold
        valleys.append({"left_peak_time_ps": times[previous] * 1e12, "right_peak_time_ps": times[index] * 1e12, "valley_time_ps": times[valley] * 1e12, "valley_value_V": values[valley] - center, "split": split})
        if split:
            groups.append([index])
        else:
            groups[-1].append(index)
    clusters: list[dict[str, Any]] = []
    for number, group in enumerate(groups, 1):
        left, right = group[0], group[-1]
        while left > origin[0] and values[left - 1] - center > threshold:
            left -= 1
        while right < origin[-1] and values[right + 1] - center > threshold:
            right += 1
        peak = max(range(left, right + 1), key=lambda candidate: values[candidate])
        area = _trap(tuple(times[index] for index in range(left, right + 1)), tuple(values[index] for index in range(left, right + 1)))
        clusters.append({"cluster_index": number, "peak_sample_index": peak, "peak_time_ps": times[peak] * 1e12, "peak_voltage_V": values[peak], "left_boundary_time_ps": times[left] * 1e12, "right_boundary_time_ps": times[right] * 1e12, "sample_count": right - left + 1, "signed_area_V_s": area, "signed_area_over_phi0": area / PHI0 if area is not None else None})
    return {"status": "DERIVED" if len(clusters) <= MAX_RESPONSES else "AMBIGUOUS_CLUSTER_COUNT", "label": label, "baseline_center_V": center, "baseline_mad_V": mad, "robust_noise_V": robust_noise, "raw_noise_threshold_V": raw_noise_threshold, "threshold_V": threshold, "threshold_rule": "max(0.35*positive FINAL peak, min(5.5*1.4826*baseline MAD, 0.8*positive FINAL peak))", "cluster_gap_rule_ps": 2.5, "valley_required_for_split": True, "valley_records": valleys, "clusters": clusters, "cluster_count": len(clusters), "not_event_count": True, "not_sfq_count": True}


def terminal_pulses(trace: Any, terminal_clusters: dict[str, Any]) -> dict[str, Any]:
    times = tuple(trace.time)
    values = _column(trace, "V(JTL6_OUT)")
    origin = _indices(times, *FINAL_WINDOW)
    clusters = terminal_clusters.get("clusters", [])
    total = _trap(tuple(times[index] for index in origin), tuple(values[index] for index in origin)) if origin else None
    base = {"signal": "V(JTL6_OUT)", "window_ps": [110.0, 200.0], "total_final_area_V_s": total, "total_final_area_over_phi0": total / PHI0 if total is not None else None, "segmentation_rule": "stored-sample significant peaks; split only at a below-threshold waveform valley; shared valley boundaries", "not_population_count": True, "not_sfq_count": True}
    if not origin or not clusters:
        return {**base, "status": "NO_RESPONSE_CLUSTER", "pulse_count": 0, "pulses": [], "split_performed": False}
    if len(clusters) > MAX_RESPONSES:
        return {**base, "status": "AMBIGUOUS_CLUSTER_COUNT", "pulse_count": len(clusters), "pulses": [], "split_performed": False}
    if len(clusters) == 1:
        return {**base, "status": "ONE_RESPONSE_CLUSTER", "pulse_count": 1, "pulses": [{"pulse_index": 1, "peak_time_ps": clusters[0]["peak_time_ps"], "left_boundary_time_ps": times[origin[0]] * 1e12, "right_boundary_time_ps": times[origin[-1]] * 1e12, "signed_area_V_s": total, "signed_area_over_phi0": total / PHI0 if total is not None else None}], "split_performed": False}
    peak_indices = [cluster["peak_sample_index"] for cluster in clusters]
    valleys: list[int] = []
    for left_peak, right_peak in zip(peak_indices, peak_indices[1:]):
        valley = min(range(left_peak, right_peak + 1), key=lambda index: values[index])
        if times[right_peak] - times[left_peak] <= CLUSTER_GAP_S or values[valley] - terminal_clusters["baseline_center_V"] > terminal_clusters["threshold_V"]:
            return {**base, "status": "AMBIGUOUS_VALLEY", "pulse_count": len(clusters), "pulses": [], "split_performed": False, "ambiguous_valley_time_ps": times[valley] * 1e12}
        valleys.append(valley)
    boundaries = [origin[0], *valleys, origin[-1]]
    pulses: list[dict[str, Any]] = []
    for index, cluster in enumerate(clusters):
        left, right = boundaries[index], boundaries[index + 1]
        area = _trap(times[left:right + 1], values[left:right + 1])
        pulses.append({"pulse_index": index + 1, "peak_time_ps": cluster["peak_time_ps"], "left_boundary_time_ps": times[left] * 1e12, "right_boundary_time_ps": times[right] * 1e12, "signed_area_V_s": area, "signed_area_over_phi0": area / PHI0 if area is not None else None})
    return {**base, "status": f"{len(clusters)}_SEPARATED_PULSES", "pulse_count": len(clusters), "pulses": pulses, "pulse_separation_ps": [pulses[index + 1]["peak_time_ps"] - pulses[index]["peak_time_ps"] for index in range(len(pulses) - 1)], "valley_times_ps": [times[index] * 1e12 for index in valleys], "split_performed": True, "area_partition_residual_V_s": total - sum(pulse["signed_area_V_s"] for pulse in pulses) if total is not None and all(pulse["signed_area_V_s"] is not None for pulse in pulses) else None}


def _time(record: dict[str, Any], response_index: int) -> float | None:
    landmark = record.get("landmarks", {}).get(str(response_index))
    return landmark.get("time_ps") if isinstance(landmark, dict) else None


def _ordered(values: list[float | None]) -> bool:
    return all(value is not None for value in values) and all(left < right for left, right in zip(values, values[1:]))


def generalized_response_oracle(trace: Any) -> dict[str, Any]:
    phases = OrderedDict((name, phase_landmarks(trace, label)) for name, label in PHASE_LABELS.items())
    voltages = OrderedDict((name, voltage_clusters(trace, label)) for name, label in VOLTAGE_LABELS.items())
    terminal = terminal_pulses(trace, voltages["JTL6"])
    responses: list[dict[str, Any]] = []
    for response_index in range(1, MAX_RESPONSES + 1):
        phase_times = [_time(phases["BJ1"], response_index), _time(phases["BJ2"], response_index)] + [_time(phases[f"JTL{stage}"], response_index) for stage in range(1, 7)]
        phase_checks = {"BJ1_before_BJ2": phase_times[0] is not None and phase_times[1] is not None and phase_times[0] < phase_times[1], "ordered_BJ1_BJ2_JTL1_to_JTL6": _ordered(phase_times)}
        pulse_times = [voltages["QBOUT"].get("clusters", [])[response_index - 1].get("peak_time_ps") if len(voltages["QBOUT"].get("clusters", [])) >= response_index else None] + [voltages[f"JTL{stage}"].get("clusters", [])[response_index - 1].get("peak_time_ps") if len(voltages[f"JTL{stage}"].get("clusters", [])) >= response_index else None for stage in range(1, 7)]
        terminal_time = terminal.get("pulses", [])[response_index - 1].get("peak_time_ps") if len(terminal.get("pulses", [])) >= response_index else None
        voltage_checks = {"all_registered_voltage_signals_have_response_cluster": all(record.get("cluster_count", 0) >= response_index for record in voltages.values()), "ordered_QBOUT_JTL1_to_JTL6": _ordered(pulse_times), "terminal_pulse_present": terminal_time is not None, "terminal_corresponds_to_JTL6_output": terminal_time is not None and pulse_times[-1] == terminal_time}
        checks = {**phase_checks, **voltage_checks}
        responses.append({"response_index": response_index, "complete": all(checks.values()), "status": "BOUNDED_RESULT" if all(checks.values()) else "INCOMPLETE_OR_UNKNOWN", "phase_landmark_times_ps": {"BJ1": phase_times[0], "BJ2": phase_times[1], **{f"JTL{stage}": phase_times[stage + 1] for stage in range(1, 7)}}, "downstream_voltage_peak_times_ps": {"QBOUT": pulse_times[0], **{f"JTL{stage}": pulse_times[stage] for stage in range(1, 7)}, "terminal": terminal_time}, "phase_checks": phase_checks, "voltage_checks": voltage_checks, "checks": checks, "not_event_count": True, "not_sfq_count": True})
    count = 0
    for response in responses:
        if not response["complete"]:
            break
        count = response["response_index"]
    extra_cluster_ambiguity = any(record.get("cluster_count", 0) > MAX_RESPONSES for record in voltages.values()) or terminal.get("status") == "AMBIGUOUS_CLUSTER_COUNT"
    if extra_cluster_ambiguity:
        count = 0
        for response in responses:
            if not response["complete"]:
                break
            count = response["response_index"]
    return {"schema": "bjs400-n-response-multi-evidence-oracle-v1", "max_supported_responses": MAX_RESPONSES, "status": "BOUNDED_RESULT" if count > 0 else "NO_COMPLETE_RESPONSE_CANDIDATE", "complete_response_count": count, "response_count_candidate": count, "response_records": responses, "phase_landmarks": phases, "voltage_signal_cluster_counts": {name: record.get("cluster_count") for name, record in voltages.items()}, "voltage_pulse_clusters": voltages, "terminal_pulse_analysis": terminal, "extra_cluster_ambiguity": extra_cluster_ambiguity, "hamming_weight_used_as_oracle_input": False, "phase_reference_policy": "all cumulative landmarks use FINAL-origin baseline [101,110) ps; no L1 segment is a phase reference", "not_event_count": True, "not_sfq_count": True, "scientific_interpretation_performed": False}
