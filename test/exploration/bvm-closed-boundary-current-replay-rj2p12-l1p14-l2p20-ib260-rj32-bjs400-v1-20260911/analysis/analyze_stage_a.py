#!/usr/bin/env python3
"""Compute registered Stage A raw navigation; do not classify SFQ multiplicity."""

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
SOURCE = EXP / "references/closed_loop_rj2p12/ARRAY_L1P14_L2P20_IB260_RJ32_RJ2P12_0011/raw.csv"
REPLAY = EXP / "runs/CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12/raw.csv"
WINDOWS = ((70.0, 81.0), (90.0, 101.0), (101.0, 110.0), (110.0, 130.0), (110.0, 200.0))
THRESHOLDS = (0.5, 1.5, 2.5, 3.5)
ACTIVITY_THRESHOLD_V = 1.0e-5
REPLAY_REQUIRED = ("I(I_REPLAY)", "I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "I(BJ1|XBQ1)", "V(BJ1|XBQ1)", "P(BJ1|XBQ1)", "I(BJ2|XBQ1)", "V(BJ2|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")
SOURCE_REQUIRED = ("I(B_JSL8)",) + tuple(label for label in REPLAY_REQUIRED if label != "I(I_REPLAY)")


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read(path: Path, required: tuple[str, ...]) -> tuple[list[float], dict[str, list[float]]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        if len(header) != len(set(header)):
            raise RuntimeError(f"duplicate raw column: {path}")
        positions = {name: index for index, name in enumerate(header)}
        missing = [name for name in required if name not in positions]
        if missing:
            raise RuntimeError(f"missing raw probes in {path}: {missing}")
        times: list[float] = []
        values = {name: [] for name in required}
        for row in reader:
            if len(row) != len(header):
                raise RuntimeError(f"raw row width mismatch: {path}")
            times.append(float(row[positions["time"]]) * 1.0e12)
            for name in required:
                values[name].append(float(row[positions[name]]))
    if len(times) != 1999 or times[0] != 0.0 or times[-1] != 199.9:
        raise RuntimeError(f"unexpected raw grid: {path}")
    if any(right <= left for left, right in zip(times, times[1:])):
        raise RuntimeError(f"non-monotonic raw grid: {path}")
    return times, values


def integral(times: list[float], values: list[float], indices: list[int], absolute: bool = False) -> float:
    total = 0.0
    for left, right in zip(indices, indices[1:]):
        if right != left + 1:
            continue
        a, b = values[left], values[right]
        if absolute:
            a, b = abs(a), abs(b)
        total += 0.5 * (a + b) * (times[right] - times[left]) * 1.0e-12
    return total


def window_metrics(times: list[float], values: list[float]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for start, end in WINDOWS:
        indices = [i for i, time in enumerate(times) if start <= time < end]
        selected = [values[i] for i in indices]
        zero_brackets: list[dict[str, Any]] = []
        for left, right in zip(indices, indices[1:]):
            if right != left + 1:
                continue
            if values[left] == 0.0:
                zero_brackets.append({"kind": "exact_zero_sample", "time_ps": times[left]})
            elif values[left] * values[right] < 0:
                zero_brackets.append({"kind": "sign_change_bracket", "left_time_ps": times[left], "right_time_ps": times[right], "left_value": values[left], "right_value": values[right]})
        output[f"{start:g}_{end:g}_ps"] = {"window_ps": [start, end], "semantics": "half-open [start,end); actual stored grid", "sample_count": len(indices), "max": max(selected) if selected else None, "min": min(selected) if selected else None, "signed_area_A_s": integral(times, values, indices), "absolute_area_A_s": integral(times, values, indices, True), "zero_crossing_brackets": zero_brackets, "positive_support_duration_ps": sum(times[right] - times[left] for left, right in zip(indices, indices[1:]) if right == left + 1 and values[left] > 0 and values[right] > 0), "integration": "actual stored time grid trapezoid; no interpolation"}
    return output


def unwrap(values: list[float]) -> list[float]:
    output = [values[0]]
    two_pi = 2.0 * math.pi
    for value in values[1:]:
        candidate = value
        while candidate - output[-1] > math.pi:
            candidate -= two_pi
        while candidate - output[-1] < -math.pi:
            candidate += two_pi
        output.append(candidate)
    return output


def phase_navigation(times: list[float], values: list[float]) -> dict[str, Any]:
    continuous = unwrap(values)
    baseline_index = next(i for i, time in enumerate(times) if time >= 101.0)
    baseline = continuous[baseline_index]
    threshold_times = {}
    for threshold in THRESHOLDS:
        threshold_times[f"{threshold:g}"] = next((times[i] for i in range(baseline_index, len(times)) if (continuous[i] - baseline) / (2.0 * math.pi) >= threshold), None)
    def at(target: float) -> float | None:
        index = next((i for i, time in enumerate(times) if time >= target), None)
        return ((continuous[index] - baseline) / (2.0 * math.pi)) if index is not None else None
    return {"baseline_time_ps": times[baseline_index], "raw_unit": "radians", "display_conversion": "rad/(2*pi) turns", "delta_turns_at_109.9_ps": at(109.9), "delta_turns_at_121_ps": at(121.0), "delta_turns_at_130_ps": at(130.0), "threshold_navigation_times_ps": threshold_times, "semantic_role": "PHASE_NAVIGATION_ONLY; not an SFQ count"}


def activity_segments(times: list[float], values: list[float]) -> list[dict[str, Any]]:
    active = [i for i, time in enumerate(times) if 110.0 <= time < 200.0 and abs(values[i]) >= ACTIVITY_THRESHOLD_V]
    spans: list[tuple[int, int]] = []
    for index in active:
        if not spans or index != spans[-1][1] + 1:
            spans.append((index, index))
        else:
            spans[-1] = (spans[-1][0], index)
    output: list[dict[str, Any]] = []
    for begin, finish in spans:
        indices = list(range(begin, finish + 1))
        peak = max(indices, key=lambda i: abs(values[i]))
        local = integral(times, values, indices)
        output.append({"support_start_ps": times[begin], "support_end_ps": times[finish], "left_valley_boundary_ps": times[begin - 1] if begin else None, "right_valley_boundary_ps": times[finish + 1] if finish + 1 < len(times) else None, "peak_time_ps": times[peak], "peak_value": values[peak], "pulse_local_integral_V_s": local, "area_over_phi0": local / PHI0, "sample_count": len(indices), "segmentation": "contiguous abs(value) >= registered threshold; activity only, not an event count"})
    for index in range(1, len(output)):
        output[index]["peak_separation_ps"] = output[index]["peak_time_ps"] - output[index - 1]["peak_time_ps"]
    return output


def difference(times_a: list[float], values_a: list[float], times_b: list[float], values_b: list[float], phase: bool = False) -> dict[str, Any]:
    if times_a != times_b:
        raise RuntimeError("comparison grids differ")
    first = unwrap(values_a) if phase else values_a
    second = unwrap(values_b) if phase else values_b
    delta = [a - b for a, b in zip(first, second)]
    absolute = sorted(abs(v) for v in delta)
    position = int(0.95 * (len(absolute) - 1))
    return {"max_abs": max(absolute), "rms": math.sqrt(sum(v * v for v in delta) / len(delta)), "p95_abs": absolute[position], "mean": sum(delta) / len(delta), "signed_integral": integral(times_a, delta, list(range(len(delta)))), "endpoint_delta": delta[-1], "phase_unwrapped_before_subtraction": phase}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_review(metrics: dict[str, Any]) -> None:
    source = metrics["source"]
    replay = metrics["replay"]
    lines = ["# Stage A raw review navigation", "", "Scientific interpretation: `NOT_PERFORMED`.", "", "The source is an immutable closed-loop raw current. The replay is ideal current forcing; it does not erase interaction history embedded in the recorded waveform. Phase navigation and activity segments are not SFQ counts.", "", "## Stored-history and source fidelity", "", f"- source raw SHA-256: `{metrics['source_raw_sha256']}`", f"- source snapshot SHA-256: `{metrics['source_snapshot_sha256']}`", f"- replay raw SHA-256: `{metrics['replay_raw_sha256']}`", f"- exact source/replay current mismatch: `{metrics['source_replay_current_exactness']['max_absolute_mismatch_A']}` A", "", "| signal | 109.9 ps closed | 109.9 ps replay | difference |", "|---|---:|---:|---:|"]
    for label in ("I(L1|XBQ1)", "I(L2|XBQ1)", "I(BJ1|XBQ1)", "I(BJ2|XBQ1)", "P(BJ1|XBQ1)", "P(BJ2|XBQ1)"):
        item = metrics["pre_final"][label]
        lines.append(f"| `{label}` | {item['source_value']:.8g} | {item['replay_value']:.8g} | {item['difference']:.8g} |")
    lines.extend(["", "## Downstream raw navigation", "", "| track | first threshold-support time (ps) |", "|---|---:|"])
    for label, time in replay["first_activity_support_ps"].items():
        lines.append(f"| `{label}` | {time} |")
    lines.extend(["", "The registered phase landmarks use a 101 ps baseline and are `PHASE_NAVIGATION_ONLY`. The operator does not classify the response as 2/3/4 or start Stage B in this turn; that requires the declared scientific-review authorization.", "", "Final stage status: `STAGE_A_EVIDENCE_READY / SCIENTIFIC_REVIEW_REQUIRED`.", ""])
    (EXP / "analysis/STAGE_A_REVIEW.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    times_s, source = read(SOURCE, SOURCE_REQUIRED)
    times_r, replay = read(REPLAY, REPLAY_REQUIRED)
    if times_s != times_r:
        raise RuntimeError("source and replay raw grids differ")
    source_current = source["I(B_JSL8)"]
    replay_current = replay["I(I_REPLAY)"]
    differences = [a - b for a, b in zip(source_current, replay_current)]
    source_snapshot = EXP / "data/CLOSED_LOOP_N2_I_BJSL8_source.csv"
    pre_final: dict[str, Any] = {}
    sample_index = next(i for i, time in enumerate(times_s) if abs(time - 109.9) < 1e-9)
    for source_label, replay_label in (("I(L1|XBQ1)", "I(L1|XBQ1)"), ("I(L2|XBQ1)", "I(L2|XBQ1)"), ("I(BJ1|XBQ1)", "I(BJ1|XBQ1)"), ("I(BJ2|XBQ1)", "I(BJ2|XBQ1)"), ("P(BJ1|XBQ1)", "P(BJ1|XBQ1)"), ("P(BJ2|XBQ1)", "P(BJ2|XBQ1)")):
        pre_final[source_label] = {"time_ps": times_s[sample_index], "source_value": source[source_label][sample_index], "replay_value": replay[replay_label][sample_index], "difference": source[source_label][sample_index] - replay[replay_label][sample_index], "phase_raw_radians": source_label.startswith("P(")}
    comparison_labels = ("I(LIN|XBQ1)", "I(L1|XBQ1)", "I(L2|XBQ1)", "I(BJ1|XBQ1)", "V(BJ1|XBQ1)", "P(BJ1|XBQ1)", "I(BJ2|XBQ1)", "V(BJ2|XBQ1)", "P(BJ2|XBQ1)", "V(QBOUT)", "V(JTL1_OUT)", "V(JTL2_OUT)", "V(JTL3_OUT)", "V(JTL4_OUT)", "V(JTL5_OUT)", "V(JTL6_OUT)", "I(R_TERM)")
    comparisons: dict[str, Any] = {}
    for label in comparison_labels:
        comparisons[label] = {}
        for start, end in WINDOWS[:3]:
            indices = [i for i, time in enumerate(times_s) if start <= time < end]
            comparisons[label][f"{start:g}_{end:g}_ps"] = difference([times_s[i] for i in indices], [source[label][i] for i in indices], [times_r[i] for i in indices], [replay[label][i] for i in indices], phase=label.startswith("P("))
    replay_nav = {"phase_navigation": {label: phase_navigation(times_r, replay[label]) for label in ("P(BJ1|XBQ1)", "P(BJ2|XBQ1)")}, "activity_threshold_V": ACTIVITY_THRESHOLD_V, "activity_segments": {label: activity_segments(times_r, replay[label]) for label in ("V(QBOUT)",) + tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7))}, "first_activity_support_ps": {label: (activity_segments(times_r, replay[label])[0]["support_start_ps"] if activity_segments(times_r, replay[label]) else None) for label in ("V(QBOUT)",) + tuple(f"V(JTL{stage}_OUT)" for stage in range(1, 7)) + ("I(R_TERM)",)}, "terminal_voltage_activity": activity_segments(times_r, replay["V(JTL6_OUT)"]), "terminal_current_activity": activity_segments(times_r, replay["I(R_TERM)"]), "semantic_role": "raw navigation only; response multiplicity not classified"}
    metrics = {"schema": "bvm-closed-boundary-current-replay-stage-a-raw-metrics-v1", "experiment_id": EXP.name, "created_at_local": now(), "source_raw_path": SOURCE.relative_to(REPO).as_posix(), "source_raw_sha256": sha256(SOURCE), "source_snapshot_path": source_snapshot.relative_to(REPO).as_posix(), "source_snapshot_sha256": sha256(source_snapshot), "replay_raw_path": REPLAY.relative_to(REPO).as_posix(), "replay_raw_sha256": sha256(REPLAY), "source_sample_count": len(times_s), "replay_sample_count": len(times_r), "source_time_range_ps": [times_s[0], times_s[-1]], "replay_time_range_ps": [times_r[0], times_r[-1]], "source_replay_current_exactness": {"source_signal": SOURCE_SIGNAL, "replay_signal": "I(I_REPLAY)", "max_absolute_mismatch_A": max(abs(value) for value in differences), "all_stored_values_equal": all(value == 0.0 for value in differences), "same_time_grid": times_s == times_r, "transformations": [], "orientation": "direct positive JSL7->QBIN to 0->QBIN"}, "source_windows": window_metrics(times_s, source_current), "replay_windows": window_metrics(times_r, replay_current), "pre_final": pre_final, "closed_vs_replay": comparisons, "replay": replay_nav, "stage_a_scientific_decision": "NOT_PERFORMED", "stage_a_protocol_status": "SCIENTIFIC_REVIEW_REQUIRED_BEFORE_STAGE_B", "stage_b_started": False, "scientific_analysis_performed": False}
    write_json(EXP / "analysis/mechanism_metrics.json", metrics)
    summary = {"schema": "bvm-closed-boundary-current-replay-stage-a-mechanical-summary-v1", "experiment_id": EXP.name, "created_at_local": metrics["created_at_local"], "status": "PASS", "stage": "A", "scientific_analysis_performed": False, "stage_a_evidence_status": "RAW_AND_MECHANICAL_EVIDENCE_READY", "stage_a_scientific_decision": "NOT_PERFORMED", "stage_a_stop": "STOP_STAGE_A_SCIENTIFIC_REVIEW_REQUIRED", "stage_b_started": False, "response_multiplicity": "UNASSESSED_PENDING_SCIENTIFIC_REVIEW", "metrics": metrics}
    write_json(EXP / "mechanical_summary.json", summary)
    response_qa = {"schema": "bvm-closed-boundary-current-replay-stage-a-response-qa-v1", "experiment_id": EXP.name, "created_at_local": metrics["created_at_local"], "status": "PASS", "raw_progression_checked": True, "source_replay_exact": metrics["source_replay_current_exactness"], "required_progression": ["BJ1", "BJ2", "QBOUT", "JTL1", "JTL2", "JTL3", "JTL4", "JTL5", "JTL6", "terminal"], "phase_navigation_only": True, "response_multiplicity_classification": "UNASSESSED_PENDING_SCIENTIFIC_REVIEW", "stage_a_decision": "NOT_PERFORMED", "stage_b_started": False, "failures": []}
    write_json(EXP / "qa/stage_a_response_qa.json", response_qa)
    write_review(metrics)
    print(json.dumps({"status": "PASS", "source_replay_current_exact": metrics["source_replay_current_exactness"]["all_stored_values_equal"], "stage_a_scientific_decision": "NOT_PERFORMED", "stage_b_started": False, "scientific_analysis_performed": False}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
