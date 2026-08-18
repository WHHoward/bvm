#!/usr/bin/env python3
"""Independent raw-only cross-check for the R0b decisive evidence.

This is intentionally not an import of analyze_r0b.py.  It recomputes the
qualifying phase segment, same-segment voltage area, and receiver KCL directly
from the four raw CSV files.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return [{key: float(value) for key, value in row.items()} for row in reader]


def unwrap(rows):
    phase = [rows[0]["P(B_TRIG|XTRIG)"]]
    for left, right in zip(rows, rows[1:]):
        delta = right["P(B_TRIG|XTRIG)"] - left["P(B_TRIG|XTRIG)"]
        while delta > math.pi:
            delta -= TWO_PI
        while delta < -math.pi:
            delta += TWO_PI
        phase.append(phase[-1] + delta)
    return phase


def area(rows):
    return sum(
        0.5 * (left["V(B_TRIG|XTRIG)"] + right["V(B_TRIG|XTRIG)"])
        * (right["time"] - left["time"])
        for left, right in zip(rows, rows[1:])
    )


def segments(rows, phase):
    indices = [i for i, row in enumerate(rows) if 94e-12 <= row["time"] <= 170e-12]
    part = [rows[i] for i in indices]
    p = [phase[i] for i in indices]
    if len(part) < 2:
        return []
    start = 0
    direction = None
    out = []

    def close(end, sign):
        if end <= start or sign is None:
            return
        delta = p[end] - p[start]
        segment_area = area(part[start : end + 1]) / PHI0
        out.append(
            {
                "start_time_ps": part[start]["time"] * 1e12,
                "end_time_ps": part[end]["time"] * 1e12,
                "direction": sign,
                "delta_rad": delta,
                "delta_turns": delta / TWO_PI,
                "area_turns": segment_area,
                "area_minus_phase_turns": segment_area - delta / TWO_PI,
                "complete_2pi": abs(delta) >= TWO_PI,
            }
        )

    for i, (left, right) in enumerate(zip(p, p[1:])):
        delta = right - left
        sign = 1 if delta > 0.0 else -1 if delta < 0.0 else 0
        if not sign:
            continue
        if direction is None:
            direction = sign
        elif sign != direction:
            close(i, direction)
            start = i
            direction = sign
    close(len(part) - 1, direction)
    return out


def summarize(case):
    path = ROOT / "raw" / "a050-b15" / case / "run-01.csv"
    rows = load(path)
    phase = unwrap(rows)
    activity = [
        (row, p)
        for row, p in zip(rows, phase)
        if 94e-12 <= row["time"] <= 130e-12
    ]
    segs = segments(rows, phase)
    largest = max(segs, key=lambda item: abs(item["delta_turns"]))
    kcl = []
    branch = []
    for row in rows:
        if 94e-12 <= row["time"] <= 130e-12:
            kcl.append(
                abs(
                    row["I(B_TRIG|XTRIG)"]
                    - row["I(R_IN|XTRIG)"]
                    - row["I(I_TRIG_BIAS|XTRIG)"]
                )
            )
            branch.append(abs(row["I(R_IN|XTRIG)"] - row["I(L_SL|XBVM1)"]))
    activity_phase = [p for _, p in activity]
    activity_rows = [row for row, _ in activity]
    complete = [item for item in segs if item["complete_2pi"] and item["start_time_ps"] <= 130.0]
    return {
        "sha256": digest(path),
        "rows": len(rows),
        "time_start_ps": rows[0]["time"] * 1e12,
        "time_end_ps": rows[-1]["time"] * 1e12,
        "activity_phase_range_rad": max(activity_phase) - min(activity_phase),
        "activity_endpoint_delta_turns": (activity_phase[-1] - activity_phase[0]) / TWO_PI,
        "activity_voltage_area_turns": area(activity_rows) / PHI0,
        "largest_segment": largest,
        "qualifying_complete_segments": complete,
        "max_kcl_residual_A": max(kcl),
        "max_input_vs_sl_current_residual_A": max(branch),
    }


def main():
    result = {
        "method": "independent raw-only phase/V/KCL cross-check; no sfq count",
        "canonical_bvm_sha256": digest(ROOT / "inputs" / "bvm_cell.cir"),
        "jjmit_sha256": digest(ROOT / "inputs" / "jjmit.cir"),
        "cases": {case: summarize(case) for case in CASES},
    }
    (ROOT / "analysis" / "independent-crosscheck.json").write_text(json.dumps(result, indent=2) + "\n")
    for case, data in result["cases"].items():
        print(
            f"{case}: max_segment={data['largest_segment']['delta_turns']:.9g} turns, "
            f"complete={bool(data['qualifying_complete_segments'])}, "
            f"KCL_max={data['max_kcl_residual_A']:.3e} A, "
            f"branch_max={data['max_input_vs_sl_current_residual_A']:.3e} A"
        )


if __name__ == "__main__":
    main()
