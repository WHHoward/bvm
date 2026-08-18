#!/usr/bin/env python3
"""analyze_internal_readout_v2.py -- corrected BVM Internal Readout analysis.

Revision 2 (user review 2026-08-19): replaces the invalid >pi/2 sample-jump
event criterion with continuous unwrapped-phase + same-junction voltage
joint segmentation.  Distinguishes:
  - localized 2pi transition(s)
  - multiple separable transitions
  - sustained phase-running without retrapping
Also fixes JM1/JM2 storage-signature independence (previous loop reused the
same output keys) and adds inductive loop-current signatures.

Activity segmentation (bounded, exploration-level, not a frozen gate):
  active sample: |V(B_Jx)| > V_ACT (default 50 uV; justified by static
  PRE mean ~0.22 uV vs READ mean ~0.72 mV).
  An activity interval runs while active; a retrap gap is a run of
  inactive samples between intervals.  Classification per interval pair:
  each interval's unwrapped phase accumulation is compared to k*2pi and
  its voltage-area integral to k*Phi0.
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
TWO_PI = Decimal("6.283185307179586476925286767")
PHI0_WB = Decimal("2.067833848e-15")
PI = Decimal("3.141592653589793238462643383")

RUNS = ["pos-read-single", "pos-read-repeated", "neg-read-single",
        "neg-read-repeated"]

# windows (ps) -- half-open
PRE = (Decimal("80e-12"), Decimal("90e-12"))
READ1 = (Decimal("94e-12"), Decimal("130e-12"))
READ2 = (Decimal("146e-12"), Decimal("182e-12"))
POST1 = (Decimal("140e-12"), Decimal("150e-12"))
POST2 = (Decimal("210e-12"), Decimal("220e-12"))

V_ACT = Decimal("50e-6")          # bounded activity threshold (volts)
MIN_GAP_SAMPLES = 8               # ~0.1 ps inactivity => separable
STORE_COLS = ["P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)",
              "I(L_M1|XBVM1)", "I(L_M2|XBVM1)", "I(L_M3|XBVM1)",
              "I(L_PM|XBVM1)"]


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


def unwrap_phase(ts, ph, lo, hi):
    """Continuous unwrapped phase over window, returned as list of
    (t, unwrapped_phi) for in-window samples."""
    out = []
    prev = None
    acc = Decimal(0)
    for t, p in zip(ts, ph):
        if not in_win(t, lo, hi):
            prev = None
            continue
        if prev is not None:
            d = p - prev
            d = (d + PI) % TWO_PI - PI   # to (-pi, pi]
            acc += d
        else:
            acc = p
        out.append((t, acc))
        prev = p
    return out


def segment_activity(ts, v, lo, hi):
    """Split window samples into activity intervals.  Returns list of
    (i_start, i_end) sample indices where |V| >= V_ACT, merging intervals
    separated by < MIN_GAP_SAMPLES inactive samples."""
    active = [abs(x) >= V_ACT for t, x in zip(ts, v) if in_win(t, lo, hi)]
    if not active:
        return []
    intervals = []
    i = 0
    n = len(active)
    while i < n:
        if active[i]:
            j = i
            while j < n:
                if active[j]:
                    j += 1
                    continue
                # inactive run; merge if short
                k = j
                while k < n and not active[k]:
                    k += 1
                if k - j < MIN_GAP_SAMPLES:
                    j = k
                    continue
                break
            intervals.append((i, j))
            i = j
        else:
            i += 1
    return intervals


def interval_metrics(ts, ph_unw, v, win_idx, w0, w1):
    """Metrics for a contiguous slice of in-window sample indices
    [w0, w1].  ph_unw[w] = (t, unwrapped_phi); win_idx[w] = global index."""
    t0 = ph_unw[w0][0]; t1 = ph_unw[w1][0]
    dphi = ph_unw[w1][1] - ph_unw[w0][1]
    g0 = win_idx[w0]; g1 = win_idx[w1]
    va = Decimal(0)
    for k in range(g0, g1):
        dt = ts[k + 1] - ts[k]
        va += (v[k] + v[k + 1]) / 2 * dt
    dphi_va = va * TWO_PI / PHI0_WB
    return {"t_start_ps": str(t0 * Decimal("1e12")),
            "t_end_ps": str(t1 * Decimal("1e12")),
            "duration_ps": str((t1 - t0) * Decimal("1e12")),
            "dphi_unwrapped_rad": str(dphi),
            "turns": str(dphi / TWO_PI),
            "voltage_area_Vs": str(va),
            "dphi_from_va_rad": str(dphi_va),
            "dphi_matches_va": abs(dphi - dphi_va) < Decimal("0.01"),
            "nearest_int_turns": str(round(float(dphi / TWO_PI)))}


def classify(mets):
    """Joint phase+voltage classification (bounded, exploration).

    The dominant interval carries the main phase accumulation; residual
    intervals whose |turns| << 1 are decaying ringing, not separable
    2pi transitions.  Classification:
      NO_ACTIVITY               : no interval
      LOCALIZED_SINGLE_2PI      : one dominant interval, |turns| ~ 1
      MULTIPLE_SEPARABLE_2PI    : >=2 intervals each with |turns| ~ 1
      SUSTAINED_RUNNING         : one dominant interval, |turns| >= 1.5
      DOMINANT_RUNNING_PLUS_RING: dominant multi-turn + ringing tail
    """
    if not mets:
        return "NO_ACTIVITY"
    turnses = [abs(Decimal(m["turns"])) for m in mets]
    dominant = max(turnses)
    separable = [t for t in turnses if Decimal("0.7") <= t <= Decimal("1.3")]
    if dominant >= Decimal("1.5"):
        if len(separable) >= 2:
            return "MULTIPLE_SEPARABLE_2PI"
        if len(turnses) >= 2 and max(turnses[1:]) < Decimal("0.7"):
            return "DOMINANT_RUNNING_PLUS_RING"
        return "SUSTAINED_RUNNING"
    if len(separable) >= 2:
        return "MULTIPLE_SEPARABLE_2PI"
    if dominant >= Decimal("0.7"):
        return "LOCALIZED_SINGLE_2PI"
    return "WEAK_ACTIVITY"


def window_metrics(ts, cols, lo, hi):
    out = {}
    for jj in ("P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"):
        ph_unw = unwrap_phase(ts, cols[jj], lo, hi)
        v = cols["V(B_JS1|XBVM1)" if "JS1" in jj else "V(B_JS2|XBVM1)"]
        ivs = segment_activity(ts, v, lo, hi)
        win_idx = [i for i, t in enumerate(ts) if in_win(t, lo, hi)]
        mets = [interval_metrics(ts, ph_unw, v, win_idx, a0, a1 - 1)
                for (a0, a1) in ivs]
        out[f"{jj}_intervals"] = mets
        out[f"{jj}_classification"] = classify(mets)
        dphi = ph_unw[-1][1] - ph_unw[0][1] if ph_unw else None
        va = Decimal(0)
        for k in range(len(ts) - 1):
            if in_win(ts[k], lo, hi) and in_win(ts[k + 1], lo, hi):
                va += (v[k] + v[k + 1]) / 2 * (ts[k + 1] - ts[k])
        out[f"{jj}_window_dphi_rad"] = str(dphi)
        out[f"{jj}_window_va_Vs"] = str(va)
        out[f"{jj}_window_va_dphi_rad"] = str(va * TWO_PI / PHI0_WB)
    return out


def storage_signature(ts, cols, lo, hi):
    """Independent per-column signature value (last in-window sample)."""
    out = {}
    for col in STORE_COLS:
        sel = [(t, x) for t, x in zip(ts, cols[col]) if in_win(t, lo, hi)]
        out[col] = str(sel[-1][1]) if sel else None
    return out


def main():
    results = {}
    for run in RUNS:
        path = RAW / run / "run-01.csv"
        hdr, ts, cols = load(path)
        r = {"run": run}
        for wname, (lo, hi) in (("READ1", READ1), ("READ2", READ2)):
            r[wname] = window_metrics(ts, cols, lo, hi)
        results[run] = r
    # storage signature: use diag runs (have L_M1/L_M2/L_PM probes)
    for pol in ("pos", "neg"):
        run = f"{pol}-diag"
        path = RAW / run / "run-01.csv"
        hdr, ts, cols = load(path)
        results[run] = {"run": run}
        for sname, (lo, hi) in (("PRE", PRE), ("POST1", POST1),
                                ("POST2", POST2)):
            results[run][f"storage_{sname}"] = storage_signature(
                ts, cols, lo, hi)
    out_path = ROOT / "analysis-v2.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}")
    for run in RUNS + ["pos-diag", "neg-diag"]:
        r = results[run]
        line = f"{run}:"
        if "READ1" in r:
            for wname in ("READ1", "READ2"):
                for jj in ("P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"):
                    line += (f" {wname} {jj.split('|')[0]}="
                             f"{r[wname][f'{jj}_classification']}")
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
