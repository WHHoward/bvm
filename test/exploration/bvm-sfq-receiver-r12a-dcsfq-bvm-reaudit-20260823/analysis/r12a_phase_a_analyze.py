#!/usr/bin/env python3
"""Phase-A evidence extraction for the R12-A DCSFQ_BVM re-audit.

This script deliberately does not call scripts/sfq_metrics.py.  It reports
same-JJ continuous phase and same-segment voltage-area quantities, with the
zero-input run used only as a matched bias-startup reference.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT_JSON = ROOT / "analysis" / "phase-a-metrics.json"
OUT_TABLE = ROOT / "analysis" / "phase-a-summary.csv"

PHI0 = 2.067833848e-15
CASES = {
    "phase-a-zero": 0.0,
    "phase-a-bump-68u4": 68.4,
    "phase-a-bump-300u": 300.0,
}
JJS = ("B1", "B2", "B3")
WINDOWS = {
    "startup": (0.0, 7.0),
    "pre_input": (7.0, 10.0),
    "input_activity": (10.0, 45.0),
    "post": (60.0, 180.0),
}
CURRENT_NAMES = (
    "I(L1|XDCSFQ)",
    "I(L2|XDCSFQ)",
    "I(L3|XDCSFQ)",
    "I(L4|XDCSFQ)",
    "I(L5|XDCSFQ)",
    "I(L6|XDCSFQ)",
    "I(LB1|XDCSFQ)",
    "I(LB2|XDCSFQ)",
    "I(IB1|XDCSFQ)",
    "I(IB2|XDCSFQ)",
    "I(RB1|XDCSFQ)",
    "I(RB2|XDCSFQ)",
    "I(RB3|XDCSFQ)",
)


def load_case(name: str) -> dict[str, np.ndarray]:
    path = RAW / name / "run-01.csv"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    columns = rows[0].keys()
    arrays = {
        column: np.asarray([float(row[column]) for row in rows], dtype=float)
        for column in columns
    }
    time_s = arrays["time"]
    if not np.all(np.isfinite(time_s)) or np.any(np.diff(time_s) <= 0):
        raise ValueError(f"invalid time axis: {path}")
    arrays["time_s"] = time_s
    arrays["time_ps"] = time_s * 1e12
    return arrays


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def mask_for(time_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    lo, hi = window
    return (time_ps >= lo) & (time_ps < hi)


def median(values: np.ndarray) -> float:
    return float(np.median(values))


def p2p(values: np.ndarray) -> float:
    return float(np.max(values) - np.min(values))


def turns(delta_rad: float) -> float:
    return float(delta_rad / (2.0 * math.pi))


def voltage_area(time_s: np.ndarray, voltage: np.ndarray) -> float:
    return float(np.trapezoid(voltage, time_s) / PHI0)


def phase_area_residual(delta_rad: float, area_turns: float) -> float:
    return float(turns(delta_rad) - area_turns)


def monotonic_segments(
    time_ps: np.ndarray, phase_rad: np.ndarray, voltage: np.ndarray
) -> list[dict[str, float]]:
    """Return descriptive sign-consistent phase segments.

    This is not an event counter.  The result is a trace-audit aid: every
    candidate must still be checked against the same-JJ area and post-state.
    Exact zero increments are carried with the preceding sign where possible.
    """

    dphase = np.diff(phase_rad)
    signs = np.sign(dphase)
    nonzero = np.flatnonzero(signs)
    if nonzero.size == 0:
        return []
    for index in range(len(signs)):
        if signs[index] == 0:
            left = nonzero[nonzero < index]
            right = nonzero[nonzero > index]
            if left.size:
                signs[index] = signs[left[-1]]
            elif right.size:
                signs[index] = signs[right[0]]

    starts = [0]
    for index in range(1, len(signs)):
        if signs[index] != signs[index - 1]:
            starts.append(index)
    ends = starts[1:] + [len(signs)]
    result: list[dict[str, float]] = []
    for start, end in zip(starts, ends):
        # The segment includes phase samples [start, end].
        if end <= start:
            continue
        delta = float(phase_rad[end] - phase_rad[start])
        area = voltage_area(
            time_ps[start : end + 1] * 1e-12,
            voltage[start : end + 1],
        )
        result.append(
            {
                "start_ps": float(time_ps[start]),
                "end_ps": float(time_ps[end]),
                "direction": int(signs[start]),
                "turns": turns(delta),
                "abs_turns": abs(turns(delta)),
                "voltage_area_turns": area,
                "phase_area_residual_turns": phase_area_residual(delta, area),
            }
        )
    return result


def phase_metrics(
    time_s: np.ndarray,
    time_ps: np.ndarray,
    phase: np.ndarray,
    voltage: np.ndarray,
    zero_phase: np.ndarray | None,
    zero_voltage: np.ndarray | None,
) -> dict[str, object]:
    unwrapped = np.unwrap(phase)
    zero_unwrapped = np.unwrap(zero_phase) if zero_phase is not None else None
    differential = unwrapped - zero_unwrapped if zero_unwrapped is not None else unwrapped
    differential_voltage = (
        voltage - zero_voltage if zero_voltage is not None else voltage
    )

    windows: dict[str, object] = {}
    for label, bounds in WINDOWS.items():
        mask = mask_for(time_ps, bounds)
        local = unwrapped[mask]
        diff_local = differential[mask]
        windows[label] = {
            "absolute_start_to_end_turns": turns(local[-1] - local[0]),
            "absolute_range_turns": turns(np.max(local) - np.min(local)),
            "absolute_p2p_post_or_window_turns": turns(np.max(local) - np.min(local)),
            "absolute_voltage_area_turns": voltage_area(time_s[mask], voltage[mask]),
            "differential_start_to_end_turns": turns(diff_local[-1] - diff_local[0]),
            "differential_range_turns": turns(np.max(diff_local) - np.min(diff_local)),
            "differential_p2p_turns": turns(np.max(diff_local) - np.min(diff_local)),
            "differential_voltage_area_turns": voltage_area(
                time_s[mask], differential_voltage[mask]
            ),
        }

    activity = mask_for(time_ps, WINDOWS["input_activity"])
    segments = monotonic_segments(
        time_ps[activity], differential[activity], differential_voltage[activity]
    )
    segments.sort(key=lambda item: item["abs_turns"], reverse=True)
    windows["input_activity"]["monotonic_segments_descending"] = segments
    windows["input_activity"]["largest_monotonic_segment"] = segments[0] if segments else None
    windows["input_activity"]["segments_abs_ge_0_8_turn"] = [
        item for item in segments if item["abs_turns"] >= 0.8
    ]
    return {
        "windows": windows,
        "absolute_initial_phase_rad": float(unwrapped[0]),
        "absolute_final_phase_rad": float(unwrapped[-1]),
        "absolute_total_turns": turns(unwrapped[-1] - unwrapped[0]),
        "differential_initial_phase_rad": float(differential[0]),
        "differential_final_phase_rad": float(differential[-1]),
        "differential_total_turns": turns(differential[-1] - differential[0]),
        "post_phase_p2p_turns": windows["post"]["differential_p2p_turns"],
    }


def current_metrics(time_ps: np.ndarray, data: dict[str, np.ndarray]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name in CURRENT_NAMES:
        if name not in data:
            continue
        values = data[name]
        result[name] = {}
        for label, bounds in WINDOWS.items():
            mask = mask_for(time_ps, bounds)
            result[name][label] = {
                "median_uA": median(values[mask]) * 1e6,
                "min_uA": float(np.min(values[mask]) * 1e6),
                "max_uA": float(np.max(values[mask]) * 1e6),
                "p2p_uA": p2p(values[mask]) * 1e6,
            }
    return result


def main() -> None:
    data = {name: load_case(name) for name in CASES}
    reference = data["phase-a-zero"]
    all_metrics: dict[str, object] = {
        "analysis": {
            "script": str(Path(__file__).relative_to(ROOT)),
            "phi0_Wb": PHI0,
            "windows_ps": WINDOWS,
            "reference_case": "phase-a-zero",
            "note": "Differential traces subtract the matched 0uA bias-startup run; they are not independent event counts.",
        },
        "cases": {},
    }

    table_rows: list[dict[str, object]] = []
    for name, input_uA in CASES.items():
        case = data[name]
        case_result: dict[str, object] = {
            "input_uA": input_uA,
            "raw_path": str((RAW / name / "run-01.csv").relative_to(ROOT)),
            "raw_sha256": sha256(RAW / name / "run-01.csv"),
            "rows": int(len(case["time_s"])),
            "time_start_ps": float(case["time_ps"][0]),
            "time_end_ps": float(case["time_ps"][-1]),
            "dt_ps_median": float(np.median(np.diff(case["time_ps"]))),
            "junctions": {},
            "currents": current_metrics(case["time_ps"], case),
            "scalar_ranges": {},
        }
        for jj in JJS:
            pkey = f"P({jj}|XDCSFQ)"
            vkey = f"V({jj}|XDCSFQ)"
            metrics = phase_metrics(
                case["time_s"],
                case["time_ps"],
                case[pkey],
                case[vkey],
                reference[pkey],
                reference[vkey],
            )
            case_result["junctions"][jj] = metrics
            activity = metrics["windows"]["input_activity"]
            largest = activity["largest_monotonic_segment"] or {}
            table_rows.append(
                {
                    "case": name,
                    "input_uA": input_uA,
                    "junction": jj,
                    "differential_activity_range_turns": activity["differential_range_turns"],
                    "differential_net_input_turns": activity["differential_start_to_end_turns"],
                    "largest_segment_turns": largest.get("turns", float("nan")),
                    "largest_segment_abs_turns": largest.get("abs_turns", float("nan")),
                    "largest_segment_voltage_area_turns": largest.get(
                        "voltage_area_turns", float("nan")
                    ),
                    "largest_segment_residual_turns": largest.get(
                        "phase_area_residual_turns", float("nan")
                    ),
                    "post_differential_p2p_turns": metrics["post_phase_p2p_turns"],
                }
            )
        for key in ("V(IN1)", "V(OUT1)", "I(I_IN)", "I(R_LOAD)"):
            if key in case:
                case_result["scalar_ranges"][key] = {
                    label: {
                        "min": float(np.min(case[key][mask_for(case["time_ps"], bounds)])),
                        "max": float(np.max(case[key][mask_for(case["time_ps"], bounds)])),
                        "p2p": p2p(case[key][mask_for(case["time_ps"], bounds)]),
                    }
                    for label, bounds in WINDOWS.items()
                }
        all_metrics["cases"][name] = case_result

    OUT_JSON.write_text(json.dumps(all_metrics, indent=2, sort_keys=True) + "\n")
    with OUT_TABLE.open("w", newline="") as handle:
        fields = list(table_rows[0].keys())
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(table_rows)

    print("case,input_uA,junction,activity_range_turns,net_input_turns,largest_segment_turns,largest_segment_area_turns,post_p2p_turns")
    for row in table_rows:
        print(
            f"{row['case']},{row['input_uA']:.1f},{row['junction']},"
            f"{row['differential_activity_range_turns']:.9g},"
            f"{row['differential_net_input_turns']:.9g},"
            f"{row['largest_segment_turns']:.9g},"
            f"{row['largest_segment_voltage_area_turns']:.9g},"
            f"{row['post_differential_p2p_turns']:.9g}"
        )


if __name__ == "__main__":
    main()
