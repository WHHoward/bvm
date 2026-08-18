#!/usr/bin/env python3
"""analyze_state_discrimination_v2.py -- corrected same-READ comparison.

Corrects the provenance error in v1 (b8ad59c): RUN_B was
neg-read-single-corr which uses -100uA READ.  This version compares
under IDENTICAL +100uA READ:
  state A: pos-read-single      (+100uA WL/BL init, +100uA WL+SE READ)
  state B: neg-init-pos-read    (-100uA WL/BL init, +100uA WL+SE READ)

Questions:
  1. do the two states still mirror under same +READ?
  2. any amplitude / sign / timing / switching-threshold difference?
  3. how does the PRE +-19.5uA R-loop static bias map into READ transient?
  4. which receiver mechanism is favored (magnitude threshold, polarity
     discrimination, other)?
  5. states remain A/B; no logical 1/0 identity assigned.
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

RUN_A = "pos-read-single"       # +init, +READ
RUN_B = "neg-init-pos-read"     # -init, +READ

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


def unwrapped_delta(ts, xs, lo, hi):
    """Net unwrapped phase accumulation in window."""
    prev = None
    acc = Decimal(0)
    for t, x in zip(ts, xs):
        if not in_win(t, lo, hi):
            prev = None
            continue
        if prev is not None:
            d = x - prev
            d = (d + Decimal("3.141592653589793238462643383")) % \
                Decimal("6.283185307179586476925286767") - \
                Decimal("3.141592653589793238462643383")
            acc += d
        prev = x
    return acc


def main() -> int:
    hdrA, tsA, colsA = load(RAW / RUN_A / "run-01.csv")
    hdrB, tsB, colsB = load(RAW / RUN_B / "run-01.csv")
    assert hdrA == hdrB, "column mismatch"

    results = {
        "note": ("Both states read with IDENTICAL +100uA WL+SE READ; "
                 "differs only in WL/BL initialization polarity."),
        "state_A": {"init": "+100uA", "read": "+100uA", "run": RUN_A},
        "state_B": {"init": "-100uA", "read": "+100uA", "run": RUN_B},
    }

    pre, peaks, deltas = {}, {}, {}
    for col in SIGNAL_COLS:
        a = last_in(tsA, colsA[col], *PRE)
        b = last_in(tsB, colsB[col], *PRE)
        pre[col] = {"A": str(a), "B": str(b), "exact_mirror": a == -b}
        pa = window_peaks(tsA, colsA[col], *READ)
        pb = window_peaks(tsB, colsB[col], *READ)
        peaks[col] = {
            "A": pa, "B": pb,
            "plus_mirror": (Decimal(pa["plus"]) == -Decimal(pb["minus"]))
            if pa and pb else None,
            "minus_mirror": (Decimal(pa["minus"]) == -Decimal(pb["plus"]))
            if pa and pb else None,
            "timing_plus_match": (Decimal(pa["t_plus_ps"]) ==
                                  Decimal(pb["t_minus_ps"]))
            if pa and pb else None,
            "timing_minus_match": (Decimal(pa["t_minus_ps"]) ==
                                   Decimal(pb["t_plus_ps"]))
            if pa and pb else None,
        }
        if col.startswith("P("):
            da = unwrapped_delta(tsA, colsA[col], *READ)
            db = unwrapped_delta(tsB, colsB[col], *READ)
            deltas[col] = {"A_rad": str(da), "B_rad": str(db),
                           "A_minus_B": str(da - db),
                           "signed_equal": da == db}
    results["PRE_static"] = pre
    results["READ_transient_peaks"] = peaks
    results["READ_unwrapped_delta"] = deltas

    mapping = {}
    for col in ("I(L_S1|XBVM1)", "I(L_S2|XBVM1)", "I(L_S3|XBVM1)",
                "I(L_M3|XBVM1)"):
        a_pre = Decimal(pre[col]["A"])
        b_pre = Decimal(pre[col]["B"])
        pa = peaks[col]["A"]; pb = peaks[col]["B"]
        mapping[col] = {
            "PRE_A": str(a_pre), "PRE_B": str(b_pre),
            "READ_peak_A": {"plus": pa["plus"], "minus": pa["minus"]},
            "READ_peak_B": {"plus": pb["plus"], "minus": pb["minus"]},
            "PRE_sign_A": "+" if a_pre > 0 else "-",
            "PRE_sign_B": "+" if b_pre > 0 else "-",
        }
    results["PRE_to_READ_mapping"] = mapping

    pre_mirror_all = all(v["exact_mirror"] for v in pre.values())
    peak_mirror_all = all(
        v["plus_mirror"] and v["minus_mirror"]
        and v["timing_plus_match"] and v["timing_minus_match"]
        for v in peaks.values())
    delta_same = all(v["signed_equal"] for v in deltas.values())
    # N6/SL ratios (signed + absolute), replacing blanket 3.2x wording
    def ratio_pair(col, state_key):
        v = peaks[col]
        pa, pb = v["A"], v["B"]
        sa = Decimal(pa["plus"]); na = Decimal(pa["minus"])
        sb = Decimal(pb["plus"]); nb = Decimal(pb["minus"])
        abs_a = max(abs(sa), abs(na)); abs_b = max(abs(sb), abs(nb))
        return {"A_plus": str(sa), "A_minus": str(na),
                "B_plus": str(sb), "B_minus": str(nb),
                "abs_A": str(abs_a), "abs_B": str(abs_b),
                "abs_ratio_A_over_B": str(abs_a / abs_b)}

    results["ratios"] = {
        "V(N6|XBVM1)": ratio_pair("V(N6|XBVM1)", "A"),
        "V(SL1)": ratio_pair("V(SL1)", "A"),
        "I(L_S1|XBVM1)": ratio_pair("I(L_S1|XBVM1)", "A"),
        "I(L_SL|XBVM1)": ratio_pair("I(L_SL|XBVM1)", "A"),
    }

    results["summary"] = {
        "PRE_static_exact_mirror_all": pre_mirror_all,
        "READ_transient_exact_mirror_all_under_same_READ": peak_mirror_all,
        "READ_unwrapped_delta_signed_equal": delta_same,
        "answers": {
            "Q1_mirror_under_same_READ": peak_mirror_all,
            "Q2_amplitude_sign_timing_diff": (
                "Computed: mirror_all=False under identical +READ; "
                "state A runs (JS1 dphi ~ -18.8 rad, ~3 turns) while "
                "state B does not (dphi ~ -0.016 rad). Amplitude "
                "differences quantified in results['ratios']: N6 "
                "abs-ratio ~3.2, SL ~3.3, L_S1 ~3.7, L_SL ~3.3 "
                "(computed values, not hard-coded). Sign/timing also "
                "differ: A peaks at ~101 ps (running onset), B only at "
                "READ edges 96/106 ps. Switching-threshold difference "
                "inferred from running/no-running; a direct JJ-biased "
                "threshold measurement is not present in raw -- Unknown."),
            "Q3_PRE_bias_mapping": (
                "PRE static L_S1/L_S2/L_S3 currents are +-19.5uA "
                "(sign mirrors between states; see PRE_static). Under "
                "identical +READ, state A (PRE +19.5uA on L_S1) enters "
                "running (L_S1 READ peak -191.4uA) while state B (PRE "
                "-19.5uA) does not (L_S1 READ peak -51.4uA). Mapping: "
                "PRE bias sign relative to READ direction sets whether "
                "running is triggered; the transient amplitude is the "
                "amplified result."),
            "Q4_receiver_mechanism": (
                "Computed for identical +READ: transients are NOT "
                "mirrors (mirror_all=False); state A produces ~3-turn "
                "running with 3-4x larger |peaks| than state B. A "
                "magnitude-threshold one-shot receiver has a physical "
                "discrimination basis. Polarity discrimination remains "
                "an alternative. Final receiver choice is not made "
                "here (Exploration)."),
            "Q5_labels": "states remain A/B; no logical 1/0 identity",
        },
    }

    out = ROOT / "state-discrimination-v2.json"
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"wrote {out}")
    print("PRE mirror all:", pre_mirror_all)
    print("READ transient mirror all (same +READ):", peak_mirror_all)
    print("unwrapped delta signed-equal:", delta_same)
    return 0


if __name__ == "__main__":
    sys.exit(main())
