#!/usr/bin/env python3
"""build_source_spec.py -- BVM_SOURCE_SPEC_V1 A02 builder (C01 rework).

Adds corrected V/I (x_star = read-PREmean minus control-PREmean at
identical literal Decimal tokens) and frozen descriptors (peak/rms/
time-normalized-L1) per 4-load x 2-polarity stratum; orientation records
L_SL direction N8 -> SL explicitly.
"""
import csv, hashlib, json, pathlib, yaml
from decimal import Decimal

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SRC_WIN = (Decimal("94e-12"), Decimal("130e-12"))

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    return hdr, rows[1:]

def mean(vals): return sum(vals) / len(vals)

def main():
    corrected = {}
    descriptors = {}
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
            t_ps = [str(t * Decimal("1e12")) for t in tr]
            corrected[key] = {"time_ps": t_ps,
                              "v_star_V": [str(x) for x in v_star],
                              "i_star_A": [str(x) for x in i_star]}
            sel = [k for k in range(len(tr)) if SRC_WIN[0] <= tr[k] < SRC_WIN[1]]
            def desc(vals):
                peak = max((abs(vals[k]), k) for k in sel)[1]
                rms = (sum(vals[k]*vals[k] for k in sel)/len(sel))**Decimal("0.5")
                dt = tr[sel[1]] - tr[sel[0]]
                l1 = (sum(abs(vals[k]) for k in sel) * dt) / (tr[sel[-1]] - tr[sel[0]])
                return {"peak_index": peak, "peak_time_ps": str(tr[peak]*Decimal("1e12")),
                        "peak_value": str(vals[peak]), "rms": str(rms),
                        "time_normalized_l1": str(l1)}
            descriptors[key] = {"v_star": desc(v_star), "i_star": desc(i_star)}
    spec = {"schema_version": "bvm-source-spec-v1",
            "run_id": "bvm-s2-stable-load-20260817-01",
            "family_size": 16,
            "corrected_vi": corrected,
            "descriptors": descriptors,
            "windows_ps": {"pre": [80, 90], "source_activity": [94, 130]},
            "timestamp": "Decimal_from_literal_CSV_token; no interpolation/resampling/fitting"}
    (ATTEMPT/"bvm-source-spec-v1.yaml").write_text(
        yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    orient = {
        "schema_version": "bvm-source-spec-terminal-orientation-v1",
        "port": {"V(SL1)": "SL1 node to ground",
                 "I(L_SL|XBVM1)": "element L_SL, direction N8 -> SL (port output)"},
        "conventions": {"voltage_positive": "SL1 positive with respect to ground",
                        "current_positive": "positive I(L_SL) flows from N8 to SL (out of closure toward DataOut)"},
        "netlist_hashes": {
            "circuits/bvm/bvm_cell.cir": sha256(REPO/"circuits/bvm/bvm_cell.cir"),
            "circuits/models/jjmit.cir": sha256(REPO/"circuits/models/jjmit.cir")}}
    (ATTEMPT/"terminal-orientation.yaml").write_text(
        yaml.safe_dump(orient, sort_keys=False), encoding="utf-8")
    print("A02 spec (corrected V/I + descriptors) + orientation (N8->SL) written")

if __name__ == "__main__":
    main()
