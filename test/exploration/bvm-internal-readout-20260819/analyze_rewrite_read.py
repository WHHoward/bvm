#!/usr/bin/env python3
"""analyze_rewrite_read.py -- continuous rewrite/read closure analysis.

Analyzes rewrite-read-1010 and rewrite-read-0101 (4 cycles x 170 ps).
Cycle k windows (relative to cycle offset 170k ps):
  PRE    [80, 90)   -- storage signature before READ
  READ   [94, 130)  -- READ window (equivalent to isolated canonical)
  POST   [140, 150) -- post-READ recovery observation

Per cycle reports:
  - JM1/JM2 phase at PRE/POST (storage signature flip)
  - L_M1/L_M2/L_M3/L_PM currents at PRE/POST
  - JS1/JS2 unwrapped turns in READ window
  - N6/SL signed/absolute peaks + timing
  - L_S1/S2/S3 READ peaks
Questions: write/read correctness, read1 running persistence,
read0 no-running persistence, cycle-to-cycle reproducibility,
drift/history dependence, cross-cycle write interference.
Reference comparison: isolated canonical runs (pos-read-single,
neg-init-pos-read) -- informational, not byte-identical requirement.
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

PI = Decimal("3.141592653589793238462643383")
TWO_PI = Decimal("6.283185307179586476925286767")
CYCLE_PS = Decimal("170")

SEQS = {"rewrite-read-1010": [1, 0, 1, 0],
        "rewrite-read-0101": [0, 1, 0, 1]}

PHASE_COLS = ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)",
              "P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"]
CURR_COLS = ["I(L_M1|XBVM1)", "I(L_M2|XBVM1)", "I(L_M3|XBVM1)",
             "I(L_PM|XBVM1)", "I(L_S1|XBVM1)", "I(L_S2|XBVM1)",
             "I(L_S3|XBVM1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)"]
NODE_COLS = ["V(N6|XBVM1)", "V(SL1)"]


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


def window_value(ts, xs, lo, hi):
    sel = [(t, x) for t, x in zip(ts, xs) if in_win(t, lo, hi)]
    if not sel:
        return None
    return sel[-1][1]


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
            "minus": str(pmin[1]),
            "abs_peak": str(max(abs(pmax[1]), abs(pmin[1])))}


def cycle_analysis(ts, cols, k):
    o = k * CYCLE_PS * Decimal("1e-12")
    pre = (o + Decimal("80e-12"), o + Decimal("90e-12"))
    read = (o + Decimal("94e-12"), o + Decimal("130e-12"))
    post = (o + Decimal("140e-12"), o + Decimal("150e-12"))

    out = {"cycle": k}
    for col in PHASE_COLS:
        pv = window_value(ts, cols[col], *pre)
        po = window_value(ts, cols[col], *post)
        out[f"PRE_{col}"] = str(pv)
        out[f"POST_{col}"] = str(po)
        out[f"PREPOST_{col}_delta"] = str(po - pv)
    for col in CURR_COLS:
        out[f"PRE_{col}"] = str(window_value(ts, cols[col], *pre))
        out[f"POST_{col}"] = str(window_value(ts, cols[col], *post))
    for col in ("P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"):
        d = unwrapped_delta(ts, cols[col], *read)
        out[f"READ_{col}_dphi_rad"] = str(d)
        out[f"READ_{col}_turns"] = str(d / TWO_PI)
    for col in NODE_COLS:
        out[f"READ_{col}_peaks"] = window_peaks(ts, cols[col], *read)
    for col in ("I(L_S1|XBVM1)", "I(L_S2|XBVM1)", "I(L_S3|XBVM1)",
                "I(L_SL|XBVM1)"):
        out[f"READ_{col}_peaks"] = window_peaks(ts, cols[col], *read)
    return out


def main() -> int:
    results = {}
    for seq_name, bits in SEQS.items():
        hdr, ts, cols = load(RAW / seq_name / "run-01.csv")
        cycles = []
        for k in range(4):
            c = cycle_analysis(ts, cols, k)
            c["expected_write"] = bits[k]
            c["read_is_read1"] = bits[k] == 1
            cycles.append(c)
        results[seq_name] = {"sequence": bits, "cycles": cycles}

    out_path = ROOT / "rewrite-read-analysis.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}")

    for seq_name, bits in SEQS.items():
        print(f"=== {seq_name} (write seq {bits}) ===")
        for c in results[seq_name]["cycles"]:
            js1 = c["READ_P(B_JS1|XBVM1)_turns"]
            js2 = c["READ_P(B_JS2|XBVM1)_turns"]
            n6 = c["READ_V(N6|XBVM1)_peaks"]
            jm1_pre = c["PRE_P(B_JM1|XBVM1)"]
            jm1_post = c["POST_P(B_JM1|XBVM1)"]
            print(f"  cyc{c['cycle']} write={c['expected_write']} "
                  f"JS1={js1[:10]} JS2={js2[:10]} "
                  f"N6=+{n6['plus'][:9]}@ps{n6['t_plus_ps'][:8]} "
                  f"JM1_pre={jm1_pre[:10]} post={jm1_post[:10]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
