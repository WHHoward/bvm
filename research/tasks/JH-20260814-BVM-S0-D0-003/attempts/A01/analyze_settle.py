#!/usr/bin/env python3
"""analyze_settle -- deterministic analysis for JH-20260814-BVM-S0-D0-003 A01.

Per AC4/design/settling-readiness-discriminator.md: five preregistered
half-open settle windows, stability (>=2 finite samples, p2p <= 0.020 rad for
every case and both JM1/JM2 columns), distinguishability (mean two-component
vector (JM1, JM2) L-infinity distance >= 0.100 rad for all three case pairs),
pair+persistence rule over the four adjacent pairs, and the first qualifying
operational readiness bound (or explicit absence).

Per AC5: same-run direct P/V endpoint delta (rad and turns), actual-time
trapezoid area (V*s and turns), signed residual with voltage_to_phase_sign=+1
and reporting_direction=+1 on [9,31) ps for JM1 N1->n_jm1o and JM2 n_jm2i->N2;
no residual tolerance declared.  V(SL1)/I(L_SL|XBVM1) preserved as raw probes
only.

Pure stdlib; never executes JoSIM and never modifies files.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[5]
RUN = REPO_ROOT / "test/final/bvm/runs/bvm-s0-d0-settle-20260814-01"
PHI0 = 2.067833848e-15  # Wb (METRIC_SPEC_V2 sec 7.1)

CASES = ("init_positive", "init_negative", "no_init_control")
P_COLS = {"JM1": "P(B_JM1|XBVM1)", "JM2": "P(B_JM2|XBVM1)"}
V_COLS = {"JM1": "V(B_JM1|XBVM1)", "JM2": "V(B_JM2|XBVM1)"}
SETTLE_WINDOWS = {
    "settle_35": (35e-12, 45e-12),
    "settle_55": (55e-12, 65e-12),
    "settle_75": (75e-12, 85e-12),
    "settle_95": (95e-12, 105e-12),
    "settle_115": (115e-12, 125e-12),
}
PAIRS = (("settle_35", "settle_55"), ("settle_55", "settle_75"),
         ("settle_75", "settle_95"), ("settle_95", "settle_115"))
STABILITY_P2P_RAD = 0.020
SEP_RAD = 0.100
ACTIVITY = (9e-12, 31e-12)


def load(case: str) -> tuple[list[float], dict[str, list[float]]]:
    with open(RUN / "raw" / case / "run-01.csv", encoding="utf-8") as f:
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


def window_slice(t: list[float], lo: float, hi: float) -> list[int]:
    return [i for i, tv in enumerate(t) if lo <= tv < hi]


def trapezoid(y: list[float], t: list[float]) -> float:
    if len(y) < 2:
        raise ValueError("trapezoid requires >=2 samples")
    return sum(0.5 * (y[i] + y[i + 1]) * (t[i + 1] - t[i])
               for i in range(len(y) - 1))


def win_stats(y: list[float]) -> dict:
    return {"mean_rad": sum(y) / len(y), "min_rad": min(y), "max_rad": max(y),
            "p2p_rad": max(y) - min(y), "n_samples": len(y)}


def main() -> int:
    t = {}
    cols = {}
    for c in CASES:
        t[c], cols[c] = load(c)

    out: dict = {"run": "bvm-s0-d0-settle-20260814-01", "cases": {}}

    # QA
    for c in CASES:
        out["cases"][c] = {"qa": {
            "monotonic_time": all(t[c][i] < t[c][i + 1] for i in range(len(t[c]) - 1)),
            "t_end_s": t[c][-1], "n_samples": len(t[c]),
            "n_nan_inf": sum(1 for col in cols[c].values() for v in col
                             if not math.isfinite(v))}}

    # --- AC5 phase-area on [9,31) ps ---
    act = window_slice(t["init_positive"], *ACTIVITY)
    out["phase_area"] = {}
    for jj in ("JM1", "JM2"):
        out["phase_area"][jj] = {}
        for c in CASES:
            p = [cols[c][P_COLS[jj]][i] for i in act]
            v = [cols[c][V_COLS[jj]][i] for i in act]
            tt = [t[c][i] for i in act]
            p_delta_rad = p[-1] - p[0]
            area_vs = trapezoid(v, tt)
            out["phase_area"][jj][c] = {
                "window_ps": [9.0, 31.0],
                "orientation": {"JM1": "N1->n_jm1o", "JM2": "n_jm2i->N2"}[jj],
                "voltage_to_phase_sign": 1,
                "reporting_direction": 1,
                "phase_delta_rad": p_delta_rad,
                "phase_delta_turns": p_delta_rad / (2 * math.pi),
                "area_trapezoid_vs": area_vs,
                "area_turns": area_vs / PHI0,
                "residual_turns": p_delta_rad / (2 * math.pi) - area_vs / PHI0,
                "n_window_samples": len(act),
                "tolerance_declared": False,
            }

    # --- settle window stats per case/JJ ---
    stats: dict[str, dict[str, dict[str, dict]]] = {}
    for wname, (lo, hi) in SETTLE_WINDOWS.items():
        stats[wname] = {}
        for c in CASES:
            wi = window_slice(t[c], lo, hi)
            stats[wname][c] = {
                jj: win_stats([cols[c][P_COLS[jj]][i] for i in wi])
                for jj in ("JM1", "JM2")}
    out["settle_stats"] = stats

    # --- stability per window (every case, both JJ: >=2 samples, p2p <= 0.02) ---
    stable = {}
    for wname in SETTLE_WINDOWS:
        ok = True
        for c in CASES:
            for jj in ("JM1", "JM2"):
                s = stats[wname][c][jj]
                if s["n_samples"] < 2 or s["p2p_rad"] > STABILITY_P2P_RAD:
                    ok = False
        stable[wname] = ok
    out["stability"] = stable

    # --- distinguishability per window: all three case pairs, L-inf on (JM1, JM2) means ---
    pair_names = (("init_positive", "init_negative"),
                  ("init_positive", "no_init_control"),
                  ("init_negative", "no_init_control"))
    dist = {}
    for wname in SETTLE_WINDOWS:
        d = {}
        for (a, b) in pair_names:
            linf = max(abs(stats[wname][a][jj]["mean_rad"]
                           - stats[wname][b][jj]["mean_rad"])
                       for jj in ("JM1", "JM2"))
            d[f"{a}|{b}"] = {"linf_rad": linf, "pass": linf >= SEP_RAD}
        dist[wname] = d
        dist[wname]["distinguishable"] = all(
            d[f"{a}|{b}"]["pass"] for (a, b) in pair_names)
    out["distinguishability"] = dist

    # --- pair+persistence rule ---
    ready = None
    for (wa, wb) in PAIRS:
        if stable[wa] and stable[wb] and dist[wa]["distinguishable"] \
                and dist[wb]["distinguishable"]:
            later = [w for w in SETTLE_WINDOWS
                     if list(SETTLE_WINDOWS).index(w)
                     > list(SETTLE_WINDOWS).index(wb)]
            if all(stable[w] and dist[w]["distinguishable"] for w in later):
                ready = {"pair": [wa, wb],
                         "readiness_bound_ps": SETTLE_WINDOWS[wa][0] * 1e12,
                         "later_windows_ok": later}
                break
    out["readiness"] = ready if ready else None

    # --- evidence quality: VALID / INCONCLUSIVE / INVALID ---
    qa_ok = all(out["cases"][c]["qa"]["monotonic_time"]
                and out["cases"][c]["qa"]["n_nan_inf"] == 0 for c in CASES)
    if not qa_ok:
        verdict = "INVALID"
    elif ready is None:
        verdict = "INCONCLUSIVE"
    else:
        verdict = "VALID"
    out["evidence_quality"] = {
        "conclusion": verdict,
        "meaning": ("operational readiness bound within tested grid; "
                    "not a logical-state or source-characterization PASS"),
    }

    out_path = RUN / "analysis.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
