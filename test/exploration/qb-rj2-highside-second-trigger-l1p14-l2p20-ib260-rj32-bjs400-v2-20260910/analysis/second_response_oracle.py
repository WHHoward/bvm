#!/usr/bin/env python3
"""Registered cumulative/pulse oracle for the second FINAL-origin response.

This module deliberately keeps two evidence paths visible:

* cumulative phase landmarks are measured from the common 101--110 ps
  FINAL-origin baseline; and
* direct voltage response clusters are found from stored samples and a
  registered adaptive threshold/valley rule.

Neither path is an SFQ counter.  The result is a bounded mechanical candidate
only, and a missing independent path keeps the second-response status negative.
"""

from __future__ import annotations

import math
import statistics
from collections import OrderedDict
from typing import Any


PHI0 = 2.067833848e-15
FINAL_BASELINE = (101e-12, 110e-12)
FINAL_WINDOW = (110e-12, 200e-12)
VOLTAGE_SIGNALS = (
    "V(BJ1|XBQ1)",
    "V(BJ2|XBQ1)",
    "V(QBOUT)",
    "V(JTL1_OUT)",
    "V(JTL2_OUT)",
    "V(JTL3_OUT)",
    "V(JTL4_OUT)",
    "V(JTL5_OUT)",
    "V(JTL6_OUT)",
)
PHASE_SIGNALS = (
    "P(BJ1|XBQ1)",
    "P(BJ2|XBQ1)",
    "P(B01|XJTL1_1)",
    "P(B01|XJTL1_2)",
    "P(B01|XJTL1_3)",
    "P(B01|XJTL1_4)",
    "P(B01|XJTL1_5)",
    "P(B01|XJTL1_6)",
)
CLUSTER_GAP_S = 2.5e-12
BASELINE_NOISE_MULTIPLIER = 5.5
PEAK_FRACTION = 0.35


def _indices(times: tuple[float, ...], start: float, end: float) -> tuple[int, ...]:
    return tuple(index for index, value in enumerate(times) if start <= value < end)


def _trapezoid(times: tuple[float, ...], values: tuple[float, ...]) -> float | None:
    if len(times) < 2 or len(values) != len(times):
        return None
    return sum((values[index] + values[index + 1]) * 0.5 * (times[index + 1] - times[index]) for index in range(len(times) - 1))


def _unwrap(values: tuple[float, ...]) -> tuple[float, ...]:
    if not values:
        return ()
    result = [values[0]]
    for previous, current in zip(values, values[1:]):
        delta = current - previous
        while delta > math.pi:
            delta -= 2.0 * math.pi
        while delta < -math.pi:
            delta += 2.0 * math.pi
        result.append(result[-1] + delta)
    return tuple(result)


def _column(trace: Any, label: str) -> tuple[float, ...]:
    return tuple(float(value) for value in trace.column(label))


def phase_landmarks(trace: Any, label: str) -> dict[str, Any]:
    times = tuple(trace.time)
    baseline = _indices(times, *FINAL_BASELINE)
    origin = _indices(times, *FINAL_WINDOW)
    if not baseline or not origin:
        return {"status": "UNKNOWN", "label": label, "raw_unit": "rad", "display_unit": "turns"}
    continuous = _unwrap(_column(trace, label))
    reference = continuous[baseline[0]]
    relative = {index: (continuous[index] - reference) / (2.0 * math.pi) for index in origin}

    def crossing(threshold: float) -> int | None:
        return next((index for index in origin if relative[index] >= threshold), None)

    first = crossing(0.5)
    regen = crossing(0.9)
    second = crossing(1.5)
    return {
        "status": "DERIVED",
        "label": label,
        "raw_unit": "rad",
        "display_unit": "turns",
        "conversion": "continuous_unwrap(raw_rad)/(2*pi)",
        "baseline_window_ps": [101.0, 110.0],
        "origin_window_ps": [110.0, 200.0],
        "baseline_reference_time_ps": times[baseline[0]] * 1e12,
        "first_0p5_sample_index": first,
        "first_0p5_time_ps": times[first] * 1e12 if first is not None else None,
        "first_0p9_sample_index": regen,
        "first_0p9_time_ps": times[regen] * 1e12 if regen is not None else None,
        "second_1p5_sample_index": second,
        "second_1p5_time_ps": times[second] * 1e12 if second is not None else None,
        "max_relative_turns": max(relative.values()),
        "final_relative_turns": relative[origin[-1]],
        "not_event_count": True,
        "not_sfq_count": True,
    }


def _voltage_clusters(trace: Any, label: str) -> dict[str, Any]:
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
    threshold = max(BASELINE_NOISE_MULTIPLIER * robust_noise, PEAK_FRACTION * peak_positive)
    peaks = [
        index for index in origin
        if values[index] - center >= threshold
        and index > 0
        and index + 1 < len(values)
        and values[index] >= values[index - 1]
        and values[index] > values[index + 1]
    ]
    groups: list[list[int]] = []
    valley_records: list[dict[str, Any]] = []
    for index in peaks:
        if not groups:
            groups.append([index])
            continue
        previous = groups[-1][-1]
        valley_index = min(range(previous, index + 1), key=lambda candidate: values[candidate] - center)
        valley_value = values[valley_index] - center
        separated = times[index] - times[previous] > CLUSTER_GAP_S and valley_value <= threshold
        valley_records.append({
            "left_peak_time_ps": times[previous] * 1e12,
            "right_peak_time_ps": times[index] * 1e12,
            "valley_time_ps": times[valley_index] * 1e12,
            "valley_value_V": values[valley_index] - center,
            "split": separated,
        })
        if separated:
            groups.append([index])
        else:
            groups[-1].append(index)

    clusters: list[dict[str, Any]] = []
    for position, group in enumerate(groups):
        left = group[0]
        right = group[-1]
        while left > origin[0] and values[left - 1] - center > threshold:
            left -= 1
        while right < origin[-1] and values[right + 1] - center > threshold:
            right += 1
        peak_index = max(range(left, right + 1), key=lambda candidate: values[candidate])
        area = _trapezoid(tuple(times[index] for index in range(left, right + 1)), tuple(values[index] for index in range(left, right + 1)))
        clusters.append({
            "cluster_index": position + 1,
            "peak_sample_index": peak_index,
            "peak_time_ps": times[peak_index] * 1e12,
            "peak_voltage_V": values[peak_index],
            "left_boundary_time_ps": times[left] * 1e12,
            "right_boundary_time_ps": times[right] * 1e12,
            "sample_count": right - left + 1,
            "signed_area_V_s": area,
            "signed_area_over_phi0": area / PHI0 if area is not None else None,
        })
    return {
        "status": "DERIVED",
        "label": label,
        "baseline_center_V": center,
        "baseline_mad_V": mad,
        "robust_noise_V": robust_noise,
        "threshold_V": threshold,
        "threshold_rule": "max(5.5 * 1.4826 * baseline MAD, 0.35 * positive FINAL peak above baseline median)",
        "cluster_gap_rule_ps": 2.5,
        "valley_required_for_split": True,
        "valley_records": valley_records,
        "clusters": clusters,
        "cluster_count": len(clusters),
        "not_event_count": True,
        "not_sfq_count": True,
    }


def _inclusive_area(times: tuple[float, ...], values: tuple[float, ...], left: int, right: int) -> float | None:
    return _trapezoid(times[left:right + 1], values[left:right + 1])


def terminal_pulses(trace: Any, terminal_clusters: dict[str, Any]) -> dict[str, Any]:
    times = tuple(trace.time)
    values = _column(trace, "V(JTL6_OUT)")
    origin = _indices(times, *FINAL_WINDOW)
    clusters = terminal_clusters.get("clusters", [])
    total_area = _trapezoid(tuple(times[index] for index in origin), tuple(values[index] for index in origin)) if origin else None
    base: dict[str, Any] = {
        "status": "UNKNOWN",
        "signal": "V(JTL6_OUT)",
        "window_ps": [110.0, 200.0],
        "segmentation_rule": "stored-sample significant peaks with adaptive threshold; split only at a below-threshold waveform valley",
        "total_final_area_V_s": total_area,
        "total_final_area_over_phi0": total_area / PHI0 if total_area is not None else None,
        "not_population_count": True,
        "not_sfq_count": True,
    }
    if len(origin) < 2 or not clusters:
        return {**base, "reason": "no terminal response cluster"}
    if len(clusters) == 1:
        cluster = clusters[0]
        return {
            **base,
            "status": "ONE_RESPONSE_CLUSTER",
            "pulse_count": 1,
            "pulses": [{
                "pulse_index": 1,
                "peak_time_ps": cluster["peak_time_ps"],
                "left_boundary_time_ps": times[origin[0]] * 1e12,
                "right_boundary_time_ps": times[origin[-1]] * 1e12,
                "signed_area_V_s": total_area,
                "signed_area_over_phi0": total_area / PHI0 if total_area is not None else None,
            }],
            "split_performed": False,
        }
    if len(clusters) != 2:
        return {**base, "status": "AMBIGUOUS_CLUSTER_COUNT", "pulse_count": len(clusters), "clusters": clusters, "split_performed": False}
    first_peak = clusters[0]["peak_sample_index"]
    second_peak = clusters[1]["peak_sample_index"]
    if second_peak <= first_peak:
        return {**base, "status": "UNKNOWN", "reason": "non-ordered terminal peaks"}
    valley = min(range(first_peak, second_peak + 1), key=lambda index: values[index])
    valley_value = values[valley]
    threshold = terminal_clusters["threshold_V"]
    separated = valley_value - terminal_clusters["baseline_center_V"] <= threshold and times[second_peak] - times[first_peak] > CLUSTER_GAP_S
    if not separated:
        return {**base, "status": "AMBIGUOUS_VALLEY", "pulse_count": 2, "valley_time_ps": times[valley] * 1e12, "valley_value_V": valley_value, "split_performed": False}
    first_area = _inclusive_area(times, values, origin[0], valley)
    second_area = _inclusive_area(times, values, valley, origin[-1])
    pulses = [
        {"pulse_index": 1, "peak_time_ps": clusters[0]["peak_time_ps"], "left_boundary_time_ps": times[origin[0]] * 1e12, "right_boundary_time_ps": times[valley] * 1e12, "signed_area_V_s": first_area, "signed_area_over_phi0": first_area / PHI0 if first_area is not None else None},
        {"pulse_index": 2, "peak_time_ps": clusters[1]["peak_time_ps"], "left_boundary_time_ps": times[valley] * 1e12, "right_boundary_time_ps": times[origin[-1]] * 1e12, "signed_area_V_s": second_area, "signed_area_over_phi0": second_area / PHI0 if second_area is not None else None},
    ]
    return {
        **base,
        "status": "TWO_SEPARATED_PULSES",
        "pulse_count": 2,
        "pulses": pulses,
        "pulse_separation_ps": clusters[1]["peak_time_ps"] - clusters[0]["peak_time_ps"],
        "valley_time_ps": times[valley] * 1e12,
        "valley_value_V": valley_value,
        "valley_below_threshold": True,
        "split_performed": True,
        "area_partition_residual_V_s": total_area - first_area - second_area if total_area is not None and first_area is not None and second_area is not None else None,
    }


def _ordered_times(values: list[float | None]) -> bool:
    return all(value is not None for value in values) and all(left < right for left, right in zip(values, values[1:]))


def repaired_second_response_oracle(trace: Any) -> dict[str, Any]:
    phases = OrderedDict((label, phase_landmarks(trace, label)) for label in PHASE_SIGNALS)
    first_phase_times = [
        phases["P(BJ1|XBQ1)"].get("first_0p5_time_ps"),
        phases["P(BJ2|XBQ1)"].get("first_0p5_time_ps"),
        *(phases[f"P(B01|XJTL1_{stage})"].get("first_0p5_time_ps") for stage in range(1, 7)),
    ]
    second_phase_times = [
        phases["P(BJ1|XBQ1)"].get("second_1p5_time_ps"),
        phases["P(BJ2|XBQ1)"].get("second_1p5_time_ps"),
        *(phases[f"P(B01|XJTL1_{stage})"].get("second_1p5_time_ps") for stage in range(1, 7)),
    ]
    pulse_clusters = OrderedDict((label, _voltage_clusters(trace, label)) for label in VOLTAGE_SIGNALS)
    terminal = terminal_pulses(trace, pulse_clusters["V(JTL6_OUT)"])
    first_pulse_counts = all(record.get("cluster_count", 0) >= 1 for record in pulse_clusters.values())
    one_response_counts = all(record.get("cluster_count") == 1 for record in pulse_clusters.values())
    second_pulse_counts = all(record.get("cluster_count") == 2 for record in pulse_clusters.values())
    def cluster_time(label: str, index: int) -> float | None:
        clusters = pulse_clusters[label].get("clusters", [])
        return clusters[index].get("peak_time_ps") if len(clusters) > index else None

    downstream_first = [cluster_time("V(QBOUT)", 0)] + [cluster_time(f"V(JTL{stage}_OUT)", 0) for stage in range(1, 7)]
    downstream_second = [cluster_time("V(QBOUT)", 1)] + [cluster_time(f"V(JTL{stage}_OUT)", 1) for stage in range(1, 7)]
    first_checks = {
        "first_phase_landmarks_present": all(value is not None for value in first_phase_times),
        "first_phase_ordered": _ordered_times(first_phase_times),
        "first_voltage_cluster_present_per_registered_signal": first_pulse_counts,
        "first_terminal_response_cluster_present": terminal.get("pulse_count", 0) >= 1,
        "first_downstream_voltage_ordered_QBOUT_to_terminal": _ordered_times(downstream_first),
    }
    second_checks = {
        "second_phase_landmarks_present": all(value is not None for value in second_phase_times),
        "second_phase_ordered_BJ1_BJ2_JTL1_to_JTL6": _ordered_times(second_phase_times),
        "two_voltage_clusters_per_registered_signal": second_pulse_counts,
        "two_separated_terminal_pulses": terminal.get("status") == "TWO_SEPARATED_PULSES",
        "second_downstream_voltage_ordered_QBOUT_to_terminal": _ordered_times(downstream_second),
    }
    return {
        "schema": "bjs400-rj2-second-response-oracle-v2",
        "status": "BOUNDED_RESULT" if all(second_checks.values()) else "NO_SECOND_COMPLETE_MULTI_EVIDENCE_CANDIDATE",
        "first_response_status": "BOUNDED_RESULT" if all(first_checks.values()) else "NO_FIRST_COMPLETE_RESPONSE_CANDIDATE",
        "single_response_status": "BOUNDED_RESULT" if all(first_checks.values()) and one_response_counts and terminal.get("status") == "ONE_RESPONSE_CLUSTER" else "NO_SINGLE_COMPLETE_RESPONSE_CANDIDATE",
        "phase_baseline": {"window_ps": [101.0, 110.0], "reference": "first stored sample in FINAL baseline"},
        "phase_landmarks": phases,
        "first_progression_times_ps": first_phase_times,
        "second_progression_times_ps": second_phase_times,
        "first_checks": first_checks,
        "second_checks": second_checks,
        "voltage_signal_cluster_counts": {label: record.get("cluster_count") for label, record in pulse_clusters.items()},
        "voltage_pulse_clusters": pulse_clusters,
        "terminal_pulse_analysis": terminal,
        "phase_reference_policy": "all cumulative landmarks use FINAL-origin baseline [101,110) ps; strongest later L1 segment is never a phase reference",
        "pulse_reference_policy": "direct voltage clusters are independent of phase landmarks and are split only at a registered below-threshold valley",
        "not_event_count": True,
        "not_sfq_count": True,
        "scientific_interpretation_performed": False,
    }
