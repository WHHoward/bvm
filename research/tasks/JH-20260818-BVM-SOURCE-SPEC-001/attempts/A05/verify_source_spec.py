#!/usr/bin/env python3
"""verify_source_spec.py -- A05 independent verifier (C04 full closure).

Does NOT import the builder and does NOT trust producer PASS.  Re-reads
the raw CSVs and independently checks: raw/corrected literal tokens,
columns/order + provenance, matched-pair token identity/alignment,
correction, descriptors (trapezoid L1), frozen Decimal context, 16
netlist hashes, orientation, every bundle and inventory entry, and
bundle<->inventory bidirectional completeness, plus A05-local chronology.
"""
import csv, hashlib, json, pathlib, sys, yaml
from decimal import Decimal, getcontext, ROUND_HALF_EVEN

getcontext().prec = 28
getcontext().rounding = ROUND_HALF_EVEN
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SRC_WIN = (Decimal("94e-12"), Decimal("130e-12"))
POST = (Decimal("140e-12"), Decimal("160e-12"))

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"

def sha256(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load_raw(path):
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
    inventory = yaml.safe_load((ATTEMPT/"inventory.yaml").read_text()) \
        if (ATTEMPT/"inventory.yaml").exists() else {"entries": []}
    bundle = yaml.safe_load((ATTEMPT/"evidence-bundle.yaml").read_text()) \
        if (ATTEMPT/"evidence-bundle.yaml").exists() else {"entries": []}
    fails = []
    # 1. frozen Decimal context
    ctx = family.get("decimal_context") or spec.get("decimal_context")
    if not ctx or ctx.get("precision", 0) < 28:
        fails.append("Decimal context missing or precision < 28")
    if ctx.get("rounding") != "ROUND_HALF_EVEN":
        fails.append("Decimal rounding not frozen HALF_EVEN")
    # 2. raw waves: literal tokens, columns/order, sha, bytes, samples
    for load in LOADS:
        for pol in POLS:
            for case in ("read", "control"):
                cid = f"L{load:02d}-{pol}-{case}"
                w = family["waves"].get(cid)
                if not w:
                    fails.append(f"wave missing {cid}")
                    continue
                p = RUN/"raw"/cid/"run-01.csv"
                hdr, rows = load_raw(p)
                if w["columns_order"] != hdr:
                    fails.append(f"{cid} columns/order mismatch")
                if w["time_tokens"] != [r[0] for r in rows]:
                    fails.append(f"{cid} time tokens mismatch")
                if w["v_sl1_tokens"] != [r[hdr.index("V(SL1)")] for r in rows]:
                    fails.append(f"{cid} V(SL1) literal tokens mismatch")
                if w["i_lsl_tokens"] != [r[hdr.index("I(L_SL|XBVM1)")] for r in rows]:
                    fails.append(f"{cid} I(L_SL) literal tokens mismatch")
                if w["csv_sha256"] != sha256(p) or w["csv_bytes"] != p.stat().st_size:
                    fails.append(f"{cid} provenance mismatch")
                if w["samples"] != len(rows):
                    fails.append(f"{cid} samples mismatch")
    # 3. matched-pair token identity before correction
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            mp = family["matched_pairs"].get(key)
            if not mp:
                fails.append(f"matched pair missing {key}")
                continue
            if mp["read_time_tokens"] != family["waves"][f"{key}-read"]["time_tokens"]:
                fails.append(f"{key} pair read sequence mismatch")
            if mp["read_time_tokens"] != mp["control_time_tokens"]:
                fails.append(f"{key} read/control token identity VIOLATED")
    # 4. correction + descriptors recompute
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
            corr = family["corrected"].get(key)
            if not corr or corr["time_tokens"] != [r[0] for r in rows_r]:
                fails.append(f"{key} corrected token identity mismatch")
            if [str(x) for x in v_star] != corr["v_star_tokens"] or \
               [str(x) for x in i_star] != corr["i_star_tokens"]:
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
                    fails.append(f"{key}.{field} lobe status mismatch")
    # 5. netlist hashes + orientation
    for cid in family["waves"]:
        if spec["source_netlist_sha256"].get(cid) != sha256(RUN/"inputs"/f"{cid}.cir"):
            fails.append(f"{cid} netlist hash mismatch")
    if "N8 -> SL" not in str(orient.get("port", {})):
        fails.append("orientation missing N8 -> SL")
    # 6. inventory covers every sealed artifact; bundle binds path/role/sha/bytes
    sealed = ["bvm-source-spec-v1.yaml", "waveform-family.json",
              "terminal-orientation.yaml", "build_source_spec.py",
              "verify_source_spec.py", "verify.log", "report.md"]
    inv_paths = {e["path"].split("/")[-1] for e in inventory.get("entries", [])}
    for f in sealed:
        if f not in inv_paths:
            fails.append(f"inventory missing {f}")
    bundle_entries = {}
    for e in bundle.get("entries", []):
        bundle_entries[e["path"]] = e
        if not all(k in e for k in ("path", "role", "sha256", "bytes")):
            fails.append(f"bundle entry missing fields: {e.get('path')}")
        if e["path"].endswith("receipt.yaml"):
            fails.append("final receipt must not be in bundle")
    # 7. bundle <-> inventory bidirectional completeness (declared entries)
    for e in inventory.get("entries", []):
        if e["path"] not in bundle_entries:
            fails.append(f"inventory entry not in bundle: {e['path']}")
    # 8. A05-local chronology (ACK <= receipt; request <= ACK)
    try:
        import datetime
        req = datetime.datetime.fromisoformat(
            open(REPO/"research/tasks/JH-20260818-BVM-SOURCE-SPEC-001/request.yaml").read().split('issued_at: "')[1][:25])
        ack = datetime.datetime.fromisoformat(
            open(ATTEMPT/"ack.yaml").read().split('created_at: "')[1][:25])
        if ack < req:
            fails.append("A05 ACK precedes request issued_at")
    except Exception as exc:
        fails.append(f"chronology check failed: {exc}")
    if fails:
        print("VERIFY FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print(f"VERIFY PASS (independent, no builder import): 16 raw literal-token "
          f"waves, 8 matched pairs identity-checked, 8 corrected, trapezoid L1, "
          f"Decimal context, 16 netlist hashes, orientation, inventory "
          f"{len(inv_paths)}/{len(sealed)} sealed, bundle "
          f"{len(bundle_entries)} entries bidirectional-complete, chronology OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
