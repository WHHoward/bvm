#!/usr/bin/env python3
"""Independent mechanical recheck of the strict summary against raw CSVs.

This intentionally does not import ``reclassify_strict_events.py``.  It checks
the selected BJL2 segment and same-segment area from the raw files again, then
compares only the numeric fields needed for the audit.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import numpy as np


HERE = Path(__file__).resolve()
TARGET = HERE.parents[1]
REPO = TARGET.parents[2]
MATRIX = REPO / "test/exploration/bvm-load-qb-matrix-v1-20260901"
RAW = MATRIX / "raw"
SUMMARY = TARGET / "analysis/strict-event-summary.csv"
OUT = TARGET / "analysis/independent-raw-recheck.json"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
ACTIVITY = (94.0, 130.0)
WIDTHS = (9, 13)
LOADS = {"12x320": 12, "8x500": 8}
ROLES = ("logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control")
FIXTURES = ("replay", "physical")


def read(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader if row]
    # BJL2 columns are unique in the matrix CSVs; first occurrence is used for
    # the time axis if a future JoSIM print adds a duplicate unrelated field.
    index = {name: pos for pos, name in enumerate(header)}
    return {
        name: np.asarray([float(row[pos]) for row in rows], dtype=float)
        for name, pos in index.items()
    }


def trapezoid(time_s: np.ndarray, values: np.ndarray) -> float:
    return float(np.trapezoid(values, time_s) if hasattr(np, "trapezoid") else np.trapz(values, time_s))


def runs(values: np.ndarray) -> list[tuple[int, int]]:
    if values.size < 2:
        return []
    signs = np.sign(np.diff(values))
    nonzero = np.flatnonzero(signs)
    if nonzero.size == 0:
        return []
    starts = [0]
    direction = int(signs[nonzero[0]])
    for position in nonzero[1:]:
        next_direction = int(signs[position])
        if next_direction != direction:
            starts.append(int(position))
            direction = next_direction
    ends = starts[1:] + [values.size - 1]
    return [(start, end) for start, end in zip(starts, ends) if end > start]


def raw_largest(path: Path) -> dict[str, float | int | None]:
    data = read(path)
    time_s = data["time"]
    phase = np.unwrap(data["P(BJL2|XBQ)"])
    voltage = data["V(BJL2|XBQ)"]
    mask = (time_s >= ACTIVITY[0] * 1e-12) & (time_s < ACTIVITY[1] * 1e-12)
    selected = np.flatnonzero(mask)
    records = []
    for start, end in runs(phase[selected]):
        indices = selected[start : end + 1]
        delta = float((phase[indices[-1]] - phase[indices[0]]) / TWO_PI)
        area = float(trapezoid(time_s[indices], voltage[indices]) / PHI0)
        records.append({
            "delta": delta,
            "area": area,
            "start_ps": float(time_s[indices[0]] * 1e12),
            "end_ps": float(time_s[indices[-1]] * 1e12),
        })
    largest = max(records, key=lambda item: abs(item["delta"])) if records else None
    return largest or {"delta": None, "area": None, "start_ps": None, "end_ps": None}


def main() -> None:
    with SUMMARY.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    indexed = {(row["fixture"], int(row["width_ps"]), row["jsl_load"], row["role"]): row for row in rows}
    checks = []
    max_errors = {"delta_turns": 0.0, "area_turns": 0.0, "start_ps": 0.0, "end_ps": 0.0}
    for fixture in FIXTURES:
        for width in WIDTHS:
            for load in LOADS:
                for role in ROLES:
                    key = (fixture, width, load, role)
                    path = RAW / fixture / f"{width}ps" / load / role / "run-01.csv"
                    raw = raw_largest(path)
                    row = indexed[key]
                    observed = {
                        "delta_turns": float(row["largest_monotonic_segment_turns"]),
                        "area_turns": float(row["same_segment_voltage_area_turns"]),
                        "start_ps": float(row["largest_monotonic_segment_start_ps"]),
                        "end_ps": float(row["largest_monotonic_segment_end_ps"]),
                    }
                    raw_for_compare = {
                        "delta_turns": raw["delta"],
                        "area_turns": raw["area"],
                        "start_ps": raw["start_ps"],
                        "end_ps": raw["end_ps"],
                    }
                    errors = {name: abs(float(raw_for_compare[name]) - value) for name, value in observed.items()}
                    for name, error in errors.items():
                        max_errors[name] = max(max_errors[name], error)
                    checks.append({
                        "fixture": fixture,
                        "width_ps": width,
                        "jsl_load": load,
                        "role": role,
                        "status": "PASS" if max(errors.values()) <= 1e-10 else "FAIL",
                        "raw_recomputed": raw_for_compare,
                        "summary_observed": observed,
                        "absolute_errors": errors,
                    })
    anchors = [item for item in checks if item["role"] == "logical1_read" and item["jsl_load"] == "12x320"]
    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    OUT.write_text(json.dumps({
        "document_type": "independent_raw_recheck",
        "status": status,
        "method": "independent csv reader + numpy.unwrap + sign-run segmentation + actual-time trapezoid",
        "input": "current matrix raw only",
        "case_count": len(checks),
        "max_absolute_errors": max_errors,
        "anchors": anchors,
        "cases": checks,
    }, indent=2) + "\n", encoding="utf-8")
    print(status)
    print(json.dumps({"case_count": len(checks), "max_absolute_errors": max_errors}, sort_keys=True))


if __name__ == "__main__":
    main()
