#!/usr/bin/env python3
"""Produce registered raw-oriented measurements without scientific interpretation."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
PHI0 = 2.067833848e-15
SOURCE_RUNS = {"N2": "PASSIVE_N2_0011", "N3": "PASSIVE_N3_0111", "N4": "PASSIVE_N4_1111"}
REPLAY_RUNS = {"N2": "REPLAY_N2_0011_RJ2P12", "N3": "REPLAY_N3_0111_RJ2P12", "N4": "REPLAY_N4_1111_RJ2P12"}
REFERENCE_RUNS = {"N2": "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011", "N3": "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0111", "N4": "ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_1111"}
WINDOWS = ((110.0, 121.0), (121.0, 124.0), (121.0, 126.0), (121.0, 130.0), (110.0, 200.0))
PHASE_THRESHOLDS = (0.5, 1.5, 2.5, 3.5)
ACTIVITY_THRESHOLD_V = 1.0e-5
REPLAY_REQUIRED = (
    "P(BJ1|XBQ1)", "V(BJ1|XBQ1)", "I(BJ1|XBQ1)",
    "P(BJ2|XBQ1)", "V(BJ2|XBQ1)", "I(BJ2|XBQ1)",
    "V(QBOUT)", "I(L1|XBQ1)", "I(L2|XBQ1)", "I(LIN|XBQ1)",
    "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)",
    "I(R_TERM)", "I(I_REPLAY)",
)
COMPARISON_LABELS = (
    "P(BJ1|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)",
    "I(L1|XBQ1)", "I(L2|XBQ1)", "I(LIN|XBQ1)",
    "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)",
    "I(R_TERM)",
)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_columns(path: Path, required: tuple[str, ...]) -> tuple[list[float], dict[str, list[float]], list[str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) != len(set(header)):
            raise RuntimeError(f"duplicate raw columns: {path}")
        positions = {name: index for index, name in enumerate(header)}
        missing = [name for name in required if name not in positions]
        if missing:
            raise RuntimeError(f"missing columns in {path}: {missing}")
        time_index = positions.get("time")
        if time_index is None:
            raise RuntimeError(f"missing time column: {path}")
        values = {name: [] for name in required}
        times: list[float] = []
        for row in reader:
            if len(row) != len(header):
                raise RuntimeError(f"raw row width mismatch: {path}")
            times.append(float(row[time_index]) * 1.0e12)
            for name in required:
                values[name].append(float(row[positions[name]]))
    if len(times) < 2 or any(not math.isfinite(value) for value in times):
        raise RuntimeError(f"invalid time grid: {path}")
    if any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"non-increasing time grid: {path}")
    for name, column in values.items():
        if any(not math.isfinite(value) for value in column):
            raise RuntimeError(f"non-finite column {name}: {path}")
    return times, values, header


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return float("nan")
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def selected_indices(times: list[float], start: float, end: float) -> list[int]:
    return [index for index, time in enumerate(times) if start <= time < end]


def actual_grid_integral(times: list[float], values: list[float], indices: list[int], absolute: bool = False) -> float:
    if len(indices) < 2:
        return 0.0
    total = 0.0
    for left, right in zip(indices, indices[1:]):
        if right != left + 1:
            continue
        y0, y1 = values[left], values[right]
        if absolute:
            y0, y1 = abs(y0), abs(y1)
        total += 0.5 * (y0 + y1) * ((times[right] - times[left]) * 1.0e-12)
    return total


def zero_brackets(times: list[float], values: list[float], indices: list[int]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for left, right in zip(indices, indices[1:]):
        if right != left + 1:
            continue
        a, b = values[left], values[right]
        if a == 0.0:
            result.append({"kind": "exact_zero_sample", "time_ps": times[left], "left_index": left})
        elif a * b < 0.0:
            result.append({"kind": "sign_change_bracket", "left_time_ps": times[left], "right_time_ps": times[right], "left_value_A": a, "right_value_A": b})
    if indices and values[indices[-1]] == 0.0:
        result.append({"kind": "exact_zero_sample", "time_ps": times[indices[-1]], "left_index": indices[-1]})
    return result


def positive_support_duration(times: list[float], values: list[float], indices: list[int]) -> float:
    duration_ps = 0.0
    for left, right in zip(indices, indices[1:]):
        if right == left + 1 and values[left] > 0.0 and values[right] > 0.0:
            duration_ps += times[right] - times[left]
    return duration_ps


def source_window_metrics(times: list[float], values: list[float]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for start, end in WINDOWS:
        indices = selected_indices(times, start, end)
        selected = [values[index] for index in indices]
        signed = actual_grid_integral(times, values, indices)
        absolute = actual_grid_integral(times, values, indices, absolute=True)
        key = f"{start:g}_{end:g}_ps"
        output[key] = {
            "window_ps": [start, end],
            "semantics": "half-open [start,end); actual stored grid",
            "sample_count": len(indices),
            "max_A": max(selected) if selected else None,
            "min_A": min(selected) if selected else None,
            "max_uA": max(selected) * 1.0e6 if selected else None,
            "min_uA": min(selected) * 1.0e6 if selected else None,
            "signed_area_A_s": signed,
            "absolute_area_A_s": absolute,
            "positive_support_duration_ps": positive_support_duration(times, values, indices),
            "zero_crossing_brackets": zero_brackets(times, values, indices),
            "integration": "trapezoid on actual stored time grid; no interpolation",
        }
    return output


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    two_pi = 2.0 * math.pi
    for value in values[1:]:
        candidate = value
        delta = candidate - result[-1]
        while delta > math.pi:
            candidate -= two_pi
            delta = candidate - result[-1]
        while delta < -math.pi:
            candidate += two_pi
            delta = candidate - result[-1]
        result.append(candidate)
    return result


def first_time_at_or_after(times: list[float], start: float) -> int:
    for index, time in enumerate(times):
        if time >= start:
            return index
    raise RuntimeError(f"time window starts after raw trace: {start}")


def phase_navigation(times: list[float], values: list[float], start: float = 110.0) -> dict[str, Any]:
    continuous = unwrap(values)
    base_index = first_time_at_or_after(times, start)
    baseline = continuous[base_index]
    delta_turns = [(continuous[index] - baseline) / (2.0 * math.pi) for index in range(base_index, len(times))]
    threshold_times: dict[str, float | None] = {}
    for threshold in PHASE_THRESHOLDS:
        first = next((times[base_index + offset] for offset, value in enumerate(delta_turns) if value >= threshold), None)
        threshold_times[f"{threshold:g}"] = first
    def value_at(target: float) -> float | None:
        indices = [index for index, time in enumerate(times) if time >= target]
        return delta_turns[indices[0] - base_index] if indices else None
    return {
        "baseline_time_ps": times[base_index],
        "raw_phase_unit": "radians",
        "display_conversion": "rad/(2*pi) turns",
        "delta_turns_at_121_ps": value_at(121.0),
        "delta_turns_at_130_ps": value_at(130.0),
        "delta_turns_at_200_ps": value_at(200.0),
        "max_delta_turns_110_to_200": max(delta_turns) if delta_turns else None,
        "threshold_navigation_times_ps": threshold_times,
        "semantic_role": "PHASE_NAVIGATION_ONLY; not an SFQ count",
    }


def activity_segments(times: list[float], values: list[float], start: float = 110.0, end: float = 200.0) -> list[dict[str, Any]]:
    active = [index for index, time in enumerate(times) if start <= time < end and abs(values[index]) >= ACTIVITY_THRESHOLD_V]
    segments: list[tuple[int, int]] = []
    for index in active:
        if not segments or index != segments[-1][1] + 1:
            segments.append((index, index))
        else:
            segments[-1] = (segments[-1][0], index)
    output: list[dict[str, Any]] = []
    for begin, finish in segments:
        indices = list(range(begin, finish + 1))
        peak = max(indices, key=lambda index: abs(values[index]))
        local_area = actual_grid_integral(times, values, indices)
        output.append({
            "support_start_ps": times[begin],
            "support_end_ps": times[finish],
            "left_valley_boundary_ps": times[begin - 1] if begin > 0 else None,
            "right_valley_boundary_ps": times[finish + 1] if finish + 1 < len(times) else None,
            "peak_time_ps": times[peak],
            "peak_value_V": values[peak],
            "peak_abs_value_V": abs(values[peak]),
            "pulse_local_signed_integral_V_s": local_area,
            "pulse_local_area_over_phi0": local_area / PHI0,
            "sample_count": len(indices),
            "segmentation": f"contiguous |V| >= {ACTIVITY_THRESHOLD_V:g} V on actual raw samples; activity segment, not an event count",
        })
    for index in range(1, len(output)):
        output[index]["peak_separation_from_previous_ps"] = output[index]["peak_time_ps"] - output[index - 1]["peak_time_ps"]
    return output


def range_record(values: list[float], times: list[float]) -> dict[str, Any]:
    maximum = max(values)
    minimum = min(values)
    return {"min": minimum, "max": maximum, "min_time_ps": times[values.index(minimum)], "max_time_ps": times[values.index(maximum)]}


def load_replay(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    times, values, _ = read_columns(path, REPLAY_REQUIRED)
    return times, values


def load_reference(path: Path) -> tuple[list[float], dict[str, list[float]]]:
    times, values, _ = read_columns(path, ("I(B_JSL8)",) + COMPARISON_LABELS)
    return times, values


def descriptive_difference(times_a: list[float], values_a: list[float], times_b: list[float], values_b: list[float], phase: bool = False) -> dict[str, Any]:
    if times_a != times_b:
        raise RuntimeError("pointwise comparison requires identical stored time grids")
    first = unwrap(values_a) if phase else values_a
    second = unwrap(values_b) if phase else values_b
    delta = [left - right for left, right in zip(first, second)]
    area = actual_grid_integral(times_a, delta, list(range(len(delta))))
    absolute = [abs(value) for value in delta]
    return {"max_abs": max(absolute), "rms": math.sqrt(sum(value * value for value in delta) / len(delta)), "p95_abs": percentile(absolute, 0.95), "mean": sum(delta) / len(delta), "p2p": max(delta) - min(delta), "signed_integral": area, "endpoint_delta": delta[-1], "phase_unwrapped_before_subtraction": phase}


def source_population_comparison(source_data: dict[str, tuple[list[float], list[float]]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    labels = ("N2_vs_N3", "N2_vs_N4", "N3_vs_N4")
    pairs = (("N2", "N3"), ("N2", "N4"), ("N3", "N4"))
    for label, (left, right) in zip(labels, pairs):
        times_a, values_a = source_data[left]
        times_b, values_b = source_data[right]
        result[label] = descriptive_difference(times_a, values_a, times_b, values_b)
    return result


def replay_record(times: list[float], values: dict[str, list[float]]) -> dict[str, Any]:
    phases = {label: phase_navigation(times, values[label]) for label in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)")}
    activity_labels = ("V(QBOUT)",) + tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7)) + ("I(R_TERM)",)
    activities = {label: activity_segments(times, values[label]) for label in activity_labels}
    progression = {label: (segments[0]["support_start_ps"] if segments else None) for label, segments in activities.items()}
    return {
        "phase_navigation": phases,
        "activity_threshold_V": ACTIVITY_THRESHOLD_V,
        "activity_segments": activities,
        "ordered_activity_support_start_ps": progression,
        "range": {label: range_record(values[label], times) for label in REPLAY_REQUIRED if not label.startswith("P(")},
        "semantic_role": "raw navigation and registered activity arithmetic; scientific response classification not performed",
    }


def closed_vs_replay(replay: dict[str, tuple[list[float], dict[str, list[float]]]], references: dict[str, tuple[list[float], dict[str, list[float]]]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    mapping: dict[str, tuple[str, str, bool]] = {
        "source_current": ("I(B_JSL8)", "I(I_REPLAY)", False),
        "BJ1_phase": ("P(BJ1|XBQ1)", "P(BJ1|XBQ1)", True),
        "BJ2_phase": ("P(BJ2|XBQ1)", "P(BJ2|XBQ1)", True),
    }
    for label in COMPARISON_LABELS:
        mapping[label] = (label, label, label.startswith("P("))
    for population in ("N2", "N3", "N4"):
        replay_times, replay_values = replay[population]
        ref_times, ref_values = references[population]
        result[population] = {}
        for name, (ref_label, replay_label, phase) in mapping.items():
            result[population][name] = descriptive_difference(ref_times, ref_values[ref_label], replay_times, replay_values[replay_label], phase=phase)
    return result


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_review(source_metrics: dict[str, Any], replay_metrics: dict[str, Any], comparison: dict[str, Any]) -> None:
    lines = [
        "# Mechanism diagnostic raw review navigation", "",
        "Scientific interpretation: `NOT_PERFORMED`.", "",
        "This document records direct raw-oriented arithmetic and navigation only. The passive waveform is a counterfactual source fixture and the replay is ideal current forcing. No phase, activity segment, voltage area, terminal area or phase landmark is an SFQ count.", "",
        "## Passive source windows", "",
        "| population | window (ps) | samples | max (uA) | min (uA) | signed area (A s) | abs area (A s) | positive support (ps) |", "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for population in ("N2", "N3", "N4"):
        for window in source_metrics[population]["windows"].values():
            lines.append(f"| {population} | {window['window_ps'][0]:g}–{window['window_ps'][1]:g} | {window['sample_count']} | {window['max_uA']:.6g} | {window['min_uA']:.6g} | {window['signed_area_A_s']:.6g} | {window['absolute_area_A_s']:.6g} | {window['positive_support_duration_ps']:.6g} |")
    lines.extend(["", "Zero crossings are retained as exact-zero samples or sign-change brackets; no crossing interpolation was performed.", "", "## Replay navigation", "", "| replay | BJ1 delta at 130 ps (turn display) | BJ2 delta at 130 ps (turn display) | QBOUT first activity (ps) | JTL1 first activity (ps) | JTL6 first activity (ps) | terminal first activity (ps) |", "|---|---:|---:|---:|---:|---:|---:|"])
    for population in ("N2", "N3", "N4"):
        item = replay_metrics[population]["navigation"]
        phases = item["phase_navigation"]
        progression = item["ordered_activity_support_start_ps"]
        lines.append(f"| {population} | {phases['P(BJ1|XBQ1)']['delta_turns_at_130_ps']:.6g} | {phases['P(BJ2|XBQ1)']['delta_turns_at_130_ps']:.6g} | {progression['V(QBOUT)']} | {progression['V(JTL1_OUT)']} | {progression['V(JTL6_OUT)']} | {progression['I(R_TERM)']} |")
    lines.extend(["", "The four registered cumulative-phase landmarks (`+0.5`, `+1.5`, `+2.5`, `+3.5` turns) are navigation only. Activity segments use the preregistered absolute-voltage threshold and are not response counts.", "", "## Closed-loop versus replay", "", "The following descriptive comparisons use identical stored time grids and unwrap each phase trace before subtraction. They are not causal conclusions.", "", "| population | source current max abs delta (A) | BJ1 phase max abs delta (rad) | BJ2 phase max abs delta (rad) | QBOUT max abs delta (V) | JTL6 max abs delta (V) | terminal max abs delta (A) |", "|---|---:|---:|---:|---:|---:|---:|"])
    for population in ("N2", "N3", "N4"):
        item = comparison[population]
        lines.append(f"| {population} | {item['source_current']['max_abs']:.6g} | {item['BJ1_phase']['max_abs']:.6g} | {item['BJ2_phase']['max_abs']:.6g} | {item['V(QBOUT)']['max_abs']:.6g} | {item['V(JTL6_OUT)']['max_abs']:.6g} | {item['I(R_TERM)']['max_abs']:.6g} |")
    lines.extend([
        "", "## Review boundary", "",
        "- response multiplicity classification: `UNASSESSED_PENDING_SCIENTIFIC_REVIEW`",
        "- no automatic upgrade to 2/3/4 was made",
        "- no causal statement about QB-to-source back-action was made",
        "- raw CSV, decks, logs, metadata and source/reference hashes remain the authority.", "",
    ])
    (EXP / "analysis/MECHANISM_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    source_metrics: dict[str, Any] = {}
    source_data: dict[str, tuple[list[float], list[float]]] = {}
    for population, run in SOURCE_RUNS.items():
        path = EXP / "runs" / run / "raw.csv"
        times, values, _ = read_columns(path, ("I(B_JSL8)",))
        source_data[population] = (times, values["I(B_JSL8)"])
        source_metrics[population] = {"run_id": run, "raw_path": path.relative_to(REPO).as_posix(), "raw_sha256": sha256(path), "sample_count": len(times), "time_range_ps": [times[0], times[-1]], "windows": source_window_metrics(times, values["I(B_JSL8)"]), "counterfactual": True, "semantic_role": "PASSIVE_CAPTURE_COUNTERFACTUAL"}
    source_metrics["population_comparison"] = source_population_comparison(source_data)
    replay_data: dict[str, tuple[list[float], dict[str, list[float]]]] = {}
    replay_metrics: dict[str, Any] = {}
    for population, run in REPLAY_RUNS.items():
        path = EXP / "runs" / run / "raw.csv"
        times, values = load_replay(path)
        replay_data[population] = (times, values)
        replay_metrics[population] = {"run_id": run, "raw_path": path.relative_to(REPO).as_posix(), "raw_sha256": sha256(path), "sample_count": len(times), "time_range_ps": [times[0], times[-1]], "navigation": replay_record(times, values), "ideal_current_forcing": True}
    reference_data: dict[str, tuple[list[float], dict[str, list[float]]]] = {}
    reference_records: dict[str, Any] = {}
    for population, run in REFERENCE_RUNS.items():
        path = EXP / "references/closed_loop_rj2p12" / run / "raw.csv"
        times, values = load_reference(path)
        reference_data[population] = (times, values)
        reference_records[population] = {"run_id": run, "raw_path": path.relative_to(REPO).as_posix(), "raw_sha256": sha256(path), "sample_count": len(times), "time_range_ps": [times[0], times[-1]], "immutable_reference": True}
    comparison = closed_vs_replay(replay_data, reference_data)
    metrics = {"schema": "bvm-population-passive-source-replay-raw-mechanism-metrics-v1", "experiment_id": EXP.name, "created_at_local": now(), "source_signal": "I(B_JSL8)", "source": source_metrics, "replay": replay_metrics, "closed_loop_references": reference_records, "closed_loop_vs_replay": comparison, "activity_threshold_V": ACTIVITY_THRESHOLD_V, "phi0_Wb": PHI0, "scientific_analysis_performed": False, "interpretation_status": "NOT_PERFORMED"}
    write_json(EXP / "analysis/mechanism_metrics.json", metrics)
    summary = {"schema": "bvm-population-passive-source-replay-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": metrics["created_at_local"], "status": "PASS", "scientific_analysis_performed": False, "response_multiplicity_classification": "UNASSESSED_PENDING_SCIENTIFIC_REVIEW", "source": source_metrics, "replay": replay_metrics, "closed_loop_vs_replay": comparison, "raw_authority": True, "phase_navigation_only": True}
    write_json(EXP / "mechanical_summary.json", summary)
    response_qa = {"schema": "bvm-population-passive-source-replay-response-qa-v1", "experiment_id": EXP.name, "created_at_local": metrics["created_at_local"], "status": "PASS", "scientific_analysis_performed": False, "raw_required_progression_checked": True, "required_progression": ["BJ1", "BJ2", "QBOUT", "JTL1", "JTL2", "JTL3", "JTL4", "JTL5", "JTL6", "R_TERM"], "phase_navigation_thresholds_turns": list(PHASE_THRESHOLDS), "activity_threshold_V": ACTIVITY_THRESHOLD_V, "response_multiplicity_classification": "UNASSESSED_PENDING_SCIENTIFIC_REVIEW", "sfq_count_defined": False, "unknowns": ["whether any activity segment is an SFQ event", "whether an observed difference is causal back-action", "whether a 2/3/4 response classification is scientifically supported"], "failures": []}
    write_json(EXP / "qa/response_qa.json", response_qa)
    write_review(source_metrics, replay_metrics, comparison)
    print(json.dumps({"status": "PASS", "source_cases": list(source_metrics), "replay_cases": list(replay_metrics), "reference_cases": list(reference_records), "scientific_analysis_performed": False, "response_multiplicity_classification": "UNASSESSED_PENDING_SCIENTIFIC_REVIEW"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
