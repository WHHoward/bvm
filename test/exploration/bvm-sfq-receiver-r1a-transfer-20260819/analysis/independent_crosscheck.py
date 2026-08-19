#!/usr/bin/env python3
"""Independent raw cross-check for R1a trigger and secondary metrics."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
POINT = "l020-k080"
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]
PHASE = "P(B_TRIG|XTRIG)"
VOLTAGE = "V(B_TRIG|XTRIG)"
VSEC = "V(N_SEC|XTRIG)"
ISEC = "I(R_SEC_LOAD|XTRIG)"


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


def select(rows, lo, hi):
    return [row for row in rows if lo <= row["time"] * 1e12 <= hi]


def median(rows, key):
    values = sorted(row[key] for row in rows)
    return values[len(values) // 2] if len(values) % 2 else 0.5 * (values[len(values) // 2 - 1] + values[len(values) // 2])


def integrate(rows):
    return sum(
        0.5 * (left[VOLTAGE] + right[VOLTAGE]) * (right["time"] - left["time"])
        for left, right in zip(rows, rows[1:])
    ) / PHI0


def unwrap(rows):
    values = []
    for index, row in enumerate(rows):
        if index == 0:
            values.append(row[PHASE])
            continue
        delta = row[PHASE] - rows[index - 1][PHASE]
        while delta > math.pi:
            delta -= TWO_PI
        while delta < -math.pi:
            delta += TWO_PI
        values.append(values[-1] + delta)
    return values


def phase_segments(rows):
    part = select(rows, 94.0, 170.0)
    if len(part) < 2:
        return []
    phase = unwrap(part)
    deltas = [right - left for left, right in zip(phase, phase[1:])]
    start = 0
    direction = None
    segments = []

    def append(end, sign):
        if end <= start or sign is None:
            return
        delta_turns = (phase[end] - phase[start]) / TWO_PI
        segment_rows = part[start : end + 1]
        segments.append(
            {
                "start_time_ps": part[start]["time"] * 1e12,
                "end_time_ps": part[end]["time"] * 1e12,
                "phase_delta_turns": delta_turns,
                "phase_abs_turns": abs(delta_turns),
                "same_junction_voltage_area_turns": integrate(segment_rows),
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
    return segments


def amplitude(rows, key):
    pre = select(rows, 80.0, 90.0)
    activity = select(rows, 94.0, 130.0)
    baseline = median(pre, key)
    return max((abs(row[key] - baseline) for row in activity), default=0.0)


def summarize(path):
    rows = load(path)
    segments = phase_segments(rows)
    return {
        "sha256": sha256(path),
        "largest_trigger_abs_turns": max((segment["phase_abs_turns"] for segment in segments), default=0.0),
        "largest_trigger_area_turns": (max(segments, key=lambda segment: segment["phase_abs_turns"])["same_junction_voltage_area_turns"] if segments else 0.0),
        "trigger_complete": any(segment["complete_2pi"] and segment["start_time_ps"] <= 130.0 for segment in segments),
        "secondary_v_amplitude": amplitude(rows, VSEC),
        "secondary_i_amplitude": amplitude(rows, ISEC),
    }


def main():
    primary = json.loads((ROOT / "analysis" / "r1a-analysis.json").read_text())
    comparisons = []
    raw = {}
    primary_cases = primary["cases"]
    for case_id in CASES:
        path = ROOT / "raw" / POINT / case_id / "run-01.csv"
        cross = summarize(path)
        raw[case_id] = cross
        pcase = primary_cases[case_id]
        pseg = pcase["trigger"]["trigger_analysis"]["largest_abs_segment"]
        pv = pcase["secondary"][VSEC]["activity_abs_deviation_peak"]
        pi = pcase["secondary"][ISEC]["activity_abs_deviation_peak"]
        comparisons.append(
            {
                "case": case_id,
                "sha_match": pcase["sha256"] == cross["sha256"],
                "trigger_largest_match": abs(pseg["phase_abs_turns"] - cross["largest_trigger_abs_turns"]) < 1e-9,
                "trigger_area_match": abs(pseg["same_junction_voltage_area_turns"] - cross["largest_trigger_area_turns"]) < 1e-8,
                "trigger_complete_match": pcase["trigger"]["qualifying_read_trigger"] == cross["trigger_complete"],
                "secondary_v_match": abs(pv - cross["secondary_v_amplitude"]) < 1e-15,
                "secondary_i_match": abs(pi - cross["secondary_i_amplitude"]) < 1e-15,
            }
        )
    result = {
        "document_type": "r1a_independent_crosscheck",
        "method": "independent raw CSV read; adjacent phase unwrap; monotonic same-JJ area; PRE-subtracted secondary amplitudes",
        "all_comparisons_pass": all(all(item.values()) for item in comparisons),
        "comparisons": comparisons,
        "raw_metrics": raw,
    }
    out = ROOT / "analysis" / "independent-crosscheck.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("all_comparisons_pass=" + str(result["all_comparisons_pass"]))
    for item in comparisons:
        print(item["case"], "all=" + str(all(value for key, value in item.items() if key != "case")))


if __name__ == "__main__":
    main()
