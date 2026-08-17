#!/usr/bin/env python3
"""analyze_stable_load.py -- STABLE-LOAD-001 A01 analysis (frozen prereg).

Decimal-exact; computes per-stratum readiness (JM1/JM2 PRE [80,90) p2p
<=0.020 rad), control-corrected source descriptors (x_star = read-PREmean
minus control-PREmean at identical literal Decimal tokens), and endpoint-VI
at exact 97/99/101/103/105 ps tokens with frozen eligibility/compatibility.
"""
import csv, json, pathlib
from decimal import Decimal

ATTEMPT = pathlib.Path(__file__).resolve().parent
REPO = ATTEMPT.parents[4]
RUN = REPO / "test/final/bvm/runs/bvm-s2-stable-load-20260817-01"
PRE = (Decimal("80e-12"), Decimal("90e-12"))
SOURCE = (Decimal("94e-12"), Decimal("130e-12"))
THRESHOLD = Decimal("0.020")
LOADS = [1, 12, 25, 50]
POLS = ["positive", "negative"]
CASES = ["read", "control"]
TOKENS_PS = [Decimal("97"), Decimal("99"), Decimal("101"), Decimal("103"), Decimal("105")]
FLOOR_V = Decimal("5e-6"); FLOOR_I = Decimal("0.5e-6")

def load_csv(path):
    rows = list(csv.reader(open(path, encoding="utf-8")))
    hdr = [h.strip().strip('"') for h in rows[0]]
    times = [Decimal(r[0]) for r in rows[1:]]
    cols = {h: [Decimal(r[j]) for r in rows[1:]] for j, h in enumerate(hdr[1:], start=1)}
    return times, cols

def p2p(times, vals, lo, hi):
    sel = [v for t, v in zip(times, vals) if lo <= t < hi]
    return max(sel) - min(sel) if sel else Decimal("NaN")

def mean(times, vals, lo, hi):
    sel = [v for t, v in zip(times, vals) if lo <= t < hi]
    return sum(sel) / len(sel) if sel else Decimal("NaN")

def idx_at_token(times, token_ps):
    wanted = token_ps * Decimal("1e-12")
    for i, t in enumerate(times):
        if t == wanted:
            return i
    raise ValueError(f"token {token_ps} ps absent")

def main():
    data = {}
    for load in LOADS:
        for pol in POLS:
            for case in CASES:
                cid = f"L{load:02d}-{pol}-{case}"
                data[cid] = load_csv(RUN / "raw" / cid / "run-01.csv")
    runs = []
    strata = {}
    for load in LOADS:
        for pol in POLS:
            key = f"L{load:02d}-{pol}"
            ready = True
            for case in CASES:
                cid = f"{key}-{case}"
                t, c = data[cid]
                for jj in ("P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)"):
                    if p2p(t, c[jj], *PRE) > THRESHOLD:
                        ready = False
            strata[key] = ready
            runs.append({"id": key, "load_ohm": load, "polarity": pol,
                         "ready": ready})
    # endpoint-VI per polarity (only if all 4 loads ready)
    endpoint = {}
    for pol in POLS:
        loads_ready = all(strata[f"L{load:02d}-{pol}"] for load in LOADS)
        entry = {"eligible_tokens": [], "ill_conditioned_tokens": [],
                 "per_token": [], "summaries": {}}
        if loads_ready:
            vstar = {}; istar = {}
            for load in LOADS:
                tr, c_r = data[f"L{load:02d}-{pol}-read"]
                tc, c_c = data[f"L{load:02d}-{pol}-control"]
                v_r = c_r["V(SL1)"]; v_c = c_c["V(SL1)"]
                i_r = c_r["I(L_SL|XBVM1)"]; i_c = c_c["I(L_SL|XBVM1)"]
                mr = mean(tr, v_r, *PRE); mc = mean(tc, v_c, *PRE)
                mi_r = mean(tr, i_r, *PRE); mi_c = mean(tc, i_c, *PRE)
                vstar[load] = [v_r[idx_at_token(tr, tk)] - mr - (v_c[idx_at_token(tc, tk)] - mc) for tk in TOKENS_PS]
                istar[load] = [i_r[idx_at_token(tr, tk)] - mi_r - (i_c[idx_at_token(tc, tk)] - mi_c) for tk in TOKENS_PS]
            for k, tk in enumerate(TOKENS_PS):
                d_i = istar[50][k] - istar[1][k]
                d_v = vstar[50][k] - vstar[1][k]
                if abs(d_i) < FLOOR_I or abs(d_v) < FLOOR_V:
                    entry["ill_conditioned_tokens"].append(str(tk))
                    continue
                rhat = -(d_v) / d_i
                vth = vstar[1][k] + rhat * istar[1][k]
                e_l = max(abs(vstar[L][k] - (vth - rhat * istar[L][k])) for L in LOADS)
                compat = e_l <= max(FLOOR_V, Decimal("0.01") * abs(d_v))
                entry["eligible_tokens"].append(str(tk))
                entry["per_token"].append({"token_ps": str(tk), "rhat_ohm": str(rhat),
                                           "vth_V": str(vth), "e_max_V": str(e_l),
                                           "compatible": compat})
            rh = [Decimal(x["rhat_ohm"]) for x in entry["per_token"]]
            vh = [Decimal(x["vth_V"]) for x in entry["per_token"]]
            em = [Decimal(x["e_max_V"]) for x in entry["per_token"]]
            entry["summaries"] = {
                "rhat_signed_min_max_mean": [str(min(rh)), str(max(rh)), str(sum(rh)/len(rh))] if rh else [],
                "vth_min_max_mean": [str(min(vh)), str(max(vh)), str(sum(vh)/len(vh))] if vh else [],
                "e_max": str(max(em)) if em else None,
                "e_rms": str((sum(e*e for e in em)/len(em))**Decimal("0.5")) if em else None,
                "eligible": len(entry["eligible_tokens"]),
                "compatible": sum(1 for x in entry["per_token"] if x["compatible"]),
                "not_supported": sum(1 for x in entry["per_token"] if not x["compatible"]),
                "ill_conditioned": len(entry["ill_conditioned_tokens"])}
        else:
            entry["summaries"] = {"eligible": 0, "compatible": 0,
                                  "not_supported": 0, "ill_conditioned": 0}
        endpoint[pol] = entry
    ready_strata = sum(1 for v in strata.values() if v)
    if ready_strata == len(strata):
        disposition = "BOUNDED_SOURCE_CHARACTERIZATION_REPORTED"
    elif ready_strata == 0:
        disposition = "READINESS_NOT_MET"
    else:
        disposition = "PARTIALLY_EVALUABLE"
    result = {"schema_version": "bvm-s2-stable-load-analysis-v1",
              "run_id": "bvm-s2-stable-load-20260817-01",
              "attempt": "A01",
              "metric_spec": {"readiness_threshold_rad": "0.020",
                              "timestamp": "Decimal_from_literal_CSV_token",
                              "endpoint_tokens_ps": ["97", "99", "101", "103", "105"]},
              "provenance": {"binary": "build/josim-cli", "version": "v2.7.2837d13",
                             "timestep_ps": "0.0125", "tstop_ps": "170.0"},
              "strata": runs, "endpoint_vi": endpoint,
              "disposition": disposition, "unknowns": []}
    (ATTEMPT / "analysis.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print("analysis written; disposition:", disposition)
    for pol in POLS:
        s = endpoint[pol]["summaries"]
        print(f"{pol}: eligible={s['eligible']} compatible={s['compatible']} not_supported={s['not_supported']} ill={s['ill_conditioned']}")

if __name__ == "__main__":
    main()
