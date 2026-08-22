#!/usr/bin/env python3
"""Analyze the R6-B matched-ratio isolated native-QB Exploration from raw CSVs.

This script keeps raw P values in radians, derives continuous phase turns, and
cross-checks candidate monotonic segments against direct same-JJ voltage area.
It does not use scripts/sfq_metrics.py or derivative samples as event counts.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "analysis"
PHI0 = 2.067833848e-15
PI2 = 2.0 * math.pi
WINDOWS = {
    "pre": (80.0, 90.0),
    "activity": (94.0, 130.0),
    "post": (150.0, 170.0),
}
AREA_TOLERANCE_TURN = 0.05
SEGMENT_PROMINENCE_TURN = 0.005

JUNCTIONS = {
    "BJs": ("P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}
BRANCHES = {
    "Lin": "I(Lin|XBQ)",
    "L1": "I(L1|XBQ)",
    "L2": "I(L2|XBQ)",
    "L0": "I(L0|XBQ)",
    "RB": "I(RB|XBQ)",
    "RJ1": "I(RJ1|XBQ)",
    "RJ2": "I(RJ2|XBQ)",
    "R_PRI": "I(R_PRI)",
    "L_PRI": "I(L_PRI)",
    "L_SEC": "I(L_SEC)",
}
REQUIRED = {
    "time",
    *[item for triple in JUNCTIONS.values() for item in triple],
    *BRANCHES.values(),
    "V(SL1)",
    "V(N6|XBVM1)",
    "V(QB_IN)",
    "V(OUT_Q)",
    "V(L_PRI)",
    "V(L_SEC)",
    "I(R_PRI)",
    "I(L_PRI)",
    "I(L_SEC)",
    "I(L_SL|XBVM1)",
    "I(L_PSL|XBVM1)",
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
}
STATE_KEYS = [
    "P(B_JM1|XBVM1)",
    "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)",
    "P(B_JS2|XBVM1)",
]


def read_csv(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or [])
        # JoSIM normalizes element/node names in CSV headers to upper case
        # (for example BJs -> BJS and Lin -> LIN).  Keep the preregistered
        # semantic names in the analysis output, but match headers
        # case-insensitively.  This does not alter raw CSV evidence.
        field_lookup = {}
        for field in fields:
            field_lookup.setdefault(field.casefold(), field)
        missing = sorted(key for key in REQUIRED if key.casefold() not in field_lookup)
        rows = []
        conversion_error = None
        for row_number, row in enumerate(reader, start=2):
            try:
                values = {
                    key: float(row[field_lookup[key.casefold()]])
                    for key in REQUIRED
                    if key.casefold() in field_lookup
                }
            except (TypeError, ValueError) as exc:
                conversion_error = f"row {row_number}: {exc}"
                break
            rows.append(values)
    times = [row.get("time", float("nan")) for row in rows]
    finite = all(math.isfinite(value) for row in rows for value in row.values())
    increasing = all(a < b for a, b in zip(times, times[1:]))
    return fields, rows, missing, conversion_error, finite, increasing


def in_window(row, window):
    t_ps = row["time"] * 1.0e12
    return window[0] <= t_ps < window[1]


def indices_in_window(rows, window):
    return [index for index, row in enumerate(rows) if in_window(row, window)]


def median_key(rows, key, window):
    values = [rows[index][key] for index in indices_in_window(rows, window)]
    return median(values) if values else float("nan")


def trapezoid(rows, key, first, last):
    total = 0.0
    for left, right in zip(rows[first:last], rows[first + 1 : last + 1]):
        total += 0.5 * (left[key] + right[key]) * (right["time"] - left["time"])
    return total


def continuous_phase(rows, key):
    if not rows:
        return []
    result = [rows[0][key]]
    for row, previous in zip(rows[1:], rows):
        delta = row[key] - previous[key]
        while delta > math.pi:
            delta -= PI2
        while delta < -math.pi:
            delta += PI2
        result.append(result[-1] + delta)
    return result


def turning_points(values, indices):
    """Return descriptive extrema points used to form monotonic candidates."""
    half = 5
    threshold = SEGMENT_PROMINENCE_TURN * PI2
    candidates = []
    for position in range(half, len(indices) - half):
        index = indices[position]
        value = values[index]
        left = [values[indices[j]] for j in range(position - half, position)]
        right = [values[indices[j]] for j in range(position + 1, position + half + 1)]
        kind = None
        if value >= max(left + right):
            kind = "max"
        elif value <= min(left + right):
            kind = "min"
        if kind is None:
            continue
        if candidates and candidates[-1]["kind"] == kind:
            better = value > candidates[-1]["value"] if kind == "max" else value < candidates[-1]["value"]
            if better:
                candidates[-1] = {"position": position, "index": index, "kind": kind, "value": value}
            continue
        if candidates and abs(value - candidates[-1]["value"]) < threshold:
            continue
        candidates.append({"position": position, "index": index, "kind": kind, "value": value})
    points = [indices[0]] if indices else []
    points.extend(item["index"] for item in candidates)
    if indices and points[-1] != indices[-1]:
        points.append(indices[-1])
    return sorted(set(points))


def monotonic_segments(rows, phase_values, voltage_key, indices):
    points = turning_points(phase_values, indices)
    segments = []
    for first, last in zip(points, points[1:]):
        phase_rad = phase_values[last] - phase_values[first]
        area_turn = trapezoid(rows, voltage_key, first, last) / PHI0
        segments.append(
            {
                "start_ps": rows[first]["time"] * 1.0e12,
                "end_ps": rows[last]["time"] * 1.0e12,
                "phase_delta_rad": phase_rad,
                "phase_delta_turns": phase_rad / PI2,
                "area_turns": area_turn,
                "residual_turns": phase_rad / PI2 - area_turn,
                "area_consistent": abs(phase_rad / PI2 - area_turn) <= AREA_TOLERANCE_TURN,
            }
        )
    segments.sort(key=lambda item: abs(item["phase_delta_turns"]), reverse=True)
    return segments


def extrema_values(rows, key, window):
    values = [rows[index][key] for index in indices_in_window(rows, window)]
    return {
        "min": min(values) if values else float("nan"),
        "max": max(values) if values else float("nan"),
        "peak_to_peak": max(values) - min(values) if values else float("nan"),
        "peak_abs": max((abs(value) for value in values), default=float("nan")),
    }


def junction_result(rows, name):
    phase_key, voltage_key, current_key = JUNCTIONS[name]
    phase_values = continuous_phase(rows, phase_key)
    activity_indices = indices_in_window(rows, WINDOWS["activity"])
    segments = monotonic_segments(rows, phase_values, voltage_key, activity_indices)
    pre = median_key(rows, phase_key, WINDOWS["pre"])
    activity = [phase_values[index] for index in activity_indices]
    post = [phase_values[index] for index in indices_in_window(rows, WINDOWS["post"])]
    qualifying = [
        segment
        for segment in segments
        if abs(segment["phase_delta_turns"]) >= 1.0 and segment["area_consistent"]
    ]
    return {
        "phase_column": phase_key,
        "voltage_column": voltage_key,
        "current_column": current_key,
        "pre_median_rad": pre,
        "activity_min_turn": min(activity) / PI2 if activity else float("nan"),
        "activity_max_turn": max(activity) / PI2 if activity else float("nan"),
        "activity_range_turn": (max(activity) - min(activity)) / PI2 if activity else float("nan"),
        "activity_relative_min_turn": (min(activity) - pre) / PI2 if activity else float("nan"),
        "activity_relative_max_turn": (max(activity) - pre) / PI2 if activity else float("nan"),
        "activity_voltage_peak_uV": extrema_values(rows, voltage_key, WINDOWS["activity"])["peak_abs"] * 1.0e6,
        "activity_current_peak_uA": extrema_values(rows, current_key, WINDOWS["activity"])["peak_abs"] * 1.0e6,
        "post_phase_p2p_turn": (max(post) - min(post)) / PI2 if post else float("nan"),
        "post_voltage_peak_uV": extrema_values(rows, voltage_key, WINDOWS["post"])["peak_abs"] * 1.0e6,
        "segments": segments,
        "largest_segment": segments[0] if segments else None,
        "qualifying_complete_segment_count": len(qualifying),
        "qualifying_segments": qualifying,
    }


def branch_result(rows, key):
    activity = extrema_values(rows, key, WINDOWS["activity"])
    pre = median_key(rows, key, WINDOWS["pre"])
    post = median_key(rows, key, WINDOWS["post"])
    return {
        "min_uA": activity["min"] * 1.0e6,
        "max_uA": activity["max"] * 1.0e6,
        "peak_abs_uA": activity["peak_abs"] * 1.0e6,
        "pre_uA": pre * 1.0e6,
        "post_uA": post * 1.0e6,
        "post_minus_pre_uA": (post - pre) * 1.0e6,
    }


def storage_result(rows, key):
    pre = median_key(rows, key, WINDOWS["pre"])
    post = median_key(rows, key, WINDOWS["post"])
    return {
        "pre_rad": pre,
        "post_rad": post,
        "delta_rad": post - pre,
        "pre_turn": pre / PI2,
        "post_turn": post / PI2,
        "delta_turn": (post - pre) / PI2,
    }


def analyze_case(path):
    fields, rows, missing, conversion_error, finite, increasing = read_csv(path)
    case = path.parent.name
    result = {
        "case": case,
        "raw_path": str(path.relative_to(ROOT)),
        "artifact": {
            "row_count": len(rows),
            "end_ps": rows[-1]["time"] * 1.0e12 if rows else None,
            "field_count": len(fields),
            "missing_required_columns": missing,
            "conversion_error": conversion_error,
            "finite": finite,
            "time_strictly_increasing": increasing,
            "valid": bool(rows and not missing and conversion_error is None and finite and increasing),
        },
        "junctions": {},
        "branches": {},
        "source_output": {},
        "storage": {},
    }
    if not rows or missing or conversion_error:
        return result
    for name in JUNCTIONS:
        result["junctions"][name] = junction_result(rows, name)
    for name, key in BRANCHES.items():
        result["branches"][name] = branch_result(rows, key)
    for key in [
        "V(SL1)",
        "V(N6|XBVM1)",
        "V(QB_IN)",
        "V(OUT_Q)",
        "V(L_PRI)",
        "V(L_SEC)",
        "I(R_PRI)",
        "I(L_PRI)",
        "I(L_SEC)",
        "I(L_SL|XBVM1)",
        "I(L_PSL|XBVM1)",
    ]:
        result["source_output"][key] = {
            "activity": extrema_values(rows, key, WINDOWS["activity"]),
            "post": extrema_values(rows, key, WINDOWS["post"]),
        }
    for key in STATE_KEYS:
        result["storage"][key] = storage_result(rows, key)
    return result


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def provisional_verdict(cases):
    if not cases or any(not case["artifact"]["valid"] for case in cases):
        return "INVALID"
    return "ANALYSIS_ONLY_PENDING_COMPARATIVE_ADJUDICATION"


def main():
    paths = sorted(RAW.glob("*/run-01.csv"))
    cases = [analyze_case(path) for path in paths]
    summary = {
        "analysis": {
            "script": str(Path(__file__).relative_to(ROOT)),
            "phi0_Wb": PHI0,
            "windows_ps": WINDOWS,
            "event_threshold_turn": 1.0,
            "same_jj_area_tolerance_turn": AREA_TOLERANCE_TURN,
            "segment_prominence_turn": SEGMENT_PROMINENCE_TURN,
            "segment_prominence_is_descriptive": True,
            "raw_sha256": {str(path.relative_to(ROOT)): sha256(path) for path in paths},
        },
        "cases": cases,
        "provisional_verdict": provisional_verdict(cases),
    }
    output = OUT / "r6b-summary.json"
    output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
