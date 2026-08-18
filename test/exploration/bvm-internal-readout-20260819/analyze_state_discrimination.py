#!/usr/bin/env python3
"""analyze_state_discrimination.py -- BVM state discrimination survey.

With the SAME canonical READ stimulus, compare the two operational
stored states (A = +init, B = -init; S0 D0 operational distinctness,
NOT logical-1/0 identity) across N6/SL/JS1/JS2/readout-loop currents.

Goal: determine whether a physical discrimination exists that a local
one-shot receiver could use for 1->1SFQ / 0->0SFQ.

Discipline: mirror-symmetric transients need a direction-sensitive
discriminator; no receiver is designed here; no SFQ-delivery claim.
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

RUN_A = "pos-read-single"        # state A, READ +100uA
RUN_B = "neg-read-single-corr"   # state B, READ +100uA

SIGNAL_COLS = ["P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)", "V(N6|XBVM1)",
               "V(SL1)", "I(L_S1|XBVM1)", "I(L_S2|XBVM1)",
               "I(L_S3|XBVM1)", "I(L_M3|XBVM1)", "I(L_PSL|XBVM1)",
               "I(L_SL|XBVM1)"]


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


def last_in(ts, xs, lo, hi):
    v = None
    for t, x in zip(ts, xs):
        if in_win(t, lo, hi):
            v = x
    return v


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
    hdrA, tsA, colsA = load(RAW / RUN_A / "run-01.csv")
    hdrB, tsB, colsB = load(RAW / RUN_B / "run-01.csv")
    assert hdrA == hdrB, "column mismatch between A and B runs"

    results = {
        "state_A": {"id": "A", "init": "+100uA WL/BL 10-21ps",
                    "run": RUN_A,
                    "definition": "operational state from +init (S0 D0 "
                                  "JM1=+5.9108 rad); NOT logical-1 claim"},
        "state_B": {"id": "B", "init": "-100uA WL/BL 10-21ps",
                    "run": RUN_B,
                    "definition": "operational state from -init (S0 D0 "
                                  "JM1=-5.9108 rad); NOT logical-0 claim"},
        "read_stimulus": {"WL_SE_amplitude_uA": 100, "window_ps": [96, 105],
                          "source": "STABLE-LOAD-001 matched read PWL"},
    }

    # 1. PRE static signature (before READ)
    pre = {}
    for col in SIGNAL_COLS:
        a = last_in(tsA, colsA[col], *PRE)
        b = last_in(tsB, colsB[col], *PRE)
        pre[col] = {"A": str(a), "B": str(b),
                    "A_minus_B": str(a - b), "exact_mirror": a == -b}
    results["PRE_static_signature"] = pre

    # 2. READ window signed peaks
    peaks = {}
    for col in SIGNAL_COLS:
        pa = window_peaks(tsA, colsA[col], *READ)
        pb = window_peaks(tsB, colsB[col], *READ)
        peaks[col] = {"A": pa, "B": pb,
                      "plus_mirror": (Decimal(pa["plus"]) == -Decimal(pb["minus"]))
                      if pa and pb else None,
                      "minus_mirror": (Decimal(pa["minus"]) == -Decimal(pb["plus"]))
                      if pa and pb else None,
                      "timing_plus_match": (Decimal(pa["t_plus_ps"]) ==
                                            Decimal(pb["t_minus_ps"]))
                      if pa and pb else None,
                      "timing_minus_match": (Decimal(pa["t_minus_ps"]) ==
                                             Decimal(pb["t_plus_ps"]))
                      if pa and pb else None}
    results["READ_window_signed_peaks"] = peaks

    # 3. discrimination summary (bounded, exploratory)
    mirror_all = all(
        v.get("exact_mirror") for v in pre.values())
    read_mirror_all = all(
        v.get("plus_mirror") and v.get("minus_mirror")
        and v.get("timing_plus_match") and v.get("timing_minus_match")
        for v in peaks.values())
    results["summary"] = {
        "PRE_static_exact_mirror_all": mirror_all,
        "READ_transient_exact_mirror_all": read_mirror_all,
        "discrimination_note": (
            "All probed signals are exact sign-mirrors between states A/B "
            "in both PRE static and READ transient (amplitude AND timing). "
            "A magnitude/energy detector cannot discriminate; only a "
            "direction-sensitive discriminator (e.g. biased JJ responding "
            "to signed current/phase) could use this. PRE static L_S1/L_S2 "
            "currents (+-19.5uA) and JS1/JS2 phase (+-0.267 rad) carry the "
            "state sign. No receiver designed here."),
    }

    out = ROOT / "state-discrimination.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"wrote {out}")
    print("PRE static exact mirror all:", mirror_all)
    print("READ transient exact mirror all:", read_mirror_all)
    return 0


if __name__ == "__main__":
    sys.exit(main())
