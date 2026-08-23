#!/usr/bin/env python3
"""Evidence analysis for R13-A waveform replay and bounded conditioning.

This analysis deliberately does not use the legacy fast-event counter.  A
candidate B3 event is reported only as a phase/voltage-area diagnostic; the
final report still requires continuous same-JJ evidence and bounded
post-event behavior before calling it a complete local event.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


PHI0 = 2.067833848e-15
ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
RAW = ROOT / "raw"
ANALYSIS = ROOT / "analysis"
WINDOWS = {
    "pre": (85.0, 94.0),
    "activity": (94.0, 130.0),
    "post": (130.0, 165.0),
}
TRANSFORMS = ("raw-replay", "c1-rectify", "c2-hold20", "c3-rectify-hold20")
CASES = (
    "read1",
    "read0",
    "logical1-read0-control",
    "logical0-read0-control",
)
PHASES = ("P(B1|XREPLAY)", "P(B2|XREPLAY)", "P(B3|XREPLAY)")
CURRENT_COLUMNS = (
    "I(B1|XREPLAY)",
    "I(B2|XREPLAY)",
    "I(B3|XREPLAY)",
    "I(L1|XREPLAY)",
    "I(L2|XREPLAY)",
    "I(L3|XREPLAY)",
    "I(L4|XREPLAY)",
    "I(L5|XREPLAY)",
    "I(L6|XREPLAY)",
    "I(LB1|XREPLAY)",
    "I(LB2|XREPLAY)",
    "I(IB1|XREPLAY)",
    "I(IB2|XREPLAY)",
    "I(RB1|XREPLAY)",
    "I(RB2|XREPLAY)",
    "I(RB3|XREPLAY)",
)
SIGNALS = ("V(Q_REPLAY)", "I(R_LOAD)")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    fields = list(rows[0].keys())
    time_ps = np.asarray([float(row["time"]) * 1e12 for row in rows])
    arrays = {
        field: np.asarray([float(row[field]) for row in rows])
        for field in fields
        if field != "time"
    }
    if not np.all(np.isfinite(time_ps)) or not np.all(np.diff(time_ps) > 0):
        raise ValueError(f"invalid time axis: {path}")
    if not all(np.all(np.isfinite(values)) for values in arrays.values()):
        raise ValueError(f"non-finite values: {path}")
    return time_ps, arrays


def mask(time_ps: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return (time_ps >= bounds[0]) & (time_ps < bounds[1])


def turns(delta_rad: float) -> float:
    return float(delta_rad / (2.0 * math.pi))


def integrate_voltage(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    return float(np.trapezoid(voltage, time_ps * 1e-12) / PHI0)


def p2p(values: np.ndarray) -> float:
    return float(np.max(values) - np.min(values))


def rms(values: np.ndarray) -> float:
    return float(np.sqrt(np.mean(values * values)))


def scalar_window(time_ps: np.ndarray, values: np.ndarray, bounds: tuple[float, float]) -> dict[str, float]:
    selected = values[mask(time_ps, bounds)]
    return {
        "median": float(np.median(selected)),
        "min": float(np.min(selected)),
        "max": float(np.max(selected)),
        "p2p": p2p(selected),
        "rms": rms(selected),
    }


def largest_monotonic_segment(
    time_ps: np.ndarray,
    phase: np.ndarray,
    voltage: np.ndarray,
    bounds: tuple[float, float],
) -> dict[str, object]:
    """Find the largest sign-consistent phase segment in one window.

    This is a descriptive segment finder, not an event counter.  The caller
    must inspect the same-segment area and post-event behavior.
    """
    indices = np.flatnonzero(mask(time_ps, bounds))
    if len(indices) < 2:
        return {
            "direction": "none",
            "start_ps": None,
            "end_ps": None,
            "turns": 0.0,
            "voltage_area_turns": 0.0,
            "phase_area_residual_turns": 0.0,
        }
    delta = np.diff(phase[indices])
    best: tuple[float, str, int, int, float] | None = None
    for sign, direction in ((1.0, "positive"), (-1.0, "negative")):
        good = sign * delta >= 0.0
        cursor = 0
        while cursor < len(good):
            while cursor < len(good) and not good[cursor]:
                cursor += 1
            if cursor >= len(good):
                break
            end_cursor = cursor
            while end_cursor + 1 < len(good) and good[end_cursor + 1]:
                end_cursor += 1
            start = indices[cursor]
            end = indices[end_cursor + 1]
            phase_delta = float(phase[end] - phase[start])
            magnitude = sign * phase_delta
            candidate = (magnitude, direction, start, end, phase_delta)
            if best is None or candidate[0] > best[0]:
                best = candidate
            cursor = end_cursor + 1
    if best is None:
        return {
            "direction": "none",
            "start_ps": None,
            "end_ps": None,
            "turns": 0.0,
            "voltage_area_turns": 0.0,
            "phase_area_residual_turns": 0.0,
        }
    _, direction, start, end, phase_delta = best
    area = integrate_voltage(time_ps[start : end + 1], voltage[start : end + 1])
    return {
        "direction": direction,
        "start_ps": float(time_ps[start]),
        "end_ps": float(time_ps[end]),
        "turns": turns(phase_delta),
        "voltage_area_turns": area,
        "phase_area_residual_turns": float(area - turns(phase_delta)),
    }


def phase_metrics(
    time_ps: np.ndarray,
    arrays: dict[str, np.ndarray],
    phase_column: str,
) -> dict[str, object]:
    phase = np.unwrap(arrays[phase_column])
    voltage_column = phase_column.replace("P(", "V(", 1)
    activity = mask(time_ps, WINDOWS["activity"])
    pre = mask(time_ps, WINDOWS["pre"])
    post = mask(time_ps, WINDOWS["post"])
    indices = np.flatnonzero(activity)
    segment = largest_monotonic_segment(
        time_ps, phase, arrays[voltage_column], WINDOWS["activity"]
    )
    return {
        "pre_phase_rad": float(np.median(phase[pre])),
        "post_phase_rad": float(np.median(phase[post])),
        "pre_to_post_turns": turns(float(np.median(phase[post]) - np.median(phase[pre]))),
        "activity_range_turns": turns(float(np.max(phase[activity]) - np.min(phase[activity]))),
        "activity_window_phase_turns": turns(float(phase[indices[-1]] - phase[indices[0]])),
        "activity_window_v_area_turns": integrate_voltage(
            time_ps[indices[0] : indices[-1] + 1],
            arrays[voltage_column][indices[0] : indices[-1] + 1],
        ),
        "post_phase_p2p_turns": turns(p2p(phase[post])),
        "post_voltage_rms_V": rms(arrays[voltage_column][post]),
        "largest_monotonic_segment": segment,
    }


def analyze_case(transform: str, case: str) -> dict[str, object]:
    raw_path = RAW / transform / case / "run-01.csv"
    time_ps, arrays = load_csv(raw_path)
    required = []
    for phase_column in PHASES:
        required.extend((phase_column, phase_column.replace("P(", "V(", 1)))
    required.extend(CURRENT_COLUMNS)
    required.extend(SIGNALS)
    missing = sorted(set(column for column in required if column not in arrays))
    if missing:
        raise ValueError(f"{transform}/{case}: missing columns {missing}")
    phase = {
        column: phase_metrics(time_ps, arrays, column) for column in PHASES
    }
    current_windows = {
        column: {
            label: scalar_window(time_ps, arrays[column], bounds)
            for label, bounds in WINDOWS.items()
        }
        for column in CURRENT_COLUMNS
    }
    signal_windows = {
        column: {
            label: scalar_window(time_ps, arrays[column], bounds)
            for label, bounds in WINDOWS.items()
        }
        for column in SIGNALS
    }
    return {
        "raw_path": str(raw_path.relative_to(ROOT)),
        "raw_sha256": sha256(raw_path),
        "rows": int(len(time_ps)),
        "time_start_ps": float(time_ps[0]),
        "time_end_ps": float(time_ps[-1]),
        "dt_ps_median": float(np.median(np.diff(time_ps))),
        "windows_ps": WINDOWS,
        "phase": phase,
        "currents": current_windows,
        "signals": signal_windows,
    }


def fmt(value: object, digits: int = 8) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return "n/a"
        return f"{float(value):.{digits}g}"
    return str(value)


def main() -> None:
    results: dict[str, dict[str, dict[str, object]]] = {}
    for transform in TRANSFORMS:
        available = {
            case: analyze_case(transform, case)
            for case in CASES
            if (RAW / transform / case / "run-01.csv").exists()
        }
        if available:
            results[transform] = available
    b3_summary = []
    for transform, transform_results in results.items():
        for case, case_result in transform_results.items():
            metrics = case_result["phase"]["P(B3|XREPLAY)"]
            segment = metrics["largest_monotonic_segment"]
            b3_summary.append(
                {
                    "transform": transform,
                    "case": case,
                    "activity_range_turns": metrics["activity_range_turns"],
                    "largest_segment_turns": segment["turns"],
                    "largest_segment_area_turns": segment["voltage_area_turns"],
                    "largest_segment_area_residual_turns": segment[
                        "phase_area_residual_turns"
                    ],
                    "post_p2p_turns": metrics["post_phase_p2p_turns"],
                    "segment_start_ps": segment["start_ps"],
                    "segment_end_ps": segment["end_ps"],
                }
            )
    payload = {
        "experiment": "R13-A",
        "source_head": "ebe24984771255f002499ec9bef35e9953c87d28",
        "phi0_Wb": PHI0,
        "windows_ps": WINDOWS,
        "transforms": TRANSFORMS,
        "cases": CASES,
        "results": results,
        "b3_summary": b3_summary,
    }
    (ANALYSIS / "r13a-metrics.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n"
    )
    with (ANALYSIS / "r13a-b3-summary.csv").open("w", newline="") as handle:
        fields = list(b3_summary[0].keys())
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(b3_summary)
    print("transform,case,b3_activity_range_turns,b3_largest_segment_turns,b3_segment_area_turns,post_p2p_turns")
    for row in b3_summary:
        print(
            f"{row['transform']},{row['case']},"
            f"{fmt(row['activity_range_turns'])},"
            f"{fmt(row['largest_segment_turns'])},"
            f"{fmt(row['largest_segment_area_turns'])},"
            f"{fmt(row['post_p2p_turns'])}"
        )
    print("wrote analysis/r13a-metrics.json and analysis/r13a-b3-summary.csv")


if __name__ == "__main__":
    main()
