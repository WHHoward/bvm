#!/usr/bin/env python3
"""build_source_spec.py -- BVM_SOURCE_SPEC_V1 builder (A01).

Consumes ONLY the 16 accepted stable-load raw traces; emits hash-bound
bvm-source-spec-v1.yaml, full exact-token waveform-family.json, and
terminal-orientation.yaml.  Strict Decimal; no interpolation/resampling/
fitting.  No JoSIM; accepted STABLE-LOAD-001 remains scientific authority.
"""
import csv, hashlib, json, pathlib, yaml
from decimal import Decimal

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
SRC = REPO / "research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-001"
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
CASES = ["read", "control"]
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SRC_WIN = (Decimal("94e-12"), Decimal("130e-12"))
POST = (Decimal("140e-12"), Decimal("160e-12"))

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    return hdr, rows[1:]

def main():
    spec_entries = []
    family = {"schema_version": "bvm-source-spec-v1",
              "run_id": "bvm-s2-stable-load-20260817-01",
              "waves": {}}
    for load in LOADS:
        for pol in POLS:
            for case in CASES:
                cid = f"L{load:02d}-{pol}-{case}"
                p = RUN/"raw"/cid/"run-01.csv"
                hdr, rows = load_csv(p)
                times = [Decimal(r[0]) for r in rows]
                v = [Decimal(r[hdr.index("V(SL1)")]) for r in rows]
                i = [Decimal(r[hdr.index("I(L_SL|XBVM1)")]) for r in rows]
                t_ps = [str(x * Decimal("1e12")) for x in times]
                spec_entries.append({
                    "case": cid, "load_ohm": load, "polarity": pol, "case_type": case,
                    "csv": f"test/final/bvm/runs/bvm-s2-stable-load-20260817-01/raw/{cid}/run-01.csv",
                    "csv_sha256": sha256(p), "csv_bytes": p.stat().st_size,
                    "columns": hdr[1:], "samples": len(rows),
                    "t_first_ps": t_ps[0], "t_last_ps": t_ps[-1]})
                family["waves"][cid] = {
                    "time_ps": t_ps,
                    "v_sl1_V": [str(x) for x in v],
                    "i_lsl_A": [str(x) for x in i],
                    "provenance": {"csv_sha256": sha256(p), "csv_bytes": p.stat().st_size}}
    # source spec YAML
    spec = {
        "schema_version": "bvm-source-spec-v1",
        "run_id": "bvm-s2-stable-load-20260817-01",
        "family_size": 16,
        "accepted_preconditions": {
            "readiness": "all 8 strata READY (JM1/JM2 PRE [80,90) p2p <=0.020 rad)",
            "source_disposition": "BOUNDED_SOURCE_CHARACTERIZATION_REPORTED",
            "endpoint_vi": "per-polarity NOT_SUPPORTED at registered tokens (recorded fact, no affine source model asserted)"},
        "windows_ps": {"pre": [80, 90], "source_activity": [94, 130], "post": [140, 160]},
        "timestamp": "Decimal_from_literal_CSV_token; interpolation/resampling/fitting prohibited",
        "sources": spec_entries}
    (ATTEMPT/"bvm-source-spec-v1.yaml").write_text(
        yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    (ATTEMPT/"waveform-family.json").write_text(json.dumps(family), encoding="utf-8")
    # terminal orientation
    orient = {
        "schema_version": "bvm-source-spec-terminal-orientation-v1",
        "port": {"V(SL1)": "SL1 node to ground", "I(L_SL|XBVM1)": "element L_SL within BVM closure"},
        "conventions": {"voltage_positive": "SL1 positive with respect to ground",
                        "current_positive": "I(L_SL|XBVM1) positive into DataOut/SL1 port per netlist element order"},
        "netlist_hashes": {
            "circuits/bvm/bvm_cell.cir": sha256(REPO/"circuits/bvm/bvm_cell.cir"),
            "circuits/models/jjmit.cir": sha256(REPO/"circuits/models/jjmit.cir")},
        "source_netlist_provenance": {
            "template": "test/final/bvm/runs/bvm-s2-stable-load-20260817-01/inputs/*.cir (16 cases)",
            "inputs_sha256": {name: sha256(RUN/"inputs"/name)
                              for name in ["bvm_cell.cir", "jjmit.cir"]}}
    }
    (ATTEMPT/"terminal-orientation.yaml").write_text(
        yaml.safe_dump(orient, sort_keys=False), encoding="utf-8")
    print(f"spec + waveform-family ({len(family['waves'])} waves) + orientation written")

if __name__ == "__main__":
    main()
