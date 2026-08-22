#!/usr/bin/env python3
"""R5-C same-JJ phase/area and guard analysis from raw CSVs."""

from __future__ import annotations

import csv
import glob
import json
import math
import os
from statistics import median


PHI0 = 2.067833848e-15
L_H = 100.0e-12
L_TX = 0.20e-12
M = -0.80 * math.sqrt(L_H * L_TX)
BETA_L = 1.5192674482180124
SADDLE_TURN = math.acos(-1.0 / BETA_L) / (2.0 * math.pi)
REQUIRED = {
    "P(B_TRIG|XTRIG)", "V(B_TRIG|XTRIG)", "I(B_TRIG|XTRIG)",
    "I(R_IN|XTRIG)", "I(L_TX|XTRIG)", "P(B_SET|XTRIG)",
    "V(B_SET|XTRIG)", "I(B_SET|XTRIG)", "I(L_QB|XTRIG)",
    "I(R_GAUGE|XTRIG)", "V(SL1)", "V(N6|XBVM1)",
    "P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)",
    "P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)",
}


def load(path):
    with open(path, newline="") as stream:
        reader = csv.DictReader(stream)
        fields = set(reader.fieldnames or [])
        missing = sorted(REQUIRED - fields)
        rows = []
        for row in reader:
            values = {key: float(value) for key, value in row.items() if key != "time"}
            values["time_s"] = float(row["time"])
            rows.append(values)
    return fields, rows, missing


def window(rows, lo_ps, hi_ps):
    return [row for row in rows if lo_ps <= row["time_s"] * 1.0e12 < hi_ps]


def trap(rows, key, start, end):
    segment = rows[start : end + 1]
    return sum(
        0.5 * (a[key] + b[key]) * (b["time_s"] - a["time_s"])
        for a, b in zip(segment, segment[1:])
    )


def extrema(rows, indices, key, threshold_turn=0.005):
    candidates = []
    half = 5
    threshold_rad = threshold_turn * 2.0 * math.pi
    for pos in range(half, len(indices) - half):
        idx = indices[pos]
        y = rows[idx][key]
        left = [rows[indices[j]][key] for j in range(pos - half, pos)]
        right = [rows[indices[j]][key] for j in range(pos + 1, pos + half + 1)]
        if y >= max(left + right):
            kind = "max"
        elif y <= min(left + right):
            kind = "min"
        else:
            continue
        if candidates and candidates[-1]["kind"] == kind:
            better = y > candidates[-1]["value"] if kind == "max" else y < candidates[-1]["value"]
            if better:
                candidates[-1] = {"pos": pos, "index": idx, "kind": kind, "value": y}
            continue
        if candidates and abs(y - candidates[-1]["value"]) < threshold_rad:
            continue
        candidates.append({"pos": pos, "index": idx, "kind": kind, "value": y})
    return candidates


def phase_segments(rows, key_p, key_v, activity_indices):
    ex = extrema(rows, activity_indices, key_p)
    segments = []
    for a, b in zip(ex, ex[1:]):
        ia, ib = a["index"], b["index"]
        phase_turns = (rows[ib][key_p] - rows[ia][key_p]) / (2.0 * math.pi)
        area_turns = trap(rows, key_v, ia, ib) / PHI0
        segments.append(
            {
                "start_ps": rows[ia]["time_s"] * 1.0e12,
                "end_ps": rows[ib]["time_s"] * 1.0e12,
                "start_turn": rows[ia][key_p] / (2.0 * math.pi),
                "end_turn": rows[ib][key_p] / (2.0 * math.pi),
                "phase_turns": phase_turns,
                "area_turns": area_turns,
                "residual_turns": phase_turns - area_turns,
                "monotonic": phase_turns != 0.0,
            }
        )
    segments.sort(key=lambda item: abs(item["phase_turns"]), reverse=True)
    return ex, segments


def med(rows, key, lo, hi):
    values = [row[key] for row in rows if lo <= row["time_s"] * 1.0e12 < hi]
    return median(values) if values else float("nan")


def analyze(path):
    fields, rows, missing = load(path)
    times = [row["time_s"] for row in rows]
    case = os.path.basename(os.path.dirname(path))
    pre = window(rows, 80.0, 90.0)
    activity = window(rows, 97.0, 130.0)
    post = window(rows, 150.0, 170.0)
    pkey = "P(B_SET|XTRIG)"
    vkey = "V(B_SET|XTRIG)"
    activity_indices = [i for i, row in enumerate(rows) if 97.0 <= row["time_s"] * 1.0e12 < 130.0]
    ex, segments = phase_segments(rows, pkey, vkey, activity_indices)
    p_pre = median(row[pkey] for row in pre)
    p_activity = [row[pkey] for row in activity]
    p_post = [row[pkey] for row in post]
    btrig_activity = [row["P(B_TRIG|XTRIG)"] for row in activity]
    btrig_post = [row["P(B_TRIG|XTRIG)"] for row in post]
    fluxoid = [
        row[pkey] / (2.0 * math.pi)
        + (L_H * row["I(L_QB|XTRIG)"] + M * row["I(L_TX|XTRIG)"]) / PHI0
        for row in activity
    ]
    return {
        "case": case,
        "path": path,
        "artifact": {
            "row_count": len(rows),
            "end_ps": times[-1] * 1.0e12 if rows else None,
            "missing_required_columns": missing,
            "time_strictly_increasing": all(a < b for a, b in zip(times, times[1:])),
            "finite": all(math.isfinite(value) for row in rows for key, value in row.items() if key != "time_s"),
        },
        "b_set": {
            "pre_median_turn": p_pre / (2.0 * math.pi),
            "activity_min_turn": min(p_activity) / (2.0 * math.pi),
            "activity_max_turn": max(p_activity) / (2.0 * math.pi),
            "activity_min_relative_turn": (min(p_activity) - p_pre) / (2.0 * math.pi),
            "activity_max_relative_turn": (max(p_activity) - p_pre) / (2.0 * math.pi),
            "post_median_turn": median(p_post) / (2.0 * math.pi),
            "post_p2p_turn": (max(p_post) - min(p_post)) / (2.0 * math.pi),
            "activity_voltage_peak_uV": max(abs(row[vkey]) for row in activity) * 1.0e6,
            "activity_current_peak_uA": max(abs(row["I(B_SET|XTRIG)"]) for row in activity) * 1.0e6,
            "saddle_reverse_turn": -SADDLE_TURN,
            "saddle_forward_turn": SADDLE_TURN,
            "reverse_saddle_crossed": min(p_activity) / (2.0 * math.pi) < -SADDLE_TURN,
            "segments": segments,
            "largest_segment": segments[0] if segments else None,
            "qualifying_complete_segment_count": sum(abs(item["phase_turns"]) >= 1.0 for item in segments),
        },
        "source": {
            "btrig_activity_range_turn": (max(btrig_activity) - min(btrig_activity)) / (2.0 * math.pi),
            "btrig_post_p2p_turn": (max(btrig_post) - min(btrig_post)) / (2.0 * math.pi),
            "i_tx_min_uA": min(row["I(L_TX|XTRIG)"] for row in activity) * 1.0e6,
            "i_tx_max_uA": max(row["I(L_TX|XTRIG)"] for row in activity) * 1.0e6,
            "phi_ext_min_phi0": M * max(row["I(L_TX|XTRIG)"] for row in activity) / PHI0,
            "phi_ext_max_phi0": M * min(row["I(L_TX|XTRIG)"] for row in activity) / PHI0,
            "sl_peak_mV": max(abs(row["V(SL1)"]) for row in activity) * 1.0e3,
            "n6_peak_mV": max(abs(row["V(N6|XBVM1)"]) for row in activity) * 1.0e3,
        },
        "guards": {
            "fluxoid_n_activity_min": min(fluxoid),
            "fluxoid_n_activity_max": max(fluxoid),
            "r_gauge_peak_A": max(abs(row["I(R_GAUGE|XTRIG)"]) for row in rows),
            "storage_pre_post_median_turn": {
                key: {
                    "pre": med(rows, key, 80.0, 90.0) / (2.0 * math.pi),
                    "post": med(rows, key, 150.0, 170.0) / (2.0 * math.pi),
                    "delta": (med(rows, key, 150.0, 170.0) - med(rows, key, 80.0, 90.0)) / (2.0 * math.pi),
                }
                for key in ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"]
            },
        },
    }


def main():
    paths = sorted(glob.glob("test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/raw/*/run-01.csv"))
    report = {
        "constants": {
            "phi0_Wb": PHI0,
            "M_H": M,
            "beta_L": BETA_L,
            "saddle_abs_turn": SADDLE_TURN,
            "event_threshold_turn": 1.0,
            "phase_area_residual_predeclared_abs_turn": 0.05,
        },
        "cases": [analyze(path) for path in paths],
    }
    with open("test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/analysis/r5c-summary.json", "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
