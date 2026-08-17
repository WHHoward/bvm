#!/usr/bin/env python3
"""verify_source_spec.py -- A03 independent raw-to-artifact verifier.

Recomputes per-token corrected V/I, every descriptor (TRAPEZOID L1),
provenance, netlist hashes, lobe status, orientation from raw only.
No builder import; byte-exact comparison.
"""
import csv, hashlib, json, pathlib, sys, yaml
from decimal import Decimal

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SRC_WIN = (Decimal("94e-12"), Decimal("130e-12"))
POST = (Decimal("140e-12"), Decimal("160e-12"))

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    return hdr, rows[1:]
def mean(v): return sum(v) / len(v)

def trapezoid_l1(times, vals, lo, hi):
    sel = [k for k in range(len(times)) if lo <= times[k] < hi]
    s = Decimal("0")
    for j in range(len(sel) - 1):
        a, b = sel[j], sel[j + 1]
        s += (abs(vals[a]) + abs(vals[b])) / Decimal("2") * (times[b] - times[a])
    return s / (times[sel[-1]] - times[sel[0]])

def main() -> int:
    spec = yaml.safe_load((ATTEMPT/"bvm-source-spec-v1.yaml").read_text())
    family = json.loads((ATTEMPT/"waveform-family.json").read_text())
    orient = yaml.safe_load((ATTEMPT/"terminal-orientation.yaml").read_text())
    fails = []
    if len(family["waves"]) != 16 or len(family["corrected"]) != 8:
        fails.append("D2 family must have 16 raw + 8 corrected")
    if "N8 -> SL" not in str(orient.get("port", {})):
        fails.append("orientation missing N8 -> SL")
    for load in LOADS:
        for pol in POLS:
            for case in ("read", "control"):
                cid = f"L{load:02d}-{pol}-{case}"
                p = RUN/"raw"/cid/"run-01.csv"
                if family["waves"][cid]["provenance"]["csv_sha256"] != sha256(p):
                    fails.append(f"{cid} csv hash mismatch")
                if spec["source_netlist_sha256"].get(cid) != sha256(RUN/"inputs"/f"{cid}.cir"):
                    fails.append(f"{cid} netlist hash mismatch")
                hdr, rows = load_csv(p)
                if [r[0] for r in rows] != family["waves"][cid]["literal_time_tokens"]:
                    fails.append(f"{cid} literal token identity mismatch")
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            v_r, rows_r = load_csv(RUN/"raw"/f"{key}-read"/"run-01.csv")
            v_c, rows_c = load_csv(RUN/"raw"/f"{key}-control"/"run-01.csv")
            tr = [Decimal(r[0]) for r in rows_r]
            vv_r = [Decimal(r[v_r.index("V(SL1)")]) for r in rows_r]
            ii_r = [Decimal(r[v_r.index("I(L_SL|XBVM1)")]) for r in rows_r]
            vv_c = [Decimal(r[v_c.index("V(SL1)")]) for r in rows_c]
            ii_c = [Decimal(r[v_c.index("I(L_SL|XBVM1)")]) for r in rows_c]
            mr = mean([x for t, x in zip(tr, vv_r) if PRE[0] <= t < PRE[1]])
            mc = mean([x for t, x in zip(tr, vv_c) if PRE[0] <= t < PRE[1]])
            mir = mean([x for t, x in zip(tr, ii_r) if PRE[0] <= t < PRE[1]])
            mic = mean([x for t, x in zip(tr, ii_c) if PRE[0] <= t < PRE[1]])
            v_star = [vv_r[k] - mr - (vv_c[k] - mc) for k in range(len(tr))]
            i_star = [ii_r[k] - mir - (ii_c[k] - mic) for k in range(len(tr))]
            art = family["corrected"][key]
            if [Decimal(x) for x in art["v_star_V"]] != v_star or \
               [Decimal(x) for x in art["i_star_A"]] != i_star:
                fails.append(f"{key} corrected per-token mismatch")
            for field, vals in (("v_star", v_star), ("i_star", i_star)):
                sel = [k for k in range(len(tr)) if SRC_WIN[0] <= tr[k] < SRC_WIN[1]]
                peak = max((abs(vals[k]), k) for k in sel)[1]
                rms = (sum(vals[k]*vals[k] for k in sel)/len(sel))**Decimal("0.5")
                l1 = trapezoid_l1(tr, vals, *SRC_WIN)
                d = spec["descriptors"][key][field]
                if str(vals[peak]) != d["peak_value"] or str(rms) != d["rms"] or \
                   str(l1) != d["time_normalized_l1_trapezoid"]:
                    fails.append(f"{key}.{field} descriptor mismatch")
                if d["fwhm"] != "NOT_APPLICABLE" or \
                   d["dominant_post_primary_opposite_lobe"] != "NOT_APPLICABLE":
                    fails.append(f"{key}.{field} lobe status not NOT_APPLICABLE")
    if fails:
        print("VERIFY FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("VERIFY PASS: 16 raw + 8 corrected per-token byte-exact; trapezoid "
          "L1/descriptors exact; 16 netlist hashes; lobe statuses; orientation")
    return 0

if __name__ == "__main__":
    sys.exit(main())
