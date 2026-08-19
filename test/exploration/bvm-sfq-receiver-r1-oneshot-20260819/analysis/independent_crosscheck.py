#!/usr/bin/env python3
"""Small independent mechanical cross-check of R1 raw CSV event metrics.

This intentionally does not import analyze_r1.py.  It re-reads each raw CSV,
reconstructs adjacent-sample continuous phase, integrates the same-JJ voltage
over each monotonic segment, and compares only the key counts/ranges with the
primary analysis JSON.
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
POINT_IDS = ["a050-b15", "a050-b15-rq100", "a050-b15-rq1k", "a050-b15-lq10"]
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]
TRIGGER_PHASE = "P(B_TRIG|XTRIG)"
TRIGGER_VOLTAGE = "V(B_TRIG|XTRIG)"
OUTPUT_PHASE = "P(B_OUT|XTRIG)"
OUTPUT_VOLTAGE = "V(B_OUT|XTRIG)"


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        rows = [{key: float(value) for key, value in row.items()} for row in reader]
    return rows


def select(rows, lo_ps, hi_ps):
    return [row for row in rows if lo_ps <= row["time"] * 1e12 <= hi_ps]


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


def area(rows, key):
    return sum(
        0.5 * (left[key] + right[key]) * (right["time"] - left["time"])
        for left, right in zip(rows, rows[1:])
    ) / PHI0


def segments(rows, phase_key, voltage_key):
    if len(rows) < 2:
        return []
    unwrapped = unwrap(rows, phase_key)
    deltas = [right - left for left, right in zip(unwrapped, unwrapped[1:])]
    start = 0
    direction = None
    result = []

    def append(end, sign):
        if end <= start or sign is None:
            return
        delta_turns = (unwrapped[end] - unwrapped[start]) / TWO_PI
        abs_turns = abs(delta_turns)
        result.append(
            {
                "start_time_ps": rows[start]["time"] * 1e12,
                "end_time_ps": rows[end]["time"] * 1e12,
                "phase_delta_turns": delta_turns,
                "phase_abs_turns": abs_turns,
                "voltage_area_turns": area(rows[start : end + 1], voltage_key),
                "complete_units": int(math.floor(abs_turns + 1e-9)),
                "direction": sign,
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
    append(len(rows) - 1, direction)
    return result


def summarize(path):
    rows = load(path)
    trigger_rows = select(rows, 94.0, 200.0)
    output_rows = select(rows, 20.0, 200.0)
    output_read_rows = select(rows, 94.0, 140.0)
    output_post_rows = select(rows, 140.0, 200.0)
    trigger_segments = segments(trigger_rows, TRIGGER_PHASE, TRIGGER_VOLTAGE)
    output_segments = segments(output_rows, OUTPUT_PHASE, OUTPUT_VOLTAGE)
    output_read_segments = segments(output_read_rows, OUTPUT_PHASE, OUTPUT_VOLTAGE)
    output_post_segments = segments(output_post_rows, OUTPUT_PHASE, OUTPUT_VOLTAGE)
    qualifying = [
        segment
        for segment in output_segments
        if segment["complete_units"] >= 1 and 94.0 <= segment["start_time_ps"] <= 140.0
    ]
    time_ps = [row["time"] * 1e12 for row in rows]
    dts = [right - left for left, right in zip(time_ps, time_ps[1:])]
    return {
        "sha256": sha256(path),
        "rows": len(rows),
        "dt_min_ps": min(dts),
        "dt_max_ps": max(dts),
        "trigger_largest_abs_turns": max((x["phase_abs_turns"] for x in trigger_segments), default=0.0),
        "trigger_complete_units": sum(x["complete_units"] for x in trigger_segments),
        "trigger_segments": trigger_segments,
        "output_largest_abs_turns": max((x["phase_abs_turns"] for x in output_segments), default=0.0),
        "output_complete_units": sum(x["complete_units"] for x in output_segments),
        "output_read_triggered_units": sum(x["complete_units"] for x in qualifying),
        "output_post_complete_units": sum(x["complete_units"] for x in output_post_segments),
        "output_segments": output_segments,
        "output_read_triggered_segments": qualifying,
        "output_read_segments": output_read_segments,
        "output_post_segments": output_post_segments,
    }


def main():
    primary = json.loads((ROOT / "analysis" / "r1-analysis.json").read_text())
    primary_by_key = {
        (op["id"], case_id): case
        for op in primary["operating_points"]
        for case_id, case in op["cases"].items()
    }
    cases = {}
    comparisons = []
    for point in POINT_IDS:
        for case_id in CASES:
            path = ROOT / "raw" / point / case_id / "run-01.csv"
            key = (point, case_id)
            cross = summarize(path)
            cases[f"{point}/{case_id}"] = cross
            pcase = primary_by_key[key]
            p_trigger = pcase["trigger"]["trigger_analysis"]
            p_output = pcase["output"]["output_analysis"]
            comparisons.append(
                {
                    "case": f"{point}/{case_id}",
                    "sha_match": pcase["sha256"] == cross["sha256"],
                    "trigger_largest_abs_turns_match": abs(
                        p_trigger["largest_abs_segment_turns"] - cross["trigger_largest_abs_turns"]
                    ) < 1e-9,
                    "trigger_complete_units_match": p_trigger["complete_transition_units"] == cross["trigger_complete_units"],
                    "output_largest_abs_turns_match": abs(
                        p_output["largest_abs_segment_turns"] - cross["output_largest_abs_turns"]
                    ) < 1e-12,
                    "output_complete_units_match": p_output["complete_transition_units"] == cross["output_complete_units"],
                }
            )
    result = {
        "document_type": "r1_independent_crosscheck",
        "method": "independent raw CSV read; adjacent phase unwrap; sign-consistent monotonic segments; same-JJ voltage integration with CSV seconds",
        "all_comparisons_pass": all(all(item.values()) for item in comparisons),
        "comparisons": comparisons,
        "cases": cases,
    }
    out = ROOT / "analysis" / "independent-crosscheck.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("all_comparisons_pass=" + str(result["all_comparisons_pass"]))
    for item in comparisons:
        print(item["case"], "sha=" + str(item["sha_match"]), "trigger=" + str(item["trigger_complete_units_match"]), "output=" + str(item["output_complete_units_match"]))


if __name__ == "__main__":
    main()
