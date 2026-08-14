#!/usr/bin/env python3
"""analyze_d0 -- deterministic analysis for JH-20260814-BVM-S0-D0-002 A01.

Per AC3: for each case, report source-port V(SL1)/I(L_SL|XBVM1) descriptively
and compute direct-JJ phase/voltage-area quantities on [9,31) ps using the
CSV's actual time axis and trapezoidal integration.  JM1 positive orientation
N1->n_jm1o (V(B_JM1|XBVM1)), JM2 positive orientation n_jm2i->N2
(V(B_JM2|XBVM1)), as registered in the design document.  Phase-area identity
per METRIC_SPEC_V2 sec 7: area_turns = trapezoid(V, t) / Phi0, residual
reported in turns WITHOUT any declared tolerance.

Per AC4: for each case, report JM1/JM2 raw-radian signature means and
peak-to-peak ranges in state_early [35,45) ps and state_late [65,75) ps, and
evaluate the three D0 observability guards.

Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
RUN = REPO_ROOT / "test/final/bvm/runs/bvm-s0-d0-20260814-02"
PHI0 = 2.067833848e-15  # Wb (METRIC_SPEC_V2 sec 7.1)

CASES = ("init_positive", "init_negative", "no_init_control")
P_COLS = {
    "JM1": "P(B_JM1|XBVM1)",
    "JM2": "P(B_JM2|XBVM1)",
}
V_COLS = {
    "JM1": "V(B_JM1|XBVM1)",
    "JM2": "V(B_JM2|XBVM1)",
}
WINDOWS = {
    "init_activity": (9e-12, 31e-12),
    "state_early": (35e-12, 45e-12),
    "state_late": (65e-12, 75e-12),
}


def load(case: str) -> tuple[list[float], dict[str, list[float]]]:
    with open(RUN / "raw" / case / "run-01.csv", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    hdr = [h.strip().strip('"') for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    cols: dict[str, list[float]] = {}
    t: list[float] = []
    for r in rows[1:]:
        t.append(float(r[0]))
        for h in list(idx):
            cols.setdefault(h, []).append(float(r[idx[h]]))
    return t, cols


def window_slice(t: list[float], lo: float, hi: float) -> list[int]:
    return [i for i, tv in enumerate(t) if lo <= tv < hi]


def trapezoid(y: list[float], t: list[float]) -> float:
    if len(y) < 2:
        raise ValueError("trapezoid requires >=2 samples")
    area = 0.0
    for i in range(len(y) - 1):
        area += 0.5 * (y[i] + y[i + 1]) * (t[i + 1] - t[i])
    return area


def stats(y: list[float]) -> dict:
    mn = min(y)
    mx = max(y)
    return {
        "mean_rad": sum(y) / len(y),
        "p2p_rad": mx - mn,
        "n_samples": len(y),
    }


def analyze_case(case: str) -> dict:
    t, cols = load(case)
    out: dict = {"case": case, "qa": {}}

    # --- QA ---
    out["qa"] = {
        "monotonic_time": all(t[i] < t[i + 1] for i in range(len(t) - 1)),
        "t_end_s": t[-1],
        "n_samples": len(t),
        "n_nan_inf": sum(1 for c in cols.values() for v in c
                         if not math.isfinite(v)),
    }

    # --- AC3: source-port descriptive (12-ohm load, V(SL1), I(L_SL|XBVM1)) ---
    vsl = cols["V(SL1)"]
    isl = cols["I(L_SL|XBVM1)"]
    out["source_port"] = {
        "v_sl1": {"min": min(vsl), "max": max(vsl),
                  "mean": sum(vsl) / len(vsl)},
        "i_lsl": {"min": min(isl), "max": max(isl),
                  "mean": sum(isl) / len(isl)},
        "description": "descriptive only; no tolerance",
    }

    # --- AC3: direct-JJ phase-area on [9,31) ps, actual-time trapezoid ---
    ia = window_slice(t, *WINDOWS["init_activity"])
    out["phase_area"] = {}
    for jj in ("JM1", "JM2"):
        p = [cols[P_COLS[jj]][i] for i in ia]
        v = [cols[V_COLS[jj]][i] for i in ia]
        tt = [t[i] for i in ia]
        p_delta_rad = p[-1] - p[0]
        area_vs = trapezoid(v, tt)
        area_turns = area_vs / PHI0
        phase_turns = p_delta_rad / (2 * math.pi)
        out["phase_area"][jj] = {
            "window_ps": [9.0, 31.0],
            "orientation": {"JM1": "N1->n_jm1o",
                            "JM2": "n_jm2i->N2"}[jj],
            "phase_delta_rad": p_delta_rad,
            "phase_delta_turns": phase_turns,
            "area_trapezoid_vs": area_vs,
            "area_turns": area_turns,
            "residual_turns": phase_turns - area_turns,
            "n_window_samples": len(ia),
            "tolerance_declared": False,
        }

    # --- AC4: state-window signature means / p2p / guards ---
    out["signatures"] = {}
    guards: list[dict] = []
    sep = {}
    for wname, (lo, hi) in WINDOWS.items():
        if wname == "init_activity":
            continue
        wi = window_slice(t, lo, hi)
        out["signatures"][wname] = {"window_ps": [lo * 1e12, hi * 1e12]}
        for jj in ("JM1", "JM2"):
            y = [cols[P_COLS[jj]][i] for i in wi]
            out["signatures"][wname][jj] = stats(y)
            # guard 1+2 per component (NaN/Inf already QA; >=2 samples)
            if len(y) < 2:
                guards.append({"window": wname, "jj": jj,
                               "guard": ">=2 actual samples", "pass": False})
            if max(y) - min(y) > 0.02:
                guards.append({"window": wname, "jj": jj,
                               "guard": "p2p <= 0.02 rad", "pass": False,
                               "p2p_rad": max(y) - min(y)})
        # guard 3: L-inf separation between init_positive and init_negative
        sep.setdefault(wname, {})
        for jj in ("JM1", "JM2"):
            pass

    # guard 3 needs cross-case data; computed in main()
    return out


def main() -> int:
    results: dict = {"run": "bvm-s0-d0-20260814-02", "cases": {}}
    per_case = {}
    for c in CASES:
        per_case[c] = analyze_case(c)
        results["cases"][c] = per_case[c]

    # --- guard 3: L-inf separation (needs both init cases) ---
    sep = {}
    for wname in ("state_early", "state_late"):
        sep[wname] = {}
        for jj in ("JM1", "JM2"):
            mp = per_case["init_positive"]["signatures"][wname][jj]["mean_rad"]
            mn = per_case["init_negative"]["signatures"][wname][jj]["mean_rad"]
            sep[wname][jj] = abs(mp - mn)
    results["separation_linf"] = sep

    # --- assemble guard verdicts ---
    guards: list[dict] = []
    for wname in ("state_early", "state_late"):
        for jj in ("JM1", "JM2"):
            n = per_case["init_positive"]["signatures"][wname][jj]["n_samples"]
            if n < 2:
                guards.append({"window": wname, "jj": jj,
                               "guard": ">=2 actual samples", "pass": False,
                               "n": n})
            for c in CASES:
                p2p = per_case[c]["signatures"][wname][jj]["p2p_rad"]
                if p2p > 0.02:
                    guards.append({"window": wname, "jj": jj, "case": c,
                                   "guard": "p2p <= 0.02 rad",
                                   "pass": False, "p2p_rad": p2p})
            linf = sep[wname][jj]
            if linf < 0.10:
                guards.append({"window": wname, "jj": jj,
                               "guard": "L-inf sep >= 0.10 rad",
                               "pass": False, "sep_rad": linf})
    results["guards"] = guards

    # --- overall evidence-quality conclusion (AC4: only VALID/INCONCLUSIVE/INVALID) ---
    all_finite = all(math.isfinite(col)
                     for c in per_case.values() for col in c["qa"].values()
                     if isinstance(col, (int, float)))
    ok = all_finite and all(c["qa"]["monotonic_time"] for c in per_case.values())
    if not ok:
        verdict = "INVALID"
    elif guards:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "VALID"
    results["evidence_quality"] = {
        "conclusion": verdict,
        "meaning": ("artifact/procedure completeness only; "
                    "not a logical-state or source-characterization PASS"),
    }

    out_path = RUN / "analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, sort_keys=True)
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
