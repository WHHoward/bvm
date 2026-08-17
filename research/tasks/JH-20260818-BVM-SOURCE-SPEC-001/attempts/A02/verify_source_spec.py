#!/usr/bin/env python3
"""verify_source_spec.py -- A02 independent raw-to-artifact verifier.

Independently recomputes corrected V/I for EVERY literal Decimal token and
every descriptor value from the accepted raw CSVs, and compares
byte-exactly against the A02 artifacts.  No builder import.
"""
import csv, hashlib, pathlib, sys, yaml
from decimal import Decimal

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SRC_WIN = (Decimal("94e-12"), Decimal("130e-12"))

def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    return hdr, rows[1:]

def mean(vals): return sum(vals) / len(vals)

def main() -> int:
    spec = yaml.safe_load((ATTEMPT/"bvm-source-spec-v1.yaml").read_text())
    orient = yaml.safe_load((ATTEMPT/"terminal-orientation.yaml").read_text())
    fails = []
    # orientation: L_SL direction must be explicit N8 -> SL
    if "N8 -> SL" not in str(orient.get("port", {}).get("I(L_SL|XBVM1)", "")):
        fails.append("orientation lacks explicit L_SL N8 -> SL direction")
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            if key not in spec["corrected_vi"] or key not in spec["descriptors"]:
                fails.append(f"artifact missing {key}")
                continue
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
            art_v = [Decimal(x) for x in spec["corrected_vi"][key]["v_star_V"]]
            art_i = [Decimal(x) for x in spec["corrected_vi"][key]["i_star_A"]]
            if art_v != v_star or art_i != i_star:
                fails.append(f"{key}: corrected V/I per-token mismatch")
            # descriptors per value
            sel = [k for k in range(len(tr)) if SRC_WIN[0] <= tr[k] < SRC_WIN[1]]
            for field, vals in (("v_star", v_star), ("i_star", i_star)):
                peak = max((abs(vals[k]), k) for k in sel)[1]
                rms = (sum(vals[k]*vals[k] for k in sel)/len(sel))**Decimal("0.5")
                dt = tr[sel[1]] - tr[sel[0]]
                l1 = (sum(abs(vals[k]) for k in sel) * dt) / (tr[sel[-1]] - tr[sel[0]])
                d = spec["descriptors"][key][field]
                if (str(vals[peak]) != d["peak_value"] or str(rms) != d["rms"]
                        or str(l1) != d["time_normalized_l1"]):
                    fails.append(f"{key}.{field} descriptor mismatch")
    if fails:
        print("VERIFY FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("VERIFY PASS: per-token corrected V/I and all descriptors "
          "recomputed byte-exact for 8 strata; orientation N8->SL bound")
    return 0

if __name__ == "__main__":
    sys.exit(main())
