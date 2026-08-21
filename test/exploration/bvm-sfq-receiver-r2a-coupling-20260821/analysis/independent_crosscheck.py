#!/usr/bin/env python3
"""Independent raw cross-check for R1b B_TRIG/B_OUT and secondary metrics."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
POINT = os.environ.get("POINT_ID", "diff-a010-b007-k080")
RUN_ID = "run-01"
CASES = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]
TRIG_PHASE = "P(B_TRIG|XTRIG)"
TRIG_VOLTAGE = "V(B_TRIG|XTRIG)"
OUT_PHASE = "P(B_OUT|XTRIG)"
OUT_VOLTAGE = "V(B_OUT|XTRIG)"
VSEC = "V(N_SEC|XTRIG)"
ISEC = "I(R_SEC_LOAD|XTRIG)"
STORAGE = ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"]


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


def voltage_area(rows, voltage_key):
    return sum(
        0.5 * (left[voltage_key] + right[voltage_key])
        * (right["time"] - left["time"])
        for left, right in zip(rows, rows[1:])
    ) / PHI0


def phase_summary(rows, phase_key, voltage_key):
    part = select(rows, 94.0, 170.0)
    if len(part) < 2:
        return {
            "largest": None,
            "complete": False,
            "complete_count": 0,
            "segments": [],
        }
    phase = unwrap(part, phase_key)
    deltas = [right - left for left, right in zip(phase, phase[1:])]
    start = 0
    direction = None
    segments = []

    def append(end, sign):
        if end <= start or sign is None:
            return
        delta_turns = (phase[end] - phase[start]) / TWO_PI
        segment_rows = part[start : end + 1]
        area_turns = voltage_area(segment_rows, voltage_key)
        segments.append(
            {
                "start_time_ps": part[start]["time"] * 1e12,
                "end_time_ps": part[end]["time"] * 1e12,
                "direction": "increasing" if sign > 0 else "decreasing",
                "raw_phase_start_rad": part[start][phase_key],
                "raw_phase_end_rad": part[end][phase_key],
                "phase_delta_rad": phase[end] - phase[start],
                "phase_delta_turns": delta_turns,
                "phase_abs_turns": abs(delta_turns),
                "same_junction_voltage_area_turns": area_turns,
                "area_minus_phase_turns": area_turns - delta_turns,
                "area_consistent_0p05_turns": abs(area_turns - delta_turns) <= 0.05,
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
    complete = [
        segment
        for segment in segments
        if segment["complete_2pi"]
        and segment["start_time_ps"] <= 130.0
        and segment["area_consistent_0p05_turns"]
    ]
    return {
        "largest": max(segments, key=lambda item: item["phase_abs_turns"], default=None),
        "complete": bool(complete),
        "complete_count": len(complete),
        "segments": segments,
        "qualifying": complete,
    }


def amplitude(rows, key):
    pre = select(rows, 80.0, 90.0)
    activity = select(rows, 94.0, 130.0)
    baseline = median(pre, key)
    return max((abs(row[key] - baseline) for row in activity), default=0.0)


def summarize(path):
    rows = load(path)
    return {
        "sha256": sha256(path),
        "btrig": phase_summary(rows, TRIG_PHASE, TRIG_VOLTAGE),
        "bout": phase_summary(rows, OUT_PHASE, OUT_VOLTAGE),
        "secondary_v_amplitude": amplitude(rows, VSEC),
        "secondary_i_amplitude": amplitude(rows, ISEC),
        "storage": {
            key: {
                "pre_median_rad": median(select(rows, 80.0, 90.0), key),
                "post_median_rad": median(select(rows, 140.0, 150.0), key),
            }
            for key in STORAGE
        },
    }


def close(left, right, tolerance):
    return abs(left - right) <= tolerance


def main():
    primary_path = ROOT / os.environ.get(
        "PRIMARY_ANALYSIS", f"analysis/{POINT}-analysis.json"
    )
    primary = json.loads(primary_path.read_text())
    comparisons = []
    raw_metrics = {}
    for case_id in CASES:
        path = ROOT / "raw" / POINT / case_id / f"{RUN_ID}.csv"
        cross = summarize(path)
        raw_metrics[case_id] = cross
        pcase = primary["cases"][case_id]
        p_trig = pcase["trigger"]["trigger_analysis"]["largest_abs_segment"]
        p_out = pcase["output"]["output_analysis"]["largest_abs_segment"]
        p_trig_complete = pcase["trigger"]["qualifying_read_trigger"]
        p_out_complete = pcase["output"]["qualifying_read_output"]
        p_v = pcase["secondary"][VSEC]["activity_abs_deviation_peak"]
        p_i = pcase["secondary"][ISEC]["activity_abs_deviation_peak"]
        bout_phase_match = (
            (p_out is None and cross["bout"]["largest"] is None)
            or (
                p_out is not None
                and cross["bout"]["largest"] is not None
                and close(
                    p_out["phase_abs_turns"],
                    cross["bout"]["largest"]["phase_abs_turns"],
                    1e-9,
                )
            )
        )
        bout_area_match = (
            (p_out is None and cross["bout"]["largest"] is None)
            or (
                p_out is not None
                and cross["bout"]["largest"] is not None
                and close(
                    p_out["same_junction_voltage_area_turns"],
                    cross["bout"]["largest"]["same_junction_voltage_area_turns"],
                    1e-8,
                )
            )
        )
        checks = {
            "sha_match": pcase["sha256"] == cross["sha256"],
            "btrig_phase_match": close(
                p_trig["phase_abs_turns"],
                cross["btrig"]["largest"]["phase_abs_turns"],
                1e-9,
            ),
            "btrig_area_match": close(
                p_trig["same_junction_voltage_area_turns"],
                cross["btrig"]["largest"]["same_junction_voltage_area_turns"],
                1e-8,
            ),
            "btrig_complete_match": p_trig_complete == cross["btrig"]["complete"],
            "bout_phase_match": bout_phase_match,
            "bout_area_match": bout_area_match,
            "bout_complete_match": p_out_complete == cross["bout"]["complete"],
            "secondary_v_match": close(p_v, cross["secondary_v_amplitude"], 1e-15),
            "secondary_i_match": close(p_i, cross["secondary_i_amplitude"], 1e-15),
        }
        for key in STORAGE:
            checks[key + "_pre_match"] = close(
                pcase["storage"][key]["pre_median_rad"],
                cross["storage"][key]["pre_median_rad"],
                1e-9,
            )
            checks[key + "_post_match"] = close(
                pcase["storage"][key]["post_median_rad"],
                cross["storage"][key]["post_median_rad"],
                1e-9,
            )
        comparisons.append({"case": case_id, **checks})

    result = {
        "document_type": "r2a_coupling_point_independent_crosscheck",
        "method": (
            "independent raw CSV read; adjacent phase unwrap; monotonic same-JJ "
            "area for B_TRIG and B_OUT; PRE-subtracted secondary amplitude; "
            "JM1/JM2 pre/post medians"
        ),
        "all_comparisons_pass": all(
            all(value for key, value in item.items() if key != "case")
            for item in comparisons
        ),
        "comparisons": comparisons,
        "raw_metrics": raw_metrics,
    }
    output_name = os.environ.get(
        "CROSSCHECK_OUTPUT", f"analysis/{POINT}-crosscheck.json"
    )
    out = ROOT / output_name
    out.write_text(json.dumps(result, indent=2) + "\n")
    print("all_comparisons_pass=" + str(result["all_comparisons_pass"]))
    for item in comparisons:
        passed = all(value for key, value in item.items() if key != "case")
        print(item["case"], "all=" + str(passed))


if __name__ == "__main__":
    main()
