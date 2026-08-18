#!/usr/bin/env python3
"""analyze_state_matrix_2x2.py -- 2x2 state/READ-polarity matrix.

Completes the 2x2 closure:
  A/+READ   pos-read-single      (+100uA init, +100uA WL+SE READ)
  A/-READ   pos-init-neg-read    (+100uA init, -100uA WL+SE READ)
  B/+READ   neg-init-pos-read    (-100uA init, +100uA WL+SE READ)
  B/-READ   neg-read-single-corr (-100uA init, -100uA WL+SE READ)

Checks the matched/mismatched hypothesis:
  matched   (state sign == READ sign)  -> running triggered
  mismatched(state sign != READ sign)  -> no running

Per run reports: JS1/JS2 unwrapped dphi, same-JJ voltage, N6, SL,
L_S1/S2/S3 (plus L_M3, L_PSL, L_SL for completeness).  N6/SL ratios are
computed (signed + absolute), not hard-coded.
"""

import csv
import json
import pathlib
import sys
from decimal import Decimal, ROUND_HALF_EVEN, getcontext

ctx = getcontext()
ctx.prec = 28
ctx.rounding = ROUND_HALF_EVEN

ROOT = pathlib.Path(__file__).resolve().parent
RAW = ROOT / "raw"

PRE = (Decimal("80e-12"), Decimal("90e-12"))
READ = (Decimal("94e-12"), Decimal("130e-12"))
PI = Decimal("3.141592653589793238462643383")
TWO_PI = Decimal("6.283185307179586476925286767")

MATRIX = {
    "A/+READ":   {"run": "pos-read-single",      "init": "+", "read": "+"},
    "A/-READ":   {"run": "pos-init-neg-read",    "init": "+", "read": "-"},
    "B/+READ":   {"run": "neg-init-pos-read",    "init": "-", "read": "+"},
    "B/-READ":   {"run": "neg-read-single-corr", "init": "-", "read": "-"},
}

SIGNAL_COLS = ["P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)", "V(B_JS1|XBVM1)",
               "V(B_JS2|XBVM1)", "V(N6|XBVM1)", "V(SL1)",
               "I(L_S1|XBVM1)", "I(L_S2|XBVM1)", "I(L_S3|XBVM1)",
               "I(L_M3|XBVM1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)"]


def load(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    hdr = [h.strip().strip('"') for h in rows[0]]
    data = rows[1:]
    times = [Decimal(r[0]) for r in data]
    cols = {h: [Decimal(r[j]) for r in data]
            for j, h in enumerate(hdr[1:], start=1)}
    return hdr, times, cols


def in_win(t, lo, hi):
    return lo <= t < hi


def unwrapped_delta(ts, xs, lo, hi):
    prev = None
    acc = Decimal(0)
    for t, x in zip(ts, xs):
        if not in_win(t, lo, hi):
            prev = None
            continue
        if prev is not None:
            d = x - prev
            d = (d + PI) % TWO_PI - PI
            acc += d
        prev = x
    return acc


def window_peaks(ts, xs, lo, hi):
    vals = [(t, x) for t, x in zip(ts, xs) if in_win(t, lo, hi)]
    if not vals:
        return None
    pmax = max(vals, key=lambda p: p[1])
    pmin = min(vals, key=lambda p: p[1])
    return {"t_plus_ps": str(pmax[0] * Decimal("1e12")),
            "plus": str(pmax[1]),
            "t_minus_ps": str(pmin[0] * Decimal("1e12")),
            "minus": str(pmin[1])}


def main() -> int:
    runs = {}
    for key, meta in MATRIX.items():
        hdr, ts, cols = load(RAW / meta["run"] / "run-01.csv")
        entry = {"meta": meta}
        for col in SIGNAL_COLS:
            if col.startswith("P("):
                d = unwrapped_delta(ts, cols[col], *READ)
                entry[col] = {"dphi_rad": str(d),
                              "turns": str(d / TWO_PI)}
            else:
                entry[col] = {"peaks": window_peaks(ts, cols[col], *READ)}
        runs[key] = entry

    hyp = {}
    for key, meta in MATRIX.items():
        matched = meta["init"] == meta["read"]
        js1_turns = abs(Decimal(runs[key]["P(B_JS1|XBVM1)"]["turns"]))
        hyp[key] = {"matched": matched,
                    "JS1_abs_turns": str(js1_turns),
                    "running": js1_turns >= Decimal("1.5")}
    hyp_check = all(v["running"] == v["matched"] for v in hyp.values())

    def ratio(a_key, b_key, col):
        pa = runs[a_key][col]["peaks"]
        pb = runs[b_key][col]["peaks"]
        abs_a = max(abs(Decimal(pa["plus"])), abs(Decimal(pa["minus"])))
        abs_b = max(abs(Decimal(pb["plus"])), abs(Decimal(pb["minus"])))
        return {"A_abs": str(abs_a), "B_abs": str(abs_b),
                "abs_ratio_A_over_B": str(abs_a / abs_b),
                "A_plus": pa["plus"], "A_minus": pa["minus"],
                "B_plus": pb["plus"], "B_minus": pb["minus"],
                "A_peak_ps": pa["t_plus_ps"], "B_peak_ps": pb["t_plus_ps"]}

    ratios = {
        "N6_same_+READ_A_vs_B": ratio("A/+READ", "B/+READ", "V(N6|XBVM1)"),
        "SL_same_+READ_A_vs_B": ratio("A/+READ", "B/+READ", "V(SL1)"),
        "N6_same_-READ_A_vs_B": ratio("A/-READ", "B/-READ", "V(N6|XBVM1)"),
        "SL_same_-READ_A_vs_B": ratio("A/-READ", "B/-READ", "V(SL1)"),
        "L_S1_same_+READ_A_vs_B": ratio("A/+READ", "B/+READ",
                                        "I(L_S1|XBVM1)"),
        "L_S1_same_-READ_A_vs_B": ratio("A/-READ", "B/-READ",
                                        "I(L_S1|XBVM1)"),
    }

    out = {
        "matrix": runs,
        "matched_mismatched_hypothesis": hyp,
        "hypothesis_holds_all_cells": hyp_check,
        "ratios": ratios,
        "summary": {
            "running_definition": "JS1 |turns| >= 1.5 in READ window",
            "note": ("matched (state sign == READ sign) -> running; "
                     "mismatched -> no running. States remain A/B; no "
                     "logical 1/0 identity. No receiver designed."),
        },
    }
    out_path = ROOT / "state-matrix-2x2.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}")
    print("cell       matched  JS1_turns  running")
    for key, v in hyp.items():
        print(f"{key:9s}  {str(v['matched']):7s}  "
              f"{v['JS1_abs_turns'][:10]:10s}  {v['running']}")
    print("hypothesis holds in all 4 cells:", hyp_check)
    return 0


if __name__ == "__main__":
    sys.exit(main())
