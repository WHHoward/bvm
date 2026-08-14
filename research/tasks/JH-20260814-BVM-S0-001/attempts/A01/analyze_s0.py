#!/usr/bin/env python3
"""analyze_s0 -- deterministic analysis for JH-20260814-BVM-S0-001 A01.

Per design/canonical-source-baseline.md:
  - pre-window [80,90) ps operational admissibility (>=2 finite samples,
    JM1/JM2 p2p <= 0.020 rad, initialized mean-vector L-inf separation
    >= 0.100 rad);
  - activity [94,108) ps direct-JJ phase-area (vts=+1, rd=+1);
  - source [94,130) ps waveform observables for V(SL1), I(L_SL|XBVM1),
    I(I_WL1), I(I_SE1): pre-window baseline, signed min/max, largest absolute
    baseline-subtracted peak, peak time/latency from 96 ps, FWHM of the
    contiguous half-maximum interval (NOT_APPLICABLE when no finite
    half-height crossing exists; never invented by interpolation);
  - post [140,150) ps storage signature (JM1/JM2 P means);
  - adjacent-refinement convergence (0.1/0.05, 0.05/0.025) on the registered
    scalars with the registered bands;
  - CONVERGED / INCONCLUSIVE / INVALID and overall VALID / INCONCLUSIVE /
    INVALID evidence quality.

Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
RUN = REPO_ROOT / "test/final/bvm/runs/bvm-s0-canonical-20260814-01"
PHI0 = 2.067833848e-15  # Wb

CASES = ("init_positive_read", "init_positive_control",
         "init_negative_read", "init_negative_control")
STEPS = ("0.1ps", "0.05ps", "0.025ps")
P_COLS = {"JM1": "P(B_JM1|XBVM1)", "JM2": "P(B_JM2|XBVM1)"}
V_COLS = {"JM1": "V(B_JM1|XBVM1)", "JM2": "V(B_JM2|XBVM1)"}
SRC = {"V_SL1": "V(SL1)", "I_LSL": "I(L_SL|XBVM1)",
       "I_WL1": "I(I_WL1)", "I_SE1": "I(I_SE1)"}
PRE = (80e-12, 90e-12)
ACT = (94e-12, 108e-12)
SRC_WIN = (94e-12, 130e-12)
POST = (140e-12, 150e-12)
P2P_MAX = 0.020
SEP_MIN = 0.100
PAIR_BANDS = {
    "jj_platform_mean": 0.020,       # rad
    "v_peak": (5e-6, 0.05),          # max(5 uV, 5%)
    "i_peak": (0.5e-6, 0.05),        # max(0.5 uA, 5%)
    "latency_fwhm": 0.5e-12,         # s
}


def load(case: str, step: str) -> tuple[list[float], dict[str, list[float]]]:
    with open(RUN / "raw" / case / step / "run-01.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    hdr = [h.strip().strip('"') for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    cols: dict[str, list[float]] = {}
    t: list[float] = []
    for r in rows[1:]:
        t.append(float(r[0]))
        for h in idx:
            cols.setdefault(h, []).append(float(r[idx[h]]))
    return t, cols


def win_idx(t: list[float], lo: float, hi: float) -> list[int]:
    return [i for i, tv in enumerate(t) if lo <= tv < hi]


def trapezoid(y: list[float], t: list[float]) -> float:
    if len(y) < 2:
        raise ValueError("trapezoid requires >=2 samples")
    return sum(0.5 * (y[i] + y[i + 1]) * (t[i + 1] - t[i])
               for i in range(len(y) - 1))


def p2p(y: list[float]) -> float:
    return max(y) - min(y)


def peak_obs(y: list[float], t: list[float], baseline: float,
             pulse_start: float):
    """Largest absolute baseline-subtracted peak; latency from pulse_start."""
    sub = [v - baseline for v in y]
    idx_max = max(range(len(sub)), key=lambda i: abs(sub[i]))
    peak = sub[idx_max]
    lat = t[idx_max] - pulse_start
    return {"baseline": baseline, "peak_baseline_subtracted": peak,
            "abs_peak": abs(peak), "peak_time_s": t[idx_max],
            "latency_from_96ps_s": lat}


def fwhm_of(y: list[float], t: list[float], baseline: float,
            half: float) -> dict:
    """Contiguous half-maximum interval of |y - baseline| >= half."""
    sub = [abs(v - baseline) for v in y]
    idx = [i for i, v in enumerate(sub) if v >= half]
    if not idx:
        return {"fwhm_s": None, "status": "NOT_APPLICABLE",
                "reason": "no finite half-height crossing"}
    # longest contiguous run
    best = cur = [idx[0]]
    for i in range(1, len(idx)):
        if idx[i] == idx[i - 1] + 1:
            cur.append(idx[i])
        else:
            if len(cur) > len(best):
                best = cur
            cur = [idx[i]]
    if len(cur) > len(best):
        best = cur
    return {"fwhm_s": t[best[-1]] - t[best[0]], "status": "applicable",
            "n_samples_in_interval": len(best)}


def analyze() -> dict:
    out: dict = {"run": "bvm-s0-canonical-20260814-01"}
    data = {}
    for c in CASES:
        data[c] = {}
        for s in STEPS:
            t, cols = load(c, s)
            data[c][s] = (t, cols)

    # --- QA ---
    qa = {}
    qa_ok = True
    for c in CASES:
        for s in STEPS:
            t, cols = data[c][s]
            ok = (all(t[i] < t[i + 1] for i in range(len(t) - 1))
                  and all(math.isfinite(v) for col in cols.values()
                          for v in col))
            qa[f"{c}/{s}"] = {"monotonic": ok,
                              "t_end_s": t[-1], "n_samples": len(t)}
            qa_ok = qa_ok and ok
    out["qa"] = qa

    # --- pre-window admissibility (all cases/steps) ---
    adm = {}
    for s in STEPS:
        row = {}
        for c in CASES:
            t, cols = data[c][s]
            wi = win_idx(t, *PRE)
            row[c] = {jj: {"n": len(wi),
                           "p2p_rad": p2p([cols[P_COLS[jj]][i] for i in wi]),
                           "mean_rad": sum(cols[P_COLS[jj]][i] for i in wi) / len(wi)}
                      for jj in ("JM1", "JM2")}
        # separation between the two initialized mean vectors (L-inf)
        for (a, b) in (("init_positive_read", "init_negative_read"),):
            linf = max(abs(row[a][jj]["mean_rad"] - row[b][jj]["mean_rad"])
                       for jj in ("JM1", "JM2"))
            row["pos_neg_linf"] = linf
        adm[s] = {"per_case": row,
                  "admissible": all(
                      row[c][jj]["n"] >= 2 and row[c][jj]["p2p_rad"] <= P2P_MAX
                      for c in CASES for jj in ("JM1", "JM2"))
                  and row["pos_neg_linf"] >= SEP_MIN}
    out["pre_admissibility"] = adm
    all_admissible = all(adm[s]["admissible"] for s in STEPS)

    # --- activity phase-area [94,108) ps ---
    out["phase_area"] = {}
    for jj in ("JM1", "JM2"):
        out["phase_area"][jj] = {}
        for c in CASES:
            for s in STEPS:
                t, cols = data[c][s]
                wi = win_idx(t, *ACT)
                p = [cols[P_COLS[jj]][i] for i in wi]
                v = [cols[V_COLS[jj]][i] for i in wi]
                tt = [t[i] for i in wi]
                pd = p[-1] - p[0]
                av = trapezoid(v, tt)
                out["phase_area"][jj][f"{c}/{s}"] = {
                    "window_ps": [94.0, 108.0],
                    "orientation": {"JM1": "N1->n_jm1o",
                                    "JM2": "n_jm2i->N2"}[jj],
                    "vts": 1, "rd": 1,
                    "phase_delta_rad": pd,
                    "phase_delta_turns": pd / (2 * math.pi),
                    "area_trapezoid_vs": av,
                    "area_turns": av / PHI0,
                    "residual_turns": pd / (2 * math.pi) - av / PHI0,
                    "n_window_samples": len(wi)}

    # --- source-port waveform observables ---
    out["source_port"] = {}
    for c in CASES:
        out["source_port"][c] = {}
        for s in STEPS:
            t, cols = data[c][s]
            wi = win_idx(t, *SRC_WIN)
            row = {}
            for key, col in SRC.items():
                y = [cols[col][i] for i in wi]
                tt = [t[i] for i in wi]
                base = sum(y[:5]) / 5  # first samples of the window baseline
                po = peak_obs(y, tt, base, 96e-12)
                half = 0.5 * po["abs_peak"]
                fw = fwhm_of(y, tt, base, half)
                row[key] = {**po, "fwhm": fw}
            out["source_port"][c][s] = row

    # --- pre/post storage signature (JM1/JM2 P means) ---
    out["platform"] = {}
    for c in CASES:
        out["platform"][c] = {}
        for s in STEPS:
            t, cols = data[c][s]
            pre_wi = win_idx(t, *PRE)
            post_wi = win_idx(t, *POST)
            out["platform"][c][s] = {
                "pre": {jj: sum(cols[P_COLS[jj]][i] for i in pre_wi)
                        / len(pre_wi) for jj in ("JM1", "JM2")},
                "post": {jj: sum(cols[P_COLS[jj]][i] for i in post_wi)
                         / len(post_wi) for jj in ("JM1", "JM2")},
            }

    # --- convergence: adjacent refinement pairs ---
    conv = {}
    for (sA, sB) in (("0.1ps", "0.05ps"), ("0.05ps", "0.025ps")):
        ok = True
        detail = {}
        for c in CASES:
            for jj in ("JM1", "JM2"):
                for w in ("pre", "post"):
                    d = abs(out["platform"][c][sA][w][jj]
                            - out["platform"][c][sB][w][jj])
                    detail[f"{c}/{jj}/{w}"] = d
                    if d > PAIR_BANDS["jj_platform_mean"]:
                        ok = False
            # control-corrected platform delta (read - control)
            for jj in ("JM1", "JM2"):
                da = (out["platform"][c][sA]["post"][jj]
                      - out["platform"][c][sA]["pre"][jj])
                # matched control for this init sign
                ctrl = ("init_positive_control" if "positive" in c
                        else "init_negative_control")
                db = (out["platform"][ctrl][sA]["post"][jj]
                      - out["platform"][ctrl][sA]["pre"][jj])
                d1 = abs(da - db)
                ea = (out["platform"][c][sB]["post"][jj]
                      - out["platform"][c][sB]["pre"][jj])
                eb = (out["platform"][ctrl][sB]["post"][jj]
                      - out["platform"][ctrl][sB]["pre"][jj])
                d2 = abs(ea - eb)
                detail[f"{c}/{jj}/corrected_delta"] = (d1, d2)
                if d1 > PAIR_BANDS["jj_platform_mean"] or \
                        d2 > PAIR_BANDS["jj_platform_mean"]:
                    ok = False
            # source peaks
            for key, (lo, frac) in (("V_SL1", PAIR_BANDS["v_peak"]),
                                    ("I_LSL", PAIR_BANDS["i_peak"])):
                pa = out["source_port"][c][sA][key]["abs_peak"]
                pb = out["source_port"][c][sB][key]["abs_peak"]
                lim = max(lo, frac * max(pa, pb))
                d = abs(pa - pb)
                detail[f"{c}/{key}/peak"] = (d, lim)
                if d > lim:
                    ok = False
            # latency + FWHM
            for key in ("V_SL1", "I_LSL"):
                la = out["source_port"][c][sA][key]["latency_from_96ps_s"]
                lb = out["source_port"][c][sB][key]["latency_from_96ps_s"]
                if abs(la - lb) > PAIR_BANDS["latency_fwhm"]:
                    ok = False
                    detail[f"{c}/{key}/latency"] = abs(la - lb)
                fwa = out["source_port"][c][sA][key]["fwhm"]
                fwb = out["source_port"][c][sB][key]["fwhm"]
                if fwa["status"] == "applicable" and fwb["status"] == "applicable":
                    if abs(fwa["fwhm_s"] - fwb["fwhm_s"]) > PAIR_BANDS["latency_fwhm"]:
                        ok = False
                        detail[f"{c}/{key}/fwhm"] = abs(fwa["fwhm_s"] - fwb["fwhm_s"])
        conv[f"{sA}->{sB}"] = {"ok": ok, "detail": detail}
    out["convergence"] = conv
    converged = all(conv[k]["ok"] for k in conv)

    # --- verdicts ---
    if not qa_ok:
        numeric = "INVALID"
        quality = "INVALID"
    elif not all_admissible:
        numeric = "INCONCLUSIVE"
        quality = "INCONCLUSIVE"
    elif not converged:
        numeric = "INCONCLUSIVE"
        quality = "INCONCLUSIVE"
    else:
        numeric = "CONVERGED"
        quality = "VALID"
    out["numerical_status"] = numeric
    out["evidence_quality"] = {
        "conclusion": quality,
        "meaning": ("source-side calibration facts under the fixed fixture; "
                    "no receiver/Gate/logical conclusion")}

    with open(RUN / "analysis.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    print(json.dumps(out, indent=2, sort_keys=True))
    return out


if __name__ == "__main__":
    sys.exit(0 if analyze() else 1)
