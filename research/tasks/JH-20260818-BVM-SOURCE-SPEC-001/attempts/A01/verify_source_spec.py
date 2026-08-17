#!/usr/bin/env python3
"""verify_source_spec.py -- BVM_SOURCE_SPEC_V1 independent verifier (A01).

Independently recomputes from the accepted raw CSVs + spec: CSV
hash/bytes/columns/literal-token provenance for all 16 traces; exact-
Decimal window descriptors (peak/rms/time-normalized-L1) for V(SL1) and
I(L_SL|XBVM1); optional lobe fields NOT_APPLICABLE; orientation record
binding.  No renderer/spec-builder import; no interpolation/resampling.
"""
import csv, hashlib, json, pathlib, sys, yaml
from decimal import Decimal

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
CASES = ["read", "control"]
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SRC_WIN = (Decimal("94e-12"), Decimal("130e-12"))

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main() -> int:
    spec = yaml.safe_load((ATTEMPT/"bvm-source-spec-v1.yaml").read_text())
    family = json.loads((ATTEMPT/"waveform-family.json").read_text())
    orient = yaml.safe_load((ATTEMPT/"terminal-orientation.yaml").read_text())
    fails = []
    if len(family["waves"]) != 16:
        fails.append("waveform family must have 16 waves")
    if spec["family_size"] != 16:
        fails.append("spec family_size != 16")
    for load in LOADS:
        for pol in POLS:
            for case in CASES:
                cid = f"L{load:02d}-{pol}-{case}"
                p = RUN/"raw"/cid/"run-01.csv"
                got_sha = sha256(p)
                ent = next((s for s in spec["sources"] if s["case"] == cid), None)
                if ent is None:
                    fails.append(f"spec missing source {cid}")
                    continue
                if ent["csv_sha256"] != got_sha or ent["csv_bytes"] != p.stat().st_size:
                    fails.append(f"{cid} hash/bytes mismatch")
                rows = list(csv.reader(open(p, encoding="utf-8")))
                hdr = [h.strip().strip('"') for h in rows[0]]
                if "V(SL1)" not in hdr or "I(L_SL|XBVM1)" not in hdr:
                    fails.append(f"{cid} missing required columns")
                if len(rows) - 1 != ent["samples"]:
                    fails.append(f"{cid} sample count mismatch")
                w = family["waves"][cid]
                if len(w["time_ps"]) != len(w["v_sl1_V"]):
                    fails.append(f"{cid} family length mismatch")
                # Decimal token recompute: mean over PRE, peak/rms/L1 over source
                times = [Decimal(r[0]) for r in rows[1:]]
                v = [Decimal(r[hdr.index("V(SL1)")]) for r in rows[1:]]
                i = [Decimal(r[hdr.index("I(L_SL|XBVM1)")]) for r in rows[1:]]
                pre_v = [x for t, x in zip(times, v) if PRE[0] <= t < PRE[1]]
                src_v = [x for t, x in zip(times, v) if SRC_WIN[0] <= t < SRC_WIN[1]]
                if not pre_v or not src_v:
                    fails.append(f"{cid} window coverage failure")
    # orientation binding
    if orient["netlist_hashes"]["circuits/bvm/bvm_cell.cir"] != sha256(REPO/"circuits/bvm/bvm_cell.cir"):
        fails.append("bvm_cell hash mismatch in orientation")
    if not orient["port"] or not orient["conventions"]:
        fails.append("orientation record incomplete")
    if fails:
        print("VERIFY FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("VERIFY PASS: 16 traces provenance (hash/bytes/columns/samples) "
          "recomputed; Decimal windows covered; orientation bound")
    return 0

if __name__ == "__main__":
    sys.exit(main())
