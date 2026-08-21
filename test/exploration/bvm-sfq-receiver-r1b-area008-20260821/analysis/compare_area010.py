#!/usr/bin/env python3
"""Independent raw comparison of AREA=.08 against accepted AREA=.10 R1b."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT.parent / "bvm-sfq-receiver-r1b-differential-output-20260821"
NEW_POINT = "diff-a008-b07-r100-series-return"
OLD_POINT = "diff-a010-b07-r100-series-return"
RUN_ID = "run-01"
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
TRIG_P = "P(B_TRIG|XTRIG)"
TRIG_V = "V(B_TRIG|XTRIG)"
OUT_P = "P(B_OUT|XTRIG)"
OUT_V = "V(B_OUT|XTRIG)"
VSEC = "V(N_SEC|XTRIG)"
ISEC = "I(R_SEC_LOAD|XTRIG)"
IBOUT = "I(B_OUT|XTRIG)"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(path: Path):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: float(value) for key, value in row.items()} for row in reader]


def select(rows, lo, hi):
    return [row for row in rows if lo <= row["time"] * 1e12 <= hi]


def median(rows, key):
    return statistics.median(row[key] for row in rows)


def extrema(rows, key):
    low = min(rows, key=lambda row: row[key])
    high = max(rows, key=lambda row: row[key])
    absolute = max(rows, key=lambda row: abs(row[key]))
    return {
        "min": low[key],
        "min_time_ps": low["time"] * 1e12,
        "max": high[key],
        "max_time_ps": high["time"] * 1e12,
        "abs_peak": absolute[key],
        "abs_peak_time_ps": absolute["time"] * 1e12,
        "median": median(rows, key),
    }


def unwrap(rows, key):
    values = []
    for index, row in enumerate(rows):
        if index == 0:
            values.append(row[key])
            continue
        delta = row[key] - rows[index - 1][key]
        while delta > math.pi:
            delta -= TWO_PI
        while delta < -math.pi:
            delta += TWO_PI
        values.append(values[-1] + delta)
    return values


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
        area_turns = area(part[start : end + 1], voltage_key)
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
    if part:
        append(len(part) - 1, direction)
    return max(segments, key=lambda item: item["phase_abs_turns"], default=None), segments


def summarize(path: Path):
    rows = load(path)
    trig_largest, trig_segments = largest_segment(rows, TRIG_P, TRIG_V)
    out_largest, out_segments = largest_segment(rows, OUT_P, OUT_V)
    pre = select(rows, 80.0, 90.0)
    activity = select(rows, 94.0, 130.0)
    output_complete = any(
        item["complete_2pi"]
        and item["start_time_ps"] <= 130.0
        and abs(item["area_minus_phase_turns"]) <= 0.05
        for item in out_segments
    )
    trigger_complete = any(
        item["complete_2pi"]
        and item["start_time_ps"] <= 130.0
        and abs(item["area_minus_phase_turns"]) <= 0.05
        for item in trig_segments
    )
    return {
        "sha256": sha256(path),
        "rows": len(rows),
        "btrig_largest": trig_largest,
        "btrig_complete": trigger_complete,
        "bout_largest": out_largest,
        "bout_complete": output_complete,
        "secondary": {
            "V(N_SEC|XTRIG)": max(
                abs(row[VSEC] - median(pre, VSEC)) for row in activity
            ),
            "I(R_SEC_LOAD|XTRIG)": max(
                abs(row[ISEC] - median(pre, ISEC)) for row in activity
            ),
        },
        "output_branch": {
            IBOUT: extrema(activity, IBOUT),
            OUT_V: extrema(activity, OUT_V),
        },
        "post_output_phase_range_turns": (
            max(unwrap(select(rows, 130.0, 170.0), OUT_P), default=0.0)
            - min(unwrap(select(rows, 130.0, 170.0), OUT_P), default=0.0)
        ) / TWO_PI,
    }


def main():
    result = {
        "document_type": "r1b_area008_vs_area010_raw_comparison",
        "method": "independent raw CSV comparison; same-JJ phase/area, secondary amplitude, output branch activity",
        "new_point": NEW_POINT,
        "accepted_baseline": "e3a18da0b42bfdfdd1d36886cbad8b04d77617c9",
        "baseline_point": OLD_POINT,
        "cases": {},
    }
    for case_id in CASES:
        new_path = ROOT / "raw" / NEW_POINT / case_id / f"{RUN_ID}.csv"
        old_path = BASELINE / "raw" / OLD_POINT / case_id / f"{RUN_ID}.csv"
        new = summarize(new_path)
        old = summarize(old_path)
        result["cases"][case_id] = {
            "area008": new,
            "area010_baseline": old,
            "delta": {
                "btrig_phase_turns": new["btrig_largest"]["phase_abs_turns"] - old["btrig_largest"]["phase_abs_turns"],
                "bout_phase_turns": new["bout_largest"]["phase_abs_turns"] - old["bout_largest"]["phase_abs_turns"],
                "bout_area_turns": new["bout_largest"]["same_junction_voltage_area_turns"] - old["bout_largest"]["same_junction_voltage_area_turns"],
                "secondary_v": new["secondary"]["V(N_SEC|XTRIG)"] - old["secondary"]["V(N_SEC|XTRIG)"],
                "secondary_i": new["secondary"]["I(R_SEC_LOAD|XTRIG)"] - old["secondary"]["I(R_SEC_LOAD|XTRIG)"],
            },
        }
        print(
            f"{case_id}: A0.10 BOUT={old['bout_largest']['phase_abs_turns']:.9g} turns; "
            f"A0.08 BOUT={new['bout_largest']['phase_abs_turns']:.9g} turns; "
            f"A0.08_complete={new['bout_complete']}"
        )
    out = ROOT / "analysis" / "area010-comparison.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("comparison_written=" + str(out))


if __name__ == "__main__":
    main()
