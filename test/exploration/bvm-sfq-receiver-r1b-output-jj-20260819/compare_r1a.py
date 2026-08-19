#!/usr/bin/env python3
"""Independent raw comparison of accepted R1a and loaded R1b runs."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
R1A = ROOT.parent / "bvm-sfq-receiver-r1a-transfer-20260819"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]
TRIG_PHASE = "P(B_TRIG|XTRIG)"
TRIG_VOLTAGE = "V(B_TRIG|XTRIG)"
VSEC = "V(N_SEC|XTRIG)"
ISEC = "I(R_SEC_LOAD|XTRIG)"
SOURCE_KEYS = ["V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "I(R_IN|XTRIG)"]
STORAGE_KEYS = ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: float(value) for key, value in row.items()} for row in reader]


def select(rows, lo, hi):
    return [row for row in rows if lo <= row["time"] * 1e12 <= hi]


def median(rows, key):
    return statistics.median(row[key] for row in rows)


def unwrap(rows, phase_key):
    result = []
    for index, row in enumerate(rows):
        if index == 0:
            result.append(row[phase_key])
            continue
        delta = row[phase_key] - rows[index - 1][phase_key]
        while delta > math.pi:
            delta -= TWO_PI
        while delta < -math.pi:
            delta += TWO_PI
        result.append(result[-1] + delta)
    return result


def area(rows, voltage_key):
    return sum(
        0.5 * (left[voltage_key] + right[voltage_key])
        * (right["time"] - left["time"])
        for left, right in zip(rows, rows[1:])
    ) / PHI0


def largest_segment(rows, phase_key, voltage_key):
    part = select(rows, 94.0, 170.0)
    phase = unwrap(part, phase_key)
    deltas = [right - left for left, right in zip(phase, phase[1:])]
    start = 0
    direction = None
    segments = []

    def append(end, sign):
        if end <= start or sign is None:
            return
        delta = phase[end] - phase[start]
        segment_rows = part[start : end + 1]
        area_turns = area(segment_rows, voltage_key)
        segments.append(
            {
                "start_time_ps": part[start]["time"] * 1e12,
                "end_time_ps": part[end]["time"] * 1e12,
                "direction": "increasing" if sign > 0 else "decreasing",
                "phase_delta_rad": delta,
                "phase_delta_turns": delta / TWO_PI,
                "phase_abs_turns": abs(delta / TWO_PI),
                "same_junction_voltage_area_turns": area_turns,
                "area_minus_phase_turns": area_turns - delta / TWO_PI,
                "complete_2pi": abs(delta / TWO_PI) >= 1.0,
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
    return max(segments, key=lambda item: item["phase_abs_turns"], default=None), segments


def summarize(path):
    rows = load(path)
    largest, segments = largest_segment(rows, TRIG_PHASE, TRIG_VOLTAGE)
    complete = [
        item
        for item in segments
        if item["complete_2pi"]
        and item["start_time_ps"] <= 130.0
        and abs(item["area_minus_phase_turns"]) <= 0.05
    ]
    pre = select(rows, 80.0, 90.0)
    activity = select(rows, 94.0, 130.0)
    post = select(rows, 140.0, 150.0)
    return {
        "sha256": sha256(path),
        "btrig_largest": largest,
        "btrig_complete": bool(complete),
        "source_activity_abs_peak": {
            key: max((abs(row[key]) for row in activity), default=0.0)
            for key in SOURCE_KEYS
        },
        "secondary_amplitude": {
            key: max(
                (
                    abs(row[key] - median(pre, key))
                    for row in activity
                ),
                default=0.0,
            )
            for key in [VSEC, ISEC]
        },
        "storage": {
            key: {
                "pre_median_rad": median(pre, key),
                "post_median_rad": median(post, key),
                "post_minus_pre_turns": (
                    median(post, key) - median(pre, key)
                )
                / TWO_PI,
            }
            for key in STORAGE_KEYS
        },
    }


def main():
    comparison = {}
    for case_id in CASES:
        baseline = summarize(
            R1A / "raw" / "l020-k080" / case_id / "run-01.csv"
        )
        loaded = summarize(
            ROOT / "raw" / "l010-b07-rd100-loop" / case_id / "run-01.csv"
        )
        comparison[case_id] = {
            "r1a_baseline": baseline,
            "r1b_loaded": loaded,
            "delta": {
                "btrig_phase_turns": (
                    loaded["btrig_largest"]["phase_abs_turns"]
                    - baseline["btrig_largest"]["phase_abs_turns"]
                ),
                "input_current_abs_peak": (
                    loaded["source_activity_abs_peak"]["I(R_IN|XTRIG)"]
                    - baseline["source_activity_abs_peak"]["I(R_IN|XTRIG)"]
                ),
                "sl_abs_peak": (
                    loaded["source_activity_abs_peak"]["V(SL1)"]
                    - baseline["source_activity_abs_peak"]["V(SL1)"]
                ),
                "n6_abs_peak": (
                    loaded["source_activity_abs_peak"]["V(N6|XBVM1)"]
                    - baseline["source_activity_abs_peak"]["V(N6|XBVM1)"]
                ),
            },
        }
    result = {
        "document_type": "r1a_r1b_raw_comparison",
        "method": (
            "independent raw CSV read using B_TRIG same-segment phase/area, "
            "source activity, secondary PRE-subtracted amplitude, and JM1/JM2"
        ),
        "r1a_baseline": "test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/raw/l020-k080",
        "r1b_loaded": "raw/l010-b07-rd100-loop",
        "cases": comparison,
    }
    out = ROOT / "analysis" / "r1a-comparison.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    for case_id, item in comparison.items():
        print(
            f"{case_id}: R1a_BTRIG={item['r1a_baseline']['btrig_largest']['phase_abs_turns']:.9g} "
            f"turns, R1b_BTRIG={item['r1b_loaded']['btrig_largest']['phase_abs_turns']:.9g} "
            f"turns, R1b_complete={item['r1b_loaded']['btrig_complete']}"
        )


if __name__ == "__main__":
    main()
