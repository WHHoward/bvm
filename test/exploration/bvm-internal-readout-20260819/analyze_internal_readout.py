#!/usr/bin/env python3
"""analyze_internal_readout.py -- BVM Internal Readout Event Survey analysis.

Exploration-level analysis (scientific-throughput-first).  Reads the 4 raw
CSVs with Decimal literal tokens, answers the survey questions:
  1. JS1/JS2 phase transitions per READ
  2. isolated single-2pi transition candidate
  3. same-JJ phase-change vs voltage-area self-consistency
  4. phase-running / multiple-slip on JS1/JS2
  5. N6 vs SL transient locality/stability
  6. stored-state discrimination in readout dynamics
  7. repeated-READ reproducibility
  8. storage signature preservation across READ
  9. receiver-topology implication (observed/derived only)

Discipline: P() is raw radians; local JJ slip is not SFQ delivery;
cross-checks are same-junction/same-run/same-window only.
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
PHI0_WB = Decimal("2.067833848e-15")  # phi0 in Wb
PI = Decimal("3.141592653589793238462643383")

RUNS = ["pos-read-single", "pos-read-repeated", "neg-read-single",
        "neg-read-repeated"]

# READ windows (ps) -- same shape as accepted source window [94,130)
READ1 = (Decimal("94e-12"), Decimal("130e-12"))
READ2 = (Decimal("146e-12"), Decimal("182e-12"))   # 2nd READ (146-155p)
POST1 = (Decimal("140e-12"), Decimal("150e-12"))   # storage sig after R1
POST2 = (Decimal("210e-12"), Decimal("220e-12"))   # storage sig after R2
PRE = (Decimal("80e-12"), Decimal("90e-12"))       # before READ1

JJS = ["P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)", "P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"]
VOLTS = {"P(B_JS1|XBVM1)": "V(B_JS1|XBVM1)",
         "P(B_JS2|XBVM1)": "V(B_JS2|XBVM1)",
         "P(B_JM1|XBVM1)": "V(B_JM1|XBVM1)",
         "P(B_JM2|XBVM1)": "V(B_JM2|XBVM1)"}


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


def count_slips(ts, ph, lo, hi):
    """Count unwrapped phase steps > pi/2 in window; return (events, net)."""
    events = []
    prev = None
    acc = Decimal(0)
    for t, p in zip(ts, ph):
        if not in_win(t, lo, hi):
            continue
        if prev is not None:
            d = p - prev
            d = (d + PI) % TWO_PI - PI  # unwrap to (-pi, pi]
            acc += d
            if abs(d) > PI / 2:
                events.append((t, d))
        prev = p
    return events, acc


def voltage_area(ts, v, lo, hi):
    """Trapezoid integral of voltage over window (V*s)."""
    total = Decimal(0)
    prev = None
    for t, x in zip(ts, v):
        if not in_win(t, lo, hi):
            prev = None
            continue
        if prev is not None:
            total += (x + prev[1]) / 2 * (t - prev[0])
        prev = (t, x)
    return total


def phase_at_window(ts, ph, lo, hi):
    sel = [(t, p) for t, p in zip(ts, ph) if in_win(t, lo, hi)]
    if not sel:
        return None
    return sel[-1][1]


def transient_stats(ts, v, lo, hi):
    """Peak |x|, peak time, half-peak span in window."""
    sel = [(t, x) for t, x in zip(ts, v) if in_win(t, lo, hi)]
    if not sel:
        return None
    peak = max(abs(x) for _, x in sel)
    tpeak = [t for t, x in sel if abs(x) == peak][0]
    half = [t for t, x in sel if abs(x) >= peak / 2]
    width = (half[-1] - half[0]) * Decimal("1e12") if half else Decimal(0)
    return {"peak_abs": str(peak),
            "t_peak_ps": str(tpeak * Decimal("1e12")),
            "half_peak_span_ps": str(width)}


def analyze_run(run):
    path = RAW / run / "run-01.csv"
    hdr, ts, cols = load(path)
    out = {"run": run, "columns": hdr}
    for win_name, (lo, hi) in (("READ1", READ1), ("READ2", READ2)):
        for jj in ("P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"):
            ev, acc = count_slips(ts, cols[jj], lo, hi)
            n2pi = sum(1 for _, d in ev if abs(d) > PI / 2)
            out[f"{win_name}_{jj}_events"] = len(ev)
            out[f"{win_name}_{jj}_slips_gt_pihalf"] = n2pi
            out[f"{win_name}_{jj}_net_delta_rad"] = str(acc)
            va = voltage_area(ts, cols[VOLTS[jj]], lo, hi)
            dphi_from_va = va * TWO_PI / PHI0_WB
            out[f"{win_name}_{jj}_voltage_area_Vs"] = str(va)
            out[f"{win_name}_{jj}_dphi_from_va_rad"] = str(dphi_from_va)
            out[f"{win_name}_{jj}_self_consistent"] = \
                abs(acc - dphi_from_va) < Decimal("0.01")
        # storage signature
        for jj in ("P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"):
            pre_v = phase_at_window(ts, cols[jj], PRE[0], PRE[1])
            post_v = phase_at_window(ts, cols[jj], POST1[0], POST1[1])
            post2_v = phase_at_window(ts, cols[jj], POST2[0], POST2[1])
            out[f"{win_name}_JM1_post_vs_pre_delta_rad"] = \
                str(post_v - pre_v) if (post_v is not None
                                        and pre_v is not None) else None
            out[f"{win_name}_JM2_post_vs_pre_delta_rad"] = \
                str(post2_v - pre_v) if (post2_v is not None
                                         and pre_v is not None) else None
    # N6 vs SL transient (V)
    for node in ("V(N6|XBVM1)", "V(SL1)"):
        out[f"READ1_{node}_stats"] = transient_stats(ts, cols[node],
                                                     *READ1)
        out[f"READ2_{node}_stats"] = transient_stats(ts, cols[node],
                                                     *READ2)
    # I(L_*) peak in READ1
    for col in ("I(L_S1|XBVM1)", "I(L_S2|XBVM1)", "I(L_S3|XBVM1)",
                "I(L_M3|XBVM1)", "I(L_PSL|XBVM1)", "I(L_SL|XBVM1)"):
        out[f"READ1_{col}_stats"] = transient_stats(ts, cols[col], *READ1)
    return out


def main():
    results = {}
    for run in RUNS:
        results[run] = analyze_run(run)
    out_path = ROOT / "analysis.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"wrote {out_path}")
    for run in RUNS:
        r = results[run]
        line = (f"{run}: JS1 ev={r.get('READ1_P(B_JS1|XBVM1)_events')} "
                f"slips={r.get('READ1_P(B_JS1|XBVM1)_slips_gt_pihalf')} "
                f"dphi={r.get('READ1_P(B_JS1|XBVM1)_net_delta_rad')} | "
                f"JS2 ev={r.get('READ1_P(B_JS2|XBVM1)_events')} "
                f"slips={r.get('READ1_P(B_JS2|XBVM1)_slips_gt_pihalf')} "
                f"dphi={r.get('READ1_P(B_JS2|XBVM1)_net_delta_rad')}")
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
