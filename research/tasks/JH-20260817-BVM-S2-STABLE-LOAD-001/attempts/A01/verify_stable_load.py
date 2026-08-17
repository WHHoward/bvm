#!/usr/bin/env python3
"""verify_stable_load.py -- independent verifier (reads raw + frozen spec only;
does not import the analyzer). Recomputes readiness strata, endpoint-VI
eligibility/compatibility counts and disposition; compares to analysis.json."""
import csv, json, pathlib, sys
from decimal import Decimal
ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
PRE = (Decimal("80e-12"), Decimal("90e-12"))
THRESHOLD = Decimal("0.020")
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
CASES = ["read", "control"]
TOKENS = [Decimal("97"), Decimal("99"), Decimal("101"), Decimal("103"), Decimal("105")]
FLOOR_V = Decimal("5e-6"); FLOOR_I = Decimal("0.5e-6")

def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    times = [Decimal(r[0]) for r in rows[1:]]
    cols = {h: [Decimal(r[j]) for r in rows[1:]] for j, h in enumerate(hdr[1:], start=1)}
    return times, cols

def p2p(t, v, lo, hi):
    sel = [x for tt, x in zip(t, v) if lo <= tt < hi]
    return max(sel) - min(sel)

def mean(t, v, lo, hi):
    sel = [x for tt, x in zip(t, v) if lo <= tt < hi]
    return sum(sel) / len(sel)

def idx(times, tk):
    w = tk * Decimal("1e-12")
    for i, tt in enumerate(times):
        if tt == w:
            return i
    raise ValueError(f"token {tk} ps absent")

def main() -> int:
    analysis = json.loads((ATTEMPT / "analysis.json").read_text())
    ready = {}
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            ok = True
            for case in CASES:
                t, c = load_csv(RUN / "raw" / f"{key}-{case}" / "run-01.csv")
                for jj in ("P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"):
                    if p2p(t, c[jj], *PRE) > THRESHOLD:
                        ok = False
            ready[key] = ok
    fails = []
    for s in analysis["strata"]:
        if s["ready"] != ready[s["id"]]:
            fails.append(f"stratum {s['id']} readiness mismatch")
    for pol in POLS:
        exp = analysis["endpoint_vi"][pol]
        if not all(ready[f"L{l:02d}-{pol}"] for l in LOADS):
            if exp["summaries"]["eligible"] != 0:
                fails.append(f"{pol} endpoint should be empty (strata not ready)")
            continue
        el = comp = ns = ill = 0
        for tk in TOKENS:
            vstar, istar = {}, {}
            for load in LOADS:
                tr, cr = load_csv(RUN / "raw" / f"L{load:02d}-{pol}-read" / "run-01.csv")
                tc, cc = load_csv(RUN / "raw" / f"L{load:02d}-{pol}-control" / "run-01.csv")
                mr = mean(tr, cr["V(SL1)"], *PRE); mc = mean(tc, cc["V(SL1)"], *PRE)
                mi_r = mean(tr, cr["I(L_SL|XBVM1)"], *PRE); mi_c = mean(tc, cc["I(L_SL|XBVM1)"], *PRE)
                vstar[load] = cr["V(SL1)"][idx(tr, tk)] - mr - (cc["V(SL1)"][idx(tc, tk)] - mc)
                istar[load] = cr["I(L_SL|XBVM1)"][idx(tr, tk)] - mi_r - (cc["I(L_SL|XBVM1)"][idx(tc, tk)] - mi_c)
            d_i = istar[50] - istar[1]; d_v = vstar[50] - vstar[1]
            if abs(d_i) < FLOOR_I or abs(d_v) < FLOOR_V:
                ill += 1; continue
            rhat = -d_v / d_i; vth = vstar[1] + rhat * istar[1]
            e_max = max(abs(vstar[L] - (vth - rhat * istar[L])) for L in LOADS)
            el += 1
            if e_max <= max(FLOOR_V, Decimal("0.01") * abs(d_v)):
                comp += 1
            else:
                ns += 1
        s = exp["summaries"]
        if (el, comp, ns, ill) != (s["eligible"], s["compatible"], s["not_supported"], s["ill_conditioned"]):
            fails.append(f"{pol} endpoint counts mismatch")
    if fails:
        print("VERIFY FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print(f"VERIFY PASS: 16 runs, 8 strata readiness, endpoint-VI "
          f"recomputed; disposition {analysis['disposition']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
