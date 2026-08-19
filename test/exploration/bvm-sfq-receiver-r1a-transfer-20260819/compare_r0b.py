#!/usr/bin/env python3
"""Independent R0b-versus-R1a comparison from both raw CSV sets."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
R0B = ROOT.parent / "bvm-sfq-receiver-r0b-20260819"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]
PHASE = "P(B_TRIG|XTRIG)"
VOLTAGE = "V(B_TRIG|XTRIG)"
ACTIVITY = (94.0, 130.0)
TRIGGER = (94.0, 170.0)
PRE = (80.0, 90.0)
STORAGE_POST = (140.0, 150.0)


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return [{key: float(value) for key, value in row.items()} for row in reader]


def select(rows, interval):
    return [row for row in rows if interval[0] <= row["time"] * 1e12 <= interval[1]]


def median(rows, key):
    return statistics.median(row[key] for row in rows)


def peak(rows, key):
    if not rows:
        return None
    return max(abs(row[key]) for row in rows)


def unwrap(rows):
    result = []
    for index, row in enumerate(rows):
        if index == 0:
            result.append(row[PHASE])
            continue
        delta = row[PHASE] - rows[index - 1][PHASE]
        while delta > math.pi:
            delta -= TWO_PI
        while delta < -math.pi:
            delta += TWO_PI
        result.append(result[-1] + delta)
    return result


def voltage_area(rows, start, end):
    return sum(
        0.5 * (left[VOLTAGE] + right[VOLTAGE]) * (right["time"] - left["time"])
        for left, right in zip(rows[start : end + 1], rows[start + 1 : end + 1])
    ) / PHI0


def phase_summary(rows):
    part = select(rows, TRIGGER)
    if len(part) < 2:
        return {"largest": None, "complete": [], "complete_count": 0}
    unwrapped = unwrap(part)
    deltas = [right - left for left, right in zip(unwrapped, unwrapped[1:])]
    start = 0
    direction = None
    segments = []

    def append(end, sign):
        if end <= start or sign is None:
            return
        delta_rad = unwrapped[end] - unwrapped[start]
        delta_turns = delta_rad / TWO_PI
        area_turns = voltage_area(part, start, end)
        segments.append(
            {
                "start_time_ps": part[start]["time"] * 1e12,
                "end_time_ps": part[end]["time"] * 1e12,
                "direction": "increasing" if sign > 0 else "decreasing",
                "phase_delta_rad": delta_rad,
                "phase_delta_turns": delta_turns,
                "phase_abs_turns": abs(delta_turns),
                "same_junction_voltage_area_turns": area_turns,
                "area_minus_phase_turns": area_turns - delta_turns,
                "complete_2pi": abs(delta_turns) >= 1.0,
            }
        )

    for index, delta in enumerate(deltas):
        sign = 1 if delta > 0 else -1 if delta < 0 else 0
        if sign == 0:
            continue
        if direction is None:
            direction = sign
        elif sign != direction:
            append(index, direction)
            start = index
            direction = sign
    append(len(part) - 1, direction)
    complete = [segment for segment in segments if segment["complete_2pi"] and segment["start_time_ps"] <= ACTIVITY[1]]
    return {
        "trajectory_raw_start_rad": part[0][PHASE],
        "trajectory_raw_end_rad": part[-1][PHASE],
        "trajectory_unwrapped_min_rad": min(unwrapped),
        "trajectory_unwrapped_max_rad": max(unwrapped),
        "trajectory_unwrapped_range_turns": (max(unwrapped) - min(unwrapped)) / TWO_PI,
        "segments": segments,
        "largest": max(segments, key=lambda item: item["phase_abs_turns"], default=None),
        "complete": complete,
        "complete_count": len(complete),
    }


def case_summary(path):
    rows = load(path)
    return {
        "path": str(path),
        "sha256": sha256(path),
        "phase": phase_summary(rows),
        "source_activity": {
            key: peak(select(rows, ACTIVITY), key)
            for key in ["V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "I(R_IN|XTRIG)"]
        },
        "storage": {
            key: {
                "pre_median_rad": median(select(rows, PRE), key),
                "post_median_rad": median(select(rows, STORAGE_POST), key),
                "post_minus_pre_turns": (median(select(rows, STORAGE_POST), key) - median(select(rows, PRE), key)) / TWO_PI,
            }
            for key in ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"]
        },
    }


def main():
    comparison = {}
    for case_id in CASES:
        baseline = case_summary(R0B / "raw" / "a050-b15" / case_id / "run-01.csv")
        pickup = case_summary(ROOT / "raw" / "l020-k080" / case_id / "run-01.csv")
        comparison[case_id] = {
            "baseline_r0b": baseline,
            "r1a_series_pickup": pickup,
            "delta": {
                "largest_trigger_phase_turns": pickup["phase"]["largest"]["phase_abs_turns"] - baseline["phase"]["largest"]["phase_abs_turns"],
                "sl_abs_peak": pickup["source_activity"]["V(SL1)"] - baseline["source_activity"]["V(SL1)"],
                "n6_abs_peak": pickup["source_activity"]["V(N6|XBVM1)"] - baseline["source_activity"]["V(N6|XBVM1)"],
                "input_current_abs_peak": pickup["source_activity"]["I(R_IN|XTRIG)"] - baseline["source_activity"]["I(R_IN|XTRIG)"],
            },
        }
    result = {
        "document_type": "r0b_r1a_raw_comparison",
        "method": "independent raw CSV read using the same B_TRIG phase/V endpoints, actual CSV time, windows, and storage probes",
        "baseline": "test/exploration/bvm-sfq-receiver-r0b-20260819/raw/a050-b15",
        "pickup": "raw/l020-k080",
        "cases": comparison,
    }
    out = ROOT / "analysis" / "r0b-comparison.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    for case_id, item in comparison.items():
        b = item["baseline_r0b"]["phase"]["largest"]["phase_abs_turns"]
        p = item["r1a_series_pickup"]["phase"]["largest"]["phase_abs_turns"]
        print(f"{case_id}: R0b_trigger={b:.9g} turns, R1a_trigger={p:.9g} turns, R1a_complete={item['r1a_series_pickup']['phase']['complete_count']}")


if __name__ == "__main__":
    main()
