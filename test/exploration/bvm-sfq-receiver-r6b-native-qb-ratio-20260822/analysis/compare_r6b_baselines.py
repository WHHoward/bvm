#!/usr/bin/env python3
"""Compare R6-B with R6-A and canonical no-receiver read1/read0 raw.

This is a descriptive comparison tool. It does not turn activity into event
counts and does not invent a global physical tolerance.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median


RUN = Path(__file__).resolve().parents[1]
REPO = RUN.parents[2]
R6A = REPO / "test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822"
CANONICAL = REPO / "test/exploration/bvm-internal-readout-20260819/raw"
R6B = RUN / "raw"
WINDOWS = {"pre": (80.0, 90.0), "activity": (94.0, 130.0), "post": (150.0, 170.0)}
PHI_KEYS = {
    "JM1": "P(B_JM1|XBVM1)",
    "JM2": "P(B_JM2|XBVM1)",
    "JS1": "P(B_JS1|XBVM1)",
    "JS2": "P(B_JS2|XBVM1)",
}
COMPARE_KEYS = {
    "I_R_PRI": ("I(R_PRI)", "uA"),
    "I_L_PRI": ("I(L_PRI)", "uA"),
    "I_L_SEC": ("I(L_SEC)", "uA"),
    "V_L_SEC": ("V(L_SEC)", "uV"),
    "V_QB_IN": ("V(QB_IN)", "uV"),
    "V_SL": ("V(SL1)", "uV"),
    "V_N6": ("V(N6|XBVM1)", "uV"),
    "I_L_SL": ("I(L_SL|XBVM1)", "uA"),
    "I_L_PSL": ("I(L_PSL|XBVM1)", "uA"),
}
STATE_KEYS = {
    "JM1": ("P(B_JM1|XBVM1)", "turn"),
    "JM2": ("P(B_JM2|XBVM1)", "turn"),
    "JS1": ("P(B_JS1|XBVM1)", "turn"),
    "JS2": ("P(B_JS2|XBVM1)", "turn"),
}


def load_rows(path: Path):
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        lookup = {field.casefold(): field for field in fields}
        rows = []
        for raw in reader:
            row = {}
            for key, actual in lookup.items():
                try:
                    row[key] = float(raw[actual])
                except (TypeError, ValueError):
                    row[key] = float("nan")
            rows.append(row)
    return fields, rows


def values(rows, key, window):
    wanted = key.casefold()
    return [
        row[wanted]
        for row in rows
        if wanted in row
        and window[0] <= row["time"] * 1e12 < window[1]
        and math.isfinite(row[wanted])
    ]


def scale_for(unit):
    return {"uA": 1e6, "uV": 1e6, "turn": 1.0 / (2.0 * math.pi)}[unit]


def metric(rows, key, unit):
    scale = scale_for(unit)
    if not rows or key.casefold() not in rows[0]:
        return {
            "unit": unit,
            "column": key,
            "status": "NOT_APPLICABLE",
            "reason": "canonical no-receiver raw has no receiver-only column",
        }
    windows = {}
    for name, window in WINDOWS.items():
        raw = values(rows, key, window)
        scaled = [item * scale for item in raw]
        windows[name] = {
            "count": len(scaled),
            "min": min(scaled) if scaled else None,
            "max": max(scaled) if scaled else None,
            "median": median(scaled) if scaled else None,
            "p2p": max(scaled) - min(scaled) if scaled else None,
            "peak_abs": max((abs(item) for item in scaled), default=None),
        }
    if windows["pre"]["median"] is not None and windows["post"]["median"] is not None:
        windows["post_minus_pre"] = windows["post"]["median"] - windows["pre"]["median"]
    else:
        windows["post_minus_pre"] = None
    return {"unit": unit, "column": key, "status": "OBSERVED", "windows": windows}


def raw_sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def path_map():
    return {
        "read1": {
            "canonical": CANONICAL / "pos-read-single/run-01.csv",
            "r6a": R6A / "raw/read1/run-01.csv",
            "r6b": R6B / "read1/run-01.csv",
        },
        "read0": {
            "canonical": CANONICAL / "neg-init-pos-read/run-01.csv",
            "r6a": R6A / "raw/read0/run-01.csv",
            "r6b": R6B / "read0/run-01.csv",
        },
        "logical1-read0-control": {
            "r6a": R6A / "raw/logical1-read0-control/run-01.csv",
            "r6b": R6B / "logical1-read0-control/run-01.csv",
        },
        "logical0-read0-control": {
            "r6a": R6A / "raw/logical0-read0-control/run-01.csv",
            "r6b": R6B / "logical0-read0-control/run-01.csv",
        },
    }


def source_comparison(paths):
    output = {}
    for case, variants in paths.items():
        output[case] = {}
        for label, path in variants.items():
            fields, rows = load_rows(path)
            entry = {
                "path": str(path.relative_to(REPO)),
                "sha256": raw_sha(path),
                "row_count": len(rows),
                "field_count": len(fields),
                "end_ps": rows[-1]["time"] * 1e12 if rows else None,
                "signals": {},
            }
            for name, (key, unit) in COMPARE_KEYS.items():
                entry["signals"][name] = metric(rows, key, unit)
            for name, (key, unit) in STATE_KEYS.items():
                entry["signals"][name] = metric(rows, key, unit)
            output[case][label] = entry
    return output


def load_summary(path):
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def junction_comparison():
    r6a = load_summary(R6A / "analysis/r6a-summary.json")
    r6b = load_summary(RUN / "analysis/r6b-summary.json")
    result = {}
    for case in ("read1", "read0", "logical1-read0-control", "logical0-read0-control"):
        a_case = next(item for item in r6a["cases"] if item["case"] == case)
        b_case = next(item for item in r6b["cases"] if item["case"] == case)
        result[case] = {}
        for junction in ("BJs", "BJL1", "BJL2"):
            a = a_case["junctions"][junction]
            b = b_case["junctions"][junction]
            a_seg = a.get("largest_segment") or {}
            b_seg = b.get("largest_segment") or {}
            a_range = a["activity_range_turn"]
            b_range = b["activity_range_turn"]
            a_abs_seg = abs(a_seg.get("phase_delta_turns", 0.0))
            b_abs_seg = abs(b_seg.get("phase_delta_turns", 0.0))
            result[case][junction] = {
                "r6a_activity_range_turn": a_range,
                "r6b_activity_range_turn": b_range,
                "activity_range_delta_turn": b_range - a_range,
                "activity_range_gain": b_range / a_range if a_range else None,
                "r6a_largest_segment": a_seg,
                "r6b_largest_segment": b_seg,
                "largest_segment_abs_gain": b_abs_seg / a_abs_seg if a_abs_seg else None,
                "r6a_complete_segment_count": a["qualifying_complete_segment_count"],
                "r6b_complete_segment_count": b["qualifying_complete_segment_count"],
                "r6a_activity_voltage_peak_uV": a["activity_voltage_peak_uV"],
                "r6b_activity_voltage_peak_uV": b["activity_voltage_peak_uV"],
                "r6a_activity_current_peak_uA": a["activity_current_peak_uA"],
                "r6b_activity_current_peak_uA": b["activity_current_peak_uA"],
            }
    return result


def main():
    paths = path_map()
    result = {
        "comparison": "R6B_vs_R6A_vs_canonical_source",
        "windows_ps": {name: list(window) for name, window in WINDOWS.items()},
        "cases": source_comparison(paths),
        "junctions": junction_comparison(),
        "notes": [
            "R6-A/R6-B phase and area values come from their same-JJ analyzer summaries.",
            "Canonical no-receiver comparison is a source baseline, not a receiver event test.",
            "Absolute canonical read1 JS phase running is not alone a back-action verdict.",
            "No global tolerance or universal drive threshold is invented here.",
        ],
    }
    path = RUN / "analysis/r6b-baseline-comparison.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
