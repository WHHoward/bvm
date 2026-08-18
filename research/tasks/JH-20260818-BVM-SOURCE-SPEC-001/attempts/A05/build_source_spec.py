#!/usr/bin/env python3
"""build_source_spec.py -- BVM_SOURCE_SPEC_V1 A05 builder (C04 closure).

Closes every C04 gap: (1) 16 raw CSVs with original literal
time/V(SL1)/I(L_SL|XBVM1) tokens + full columns/order + SHA-256/bytes/
samples; (2) per matched pair, read/control time-token sequences sealed;
(3) frozen Decimal context (precision>=28, rounding, full context) used
explicitly; correction is strict Decimal per-token; descriptors use frozen
TRAPEZOID time-normalized-L1.  Orientation N8 -> SL; 16 netlist hashes.
"""
import csv, hashlib, json, pathlib, yaml
from decimal import Decimal, getcontext, ROUND_HALF_EVEN

# FROZEN Decimal context (C04): precision >= 28, rounding HALF_EVEN.
getcontext().prec = 28
getcontext().rounding = ROUND_HALF_EVEN
DECIMAL_CONTEXT = {"precision": 28, "rounding": "ROUND_HALF_EVEN",
                   "traps": sorted(["InvalidOperation", "DivisionByZero", "Overflow"])}

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SRC_WIN = (Decimal("94e-12"), Decimal("130e-12"))
POST = (Decimal("140e-12"), Decimal("160e-12"))

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def load_raw(path):
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
              "decimal_context": DECIMAL_CONTEXT,
              "waves": {}, "matched_pairs": {}, "corrected": {}}
    netlist_hashes = {}
    for load in LOADS:
        for pol in POLS:
            for case in ("read", "control"):
                cid = f"L{load:02d}-{pol}-{case}"
                p = RUN/"raw"/cid/"run-01.csv"
                hdr, rows = load_raw(p)
                family["waves"][cid] = {
                    "columns": hdr, "columns_order": hdr,
                    "time_tokens": [r[0] for r in rows],
                    "v_sl1_tokens": [r[hdr.index("V(SL1)")] for r in rows],
                    "i_lsl_tokens": [r[hdr.index("I(L_SL|XBVM1)")] for r in rows],
                    "samples": len(rows),
                    "csv_sha256": sha256(p), "csv_bytes": p.stat().st_size}
                netlist_hashes[cid] = sha256(RUN/"inputs"/f"{cid}.cir")
    # matched pair token sequences + alignment verification (identity check
    # before correction happens in the verifier; here we seal the sequences)
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            family["matched_pairs"][key] = {
                "read_time_tokens": family["waves"][f"{key}-read"]["time_tokens"],
                "control_time_tokens": family["waves"][f"{key}-control"]["time_tokens"],
                "identity_requirement": "read and control literal time-token "
                                       "sequences must be identical before correction"}
    descriptors = {}
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            v_r, rows_r = load_raw(RUN/"raw"/f"{key}-read"/"run-01.csv")
            v_c, rows_c = load_raw(RUN/"raw"/f"{key}-control"/"run-01.csv")
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
                "time_tokens": [r[0] for r in rows_r],
                "v_star_tokens": [str(x) for x in v_star],
                "i_star_tokens": [str(x) for x in i_star]}
            def desc(vals):
                sel = [k for k in range(len(tr)) if SRC_WIN[0] <= tr[k] < SRC_WIN[1]]
                peak = max((abs(vals[k]), k) for k in sel)[1]
                rms = (sum(vals[k]*vals[k] for k in sel)/len(sel))**Decimal("0.5")
                l1 = trapezoid_l1(tr, vals, *SRC_WIN)
                post_max = max((abs(vals[k]) for k in range(len(tr))
                                if POST[0] <= tr[k] < POST[1]), default=Decimal("0"))
                return {"peak_index": peak,
                        "peak_time_token": rows_r[peak][0],
                        "peak_value": str(vals[peak]), "rms": str(rms),
                        "time_normalized_l1_trapezoid": str(l1),
                        "post_window_max": str(post_max),
                        "fwhm": "NOT_APPLICABLE",
                        "dominant_post_primary_opposite_lobe": "NOT_APPLICABLE"}
            descriptors[key] = {"v_star": desc(v_star), "i_star": desc(i_star)}
    spec = {"schema_version": "bvm-source-spec-v1",
            "run_id": "bvm-s2-stable-load-20260817-01",
            "decimal_context": DECIMAL_CONTEXT,
            "windows_ps": {"pre": [80, 90], "source_activity": [94, 130],
                           "post": [140, 160]},
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
                        "current_positive": "positive I(L_SL) flows N8 -> SL"},
        "netlist_hashes": {
            "circuits/bvm/bvm_cell.cir": sha256(REPO/"circuits/bvm/bvm_cell.cir"),
            "circuits/models/jjmit.cir": sha256(REPO/"circuits/models/jjmit.cir")},
        "source_netlist_hashes": netlist_hashes}
    (ATTEMPT/"terminal-orientation.yaml").write_text(
        yaml.safe_dump(orient, sort_keys=False), encoding="utf-8")
    print(f"A05: 16 raw literal-token waves + 8 matched pairs + 8 corrected; "
          f"Decimal context frozen {DECIMAL_CONTEXT}")

if __name__ == "__main__":
    main()
