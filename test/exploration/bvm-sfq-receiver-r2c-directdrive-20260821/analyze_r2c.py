#!/usr/bin/env python3
"""R2-C direct-drive threshold analysis: same event criteria as R2-A/R2-B."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PHI0_WB = 2.067833848e-15
TWO_PI = 2.0 * math.pi

POINTS = [
    ("ctrl-nopulse", 0.0),
    ("amp20u0", 2.0),
    ("amp30u0", 3.0),
    ("amp40u0", 4.0),
    ("amp50u0", 5.0),
]
WINDOWS = {
    "PRE": (80.0, 90.0),
    "PULSE_ACTIVITY": (94.0, 130.0),
    "OUTPUT_ANALYSIS": (94.0, 170.0),
    "POST": (130.0, 170.0),
    "STORAGE_POST": (140.0, 150.0),
}
OUT_PHASE = "P(B_OUT|XTRIG)"
OUT_VOLTAGE = "V(B_OUT|XTRIG)"
REQUIRED = [
    "time", OUT_PHASE, OUT_VOLTAGE, "I(B_OUT|XTRIG)", "I(I_OUT_BIAS|XTRIG)",
    "I(R_OUT_DAMP|XTRIG)", "V(N_SEC|XTRIG)", "I(L_SEC|XTRIG)",
    "I(R_SEC_LOAD|XTRIG)", "P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "V(SL1)",
    "V(N6|XBVM1)", "I(L_SL|XBVM1)",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_csv(path: Path):
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        rows = []
        for raw in reader:
            row = {key: float(value) for key, value in raw.items()}
            row["_t"] = row["time"] * 1e12
            rows.append(row)
    return fields, rows


def select(rows, interval):
    lo, hi = interval
    return [r for r in rows if lo <= r["_t"] <= hi]


def median(rows, key):
    return statistics.median(r[key] for r in rows)


def trapezoid(rows, key):
    return sum(
        0.5 * (a[key] + b[key]) * (b["time"] - a["time"])
        for a, b in zip(rows, rows[1:])
    )


def unwrap(rows, phase_key):
    state = "_unwrapped"
    rows[0][state] = rows[0][phase_key]
    for prev, cur in zip(rows, rows[1:]):
        d = cur[phase_key] - prev[phase_key]
        while d > math.pi:
            d -= TWO_PI
        while d < -math.pi:
            d += TWO_PI
        cur[state] = prev[state] + d


def segments(rows):
    if len(rows) < 2:
        return []
    out = []
    start = 0
    direction = None

    def append(end, sign):
        nonlocal start
        if end <= start or sign is None:
            return
        left, right = rows[start], rows[end]
        delta_rad = right["_unwrapped"] - left["_unwrapped"]
        delta_turns = delta_rad / TWO_PI
        area_wb = trapezoid(rows[start : end + 1], OUT_VOLTAGE)
        area_turns = area_wb / PHI0_WB
        out.append({
            "start_ps": left["_t"], "end_ps": right["_t"],
            "direction": "increasing" if sign > 0 else "decreasing",
            "delta_turns": delta_turns,
            "abs_turns": abs(delta_turns),
            "area_turns": area_turns,
            "area_minus_phase_turns": area_turns - delta_turns,
            "complete_2pi": abs(delta_turns) >= 1.0,
            "complete_and_consistent": abs(delta_turns) >= 1.0
            and abs(area_turns - delta_turns) <= 0.05,
            "rows": end - start + 1,
        })

    for i in range(1, len(rows)):
        d = rows[i]["_unwrapped"] - rows[i - 1]["_unwrapped"]
        s = 1 if d > 0 else -1 if d < 0 else 0
        if s == 0:
            continue
        if direction is None:
            direction = s
        elif s != direction:
            append(i - 1, direction)
            start = i
            direction = s
    append(len(rows) - 1, direction)
    return out


def analyze_point(pid, amp_uA):
    path = ROOT / "raw" / pid / "run-01.csv"
    fields, rows = load_csv(path)
    missing = [k for k in REQUIRED if k not in fields]
    times = [r["_t"] for r in rows]
    dts = [b - a for a, b in zip(times, times[1:])]
    finite = all(math.isfinite(v) for r in rows for k, v in r.items() if k != "_unwrapped")
    increasing = all(b > a for a, b in zip(times, times[1:]))
    unwrap(rows, OUT_PHASE)

    pre = select(rows, WINDOWS["PRE"])
    ib_base = median(pre, "I(B_OUT|XTRIG)")
    v_base = median(pre, "V(N_SEC|XTRIG)")

    act = select(rows, WINDOWS["PULSE_ACTIVITY"])
    dib = [(r["I(B_OUT|XTRIG)"] - ib_base) * 1e6 for r in act]
    dv = [(r["V(N_SEC|XTRIG)"] - v_base) * 1e6 for r in act]

    oa = select(rows, WINDOWS["OUTPUT_ANALYSIS"])
    segs = segments(oa)
    complete = [s for s in segs if s["complete_2pi"]]
    qualifying = [
        s for s in complete
        if s["start_ps"] <= 130.0 and abs(s["area_minus_phase_turns"]) <= 0.05
    ]
    post = select(rows, WINDOWS["POST"])
    post_v_peak = max((abs(r[OUT_VOLTAGE]) for r in post), default=0.0)
    post_segs = segments(post)
    post_monotonic_turns = max((abs(s["abs_turns"]) for s in post_segs), default=0.0)

    storage_post = select(rows, WINDOWS["STORAGE_POST"])
    jm1 = median(storage_post, "P(B_JM1|XBVM1)")
    jm2 = median(storage_post, "P(B_JM2|XBVM1)")

    largest = max(segs, key=lambda s: s["abs_turns"], default=None)
    total_complete_turns = sum(int(abs(s["delta_turns"]) + 1e-9) for s in complete)
    return {
        "id": pid,
        "amplitude_uA": amp_uA,
        "csv_sha256": sha256(path),
        "qa": {
            "rows": len(rows), "dt_min_ps": min(dts), "dt_max_ps": max(dts),
            "strictly_increasing": increasing, "all_finite": finite,
            "missing_columns": missing,
            "artifact_valid": bool(rows) and not missing and increasing and finite,
        },
        "drive_diagnostics": {
            "max_delta_i_bout_uA": max(dib), "min_delta_i_bout_uA": min(dib),
            "max_delta_v_nsec_uV": max(dv), "min_delta_v_nsec_uV": min(dv),
            "i_bout_abs_peak_uA": max(abs(r["I(B_OUT|XTRIG)"]) for r in act) * 1e6,
        },
        "output": {
            "largest_segment": largest,
            "n_complete_segments": len(complete),
            "total_complete_turn_units": total_complete_turns,
            "qualifying_event": bool(qualifying),
            "qualifying_segments": qualifying,
            "post_window_v_peak_uV": post_v_peak * 1e6,
            "post_window_largest_monotonic_turns": post_monotonic_turns,
        },
        "storage": {"jm1_post_rad": jm1, "jm2_post_rad": jm2},
    }


def main():
    results = [analyze_point(pid, amp) for pid, amp in POINTS]
    first_threshold = next(
        (r for r in results if r["amplitude_uA"] > 0 and r["output"]["qualifying_event"]),
        None,
    )
    summary = {
        "document_type": "exploration_aggregate",
        "experiment": "R2-C direct-drive B_OUT activation-threshold calibration",
        "points": results,
        "first_qualifying_amplitude_uA": (
            first_threshold["amplitude_uA"] if first_threshold else None
        ),
        "verdict_candidate": (
            "THRESHOLD_FOUND" if first_threshold else
            "NO_THRESHOLD_IN_BOUNDED_MATRIX"
        ),
    }
    (ROOT / "analysis" / "r2c-summary.json").write_text(json.dumps(summary, indent=2))
    for r in results:
        o = r["output"]
        ls = o["largest_segment"]
        span = f"{ls['start_ps']:.1f}-{ls['end_ps']:.1f}ps"
        print(f"{r['id']:14s} amp={r['amplitude_uA']:.1f}uA valid={r['qa']['artifact_valid']} "
              f"largest={ls['abs_turns']:.6f}t({ls['direction'][:3]},{span}) "
              f"resid={ls['area_minus_phase_turns']:+.2e} complete={o['n_complete_segments']} "
              f"qualifying={o['qualifying_event']} postVpk={o['post_window_v_peak_uV']:.1f}uV "
              f"postMono={o['post_window_largest_monotonic_turns']:.4f}t "
              f"dIBmax={r['drive_diagnostics']['max_delta_i_bout_uA']:+.2f}uA "
              f"JM1={r['storage']['jm1_post_rad']:+.3f}")


if __name__ == "__main__":
    main()
