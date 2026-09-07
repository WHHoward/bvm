#!/usr/bin/env python3
"""Build a read-only N3/N4 replay deep-dive evidence package.

This module reads existing JoSIM CSV files only.  It deliberately does not
invoke the solver or edit a circuit, parameter, timing, or raw artifact.
All numerical quantities retain their raw SI meaning until an explicit
display conversion is recorded.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from collections import OrderedDict
from io import StringIO
from pathlib import Path
from typing import Iterable, Sequence

import sys


REPO = Path(__file__).resolve().parents[4]
EXP = Path(__file__).resolve().parents[1]
BASELINE = REPO / "test/exploration/bvmsim-jm2-passive-capture-replay-v1-20260907"

sys.path.insert(0, str(REPO / "scripts"))
from bvmtools.phase import continuous_unwrap  # noqa: E402
from bvmtools.raw import RawTrace, read_csv  # noqa: E402
from bvmtools.waveform import trapezoid_integral  # noqa: E402


TAU = 2.0 * math.pi
PHI0 = 2.067833848e-15
WINDOW_START_PS = 110.0
WINDOW_END_PS = 200.0
T3_POST_PROBE_OFFSET_PS = 3.0
TERMINAL_THRESHOLD_A = 5.0e-6
TERMINAL_MERGE_PS = 1.0
SIGNIFICANT_SOURCE_THRESHOLD_A = 5.0e-6

RAW_CASES: OrderedDict[str, Path] = OrderedDict(
    [
        ("N1_REPLAY", BASELINE / "runs/replay_array/raw.csv"),
        ("N3_REPLAY", EXP / "runs/n3_replay/raw.csv"),
        ("N4_REPLAY", EXP / "runs/n4_replay/raw.csv"),
    ]
)

REPLAY_REQUIRED_HEADERS = [
    "V(QBIN)",
    "V(QBOUT)",
    "I(I_REPLAY)",
    "I(LIN|XBQ1)",
    "V(LIN|XBQ1)",
    "I(L1|XBQ1)",
    "V(L1|XBQ1)",
    "I(L2|XBQ1)",
    "V(L2|XBQ1)",
    "I(L3|XBQ1)",
    "V(L3|XBQ1)",
    "I(RJ1|XBQ1)",
    "V(RJ1|XBQ1)",
    "I(RJ2|XBQ1)",
    "V(RJ2|XBQ1)",
    "I(IB|XBQ1)",
    "P(BJS|XBQ1)",
    "V(BJS|XBQ1)",
    "I(BJS|XBQ1)",
    "P(BJ1|XBQ1)",
    "V(BJ1|XBQ1)",
    "I(BJ1|XBQ1)",
    "P(BJ2|XBQ1)",
    "V(BJ2|XBQ1)",
    "I(BJ2|XBQ1)",
    "I(R_TERM)",
]
for _stage in (1, 6):
    _handle = f"XJTL1_{_stage}"
    REPLAY_REQUIRED_HEADERS.extend(
        [
            f"P(B01|{_handle})",
            f"V(B01|{_handle})",
            f"I(B01|{_handle})",
            f"P(B02|{_handle})",
            f"V(B02|{_handle})",
            f"I(B02|{_handle})",
        ]
    )

PHASE_JJS: OrderedDict[str, tuple[str, str]] = OrderedDict(
    [
        ("BJS", ("P(BJS|XBQ1)", "V(BJS|XBQ1)")),
        ("BJ1", ("P(BJ1|XBQ1)", "V(BJ1|XBQ1)")),
        ("BJ2", ("P(BJ2|XBQ1)", "V(BJ2|XBQ1)")),
        ("JTL1_B01", ("P(B01|XJTL1_1)", "V(B01|XJTL1_1)")),
        ("JTL1_B02", ("P(B02|XJTL1_1)", "V(B02|XJTL1_1)")),
        ("JTL6_B01", ("P(B01|XJTL1_6)", "V(B01|XJTL1_6)")),
        ("JTL6_B02", ("P(B02|XJTL1_6)", "V(B02|XJTL1_6)")),
    ]
)

INTERNAL_PLOT_LABELS = [
    "I(I_REPLAY)",
    "V(QBIN)",
    "V(QBOUT)",
    "I(LIN|XBQ1)",
    "V(LIN|XBQ1)",
    "I(L1|XBQ1)",
    "V(L1|XBQ1)",
    "I(L2|XBQ1)",
    "V(L2|XBQ1)",
    "I(L3|XBQ1)",
    "V(L3|XBQ1)",
    "I(RJ1|XBQ1)",
    "V(RJ1|XBQ1)",
    "I(RJ2|XBQ1)",
    "V(RJ2|XBQ1)",
    "I(IB|XBQ1)",
    "P(BJS|XBQ1)",
    "V(BJS|XBQ1)",
    "I(BJS|XBQ1)",
    "P(BJ1|XBQ1)",
    "V(BJ1|XBQ1)",
    "I(BJ1|XBQ1)",
    "P(BJ2|XBQ1)",
    "V(BJ2|XBQ1)",
    "I(BJ2|XBQ1)",
    "P(B01|XJTL1_1)",
    "V(B01|XJTL1_1)",
    "I(B01|XJTL1_1)",
    "P(B02|XJTL1_1)",
    "V(B02|XJTL1_1)",
    "I(B02|XJTL1_1)",
    "P(B01|XJTL1_6)",
    "V(B01|XJTL1_6)",
    "I(B01|XJTL1_6)",
    "P(B02|XJTL1_6)",
    "V(B02|XJTL1_6)",
    "I(B02|XJTL1_6)",
    "I(R_TERM)",
]

EVENT_ALIGNED_SIGNAL_LABELS = [
    ("I(I_REPLAY)", "A"),
    ("V(QBIN)", "V"),
    ("P(BJS|XBQ1)", "rad"),
    ("V(BJS|XBQ1)", "V"),
    ("P(BJ1|XBQ1)", "rad"),
    ("V(BJ1|XBQ1)", "V"),
    ("I(L1|XBQ1)", "A"),
    ("I(L2|XBQ1)", "A"),
    ("P(BJ2|XBQ1)", "rad"),
    ("V(BJ2|XBQ1)", "V"),
    ("V(QBOUT)", "V"),
    ("P(B01|XJTL1_1)", "rad"),
    ("V(B01|XJTL1_1)", "V"),
    ("P(B01|XJTL1_6)", "rad"),
    ("V(B01|XJTL1_6)", "V"),
    ("I(R_TERM)", "A"),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8") == content:
            return
        raise RuntimeError(f"refusing to overwrite existing artifact: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def json_once(path: Path, value: object) -> None:
    write_once(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def ps(time_s: float) -> float:
    return float(time_s) * 1.0e12


def seconds(time_ps: float) -> float:
    return float(time_ps) * 1.0e-12


def window_indices(trace: RawTrace, start_ps: float, end_ps: float) -> list[int]:
    return [
        index
        for index, value in enumerate(trace.time)
        if float(start_ps) <= ps(value) < float(end_ps)
    ]


def exact_time_index(trace: RawTrace, target_ps: float) -> tuple[int, float]:
    index = min(range(trace.sample_count), key=lambda item: abs(ps(trace.time[item]) - target_ps))
    error = abs(ps(trace.time[index]) - target_ps)
    if error > 1.0e-6:
        raise RuntimeError(f"target {target_ps} ps is not on the stored grid for {trace.path}: error={error}")
    return index, error


def raw_grid_record(trace: RawTrace) -> dict[str, object]:
    dt_ps = [ps(trace.time[index + 1] - trace.time[index]) for index in range(trace.sample_count - 1)]
    median_dt = sorted(dt_ps)[len(dt_ps) // 2]
    gaps = [
        {
            "from_ps": ps(trace.time[index]),
            "to_ps": ps(trace.time[index + 1]),
            "dt_ps": dt_ps[index],
        }
        for index in range(len(dt_ps))
        if dt_ps[index] > median_dt * 1.5
    ]
    return {
        "sample_count": trace.sample_count,
        "time_start_ps": ps(trace.time[0]),
        "time_end_ps": ps(trace.time[-1]),
        "dt_min_ps": min(dt_ps),
        "dt_max_ps": max(dt_ps),
        "nominal_median_dt_ps": median_dt,
        "uniform_time_grid": all(value == dt_ps[0] for value in dt_ps),
        "strictly_increasing": all(trace.time[i + 1] > trace.time[i] for i in range(trace.sample_count - 1)),
        "large_gap_records": gaps,
        "window_grid": {
            "window_ps": [WINDOW_START_PS, WINDOW_END_PS],
            "sample_count": len(window_indices(trace, WINDOW_START_PS, WINDOW_END_PS)),
            "first_sample_ps": ps(trace.time[window_indices(trace, WINDOW_START_PS, WINDOW_END_PS)[0]]),
            "last_sample_ps": ps(trace.time[window_indices(trace, WINDOW_START_PS, WINDOW_END_PS)[-1]]),
            "actual_time_values_used_for_integration": True,
        },
    }


def validate_trace(trace: RawTrace) -> None:
    missing = [label for label in REPLAY_REQUIRED_HEADERS if label not in trace.headers]
    if missing:
        raise RuntimeError(f"{trace.path}: missing required replay headers: {missing}")
    if trace.duplicate_columns:
        raise RuntimeError(f"{trace.path}: duplicate columns require explicit occurrence selection: {trace.duplicate_columns}")


def local_positive_peaks(
    trace: RawTrace,
    label: str,
    start_ps: float,
    end_ps: float,
    threshold: float,
    merge_ps: float = 0.0,
) -> list[dict[str, float]]:
    values = trace.column(label)
    indices = window_indices(trace, start_ps, end_ps)
    candidates: list[dict[str, float]] = []
    for index in indices:
        if index <= 0 or index >= trace.sample_count - 1:
            continue
        value = float(values[index])
        if value <= threshold:
            continue
        if value >= float(values[index - 1]) and value > float(values[index + 1]):
            candidates.append({"time_ps": ps(trace.time[index]), "value": value})
    merged: list[dict[str, float]] = []
    for candidate in candidates:
        if not merged or candidate["time_ps"] - merged[-1]["time_ps"] > merge_ps:
            merged.append(candidate)
        elif candidate["value"] > merged[-1]["value"]:
            merged[-1] = candidate
    return merged


def local_abs_peaks(
    trace: RawTrace,
    label: str,
    start_ps: float,
    end_ps: float,
    threshold: float,
    merge_ps: float = 0.0,
) -> list[dict[str, float]]:
    values = trace.column(label)
    indices = window_indices(trace, start_ps, end_ps)
    candidates: list[dict[str, float]] = []
    for index in indices:
        if index <= 0 or index >= trace.sample_count - 1:
            continue
        value = float(values[index])
        score = abs(value)
        if score <= threshold:
            continue
        if score >= abs(float(values[index - 1])) and score > abs(float(values[index + 1])):
            candidates.append({"time_ps": ps(trace.time[index]), "value": value, "abs_value": score})
    merged: list[dict[str, float]] = []
    for candidate in candidates:
        if not merged or candidate["time_ps"] - merged[-1]["time_ps"] > merge_ps:
            merged.append(candidate)
        elif candidate["abs_value"] > merged[-1]["abs_value"]:
            merged[-1] = candidate
    return merged


def choose_nearest(
    candidates: Sequence[dict[str, float]],
    target_ps: float,
    *,
    label: str,
) -> dict[str, object] | None:
    if not candidates:
        return None
    ranked = sorted(candidates, key=lambda item: (abs(item["time_ps"] - target_ps), -item.get("value", 0.0)))
    chosen = dict(ranked[0])
    chosen["target_time_ps"] = target_ps
    chosen["selection_error_ps"] = abs(chosen["time_ps"] - target_ps)
    chosen["candidate_count"] = len(candidates)
    chosen["candidate_times_ps"] = [item["time_ps"] for item in candidates]
    chosen["selection_label"] = label
    if len(ranked) > 1:
        chosen["second_candidate_separation_ps"] = ranked[1]["time_ps"] - ranked[0]["time_ps"]
    return chosen


def trace_point(trace: RawTrace, label: str, target_ps: float) -> dict[str, float]:
    index, error = exact_time_index(trace, target_ps)
    return {"time_ps": ps(trace.time[index]), "value": float(trace.column(label)[index]), "grid_error_ps": error}


def cumulative_for(trace: RawTrace) -> dict[str, object]:
    indices = window_indices(trace, WINDOW_START_PS, WINDOW_END_PS)
    if len(indices) < 2:
        raise RuntimeError(f"not enough samples in final response window: {trace.path}")
    start = indices[0]
    out: dict[str, object] = {"start_index": start, "start_time_ps": ps(trace.time[start]), "phase": {}, "window_indices": indices}
    for name, (phase_label, voltage_label) in PHASE_JJS.items():
        raw_phase = trace.column(phase_label)
        voltage = trace.column(voltage_label)
        unwrapped = continuous_unwrap(raw_phase)
        cphi_rad = [0.0] * trace.sample_count
        cv = [0.0] * trace.sample_count
        for index in range(start, trace.sample_count):
            cphi_rad[index] = unwrapped[index] - unwrapped[start]
            if index > start:
                cv[index] = cv[index - 1] + 0.5 * (float(voltage[index - 1]) + float(voltage[index])) * (trace.time[index] - trace.time[index - 1]) / PHI0
        end = indices[-1]
        out["phase"][name] = {
            "phase_label": phase_label,
            "voltage_label": voltage_label,
            "cphi_rad": cphi_rad,
            "cphi_turns": [value / TAU for value in cphi_rad],
            "cv_over_phi0": cv,
            "endpoint": {
                "time_ps": ps(trace.time[end]),
                "cphi_rad": cphi_rad[end],
                "cphi_turns": cphi_rad[end] / TAU,
                "cv_over_phi0": cv[end],
                "phase_area_residual_turns": cphi_rad[end] / TAU - cv[end],
            },
        }
    return out


def phase_at(cumulative: dict[str, object], name: str, index: int) -> dict[str, float]:
    item = cumulative["phase"][name]
    return {
        "cphi_rad_from_110_ps": float(item["cphi_rad"][index]),
        "cphi_turns_from_110_ps": float(item["cphi_turns"][index]),
        "cv_over_phi0_from_110_ps": float(item["cv_over_phi0"][index]),
    }


def unit_for(label: str) -> str:
    if label.startswith("I("):
        return "A"
    if label.startswith("V("):
        return "V"
    if label.startswith("P("):
        return "rad"
    return "raw"


def write_csv(path: Path, times: Sequence[float], columns: Sequence[tuple[str, Sequence[float]]]) -> dict[str, object]:
    if any(len(values) != len(times) for _, values in columns):
        raise RuntimeError(f"derived column length mismatch: {path}")
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(["time"] + [label for label, _ in columns])
    for row_index, time in enumerate(times):
        writer.writerow([f"{float(time):.17g}"] + [f"{float(values[row_index]):.17g}" for _, values in columns])
    content = buffer.getvalue()
    write_once(path, content)
    return {
        "path": rel(path),
        "sha256": sha256(path),
        "labels": [label for label, _ in columns],
        "sample_count": len(times),
        "time_start_ps": ps(times[0]),
        "time_end_ps": ps(times[-1]),
    }


def waveform_stats(trace: RawTrace, label: str, start_ps: float, end_ps: float, *, threshold: float | None = None) -> dict[str, object]:
    indices = window_indices(trace, start_ps, end_ps)
    if len(indices) < 2:
        raise RuntimeError(f"fewer than two samples for {label} in [{start_ps},{end_ps}) ps")
    times = [trace.time[index] for index in indices]
    values = [float(trace.column(label)[index]) for index in indices]
    factor = 1.0e6 if label.startswith("I(") else 1.0e3 if label.startswith("V(") else 1.0
    display_unit = "uA" if label.startswith("I(") else "mV" if label.startswith("V(") else "raw"
    area_factor = 1.0e18 if label.startswith("I(") else 1.0e15 if label.startswith("V(") else 1.0
    significant: list[int] = []
    if threshold is not None:
        significant = [index for index in indices if float(trace.column(label)[index]) > threshold]
    result: dict[str, object] = {
        "label": label,
        "window_ps": [start_ps, end_ps],
        "sample_count": len(indices),
        "raw_unit": unit_for(label),
        "display_unit": display_unit,
        "minimum": min(values) * factor,
        "maximum": max(values) * factor,
        "maximum_time_ps": ps(times[values.index(max(values))]),
        "minimum_time_ps": ps(times[values.index(min(values))]),
        "max_abs": max(abs(value) for value in values) * factor,
        "max_abs_time_ps": ps(times[max(range(len(values)), key=lambda i: abs(values[i]))]),
        "rms_sample_value": math.sqrt(sum(value * value for value in values) / len(values)) * factor,
        "signed_integral": trapezoid_integral(values, times) * area_factor,
        "positive_area": trapezoid_integral([max(value, 0.0) for value in values], times) * area_factor,
        "negative_area": trapezoid_integral([min(value, 0.0) for value in values], times) * area_factor,
        "first_sample_ps": ps(times[0]),
        "last_sample_ps": ps(times[-1]),
        "actual_time_grid_for_integration": True,
    }
    if threshold is not None:
        result["significant_positive_threshold"] = threshold * factor
        result["significant_positive_threshold_unit"] = display_unit
        result["significant_positive_sample_count"] = len(significant)
        result["significant_positive_first_ps"] = ps(trace.time[significant[0]]) if significant else None
        result["significant_positive_last_ps"] = ps(trace.time[significant[-1]]) if significant else None
        result["significant_positive_duration_span_ps"] = (
            ps(trace.time[significant[-1]] - trace.time[significant[0]]) if significant else 0.0
        )
    return result


def terminal_events(trace: RawTrace) -> list[dict[str, object]]:
    peaks = local_positive_peaks(trace, "I(R_TERM)", WINDOW_START_PS, WINDOW_END_PS, TERMINAL_THRESHOLD_A, TERMINAL_MERGE_PS)
    selected = peaks[:3]
    if len(selected) < 3:
        raise RuntimeError(f"expected at least three terminal peak-like maxima in {trace.path}; got {peaks}")
    for index, item in enumerate(selected, start=1):
        item["response_index"] = index
        item["value_uA"] = item["value"] * 1.0e6
        item["probe"] = "local positive I(R_TERM) maximum > 5 uA; descriptive activity probe, not an event count"
        item["evidence_class"] = "OBSERVED"
    return selected


def primary_sequences(trace: RawTrace, terminal: Sequence[dict[str, object]]) -> dict[str, list[dict[str, object] | None]]:
    # These are descriptive voltage-peak probes.  They are not Ic tests and
    # do not certify switching or count SFQ events.
    jtl1 = local_positive_peaks(trace, "V(B01|XJTL1_1)", WINDOW_START_PS, 160.0, 0.5e-3, 0.3)
    jtl6 = local_positive_peaks(trace, "V(B01|XJTL1_6)", WINDOW_START_PS, 160.0, 0.5e-3, 0.3)
    jtl1 = jtl1[:3]
    jtl6 = jtl6[:3]
    if len(jtl1) < 3 or len(jtl6) < 3:
        raise RuntimeError(f"could not isolate three strong JTL peaks in {trace.path}: jtl1={jtl1}, jtl6={jtl6}")
    qout: list[dict[str, object] | None] = []
    bj2: list[dict[str, object] | None] = []
    bj1: list[dict[str, object] | None] = []
    for event_index in range(3):
        j1_time = float(jtl1[event_index]["time_ps"])
        q_candidates = local_positive_peaks(trace, "V(QBOUT)", j1_time - 2.0, j1_time + 0.5, 0.45e-3, 0.2)
        q_pick = choose_nearest(q_candidates, j1_time - 1.0, label="QBOUT near JTL1 peak")
        qout.append(q_pick)
        if q_pick is None:
            bj2.append(None)
            bj1.append(None)
            continue
        q_time = float(q_pick["time_ps"])
        bj2_candidates = local_positive_peaks(trace, "V(BJ2|XBQ1)", q_time - 1.0, q_time + 1.0, 0.5e-3, 0.2)
        bj2_pick = choose_nearest(bj2_candidates, q_time - 0.2, label="BJ2 near QBOUT peak")
        bj2.append(bj2_pick)
        if bj2_pick is None:
            bj1.append(None)
            continue
        bj2_time = float(bj2_pick["time_ps"])
        bj1_candidates = local_positive_peaks(trace, "V(BJ1|XBQ1)", bj2_time - 4.0, bj2_time + 2.0, 0.3e-3, 0.2)
        bj1.append(choose_nearest(bj1_candidates, bj2_time - 1.5, label="BJ1 preceding BJ2 peak"))
    bjs_peaks = local_abs_peaks(trace, "V(BJS|XBQ1)", WINDOW_START_PS, 160.0, 0.05e-3, 0.2)
    return {
        "JTL1_B01": [{**item, "value_mV": item["value"] * 1.0e3, "evidence_class": "DERIVED"} for item in jtl1],
        "JTL6_B01": [{**item, "value_mV": item["value"] * 1.0e3, "evidence_class": "DERIVED"} for item in jtl6],
        "QBOUT": [
            None if item is None else {**item, "value_mV": item["value"] * 1.0e3, "evidence_class": "DERIVED"}
            for item in qout
        ],
        "BJ2": [
            None if item is None else {**item, "value_mV": item["value"] * 1.0e3, "evidence_class": "DERIVED"}
            for item in bj2
        ],
        "BJ1": [
            None if item is None else {**item, "value_mV": item["value"] * 1.0e3, "evidence_class": "DERIVED"}
            for item in bj1
        ],
        "BJS_global_activity": {
            "evidence_class": "UNKNOWN",
            "probe_threshold_mV_abs": 0.05,
            "peak_count_before_160_ps": len(bjs_peaks),
            "top_abs_peaks": [
                {"time_ps": item["time_ps"], "value_mV": item["value"] * 1.0e3, "abs_value_mV": item["abs_value"] * 1.0e3}
                for item in sorted(bjs_peaks, key=lambda item: item["abs_value"], reverse=True)[:16]
            ],
            "reason": "BJS activity is oscillatory and overlapping across the three response chain; no unique per-response peak assignment is made",
        },
    }


def response_signal_record(
    trace: RawTrace,
    cumulative: dict[str, object],
    signal_name: str,
    peak: dict[str, object] | None,
    *,
    value_label: str,
    phase_name: str | None = None,
) -> dict[str, object]:
    if peak is None:
        return {
            "time_ps": None,
            "evidence_class": "UNKNOWN",
            "status": "UNKNOWN",
            "reason": f"no separable descriptive peak for {signal_name} in its association window",
        }
    time_ps = float(peak["time_ps"])
    index, error = exact_time_index(trace, time_ps)
    item: dict[str, object] = {
        "time_ps": time_ps,
        "evidence_class": str(peak.get("evidence_class", "DERIVED")),
        "status": "DESCRIPTIVE_PEAK",
        "raw_signal_label": value_label,
        "raw_value": float(trace.column(value_label)[index]),
        "raw_unit": unit_for(value_label),
        "grid_error_ps": error,
        "selection": {key: value for key, value in peak.items() if key not in ("evidence_class",)},
    }
    if value_label.startswith("V("):
        item["display_value"] = float(trace.column(value_label)[index]) * 1.0e3
        item["display_unit"] = "mV"
    if phase_name is not None:
        item["phase_progression"] = phase_at(cumulative, phase_name, index)
    return item


def build_timeline(trace: RawTrace, name: str, cumulative: dict[str, object]) -> dict[str, object]:
    terminal = terminal_events(trace)
    sequences = primary_sequences(trace, terminal)
    responses: list[dict[str, object]] = []
    for index, terminal_peak in enumerate(terminal):
        response: dict[str, object] = {
            "response_index": index + 1,
            "reference_time_ps": terminal_peak["time_ps"],
            "evidence_class": "OBSERVED",
            "reference": terminal_peak,
            "time_positions": {},
        }
        response["time_positions"]["BJS"] = {
            "time_ps": None,
            "evidence_class": "UNKNOWN",
            "status": "UNKNOWN",
            "reason": "BJS voltage activity is overlapping/oscillatory; no reliable per-response separation",
        }
        response["time_positions"]["BJ1"] = response_signal_record(
            trace, cumulative, "BJ1", sequences["BJ1"][index], value_label="V(BJ1|XBQ1)", phase_name="BJ1"
        )
        response["time_positions"]["BJ2"] = response_signal_record(
            trace, cumulative, "BJ2", sequences["BJ2"][index], value_label="V(BJ2|XBQ1)", phase_name="BJ2"
        )
        response["time_positions"]["QBOUT"] = response_signal_record(
            trace, cumulative, "QBOUT", sequences["QBOUT"][index], value_label="V(QBOUT)"
        )
        response["time_positions"]["JTL1_B01"] = response_signal_record(
            trace, cumulative, "JTL1_B01", sequences["JTL1_B01"][index], value_label="V(B01|XJTL1_1)", phase_name="JTL1_B01"
        )
        response["time_positions"]["JTL6_B01"] = response_signal_record(
            trace, cumulative, "JTL6_B01", sequences["JTL6_B01"][index], value_label="V(B01|XJTL1_6)", phase_name="JTL6_B01"
        )
        response["time_positions"]["R_TERM"] = response_signal_record(
            trace, cumulative, "R_TERM", terminal_peak, value_label="I(R_TERM)"
        )
        responses.append(response)
    spacing: dict[str, list[float]] = {}
    for key in ("R_TERM", "BJ1", "BJ2"):
        if key == "R_TERM":
            times = [float(item["time_ps"]) for item in terminal]
        else:
            times = [float(item["time_ps"]) for item in sequences[key] if item is not None]
        spacing[key] = [times[index + 1] - times[index] for index in range(len(times) - 1)] if len(times) >= 2 else []
    return {
        "case": name,
        "window_ps": [WINDOW_START_PS, WINDOW_END_PS],
        "terminal_probe": {
            "threshold_uA": TERMINAL_THRESHOLD_A * 1.0e6,
            "merge_separation_ps": TERMINAL_MERGE_PS,
            "meaning": "local positive current maxima for descriptive timing only; not an event count",
        },
        "internal_voltage_probes": {
            "JTL1_B01_threshold_mV": 0.5,
            "JTL6_B01_threshold_mV": 0.5,
            "QBOUT_threshold_mV": 0.45,
            "BJ2_threshold_mV": 0.5,
            "BJ1_threshold_mV": 0.3,
            "meaning": "descriptive voltage activity probes; no Ic threshold or switching inference",
        },
        "responses": responses,
        "spacing_ps": spacing,
        "bjs_global_activity": sequences["BJS_global_activity"],
        "cumulative_endpoint_summary": {
            name: cumulative["phase"][name]["endpoint"] for name in PHASE_JJS
        },
        "phase_area_semantics": "Cphi and Cv are continuous cumulative quantities from 110 ps; they are not SFQ event counts",
    }


def cumulative_csvs(traces: dict[str, RawTrace], cumulatives: dict[str, dict[str, object]]) -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
    data_dir = EXP / "plots/deep_dive/data"
    single_records: dict[str, object] = {}
    single_columns: dict[str, list[str]] = {}
    for name in ("N3_REPLAY", "N4_REPLAY"):
        trace = traces[name]
        indices = window_indices(trace, WINDOW_START_PS, WINDOW_END_PS)
        times = [trace.time[index] for index in indices]
        columns: list[tuple[str, Sequence[float]]] = []
        labels: list[str] = []
        for raw_label in ("I(I_REPLAY)", "V(QBIN)", "V(QBOUT)", "I(R_TERM)"):
            label = f"{raw_label} | {name} raw {unit_for(raw_label)}"
            columns.append((label, [trace.column(raw_label)[index] for index in indices]))
            labels.append(label)
        for jj_name in ("BJS", "BJ1", "BJ2", "JTL1_B01", "JTL1_B02", "JTL6_B01", "JTL6_B02"):
            item = cumulatives[name]["phase"][jj_name]
            phase_label = f"P({jj_name}) Cphi from 110 ps | {name} [raw rad; shown turns]"
            cv_label = f"V(Cv {jj_name} from 110 ps / Phi0) | {name} [dimensionless]"
            columns.append((phase_label, [item["cphi_rad"][index] for index in indices]))
            columns.append((cv_label, [item["cv_over_phi0"][index] for index in indices]))
            labels.extend([phase_label, cv_label])
        record = write_csv(data_dir / f"{name}_CUMULATIVE.csv", times, columns)
        single_records[name] = record
        single_columns[name] = labels

    comparison_columns: list[tuple[str, Sequence[float]]] = []
    comparison_labels: list[str] = []
    n3 = traces["N3_REPLAY"]
    n4 = traces["N4_REPLAY"]
    n3_indices = window_indices(n3, WINDOW_START_PS, WINDOW_END_PS)
    n4_indices = window_indices(n4, WINDOW_START_PS, WINDOW_END_PS)
    if [n3.time[i] for i in n3_indices] != [n4.time[i] for i in n4_indices]:
        raise RuntimeError("N3/N4 response-window grids differ; refusing unaligned comparison")
    time_values = [n3.time[index] for index in n3_indices]
    for raw_label in ("I(I_REPLAY)", "V(QBIN)", "V(QBOUT)", "I(R_TERM)"):
        for name, trace, indices in (("N3_REPLAY", n3, n3_indices), ("N4_REPLAY", n4, n4_indices)):
            label = f"{raw_label} | {name} raw {unit_for(raw_label)}"
            comparison_columns.append((label, [trace.column(raw_label)[index] for index in indices]))
            comparison_labels.append(label)
    for jj_name in ("BJS", "BJ1", "BJ2", "JTL1_B01", "JTL6_B01"):
        for name in ("N3_REPLAY", "N4_REPLAY"):
            item = cumulatives[name]["phase"][jj_name]
            label = f"P({jj_name}) Cphi from 110 ps | {name} [raw rad; shown turns]"
            comparison_columns.append((label, [item["cphi_rad"][index] for index in window_indices(traces[name], WINDOW_START_PS, WINDOW_END_PS)]))
            comparison_labels.append(label)
    comparison_record = write_csv(data_dir / "N3_VS_N4_CUMULATIVE.csv", time_values, comparison_columns)
    return {"single_records": single_records, "single_labels": single_columns}, comparison_record, {"comparison_labels": comparison_labels}


def event_aligned_csvs(traces: dict[str, RawTrace], timelines: dict[str, dict[str, object]]) -> dict[str, object]:
    data_dir = EXP / "plots/deep_dive/data"
    outputs: dict[str, object] = {}
    terminal_times = {
        name: [float(item["reference_time_ps"]) for item in timelines[name]["responses"]]
        for name in ("N3_REPLAY", "N4_REPLAY")
    }
    for event_index in (1, 2, 3):
        refs = {name: terminal_times[name][event_index - 1] for name in ("N3_REPLAY", "N4_REPLAY")}
        offsets = [(-22.0 + 0.1 * index) for index in range(261)]  # -22 ps through +4 ps, exact grid rebasing
        columns: list[tuple[str, Sequence[float]]] = []
        labels: list[str] = []
        for raw_label, unit in EVENT_ALIGNED_SIGNAL_LABELS:
            for name in ("N3_REPLAY", "N4_REPLAY"):
                values: list[float] = []
                for offset in offsets:
                    target = refs[name] + offset
                    index, _ = exact_time_index(traces[name], target)
                    values.append(float(traces[name].column(raw_label)[index]))
                label = f"{raw_label} | {name} raw {unit}"
                columns.append((label, values))
                labels.append(label)
        time_values = [seconds(offset) for offset in offsets]
        page_name = f"EVENT{event_index}_N3_VS_N4"
        record = write_csv(data_dir / f"{page_name}.csv", time_values, columns)
        outputs[page_name] = {
            **record,
            "reference_time_ps": refs,
            "relative_window_ps": [-22.0, 4.0],
            "alignment": "each case re-based to its own observed terminal peak-like reference; exact stored samples, no interpolation or value normalization",
            "labels": labels,
        }

    refs = {name: terminal_times[name][2] for name in ("N3_REPLAY", "N4_REPLAY")}
    # Use the actual last stored sample rather than the nominal 200 ps bound;
    # the half-open analysis window ends before 200 ps and the final sample is
    # 199.9 ps on these traces.
    common_end = min(ps(traces[name].time[-1]) - refs[name] for name in ("N3_REPLAY", "N4_REPLAY"))
    post_offsets = [0.1 * index for index in range(int(round(common_end * 10.0)) + 1)]
    columns = []
    labels = []
    for raw_label, unit in EVENT_ALIGNED_SIGNAL_LABELS:
        for name in ("N3_REPLAY", "N4_REPLAY"):
            values = []
            for offset in post_offsets:
                index, _ = exact_time_index(traces[name], refs[name] + offset)
                values.append(float(traces[name].column(raw_label)[index]))
            label = f"{raw_label} | {name} raw {unit}"
            columns.append((label, values))
            labels.append(label)
    post_record = write_csv(data_dir / "POST_EVENT3_N3_VS_N4.csv", [seconds(offset) for offset in post_offsets], columns)
    outputs["POST_EVENT3_N3_VS_N4"] = {
        **post_record,
        "reference_time_ps": refs,
        "relative_window_ps": [0.0, common_end],
        "absolute_coverage_ps": {
            name: [refs[name], refs[name] + common_end] for name in ("N3_REPLAY", "N4_REPLAY")
        },
        "alignment": "common overlap after each case's third observed terminal peak-like reference; exact stored samples, no interpolation or value normalization",
        "labels": labels,
    }
    return outputs


def recovery_record(trace: RawTrace, name: str, timeline: dict[str, object], cumulative: dict[str, object]) -> dict[str, object]:
    variables = OrderedDict(
        [
            ("I(L1|XBQ1)", "A"),
            ("I(L2|XBQ1)", "A"),
            ("I(L3|XBQ1)", "A"),
            ("I(BJ1|XBQ1)", "A"),
            ("I(BJ2|XBQ1)", "A"),
            ("I(RJ1|XBQ1)", "A"),
            ("I(RJ2|XBQ1)", "A"),
            ("I(IB|XBQ1)", "A"),
            ("V(QBIN)", "V"),
        ]
    )
    offsets = [0.5, 1.0, 2.0, 3.0]
    event_states: list[dict[str, object]] = []
    for response in timeline["responses"]:
        ref = float(response["reference_time_ps"])
        offsets_out: dict[str, object] = {}
        for offset in offsets:
            index, error = exact_time_index(trace, ref + offset)
            state: dict[str, object] = {"target_time_ps": ref + offset, "actual_time_ps": ps(trace.time[index]), "grid_error_ps": error}
            for label, unit in variables.items():
                value = float(trace.column(label)[index])
                factor = 1.0e6 if unit == "A" else 1.0e3 if unit == "V" else 1.0
                state[label] = {"raw_value": value, "display_value": value * factor, "raw_unit": unit, "display_unit": "uA" if unit == "A" else "mV" if unit == "V" else unit}
            state["BJ1_phase_plateau"] = {"raw_phase_rad": float(trace.column("P(BJ1|XBQ1)")[index]), **phase_at(cumulative, "BJ1", index)}
            state["BJ2_phase_plateau"] = {"raw_phase_rad": float(trace.column("P(BJ2|XBQ1)")[index]), **phase_at(cumulative, "BJ2", index)}
            offsets_out[f"+{offset:g}ps"] = state
        event_states.append({"response_index": response["response_index"], "reference_time_ps": ref, "offsets": offsets_out})
    comparisons: dict[str, object] = {}
    first = event_states[0]
    for current in event_states[1:]:
        event_key = f"event_{current['response_index']}_minus_event_1"
        comparisons[event_key] = {}
        for offset_key, state in current["offsets"].items():
            base = first["offsets"][offset_key]
            differences: dict[str, object] = {}
            for label in variables:
                differences[label] = {
                    "raw_difference": state[label]["raw_value"] - base[label]["raw_value"],
                    "display_difference": state[label]["display_value"] - base[label]["display_value"],
                    "display_unit": state[label]["display_unit"],
                }
            for phase_key in ("BJ1_phase_plateau", "BJ2_phase_plateau"):
                differences[phase_key] = {
                    "cphi_turns_difference": state[phase_key]["cphi_turns_from_110_ps"] - base[phase_key]["cphi_turns_from_110_ps"],
                    "raw_phase_rad_difference": state[phase_key]["raw_phase_rad"] - base[phase_key]["raw_phase_rad"],
                }
            comparisons[event_key][offset_key] = differences
    phase_ranges = {}
    for phase_key in ("BJ1_phase_plateau", "BJ2_phase_plateau"):
        phase_ranges[phase_key] = {}
        for offset_key in ("+0.5ps", "+1ps", "+2ps", "+3ps"):
            values = [event["offsets"][offset_key][phase_key]["cphi_turns_from_110_ps"] for event in event_states]
            phase_ranges[phase_key][offset_key] = {"min_turns": min(values), "max_turns": max(values), "range_turns": max(values) - min(values)}
    return {
        "case": name,
        "offsets_ps": offsets,
        "variables": list(variables),
        "states": event_states,
        "comparisons_to_event_1": comparisons,
        "phase_plateau_ranges_across_events": phase_ranges,
        "interpretation_boundary": "fixed-offset state comparison is descriptive; it does not establish a physical recovery mechanism",
    }


def source_residual(trace: RawTrace, t3_ps: float, *, label: str = "I(I_REPLAY)") -> dict[str, object]:
    return waveform_stats(trace, label, t3_ps, WINDOW_END_PS, threshold=SIGNIFICANT_SOURCE_THRESHOLD_A)


def post_third_probe(trace: RawTrace, name: str, t3_ps: float, cumulative: dict[str, object], n1_first: dict[str, object]) -> dict[str, object]:
    source = source_residual(trace, t3_ps)
    post_start = t3_ps + T3_POST_PROBE_OFFSET_PS
    probe_specs = OrderedDict(
        [
            ("QBIN", ("V(QBIN)", 0.25e-3, "voltage excursion")),
            ("BJS", ("V(BJS|XBQ1)", 0.10e-3, "absolute voltage activity")),
            ("BJ1", ("V(BJ1|XBQ1)", 0.30e-3, "voltage activity")),
            ("BJ2", ("V(BJ2|XBQ1)", 0.50e-3, "voltage activity")),
            ("QBOUT", ("V(QBOUT)", 0.45e-3, "pulse-like voltage activity")),
            ("JTL1_B01", ("V(B01|XJTL1_1)", 0.50e-3, "JTL1 voltage activity")),
            ("JTL6_B01", ("V(B01|XJTL1_6)", 0.50e-3, "JTL6 voltage activity")),
            ("R_TERM", ("I(R_TERM)", TERMINAL_THRESHOLD_A, "terminal current activity")),
        ]
    )
    candidates: dict[str, object] = {}
    for key, (label, threshold, meaning) in probe_specs.items():
        peaks = local_abs_peaks(trace, label, post_start, WINDOW_END_PS, threshold, 0.2)
        stats = waveform_stats(trace, label, post_start, WINDOW_END_PS)
        candidates[key] = {
            "raw_label": label,
            "probe_window_ps": [post_start, WINDOW_END_PS],
            "threshold": threshold * (1.0e6 if label.startswith("I(") else 1.0e3),
            "threshold_unit": "uA" if label.startswith("I(") else "mV",
            "meaning": meaning,
            "peak_like_candidates": [
                {"time_ps": item["time_ps"], "value": item["value"] * (1.0e6 if label.startswith("I(") else 1.0e3), "abs_value": item["abs_value"] * (1.0e6 if label.startswith("I(") else 1.0e3)}
                for item in peaks
            ],
            "waveform_stats": stats,
            "candidate_status": "CANDIDATE_ACTIVITY" if peaks else "NO_SEPARABLE_FOURTH_CANDIDATE",
            "evidence_class": "OBSERVED" if peaks else "BOUNDED_RESULT",
        }
    phase_post: dict[str, object] = {}
    post_indices = window_indices(trace, post_start, WINDOW_END_PS)
    for jj_name in ("BJS", "BJ1", "BJ2", "JTL1_B01", "JTL6_B01"):
        item = cumulative["phase"][jj_name]
        start_idx = post_indices[0]
        end_idx = post_indices[-1]
        phase_post[jj_name] = {
            "cphi_start_turns_from_110_ps": item["cphi_turns"][start_idx],
            "cphi_end_turns_from_110_ps": item["cphi_turns"][end_idx],
            "cphi_net_turns_in_probe_window": item["cphi_turns"][end_idx] - item["cphi_turns"][start_idx],
            "cphi_p2p_turns_in_probe_window": max(item["cphi_turns"][i] for i in post_indices) - min(item["cphi_turns"][i] for i in post_indices),
            "continuous_quantity_not_event_count": True,
        }
    if candidates["BJS"]["peak_like_candidates"]:
        candidates["BJS"]["candidate_status"] = "RESIDUAL_RINGDOWN_ACTIVITY_NOT_FOURTH"
        candidates["BJS"]["fourth_response_status"] = "UNKNOWN"
        candidates["BJS"]["evidence_class"] = "UNKNOWN"
        candidates["BJS"]["interpretation"] = "absolute voltage activity remains, but it is not separable from third-response ringdown and is not promoted to a fourth nonlinear response"
    positive_drive = source["significant_positive_sample_count"] > 0
    fourth = {
        "A_I_REPLAY": {
            "status": "RESIDUAL_POSITIVE_DRIVE" if positive_drive else "NO_SIGNIFICANT_POSITIVE_DRIVE",
            "evidence_class": "OBSERVED",
            "source_metrics_window_ps": [t3_ps, WINDOW_END_PS],
            "source_metrics": source,
        },
        "B_QBIN": candidates["QBIN"],
        "C_BJS": candidates["BJS"],
        "D_BJ1": candidates["BJ1"],
        "E_BJ2": candidates["BJ2"],
        "F_QBOUT": candidates["QBOUT"],
        "G_JTL1": candidates["JTL1_B01"],
        "H_JTL6_R_TERM": {
            "JTL6": candidates["JTL6_B01"],
            "R_TERM": candidates["R_TERM"],
            "joint_candidate_status": "CANDIDATE_ACTIVITY" if candidates["JTL6_B01"]["peak_like_candidates"] or candidates["R_TERM"]["peak_like_candidates"] else "NO_SEPARABLE_FOURTH_DOWNSTREAM_CANDIDATE",
            "evidence_class": "OBSERVED" if candidates["JTL6_B01"]["peak_like_candidates"] or candidates["R_TERM"]["peak_like_candidates"] else "BOUNDED_RESULT",
        },
    }
    peak_ratio = source["maximum"] / n1_first["maximum"] if n1_first["maximum"] else None
    area_ratio = source["positive_area"] / n1_first["positive_area"] if n1_first["positive_area"] else None
    return {
        "case": name,
        "t3": {
            "time_ps": t3_ps,
            "definition": "third positive I(R_TERM) peak-like maximum in FINAL_READ_RESPONSE",
            "evidence_class": "OBSERVED",
        },
        "fourth_candidate_probe_start_ps": post_start,
        "fourth_candidate_probe_end_ps": WINDOW_END_PS,
        "fourth_candidate_probe_note": "the +3 ps offset excludes the observed third terminal pulse and its immediate tail; this is a descriptive activity probe, not an Ic or switching criterion",
        "source_residual": source,
        "n1_first_response_source_reference": n1_first,
        "n4_residual_to_n1_first_positive_area_ratio": area_ratio,
        "n4_residual_to_n1_first_peak_ratio": peak_ratio,
        "phase_post_probe": phase_post,
        "fourth_response_questions": fourth,
        "earliest_observed_missing_response": {
            "location": "QB front-end / BJS-to-BJ1 progression boundary",
            "evidence_class": "BOUNDED_RESULT",
            "statement": "after the third response, no separable fourth QBIN-to-BJS/BJ1 progression is observed; the exact BJS-versus-BJ1 boundary is not uniquely localized",
            "not_root_cause": True,
        },
        "classification": {
            "primary": "D_EFFECTIVE_STIMULUS_LIMIT",
            "selected": ["D_EFFECTIVE_STIMULUS_LIMIT", "F_MIXED_OR_UNRESOLVED"],
            "evidence_class": "BOUNDED_RESULT",
            "criterion_check": {
                "D": "N4 post-t3 positive source area and peak are far below the N1 first-response reference, while no independent fourth QB/front-end progression is resolved",
                "F": "the exact first missing internal level cannot be uniquely separated because BJS residual activity is oscillatory and not a fourth-response marker",
                "A_not_selected": "no separable fourth BJS activity is established",
                "B_not_selected": "no separable fourth BJ1 attempt is established",
                "C_not_selected_as_primary": "spacing shortens, but fixed-offset phase plateaus do not by themselves establish dead time or a physical recovery mechanism",
                "E_not_selected": "no complete fourth BJ2 progression is established, so downstream loss cannot be isolated",
            },
            "boundary": "classification is a bounded raw-evidence fit, not a root-cause or hardware claim",
        },
    }


def make_plot_manifest(
    traces: dict[str, RawTrace],
    cumulative_records: dict[str, object],
    cumulative_comparison: dict[str, object],
    cumulative_labels: dict[str, object],
    aligned_records: dict[str, object],
) -> dict[str, object]:
    pages: OrderedDict[str, dict[str, object]] = OrderedDict()
    for name in ("N3_REPLAY", "N4_REPLAY"):
        record = cumulative_records["single_records"][name]
        pages[f"{name}_CUMULATIVE"] = {
            "input": record["path"],
            "input_sha256": record["sha256"],
            "labels": cumulative_records["single_labels"][name],
            "source_kind": "derived_continuous_cumulative_from_raw",
            "title": f"{name} cumulative receiver trajectory | FINAL_READ_RESPONSE 110-200 ps | continuous Cphi/Cv; descriptive",
        }
    pages["N3_VS_N4_CUMULATIVE"] = {
        "input": cumulative_comparison["path"],
        "input_sha256": cumulative_comparison["sha256"],
        "labels": cumulative_labels["comparison_labels"],
        "source_kind": "derived_raw_track_pair_comparison",
        "title": "N3 vs N4 cumulative receiver trajectory | both raw-derived tracks shown | 110-200 ps",
    }
    for name in ("N3_REPLAY", "N4_REPLAY"):
        pages[f"{name}_QB_INTERNAL"] = {
            "input": rel(RAW_CASES[name]),
            "input_sha256": sha256(RAW_CASES[name]),
            "labels": INTERNAL_PLOT_LABELS,
            "source_kind": "raw_direct_standalone",
            "title": f"{name} QB/JTL internal deep dive | raw direct | full stored trace 0-199.9 ps",
        }
    for page_name in ("EVENT1_N3_VS_N4", "EVENT2_N3_VS_N4", "EVENT3_N3_VS_N4", "POST_EVENT3_N3_VS_N4"):
        record = aligned_records[page_name]
        pages[page_name] = {
            "input": record["path"],
            "input_sha256": record["sha256"],
            "labels": record["labels"],
            "source_kind": "derived_event_aligned_raw_tracks",
            "title": f"{page_name} | raw N3/N4 tracks event-aligned | descriptive comparison",
        }
    return {
        "schema": "jm2-n3-n4-replay-deep-dive-plot-manifest-v1",
        "phase_rule": "JoSIM P raw radians; cumulative display uses Cphi_rad/(2*pi) through -j 2pi; no SFQ/event-count label",
        "pages": pages,
        "raw_direct_standalone_pages": ["N3_REPLAY_QB_INTERNAL", "N4_REPLAY_QB_INTERNAL"],
        "comparison_pages_show_both_tracks": ["N3_VS_N4_CUMULATIVE", "EVENT1_N3_VS_N4", "EVENT2_N3_VS_N4", "EVENT3_N3_VS_N4", "POST_EVENT3_N3_VS_N4"],
        "renderer_command_template": "scripts/josim-plot2.py INPUT -x OUTPUT -t sep_comb -c dark -j 2pi -w TITLE -s LABELS...",
    }


def deep_dive_markdown(
    timelines: dict[str, dict[str, object]],
    post: dict[str, object],
    recovery: dict[str, dict[str, object]],
    raw_qa: dict[str, object],
    plot_manifest: dict[str, object],
) -> str:
    def time_value(case: str, event_index: int, signal: str) -> str:
        item = timelines[case]["responses"][event_index - 1]["time_positions"][signal]
        return "UNKNOWN" if item.get("time_ps") is None else f"{float(item['time_ps']):.1f} ps"

    def chain(case: str, event_index: int) -> str:
        return "; ".join(
            [
                f"BJ1 {time_value(case, event_index, 'BJ1')}",
                f"BJ2 {time_value(case, event_index, 'BJ2')}",
                f"QBOUT {time_value(case, event_index, 'QBOUT')}",
                f"JTL1 {time_value(case, event_index, 'JTL1_B01')}",
                f"JTL6 {time_value(case, event_index, 'JTL6_B01')}",
                f"R_TERM {time_value(case, event_index, 'R_TERM')}",
                "BJS UNKNOWN",
            ]
        )

    residual = post["source_residual"]
    n1 = post["n1_first_response_source_reference"]
    area_ratio = post["n4_residual_to_n1_first_positive_area_ratio"]
    peak_ratio = post["n4_residual_to_n1_first_peak_ratio"]
    spacing_lines = []
    for case in ("N3_REPLAY", "N4_REPLAY"):
        spacing_lines.append(
            f"{case}: terminal Δt12/Δt23 = {timelines[case]['spacing_ps']['R_TERM'][0]:.1f}/{timelines[case]['spacing_ps']['R_TERM'][1]:.1f} ps; "
            f"BJ1 = {timelines[case]['spacing_ps']['BJ1'][0]:.1f}/{timelines[case]['spacing_ps']['BJ1'][1]:.1f} ps; "
            f"BJ2 = {timelines[case]['spacing_ps']['BJ2'][0]:.1f}/{timelines[case]['spacing_ps']['BJ2'][1]:.1f} ps."
        )
    phase_ranges = []
    for case in ("N3_REPLAY", "N4_REPLAY"):
        r = recovery[case]["phase_plateau_ranges_across_events"]
        phase_ranges.append(
            f"{case}: fixed-offset BJ1 Cphi range {max(v['range_turns'] for v in r['BJ1_phase_plateau'].values()):.5f} turns; "
            f"BJ2 Cphi range {max(v['range_turns'] for v in r['BJ2_phase_plateau'].values()):.5f} turns."
        )
    lines = [
        "# N3/N4 replay deep dive",
        "",
        "范围：已有 `N1_REPLAY` 作为 first-response source reference，主分析为 `N3_REPLAY`/`N4_REPLAY`；`FINAL_READ_RESPONSE=[110,200) ps`。本轮未新增 JoSIM solve，未改变 circuit、parameter、timing 或 raw。",
        "",
        "证据标签：`OBSERVED`=raw 直接观测；`DERIVED`=按实际 time 列独立重算；`BOUNDED_RESULT`=声明窗口内的有界比较；`UNKNOWN`=raw 不能可靠分离。连续 Cphi/Cv 不是 SFQ event count。",
        "",
        "## 1. N3/N4 前三个 response 的 QB→JTL→termination 时间链",
        "",
        "`OBSERVED/DERIVED`：时间来自直接电压峰和 `I(R_TERM)>5 uA` 描述性峰值探针；BJS 不做强行分配。",
        "",
        "| case | response | descriptive chain |",
        "|---|---:|---|",
    ]
    for case in ("N3_REPLAY", "N4_REPLAY"):
        for event_index in (1, 2, 3):
            lines.append(f"| {case} | {event_index} | {chain(case, event_index)} |")
    lines.extend(
        [
            "",
            "这些是联合 raw 轨迹中的描述性位置，不是离散事件计数；完整累计相位/同 JJ `Cv` 见 [N3 cumulative](plots/deep_dive/N3_REPLAY_CUMULATIVE.html)、[N4 cumulative](plots/deep_dive/N4_REPLAY_CUMULATIVE.html) 和 [N3 vs N4 cumulative](plots/deep_dive/N3_VS_N4_CUMULATIVE.html)。",
            "",
            "## 2. N4 第三个 response 后是否仍有 source drive",
            "",
            f"`OBSERVED/BOUNDED_RESULT`：`t3={post['t3']['time_ps']:.1f} ps`。在 `[t3,200) ps`，`I(I_REPLAY)` signed area={residual['signed_integral']:.3f} uA·ps，positive area={residual['positive_area']:.3f} uA·ps，negative area={residual['negative_area']:.3f} uA·ps，positive peak={residual['maximum']:.3f} uA，sample RMS={residual['rms_sample_value']:.3f} uA；按 5 uA 描述性阈值的正向样本跨度为 {residual['significant_positive_duration_span_ps']:.1f} ps。",
            f"相对于 N1 first-response reference `[110,138.8) ps` 的 positive area={n1['positive_area']:.3f} uA·ps、peak={n1['maximum']:.3f} uA，N4 residual/N1-first 比值分别为 area={area_ratio:.4f}、peak={peak_ratio:.4f}。因此可报告为：第三次 response 后仍有短时、振荡的正向 residual drive，但没有一份 N1-class 的独立 fourth-drive 规模；area 不是 SFQ count。",
            "",
            "## 3. 最早观察到的第四 response 缺失位置",
            "",
            f"`BOUNDED_RESULT/UNKNOWN`：在 `{post['fourth_candidate_probe_start_ps']:.1f}–200 ps` 的第四候选探针中，未观察到可分离的第四个 QBIN excursion、BJ1/BJ2 progression、QBOUT pulse-like candidate、JTL1/JTL6 或 R_TERM downstream candidate；BJS 仍可见振铃样残余，但不能标成第四次 nonlinear response。因此 earliest observed missing-response location 只能写成 **QB front-end / BJS→BJ1 progression boundary**，BJS 与 BJ1 的精确边界为 `UNKNOWN`，不是 root-cause 结论。",
            "",
            "## 4. response spacing 与 unrecovered-state evidence",
            "",
            "`OBSERVED`：",
            *[f"- {line}" for line in spacing_lines],
            "",
            "`DERIVED/BOUNDED_RESULT`：",
            *[f"- {line}" for line in phase_ranges],
            "",
            "N4 的前三次 spacing 比 N3 更短；固定 offset 的 BJ1/BJ2 Cphi plateau 没有给出随 response 单调扩大的偏离证据，电流/电压状态仍有差异但不足以单独判定 dead time 或 physical recovery mechanism。",
            "",
            "## 5. 当前 bottleneck classification",
            "",
            "`BOUNDED_RESULT`：最符合的是 **D. EFFECTIVE_STIMULUS_LIMIT**；由于 BJS 残余活动与 BJ1 的精确缺失边界不可唯一定位，同时保留 **F. MIXED_OR_UNRESOLVED**。这表示声明窗口内的 raw 拟合分类，不是 saturation、recovery、bias 的已证实机制，也不是硬件结论。",
            "",
            "产物入口：",
            "- [N3 QB internal](plots/deep_dive/N3_REPLAY_QB_INTERNAL.html)；[N4 QB internal](plots/deep_dive/N4_REPLAY_QB_INTERNAL.html)",
            "- [EVENT1](plots/deep_dive/EVENT1_N3_VS_N4.html)；[EVENT2](plots/deep_dive/EVENT2_N3_VS_N4.html)；[EVENT3](plots/deep_dive/EVENT3_N3_VS_N4.html)；[POST EVENT3](plots/deep_dive/POST_EVENT3_N3_VS_N4.html)",
            "- machine-readable: `analysis/n3_n4_event_timeline.json`、`analysis/n4_post_third_response.json`、`analysis/n3_n4_recovery_compare.json`；raw/hash QA: `analysis/n3_n4_raw_qa.json`；visual QA: `analysis/deep_dive_viz_qa.json`。",
            "",
            f"raw QA status: `{raw_qa['status']}`, raw hashes before/after unchanged=`{raw_qa['raw_unchanged']}`。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    raw_before = {name: sha256(path) for name, path in RAW_CASES.items()}
    traces = {name: read_csv(path) for name, path in RAW_CASES.items()}
    for trace in traces.values():
        validate_trace(trace)
    grid_records = {name: raw_grid_record(trace) for name, trace in traces.items()}
    cumulatives = {name: cumulative_for(traces[name]) for name in ("N3_REPLAY", "N4_REPLAY")}
    cumulative_manifest, cumulative_comparison, cumulative_labels = cumulative_csvs(traces, cumulatives)
    timelines = {name: build_timeline(traces[name], name, cumulatives[name]) for name in ("N3_REPLAY", "N4_REPLAY")}
    aligned_records = event_aligned_csvs(traces, timelines)
    recovery = {
        name: recovery_record(traces[name], name, timelines[name], cumulatives[name])
        for name in ("N3_REPLAY", "N4_REPLAY")
    }
    n1_peaks = local_positive_peaks(
        traces["N1_REPLAY"],
        "I(R_TERM)",
        WINDOW_START_PS,
        WINDOW_END_PS,
        TERMINAL_THRESHOLD_A,
        TERMINAL_MERGE_PS,
    )
    if not n1_peaks:
        raise RuntimeError("N1_REPLAY has no terminal first-response reference peak")
    n1_first_ref = float(n1_peaks[0]["time_ps"])
    n1_first_source = waveform_stats(traces["N1_REPLAY"], "I(I_REPLAY)", WINDOW_START_PS, n1_first_ref)
    n1_first_source["reference_response_time_ps"] = n1_first_ref
    n1_first_source["reference_definition"] = "N1 first terminal peak-like maximum; source metrics use N1_REPLAY I(I_REPLAY) before that reference"
    post = post_third_probe(traces["N4_REPLAY"], "N4_REPLAY", float(timelines["N4_REPLAY"]["responses"][2]["reference_time_ps"]), cumulatives["N4_REPLAY"], n1_first_source)
    raw_after = {name: sha256(path) for name, path in RAW_CASES.items()}
    raw_qa = {
        "schema": "jm2-n3-n4-replay-deep-dive-raw-qa-v1",
        "status": "PASS" if raw_before == raw_after else "FAIL",
        "raw_unchanged": raw_before == raw_after,
        "raw_hashes_before": raw_before,
        "raw_hashes_after": raw_after,
        "raw_cases": {
            name: {
                "path": rel(RAW_CASES[name]),
                "sha256": raw_after[name],
                "role": "N1 first-response reference" if name == "N1_REPLAY" else "main read-only deep-dive case",
                "grid": grid_records[name],
                "required_header_count": len(REPLAY_REQUIRED_HEADERS),
                "required_headers_present": True,
            }
            for name in RAW_CASES
        },
        "analysis_window_ps": [WINDOW_START_PS, WINDOW_END_PS],
        "no_solver": True,
        "no_circuit_parameter_timing_changes": True,
        "integration_rule": "trapezoid integration on actual stored time values; no resampling",
        "phase_rule": "continuous_unwrap(raw P radians) then Cphi_rad/(2*pi); no event-count interpretation",
    }
    json_once(EXP / "analysis/n3_n4_raw_qa.json", raw_qa)
    json_once(
        EXP / "analysis/n3_n4_event_timeline.json",
        {
            "schema": "jm2-n3-n4-replay-event-timeline-v1",
            "raw_provenance": raw_qa["raw_cases"],
            "window_ps": [WINDOW_START_PS, WINDOW_END_PS],
            "cases": timelines,
            "spacing_comparison": {name: timelines[name]["spacing_ps"] for name in ("N3_REPLAY", "N4_REPLAY")},
            "timing_semantics": "descriptive joint raw evidence; voltage peaks and terminal maxima are not SFQ event counts",
        },
    )
    json_once(
        EXP / "analysis/n4_post_third_response.json",
        {
            "schema": "jm2-n4-post-third-response-v1",
            "raw_provenance": raw_qa["raw_cases"],
            "analysis": post,
            "classification_boundary": "earliest observed missing-response location is not automatically a root cause",
        },
    )
    json_once(
        EXP / "analysis/n3_n4_recovery_compare.json",
        {
            "schema": "jm2-n3-n4-recovery-state-compare-v1",
            "raw_provenance": raw_qa["raw_cases"],
            "window_ps": [WINDOW_START_PS, WINDOW_END_PS],
            "cases": recovery,
            "offset_semantics": "exact stored samples at +0.5/+1/+2/+3 ps relative to each observed terminal peak-like reference",
            "mechanism_boundary": "state comparison is descriptive and does not prove physical recovery mechanism",
        },
    )
    plot_manifest = make_plot_manifest(traces, cumulative_manifest, cumulative_comparison, cumulative_labels, aligned_records)
    json_once(EXP / "analysis/deep_dive_plot_manifest.json", plot_manifest)
    json_once(
        EXP / "analysis/deep_dive_provenance.json",
        {
            "schema": "jm2-n3-n4-replay-deep-dive-provenance-v1",
            "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, text=True, capture_output=True, check=True).stdout.strip(),
            "raw_provenance": raw_qa,
            "derived_csvs": {
                "cumulative": cumulative_manifest,
                "comparison": cumulative_comparison,
                "event_aligned": aligned_records,
            },
            "solver_invoked": False,
            "visualization_is_descriptive": True,
        },
    )
    write_once(
        EXP / "N3_N4_DEEP_DIVE.md",
        deep_dive_markdown(timelines, post, recovery, raw_qa, plot_manifest),
    )
    print(
        json.dumps(
            {
                "status": raw_qa["status"],
                "raw_unchanged": raw_qa["raw_unchanged"],
                "outputs": [
                    "analysis/n3_n4_event_timeline.json",
                    "analysis/n4_post_third_response.json",
                    "analysis/n3_n4_recovery_compare.json",
                    "analysis/n3_n4_raw_qa.json",
                    "analysis/deep_dive_plot_manifest.json",
                    "analysis/deep_dive_provenance.json",
                    "N3_N4_DEEP_DIVE.md",
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0 if raw_qa["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
