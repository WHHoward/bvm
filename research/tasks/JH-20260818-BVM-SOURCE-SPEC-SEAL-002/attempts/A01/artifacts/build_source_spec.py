#!/usr/bin/env python3
"""build_source_spec.py -- SEAL-002 A01 producer.

Reconstructs BVM_SOURCE_SPEC_V1 (bvm-source-spec-v1.yaml,
waveform-family.json, terminal-orientation.yaml) as a minimal,
deterministic, hash-bound derived representation of the ACCEPTED
STABLE-LOAD-001 evidence.  Independent implementation: reads only the
accepted-input-manifest, the frozen preregistration semantics, and the 16
raw CSVs.  Does NOT import or read any old SOURCE-SPEC-001 code/artifacts.

Guarantees (producer checks, run at end):
  - 16 raw CSVs: sha256/bytes/samples/columns/order match manifest;
    literal time/V(SL1)/I(L_SL|XBVM1) tokens preserved verbatim.
  - 8 matched read/control pairs: time-token sequences byte-identical
    (alignment verified BEFORE correction).
  - Frozen Decimal context (precision=28, ROUND_HALF_EVEN, full traps),
    used explicitly for every computation.
  - Descriptors strictly reuse accepted preregistration semantics:
    earliest-tie peak, primary lobe, legal-FWHM (NOT_APPLICABLE when no
    legal same-trace bracket in source), dominant post-primary
    opposite lobe.
  - All-READY prerequisite and per-polarity endpoint-VI
    NOT_SUPPORTED_AT_REGISTERED_TOKENS preserved from accepted analysis.
  - Terminal orientation L_SL N8 -> SL; all 16 source-netlist hashes.
  - inventory.yaml and evidence-bundle.yaml required sets exactly equal,
    containing only the three payload artifacts.
"""

import csv
import hashlib
import json
import os
import pathlib
import sys
from decimal import (
    Decimal,
    ROUND_HALF_EVEN,
    FloatOperation,
    DivisionByZero,
    InvalidOperation,
    Overflow,
)

# ---------------------------------------------------------------- paths
ATTEMPT = pathlib.Path(__file__).resolve().parent.parent  # attempts/A01
TASK = ATTEMPT.parents[1]  # task root (A01 -> attempts -> task root)
REPO = TASK.parents[2]  # JoSIM root (task -> tasks -> research -> repo)

MANIFEST = TASK / "accepted-input-manifest.yaml"
ANALYSIS = (
    REPO
    / "research/tasks/JH-20260817-BVM-S2-STABLE-LOAD-001/attempts/A01/analysis.json"
)

ART = ATTEMPT / "artifacts"
SPEC = ART / "bvm-source-spec-v1.yaml"
WAVES = ART / "waveform-family.json"
ORIENT = ART / "terminal-orientation.yaml"
INVENTORY = ATTEMPT / "inventory.yaml"
BUNDLE = ATTEMPT / "evidence-bundle.yaml"

# ------------------------------------------------------- frozen contract
# precision=28, ROUND_HALF_EVEN; traps: FloatOperation, DivisionByZero,
# InvalidOperation, Overflow; flags cleared at construction.
DCTX = dict(
    precision=28,
    rounding=ROUND_HALF_EVEN,
    traps=[FloatOperation, DivisionByZero, InvalidOperation, Overflow],
)

PRE = (Decimal("80e-12"), Decimal("90e-12"))      # half-open [80, 90) ps
SOURCE = (Decimal("94e-12"), Decimal("130e-12"))  # half-open [94, 130) ps

LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
SIGNAL_COLS = ["V(SL1)", "I(L_SL|XBVM1)"]


def sha256_bytes(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def dstr(d):
    """Deterministic Decimal string."""
    return format(d, "f") if d == d.to_integral_value() else str(d)


def window_mean(times, vals, lo, hi):
    sel = [v for t, v in zip(times, vals) if lo <= t < hi]
    if not sel:
        raise ValueError(f"empty window [{lo},{hi})")
    return sum(sel) / Decimal(len(sel))


# ------------------------------------------------------------- CSV layer
def load_csv(path):
    with open(path, encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    header = [h.strip().strip('"') for h in rows[0]]
    data = rows[1:]
    n = len(data)
    times = [Decimal(r[0]) for r in data]
    cols = {}
    for j, h in enumerate(header[1:], start=1):
        cols[h] = [Decimal(r[j]) for r in data]
    return header, times, cols, n


# -------------------------------------------------------------- helpers
def ps_of(token):
    return token * Decimal("1e12")


def in_window(t, lo, hi):
    return lo <= t < hi


def earliest_argmax_abs(ts, xs):
    """t_p = min argmax_{t in source} abs(x(t)); earliest exact token wins."""
    best_i, best_v = None, None
    for i, (t, x) in enumerate(zip(ts, xs)):
        if not in_window(t, *SOURCE):
            continue
        v = abs(x)
        if best_v is None or v > best_v:
            best_i, best_v = i, v
    return best_i, best_v


def primary_lobe(ts, xs, tp_idx, sign):
    """Maximal contiguous actual-sample interval containing t_p whose
    x(t) has strict sign sign(x(t_p))."""
    n = len(ts)
    l = r = tp_idx
    while l - 1 >= 0 and in_window(ts[l - 1], *SOURCE):
        x = xs[l - 1]
        if x == 0 or (x > 0) != sign:
            break
        l -= 1
    while r + 1 < n and in_window(ts[r + 1], *SOURCE):
        x = xs[r + 1]
        if x == 0 or (x > 0) != sign:
            break
        r += 1
    return l, r


def fwhm_crossing(ts, xs, tp_idx, sign, target):
    """Nearest left/right same-trace half-height crossings of
    sign(x(t_p))*x(t) == target, searched outward from t_p.  Exact Decimal
    crossing wins; otherwise local linear interpolation within that trace
    only.  Returns (t_left_ps, t_right_ps) in ps, or None when either side
    lacks a legal same-trace bracket inside source."""
    n = len(ts)
    signv = Decimal(1) if sign else Decimal(-1)
    result = {}
    for side, rng in (("left", range(tp_idx - 1, -1, -1)),
                      ("right", range(tp_idx + 1, n))):
        found = None
        for i in rng:
            t = ts[i]
            if not in_window(t, *SOURCE):
                break  # leaving source window -> no legal bracket
            xp = signv * xs[i]
            if xp == target:
                found = ps_of(t)
                break
            # crossing between samples j=i-1 and i on both sides
            j = i - 1
            if 0 <= j < n and in_window(ts[j], *SOURCE):
                xq = signv * xs[j]
                lo, hi = min(xp, xq), max(xp, xq)
                if lo < target < hi:
                    tj, ti = ts[j], ts[i]
                    frac = (target - xq) / (xp - xq)
                    found = ps_of(tj + frac * (ti - tj))
                    break
        if found is None:
            return None
        result[side] = found
    return result["left"], result["right"]


def opposite_lobe(ts, xs, lobe_r, sign):
    """After the primary-lobe right boundary: all opposite-sign contiguous
    lobes; pick the one with greatest absolute extremum; tie -> earliest
    extremum exact token.  NOT_APPLICABLE if absent."""
    n = len(ts)
    best = None  # (abs_extremum, extremum_idx, lobe_start, lobe_end)
    i = lobe_r + 1
    while i < n:
        if not in_window(ts[i], *SOURCE):
            break
        x = xs[i]
        if x == 0 or (x > 0) == sign:
            i += 1
            continue
        j = i
        ext_i, ext_v = i, abs(x)
        while j + 1 < n and in_window(ts[j + 1], *SOURCE):
            xj = xs[j + 1]
            if xj == 0 or (xj > 0) == sign:
                break
            j += 1
            av = abs(xj)
            if av > ext_v or (av == ext_v and ts[j] < ts[ext_i]):
                ext_i, ext_v = j, av
        if best is None or ext_v > best[0] or (
                ext_v == best[0] and ts[ext_i] < ts[best[1]]):
            best = (ext_v, ext_i, i, j)
        i = j + 1
    if best is None:
        return None
    _, ext_i, lobe_l, lobe_r2 = best
    return dict(
        extremum_token=str(ts[ext_i]),
        extremum_abs=dstr(abs(xs[ext_i])),
        extremum_ps=dstr(ps_of(ts[ext_i])),
        lobe_start_token=str(ts[lobe_l]),
        lobe_end_token=str(ts[lobe_r2]),
    )


def compute_descriptors(ts, xs):
    """Per preregistration source_descriptors semantics on x_star."""
    tp_i, peak_abs = earliest_argmax_abs(ts, xs)
    if tp_i is None or peak_abs == 0:
        return {
            "peak_token": None,
            "peak_abs": None,
            "peak_ps": None,
            "latency_ps": None,
            "primary_lobe": None,
            "fwhm_ps": None,
            "fwhm_status": "NOT_APPLICABLE",
            "dominant_post_primary_opposite_lobe": None,
        }
    sign = xs[tp_i] > 0
    tp_ps = ps_of(ts[tp_i])
    lobe_l, lobe_r = primary_lobe(ts, xs, tp_i, sign)
    target = Decimal("0.5") * peak_abs
    fw = fwhm_crossing(ts, xs, tp_i, sign, target)
    if fw is None:
        fwhm_ps = None
        fwhm_status = "NOT_APPLICABLE"
    else:
        fwhm_ps = dstr(fw[1] - fw[0])
        fwhm_status = "REPORTED"
    opp = opposite_lobe(ts, xs, lobe_r, sign)
    return {
        "peak_token": str(ts[tp_i]),
        "peak_abs": dstr(peak_abs),
        "peak_ps": dstr(tp_ps),
        "latency_ps": dstr(tp_ps - Decimal("96")),
        "primary_lobe": {
            "start_token": str(ts[lobe_l]),
            "end_token": str(ts[lobe_r]),
            "samples": lobe_r - lobe_l + 1,
        },
        "fwhm_ps": fwhm_ps,
        "fwhm_status": fwhm_status,
        "dominant_post_primary_opposite_lobe": opp,
    }


# ------------------------------------------------------------ main build
def main() -> int:
    import yaml

    manifest = yaml.safe_load(MANIFEST.read_text())
    analysis = json.loads(ANALYSIS.read_text())

    raw_meta = {r["id"]: r for r in manifest["raw_csv"]}
    net_meta = {r["id"]: r for r in manifest["source_netlists"]}
    expected_order = [
        "time", "P(B_JM1|XBVM1)", "V(B_JM1|XBVM1)", "P(B_JM2|XBVM1)",
        "V(B_JM2|XBVM1)", "P(B_JS1|XBVM1)", "V(B_JS1|XBVM1)",
        "P(B_JS2|XBVM1)", "V(B_JS2|XBVM1)", "V(SL1)",
        "I(L_SL|XBVM1)", "I(I_WL1)", "I(I_BL1)", "I(I_SE1)",
    ]

    waves = {}
    for rid, meta in raw_meta.items():
        path = REPO / meta["path"]
        assert sha256_bytes(path) == meta["sha256"], f"sha mismatch {rid}"
        assert os.path.getsize(path) == meta["bytes"], f"bytes mismatch {rid}"
        header, times, cols, n = load_csv(path)
        assert header == expected_order, f"column/order mismatch {rid}"
        assert n == meta["samples"], f"samples mismatch {rid}"
        waves[rid] = {
            "id": rid,
            "path": str(meta["path"]),
            "sha256": meta["sha256"],
            "bytes": meta["bytes"],
            "samples": meta["samples"],
            "columns": header,
            "time_tokens": [str(t) for t in times],
            "vsl1_tokens": [str(x) for x in cols["V(SL1)"]],
            "isl_tokens": [str(x) for x in cols["I(L_SL|XBVM1)"]],
            "_times": times,
            "_vsl1": cols["V(SL1)"],
            "_isl": cols["I(L_SL|XBVM1)"],
        }

    # ---- matched pairs: bind both token sequences, verify alignment
    pairs = []
    for load in LOADS:
        for pol in POLS:
            rid_r = f"L{load:02d}-{pol}-read"
            rid_c = f"L{load:02d}-{pol}-control"
            wr, wc = waves[rid_r], waves[rid_c]
            seq_r = "\n".join(wr["time_tokens"])
            seq_c = "\n".join(wc["time_tokens"])
            sha_r = hashlib.sha256(seq_r.encode()).hexdigest()
            sha_c = hashlib.sha256(seq_c.encode()).hexdigest()
            assert seq_r == seq_c, f"time alignment FAIL {rid_r}/{rid_c}"
            pairs.append(dict(
                pair_id=f"L{load:02d}-{pol}",
                load_ohm=load,
                polarity=pol,
                read_id=rid_r,
                control_id=rid_c,
                read_time_sequence_sha256=sha_r,
                control_time_sequence_sha256=sha_c,
                time_alignment="IDENTICAL_BEFORE_CORRECTION",
            ))

    # ---- corrected x_star in source window, per pair per signal
    descriptors = {}
    for p in pairs:
        wr = waves[p["read_id"]]
        wc = waves[p["control_id"]]
        entry = {}
        for sig in SIGNAL_COLS:
            vr, vc = wr["_vsl1" if sig == "V(SL1)" else "_isl"], \
                wc["_vsl1" if sig == "V(SL1)" else "_isl"]
            mr = window_mean(wr["_times"], vr, *PRE)
            mc = window_mean(wc["_times"], vc, *PRE)
            t_toks, x_toks = [], []
            for t, xr, xc in zip(wr["_times"], vr, vc):
                if in_window(t, *SOURCE):
                    x_star = (xr - mr) - (xc - mc)
                    t_toks.append(str(t))
                    x_toks.append(dstr(x_star))
            entry[sig] = {
                "time_tokens": t_toks,
                "x_star_tokens": x_toks,
                "pre_mean_read": dstr(mr),
                "pre_mean_control": dstr(mc),
            }
            desc = compute_descriptors(
                [Decimal(t) for t in t_toks],
                [Decimal(x) for x in x_toks],
            )
            descriptors.setdefault(p["pair_id"], {})[sig] = desc
        p["corrected"] = entry

    # ---- readiness + endpoint-VI from ACCEPTED analysis (preserved copy)
    strata = analysis["strata"]
    readiness = {
        s["id"]: {"ready": s["ready"], "load_ohm": s["load_ohm"],
                  "polarity": s["polarity"]}
        for s in strata
    }
    assert all(s["ready"] for s in strata), "all-READY prerequisite violated"
    endpoint = {}
    for pol in POLS:
        ep = analysis["endpoint_vi"][pol]
        endpoint[pol] = {
            "eligible_tokens": ep["eligible_tokens"],
            "ill_conditioned_tokens": ep["ill_conditioned_tokens"],
            "eligible": ep["summaries"]["eligible"],
            "compatible": ep["summaries"]["compatible"],
            "not_supported": ep["summaries"]["not_supported"],
            "ill_conditioned": ep["summaries"]["ill_conditioned"],
            "disposition": "NOT_SUPPORTED_AT_REGISTERED_TOKENS",
        }
        assert ep["summaries"]["eligible"] == 5, f"{pol} eligible != 5"
        assert ep["summaries"]["compatible"] == 0, f"{pol} compatible != 0"
        assert ep["summaries"]["not_supported"] == 5, f"{pol} ns != 5"
        assert ep["summaries"]["ill_conditioned"] == 0, f"{pol} ill != 0"

    # ---- terminal orientation + netlist hashes
    orientation = {
        "schema_version": "bvm-source-spec-seal-002-orientation-v1",
        "attempt": "A01",
        "terminal_orientation": {
            "L_SL_current_reference_direction": "N8 -> SL",
            "netlist_line": "L_SL    N8      SL      0.4P",
            "source_netlist": "circuits/bvm/bvm_cell.cir",
            "probe": "I(L_SL|XBVM1)",
        },
        "source_netlists": [
            {"id": rid, "path": str(net_meta[rid]["path"]),
             "sha256": net_meta[rid]["sha256"]}
            for rid in sorted(net_meta)
        ],
        "closure": [
            {"path": str(c["path"]), "sha256": c["sha256"]}
            for c in manifest["closure"]
        ],
    }

    # ---- bvm-source-spec-v1.yaml (minimal normative package)
    spec = {
        "schema_version": "bvm-source-spec-seal-002-v1",
        "attempt": "A01",
        "task_id": "JH-20260818-BVM-SOURCE-SPEC-SEAL-002",
        "supersedes": {"task_id": "JH-20260818-BVM-SOURCE-SPEC-001",
                       "status": "historical_rework_record"},
        "normative_source": {
            "task_id": "JH-20260817-BVM-S2-STABLE-LOAD-001",
            "preregistration_sha256": manifest["authority"][
                "preregistration_sha256"],
            "analysis_sha256": manifest["accepted_derived"][0]["sha256"],
            "disposition": analysis["disposition"],
            "sole_authority": True,
        },
        "claim_ceiling": "exact_hash_bound_derived_representation_only; "
                         "1/12/25/50 ohm remain load-origin labels only; "
                         "accepted STABLE-LOAD-001 remains the sole "
                         "scientific authority; no source impedance, BQ/"
                         "SFQ/receiver/interface, mechanism, or hardware "
                         "claim.",
        "decimal_contract": {
            "context": DCTX["precision"],
            "rounding": "ROUND_HALF_EVEN",
            "traps": ["FloatOperation", "DivisionByZero", "InvalidOperation",
                      "Overflow"],
            "flags_initial": "cleared",
            "parser": "Decimal_from_literal_CSV_token",
            "tolerance_seconds": "0",
            "interpolation": "prohibited_for_cross_run_and_endpoint_vi; "
                             "same-trace local linear interpolation only "
                             "inside legal FWHM bracket per accepted "
                             "preregistration",
            "resampling": "prohibited",
            "time_alignment": "prohibited",
        },
        "windows_ps": {
            "pre": [80.0, 90.0],
            "activity": [94.0, 108.0],
            "source": [94.0, 130.0],
            "recovery": [108.0, 130.0],
            "post": [140.0, 150.0],
            "semantics": "half_open_actual_csv_time",
        },
        "descriptor_semantics": "strictly reused from accepted "
                                "preregistration (earliest tie peak, "
                                "primary activity, legal FWHM with "
                                "NOT_APPLICABLE, dominant post-primary "
                                "opposite lobe); no new norm introduced",
        "probes": ["V(SL1)", "I(L_SL|XBVM1)"],
        "readiness": {
            "all_ready": True,
            "strata": readiness,
            "requirement": "JM1/JM2 PRE phase p2p <= 0.020 rad per stratum",
        },
        "endpoint_vi": endpoint,
        "descriptors": descriptors,
        "matched_pairs": [
            {k: v for k, v in p.items() if k != "corrected"} for p in pairs
        ],
        "frozen_preregistration_sha256": manifest[
            "authority"]["preregistration_sha256"],
    }

    # ---- waveform-family.json (payload artifacts only)
    family = {
        "schema_version": "bvm-source-spec-seal-002-waveform-family-v1",
        "attempt": "A01",
        "raw_waves": [
            {k: w[k] for k in ("id", "path", "sha256", "bytes", "samples",
                               "columns", "time_tokens", "vsl1_tokens",
                               "isl_tokens")}
            for w in waves.values()
        ],
        "matched_pairs": [
            {k: p[k] for k in ("pair_id", "load_ohm", "polarity", "read_id",
                               "control_id", "read_time_sequence_sha256",
                               "control_time_sequence_sha256",
                               "time_alignment", "corrected")}
            for p in pairs
        ],
        "source_window_tokens_ps": ["94.0", "130.0"],
    }

    # ---- write payload artifacts
    ART.mkdir(parents=True, exist_ok=True)
    SPEC.write_text(
        yaml.safe_dump(spec, sort_keys=False, allow_unicode=True))
    WAVES.write_text(json.dumps(family, indent=2, ensure_ascii=False))
    ORIENT.write_text(
        yaml.safe_dump(orientation, sort_keys=False, allow_unicode=True))

    # ---- inventory + evidence bundle: exact 3-entry equal sets
    payload = [
        {"path": str(SPEC.relative_to(REPO)),
         "sha256": sha256_bytes(SPEC), "bytes": os.path.getsize(SPEC)},
        {"path": str(WAVES.relative_to(REPO)),
         "sha256": sha256_bytes(WAVES), "bytes": os.path.getsize(WAVES)},
        {"path": str(ORIENT.relative_to(REPO)),
         "sha256": sha256_bytes(ORIENT), "bytes": os.path.getsize(ORIENT)},
    ]
    assert len(payload) == 3
    inventory = {
        "schema_version": "bvm-source-spec-seal-002-inventory-v1",
        "attempt": "A01",
        "entries": [
            {"path": e["path"], "sha256": e["sha256"], "bytes": e["bytes"],
             "tag": "DELIVERED"}
            for e in payload
        ],
    }
    bundle = {
        "schema_version": "bvm-source-spec-seal-002-bundle-v1",
        "attempt": "A01",
        "entries": [
            {"path": e["path"], "role": role, "sha256": e["sha256"],
             "bytes": e["bytes"]}
            for e, role in zip(payload, ["manifest", "documentation",
                                         "manifest"])
        ],
    }
    INVENTORY.write_text(
        yaml.safe_dump(inventory, sort_keys=False, allow_unicode=True))
    BUNDLE.write_text(
        yaml.safe_dump(bundle, sort_keys=False, allow_unicode=True))

    # --------------------------------------------------- producer checks
    fails = []
    # 1. raw identity recheck (independent of manifest claims)
    for rid, meta in raw_meta.items():
        w = waves[rid]
        if w["sha256"] != sha256_bytes(REPO / meta["path"]):
            fails.append(f"raw sha drift {rid}")
        if len(w["time_tokens"]) != meta["samples"]:
            fails.append(f"token count {rid}")
    # 2. alignment pre-correction recorded
    for p in pairs:
        if p["time_alignment"] != "IDENTICAL_BEFORE_CORRECTION":
            fails.append(f"alignment {p['pair_id']}")
    # 3. frozen context fields present
    if spec["decimal_contract"]["context"] != 28:
        fails.append("decimal precision")
    if spec["decimal_contract"]["rounding"] != "ROUND_HALF_EVEN":
        fails.append("decimal rounding")
    # 4. inventory/bundle set equality
    inv_paths = {e["path"] for e in inventory["entries"]}
    bun_paths = {e["path"] for e in bundle["entries"]}
    if inv_paths != bun_paths:
        fails.append("inventory/bundle set mismatch")
    if len(inv_paths) != 3:
        fails.append("inventory not 3-entry")
    # 5. every entry's sha/bytes valid
    for e in list(inventory["entries"]) + list(bundle["entries"]):
        p = REPO / e["path"]
        if not p.exists() or sha256_bytes(p) != e["sha256"]:
            fails.append(f"entry hash {e['path']}")
    # 6. all-READY + endpoint preserved
    if not spec["readiness"]["all_ready"]:
        fails.append("all-ready")
    for pol in POLS:
        ep = spec["endpoint_vi"][pol]
        if ep["disposition"] != "NOT_SUPPORTED_AT_REGISTERED_TOKENS":
            fails.append(f"endpoint {pol}")
    # 7. orientation bound
    if orientation["terminal_orientation"][
            "L_SL_current_reference_direction"] != "N8 -> SL":
        fails.append("orientation")
    if len(orientation["source_netlists"]) != 16:
        fails.append("netlist hashes")
    # 8. descriptor semantics sanity
    for pid, sigs in descriptors.items():
        for sig, d in sigs.items():
            if d["peak_token"] is None:
                continue
            if d["fwhm_status"] not in ("REPORTED", "NOT_APPLICABLE"):
                fails.append(f"fwhm status {pid} {sig}")
            if d["primary_lobe"] is None:
                fails.append(f"lobe {pid} {sig}")

    if fails:
        print("PRODUCER CHECKS FAIL:")
        for f in fails:
            print("  -", f)
        return 1
    print("PRODUCER CHECKS PASS: 16 raw waves, 8 aligned pairs, "
          "frozen Decimal context, 3-entry equal inventory/bundle, "
          "orientation + 16 netlist hashes bound.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
