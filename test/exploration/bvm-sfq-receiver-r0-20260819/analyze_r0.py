#!/usr/bin/env python3
"""Raw-CSV QA and same-JJ evidence extraction for the R0 Exploration.

This deliberately reports phase radians, derived phase turns, and same-JJ
voltage area separately. It does not call sfq_metrics.py and does not turn
activity samples into an SFQ count.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PHI0 = 2.067833848e-15
CASES = [
    ("read1", 1, "canonical_positive"),
    ("read0", 0, "canonical_positive"),
    ("logical1-read0-control", 1, "zero_control"),
    ("logical0-read0-control", 0, "zero_control"),
]
WINDOWS = {
    "PRE": (80.0, 90.0),
    "READ_ACTIVITY": (94.0, 130.0),
    "POST": (140.0, 170.0),
    "STORAGE_POST": (140.0, 150.0),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_csv(path: Path):
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = []
        for raw in reader:
            row = {key: float(value) for key, value in raw.items()}
            row["_time_ps"] = row["time"] * 1e12
            rows.append(row)
    return fields, rows


def select(rows, window):
    lo, hi = window
    return [row for row in rows if lo <= row["_time_ps"] <= hi]


def values(rows, key):
    return [row[key] for row in rows]


def med(rows, key):
    return statistics.median(values(rows, key))


def extrema(rows, key):
    data = [(row[key], row["_time_ps"]) for row in rows]
    low = min(data)
    high = max(data)
    return {
        "min": low[0],
        "min_time_ps": low[1],
        "max": high[0],
        "max_time_ps": high[1],
        "abs_peak": max(data, key=lambda item: abs(item[0]))[0],
        "abs_peak_time_ps": max(data, key=lambda item: abs(item[0]))[1],
    }


def trapezoid_area(rows, key):
    total = 0.0
    for left, right in zip(rows, rows[1:]):
        dt = right["_time_ps"] * 1e-12 - left["_time_ps"] * 1e-12
        total += 0.5 * (left[key] + right[key]) * dt
    return total


def summarize_case(case_id, logical_state, read_kind):
    path = ROOT / "raw" / case_id / "run-01.csv"
    fields, rows = load_csv(path)
    required = [
        "time",
        "P(B_TRIG|XTRIG)",
        "V(B_TRIG|XTRIG)",
        "I(B_TRIG|XTRIG)",
        "I(R_IN|XTRIG)",
        "I(I_TRIG_BIAS|XTRIG)",
        "V(SL1)",
        "V(N6|XBVM1)",
        "I(L_SL|XBVM1)",
        "I(L_PSL|XBVM1)",
        "P(B_JM1|XBVM1)",
        "V(B_JM1|XBVM1)",
        "P(B_JM2|XBVM1)",
        "V(B_JM2|XBVM1)",
        "P(B_JS1|XBVM1)",
        "V(B_JS1|XBVM1)",
        "P(B_JS2|XBVM1)",
        "V(B_JS2|XBVM1)",
        "I(L_S1|XBVM1)",
        "I(L_S2|XBVM1)",
        "I(L_S3|XBVM1)",
        "I(L_M3|XBVM1)",
        "I(I_WL1)",
        "I(I_BL1)",
        "I(I_SE1)",
    ]
    missing = [key for key in required if key not in fields]
    times = [row["_time_ps"] for row in rows]
    finite = all(math.isfinite(value) for row in rows for key, value in row.items() if key != "_time_ps")
    increasing = all(right > left for left, right in zip(times, times[1:]))
    dts = [right - left for left, right in zip(times, times[1:])]

    windows = {}
    for name, interval in WINDOWS.items():
        part = select(rows, interval)
        windows[name] = {
            "interval_ps": list(interval),
            "rows": len(part),
            "signals": {
                key: {
                    "median": med(part, key),
                    "min": extrema(part, key)["min"],
                    "min_time_ps": extrema(part, key)["min_time_ps"],
                    "max": extrema(part, key)["max"],
                    "max_time_ps": extrema(part, key)["max_time_ps"],
                    "abs_peak": max(part, key=lambda row: abs(row[key]))[key],
                    "abs_peak_time_ps": max(part, key=lambda row: abs(row[key]))["_time_ps"],
                }
                for key in [
                    "P(B_TRIG|XTRIG)",
                    "V(B_TRIG|XTRIG)",
                    "I(B_TRIG|XTRIG)",
                    "I(R_IN|XTRIG)",
                    "I(I_TRIG_BIAS|XTRIG)",
                    "V(SL1)",
                    "V(N6|XBVM1)",
                    "I(L_SL|XBVM1)",
                    "I(L_PSL|XBVM1)",
                    "P(B_JM1|XBVM1)",
                    "P(B_JM2|XBVM1)",
                    "P(B_JS1|XBVM1)",
                    "P(B_JS2|XBVM1)",
                    "I(L_S1|XBVM1)",
                    "I(L_S2|XBVM1)",
                    "I(L_S3|XBVM1)",
                    "I(L_M3|XBVM1)",
                ]
            },
        }

    activity = select(rows, WINDOWS["READ_ACTIVITY"])
    pre = select(rows, WINDOWS["PRE"])
    storage_post = select(rows, WINDOWS["STORAGE_POST"])
    activity_phase = values(activity, "P(B_TRIG|XTRIG)")
    activity_phase_delta_rad = activity_phase[-1] - activity_phase[0]
    activity_area_wb = trapezoid_area(activity, "V(B_TRIG|XTRIG)")
    trigger = {
        "same_junction": "B_TRIG N_TRIG->0; P in rad; V in V",
        "phase_pre_median_rad": med(pre, "P(B_TRIG|XTRIG)"),
        "phase_activity_first_rad": activity_phase[0],
        "phase_activity_last_rad": activity_phase[-1],
        "phase_activity_delta_rad": activity_phase_delta_rad,
        "phase_activity_net_turns": activity_phase_delta_rad / (2 * math.pi),
        "phase_activity_range_rad": max(activity_phase) - min(activity_phase),
        "phase_activity_range_turns": (max(activity_phase) - min(activity_phase)) / (2 * math.pi),
        "voltage_area_activity_Wb": activity_area_wb,
        "voltage_area_activity_turns": activity_area_wb / PHI0,
        "voltage_abs_peak_uV": 1e6 * max(activity, key=lambda row: abs(row["V(B_TRIG|XTRIG)"]))["V(B_TRIG|XTRIG)"],
        "voltage_abs_peak_time_ps": max(activity, key=lambda row: abs(row["V(B_TRIG|XTRIG)"]))["_time_ps"],
        "post_phase_median_rad": med(storage_post, "P(B_TRIG|XTRIG)"),
        "post_minus_pre_median_rad": med(storage_post, "P(B_TRIG|XTRIG)") - med(pre, "P(B_TRIG|XTRIG)"),
    }

    # The input branch and the independently applied bias are kept in their
    # signed current directions from the CSV. The positive-drive estimate is
    # a diagnostic peak, not a frozen physical threshold.
    input_current = values(activity, "I(R_IN|XTRIG)")
    bias_current = values(activity, "I(I_TRIG_BIAS|XTRIG)")
    effective = [i + b for i, b in zip(input_current, bias_current)]
    source = {
        "SL_voltage_abs_peak_mV": 1e3 * max(activity, key=lambda row: abs(row["V(SL1)"]))["V(SL1)"],
        "SL_voltage_abs_peak_time_ps": max(activity, key=lambda row: abs(row["V(SL1)"]))["_time_ps"],
        "SL_current_abs_peak_uA": 1e6 * max(activity, key=lambda row: abs(row["I(L_SL|XBVM1)"]))["I(L_SL|XBVM1)"],
        "SL_current_abs_peak_time_ps": max(activity, key=lambda row: abs(row["I(L_SL|XBVM1)"]))["_time_ps"],
        "receiver_input_current_abs_peak_uA": 1e6 * max(activity, key=lambda row: abs(row["I(R_IN|XTRIG)"]))["I(R_IN|XTRIG)"],
        "receiver_input_current_abs_peak_time_ps": max(activity, key=lambda row: abs(row["I(R_IN|XTRIG)"]))["_time_ps"],
        "bias_current_median_uA": 1e6 * med(activity, "I(I_TRIG_BIAS|XTRIG)"),
        "effective_drive_signed_peak_uA": 1e6 * max(effective, key=abs),
        "effective_drive_positive_peak_uA": 1e6 * max(effective),
        "effective_drive_negative_peak_uA": 1e6 * min(effective),
    }

    storage = {}
    for key in ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"]:
        pre_value = med(pre, key)
        post_value = med(storage_post, key)
        storage[key] = {
            "pre_median_rad": pre_value,
            "post_median_rad": post_value,
            "post_minus_pre_rad": post_value - pre_value,
            "post_minus_pre_turns": (post_value - pre_value) / (2 * math.pi),
        }

    readout = {}
    for key in [
        "P(B_JS1|XBVM1)",
        "P(B_JS2|XBVM1)",
        "V(B_JS1|XBVM1)",
        "V(B_JS2|XBVM1)",
    ]:
        readout[key] = {
            "activity": extrema(activity, key),
            "activity_median": med(activity, key),
        }

    return {
        "case_id": case_id,
        "logical_state": logical_state,
        "read_kind": read_kind,
        "csv": str(path.relative_to(ROOT)),
        "sha256": sha256(path),
        "qa": {
            "rows": len(rows),
            "time_start_ps": times[0],
            "time_end_ps": times[-1],
            "dt_min_ps": min(dts),
            "dt_max_ps": max(dts),
            "strictly_increasing_time": increasing,
            "all_finite": finite,
            "missing_columns": missing,
            "artifact_valid": not missing and increasing and finite and len(rows) > 1,
        },
        "windows": windows,
        "trigger": trigger,
        "source_and_receiver_currents": source,
        "storage": storage,
        "readout": readout,
    }


def main():
    cases = {
        case_id: summarize_case(case_id, logical_state, read_kind)
        for case_id, logical_state, read_kind in CASES
    }
    result = {
        "document_type": "r0_raw_analysis",
        "analysis_version": "r0-local-1",
        "phi0_Wb": PHI0,
        "windows_ps": WINDOWS,
        "metric_boundary": "P is raw rad; turns=delta_rad/(2*pi); same-JJ voltage area uses actual CSV time; no SFQ count is inferred.",
        "cases": cases,
    }
    out = ROOT / "analysis" / "r0-analysis.json"
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
