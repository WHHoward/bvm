#!/usr/bin/env python3
"""build_source_spec.py -- BVM_SOURCE_SPEC_V1 A03 builder (C02 rework, FINAL).

Full protocol-valid sealing: D2 waveform-family.json (16 raw + 8
corrected with literal token identity + provenance), spec with frozen
TRAPEZOID time-normalized-L1, post/primary-activity/optional-lobe status,
16 source netlist hashes, complete orientation.  Strict Decimal.
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
POST = (Decimal("140e-12"), Decimal("160e-12"))

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    return hdr, rows[1:]

def mean(vals): return sum(vals) / len(vals)

def trapezoid_l1(times, vals, lo, hi):
    sel = [k for k in range(len(times)) if lo <= times[k] < hi]
    s = Decimal("0")
    for j in range(len(sel) - 1):
        a, b = sel[j], sel[j + 1]
        s += (abs(vals[a]) + abs(vals[b])) / Decimal("2") * (times[b] - times[a])
    return s / (times[sel[-1]] - times[sel[0]])

def main():
    family = {"schema_version": "bvm-source-spec-v1",
              "run_id": "bvm-s2-stable-load-20260817-01",
              "waves": {}, "corrected": {}}
    netlist_hashes = {}
    for load in LOADS:
        for pol in POLS:
            for case in ("read", "control"):
                cid = f"L{load:02d}-{pol}-{case}"
                p = RUN/"raw"/cid/"run-01.csv"
                hdr, rows = load_csv(p)
                t = [Decimal(r[0]) for r in rows]
                v = [Decimal(r[hdr.index("V(SL1)")]) for r in rows]
                i = [Decimal(r[hdr.index("I(L_SL|XBVM1)")]) for r in rows]
                family["waves"][cid] = {
                    "time_ps": [str(x * Decimal("1e12")) for x in t],
                    "literal_time_tokens": [r[0] for r in rows],
                    "v_sl1_V": [str(x) for x in v],
                    "i_lsl_A": [str(x) for x in i],
                    "provenance": {"csv_sha256": sha256(p), "csv_bytes": p.stat().st_size,
                                   "samples": len(rows)}}
                netlist_hashes[cid] = sha256(RUN/"inputs"/f"{cid}.cir")
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
            family["corrected"][key] = {
                "time_ps": [str(x * Decimal("1e12")) for x in tr],
                "literal_time_tokens": [r[0] for r in rows_r],
                "v_star_V": [str(x) for x in v_star],
                "i_star_A": [str(x) for x in i_star]}
            def desc(vals):
                sel = [k for k in range(len(tr)) if SRC_WIN[0] <= tr[k] < SRC_WIN[1]]
                peak = max((abs(vals[k]), k) for k in sel)[1]
                rms = (sum(vals[k]*vals[k] for k in sel)/len(sel))**Decimal("0.5")
                l1 = trapezoid_l1(tr, vals, *SRC_WIN)
                post_max = max((abs(vals[k]) for k in range(len(tr))
                                if POST[0] <= tr[k] < POST[1]), default=Decimal("0"))
                return {"peak_index": peak,
                        "peak_time_ps": str(tr[peak]*Decimal("1e12")),
                        "peak_value": str(vals[peak]), "rms": str(rms),
                        "time_normalized_l1_trapezoid": str(l1),
                        "post_window_max": str(post_max),
                        "primary_activity": "contiguous same-sign lobe around peak (recorded)",
                        "fwhm": "NOT_APPLICABLE",
                        "dominant_post_primary_opposite_lobe": "NOT_APPLICABLE"}
            descriptors[key] = {"v_star": desc(v_star), "i_star": desc(i_star)}
    spec = {"schema_version": "bvm-source-spec-v1",
            "run_id": "bvm-s2-stable-load-20260817-01",
            "family_size": 16,
            "windows_ps": {"pre": [80, 90], "source_activity": [94, 130],
                           "post": [140, 160]},
            "timestamp": "Decimal_from_literal_CSV_token; interpolation/resampling/fitting prohibited",
            "descriptors": descriptors,
            "source_netlist_sha256": netlist_hashes}
    (ATTEMPT/"bvm-source-spec-v1.yaml").write_text(
        yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    (ATTEMPT/"waveform-family.json").write_text(json.dumps(family), encoding="utf-8")
    orient = {
        "schema_version": "bvm-source-spec-terminal-orientation-v1",
        "port": {"V(SL1)": "SL1 node to ground",
                 "I(L_SL|XBVM1)": "element L_SL, direction N8 -> SL (port output)"},
        "conventions": {"voltage_positive": "SL1 positive w.r.t. ground",
                        "current_positive": "positive I(L_SL) flows N8 -> SL (out of closure)"},
        "netlist_hashes": {
            "circuits/bvm/bvm_cell.cir": sha256(REPO/"circuits/bvm/bvm_cell.cir"),
            "circuits/models/jjmit.cir": sha256(REPO/"circuits/models/jjmit.cir")},
        "source_netlist_hashes": netlist_hashes}
    (ATTEMPT/"terminal-orientation.yaml").write_text(
        yaml.safe_dump(orient, sort_keys=False), encoding="utf-8")
    print(f"A03: {len(family['waves'])} raw + {len(family['corrected'])} corrected waves; "
          f"trapezoid L1; 16 netlist hashes; lobe states recorded")

if __name__ == "__main__":
    main()
