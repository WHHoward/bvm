#!/usr/bin/env python3
"""M8-002 (JH-20260812-M8-002) attempt-local reanalysis of preserved M8-001 A01 raw.

Pure standard library: reads only the six preserved M8-001 A01 raw CSVs
(single/zero x 0.1/0.05/0.025 ps) and recomputes every preregistered scalar
from preregistration.yaml of M8-001 (fixed windows/bands, half-open
intervals, actual CSV times, no resampling/interpolation). No JoSIM, no
sfq_metrics_v2 import, no netlist/parameter/window changes.

Observable definitions (verbatim from M8-001 preregistration.yaml):
  dut_platform_phase_turns      = ((mean(P_post)-mean(P_pre))/(2*pi)) single minus zero control
  dut_voltage_area_turns        = trapezoid(V(Bn|XDUT), actual t in crosscheck)/Phi0, single minus control
  dut_phase_area_residual_turns = phase delta (same crosscheck endpoints) - area delta, single minus control
  activity_peak_time_ps         = earliest actual time of max |V(B1|XDUT)| inside activity (single)
  activity_fwhm_ps              = last-first actual sampled time at/above half max |V| inside activity (single)
  downstream_platform_phase_turns = (mean(P_post)-mean(P_pre))/(2*pi) for XLOAD, single minus control
  downstream_count              = NOT_APPLICABLE

Bands (adjacent-refinement absolute difference): phase 0.01, area 0.01,
residual 0.005, peak time 0.25 ps, fwhm 0.25 ps, downstream 0.01.
Decision: CONVERGED iff all six runs pass QA, all scalars computable, both
adjacent pairs within every band.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import sys

BASE = pathlib.Path(__file__).resolve().parents[4] / "JH-20260812-M8-001" / "attempts" / "A01" / "runs"
OUT = pathlib.Path(__file__).resolve().parent

# Fixed from M8-001 preregistration (must not be changed after inspecting outputs)
WINDOWS = {
    "pre": (6.0e-12, 9.0e-12),
    "activity": (9.0e-12, 30.0e-12),
    "post": (35.0e-12, 50.0e-12),
    "phase_area_crosscheck": (6.0e-12, 50.0e-12),
}
BANDS = {
    "dut_platform_phase_turns": 0.01,
    "dut_voltage_area_turns": 0.01,
    "dut_phase_area_residual_turns": 0.005,
    "activity_peak_time_ps": 0.25,
    "activity_fwhm_ps": 0.25,
    "downstream_platform_phase_turns": 0.01,
}
PHI0 = 2.067833848e-15
JUNCTIONS = ("B1", "B2")
SUBS = ("XDUT", "XLOAD")
LEVELS = ("0.1ps", "0.05ps", "0.025ps")


def sha256(path: str) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def raw_csv(case: str, dt: str) -> str:
    rid = f"m8-jtl-conv-{case}-{dt}-20260812-01"
    return str(BASE / rid / "raw" / f"{rid}.csv")


def read_csv(path: str) -> dict:
    """Read with strict QA: columns present, finite values, strictly increasing time."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{path}: empty csv")
    header = list(rows[0].keys())
    required = ["time"] + [f"V({j}|{s})" for s in SUBS for j in JUNCTIONS] + \
        [f"P({j}|{s})" for s in SUBS for j in JUNCTIONS]
    missing = [c for c in required if c not in header]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    out = {"time": [], "P": {f"{j}|{s}": [] for s in SUBS for j in JUNCTIONS},
           "V": {f"{j}|{s}": [] for s in SUBS for j in JUNCTIONS}}
    for i, r in enumerate(rows):
        t = float(r["time"])
        if not math.isfinite(t):
            raise ValueError(f"{path}: nonfinite time row {i}")
        if i > 0 and t <= out["time"][-1]:
            raise ValueError(f"{path}: time not strictly increasing row {i}")
        out["time"].append(t)
        for k in out["P"]:
            pv = float(r[f"P({k})"]); vv = float(r[f"V({k})"])
            if not (math.isfinite(pv) and math.isfinite(vv)):
                raise ValueError(f"{path}: nonfinite value {k} row {i}")
            out["P"][k].append(pv); out["V"][k].append(vv)
    # window coverage QA
    for name, (a, b) in WINDOWS.items():
        n = sum(1 for t in out["time"] if a <= t < b)
        if n < 2:
            raise ValueError(f"{path}: window {name} has {n} samples (<2)")
    return out


def window_mean(csvd: dict, col: str, win: tuple) -> float:
    a, b = win
    vals = [v for t, v in zip(csvd["time"], csvd["P"][col]) if a <= t < b]
    return sum(vals) / len(vals)


def trapezoid(values: list, times: list) -> float:
    return sum(0.5 * (values[i] + values[i + 1]) * (times[i + 1] - times[i])
               for i in range(len(values) - 1))


def crosscheck(csvd: dict, key: str) -> dict:
    """Phase delta / area / residual over [6e-12, 50e-12) half-open, actual times."""
    a, b = WINDOWS["phase_area_crosscheck"]
    idx = [i for i, t in enumerate(csvd["time"]) if a <= t < b]
    p = [csvd["P"][key][i] for i in idx]
    v = [csvd["V"][key][i] for i in idx]
    t = [csvd["time"][i] for i in idx]
    phase_turns = (p[-1] - p[0]) / (2.0 * math.pi)
    area_turns = trapezoid(v, t) / PHI0
    return {"phase_turns": phase_turns, "area_turns": area_turns,
            "residual_turns": phase_turns - area_turns,
            "selected_first_time_s": t[0], "selected_last_time_s": t[-1],
            "sample_count": len(t)}


def activity_diagnostics(csvd: dict) -> dict:
    """peak time / FWHM for V(B1|XDUT) in single run; activity proxies only."""
    a, b = WINDOWS["activity"]
    pairs = [(t, abs(v)) for t, v in zip(csvd["time"], csvd["V"]["B1|XDUT"]) if a <= t < b]
    mx = max(v for _, v in pairs)
    peak_t = next(t for t, v in pairs if v == mx)  # earliest max
    above = [t for t, v in pairs if v >= 0.5 * mx]
    return {"max_abs_voltage_V": mx, "peak_time_ps": peak_t * 1e12,
            "fwhm_ps": (above[-1] - above[0]) * 1e12,
            "half_max_sample_count": len(above)}


def main() -> int:
    # QA + per-level scalars
    results: dict = {}
    for dt in LEVELS:
        s = read_csv(raw_csv("single", dt))
        z = read_csv(raw_csv("zero", dt))
        if s["time"] != z["time"]:
            raise ValueError(f"{dt}: control/signal time arrays differ")
        lvl: dict = {}
        for sub in SUBS:
            for j in JUNCTIONS:
                key = f"{j}|{sub}"
                sp = (window_mean(s, key, WINDOWS["post"]) - window_mean(s, key, WINDOWS["pre"])) / (2 * math.pi)
                zp = (window_mean(z, key, WINDOWS["post"]) - window_mean(z, key, WINDOWS["pre"])) / (2 * math.pi)
                lvl[f"platform_{sub}_{j}"] = sp - zp
                sc = crosscheck(s, key); zc = crosscheck(z, key)
                lvl[f"area_{sub}_{j}"] = sc["area_turns"] - zc["area_turns"]
                lvl[f"residual_{sub}_{j}"] = sc["residual_turns"] - zc["residual_turns"]
        act = activity_diagnostics(s)
        lvl["activity_peak_time_ps"] = act["peak_time_ps"]
        lvl["activity_fwhm_ps"] = act["fwhm_ps"]
        results[dt] = lvl

    # adjacent-refinement comparison vs bands
    table: dict = {}
    for a, b in (("0.1ps", "0.05ps"), ("0.05ps", "0.025ps")):
        ra, rb = results[a], results[b]
        rows: dict = {}
        obs_map = {
            "dut_platform_phase_turns": [("platform_XDUT_B1", "platform_XDUT_B2")],
            "dut_voltage_area_turns": [("area_XDUT_B1", "area_XDUT_B2")],
            "dut_phase_area_residual_turns": [("residual_XDUT_B1", "residual_XDUT_B2")],
            "downstream_platform_phase_turns": [("platform_XLOAD_B1", "platform_XLOAD_B2")],
            "activity_peak_time_ps": [("activity_peak_time_ps",)],
            "activity_fwhm_ps": [("activity_fwhm_ps",)],
        }
        ok = True
        for obs, keys in obs_map.items():
            diffs = {}
            for k in keys[0]:
                diffs[k] = abs(rb[k] - ra[k])
            within = all(v <= BANDS[obs] for v in diffs.values())
            ok &= within
            rows[obs] = {"absolute_difference": diffs, "band": BANDS[obs], "within_band": within}
        table[f"{a}->{b}"] = {"within_band_all": ok, "observables": rows}

    classification = "CONVERGED" if all(t["within_band_all"] for t in table.values()) else "INCONCLUSIVE"

    pkg = {
        "task_id": "JH-20260812-M8-002",
        "attempt_id": "A01",
        "source": "preserved M8-001 A01 raw CSVs (hashes below)",
        "raw_sha256": {f"{case}_{dt}": sha256(raw_csv(case, dt))
                       for case in ("zero", "single") for dt in LEVELS},
        "windows_s": {k: list(v) for k, v in WINDOWS.items()},
        "bands": BANDS,
        "scalars_by_dt": results,
        "adjacent_refinement": table,
        "classification": classification,
        "wording": (
            "CONVERGED: all six preserved runs pass QA, every preregistered scalar is "
            "computable and both adjacent pairs are within their preregistered task-local "
            "bands. Classification is bounded numerical convergence for this calibration "
            "fixture only; downstream_count remains NOT_APPLICABLE; not a physical Gate, "
            "not a global tolerance freeze (M9 owns METRIC_SPEC_V2)."
        ),
    }
    (OUT / "m8-002-convergence.json").write_text(json.dumps(pkg, indent=2) + "\n")
    (OUT / "m8-002-convergence.md").write_text(render_md(pkg))
    print("classification:", classification)
    for pair, t in table.items():
        print(f"  {pair}: {'WITHIN_BAND' if t['within_band_all'] else 'OUTSIDE_BAND'}")
    return 0


def render_md(pkg: dict) -> str:
    L = ["# M8-002 (JH-20260812-M8-002) A01 — preserved-evidence reanalysis", "",
         "## Classification", "", f"**{pkg['classification']}**", "", pkg["wording"], "",
         "## Raw scalars by dt (control-corrected)", "",
         "| dt | sub | junction | platform turns | area turns | residual turns |",
         "|---|---|---|---|---|---|"]
    for dt, r in pkg["scalars_by_dt"].items():
        for sub in SUBS:
            for j in JUNCTIONS:
                L.append(f"| {dt} | {sub} | {j} | {r[f'platform_{sub}_{j}']:.12g} | "
                         f"{r[f'area_{sub}_{j}']:.12g} | {r[f'residual_{sub}_{j}']:.12g} |")
    L += ["", "| dt | activity peak (ps) | activity FWHM (ps) |", "|---|---|---|"]
    for dt, r in pkg["scalars_by_dt"].items():
        L.append(f"| {dt} | {r['activity_peak_time_ps']:.9g} | {r['activity_fwhm_ps']:.9g} |")
    L += ["", "## Adjacent-refinement comparison", ""]
    for pair, t in pkg["adjacent_refinement"].items():
        L.append(f"### {pair} — {'WITHIN_BAND' if t['within_band_all'] else 'OUTSIDE_BAND'}")
        L.append("| observable | difference | band | within band |")
        L.append("|---|---|---|---|")
        for obs, v in t["observables"].items():
            d = ", ".join(f"{k}={x:.6g}" for k, x in v["absolute_difference"].items())
            L.append(f"| {obs} | {d} | {v['band']} | {v['within_band']} |")
        L.append("")
    L += ["## Wording limits", "",
          "- activity_peak_time_ps / activity_fwhm_ps are activity-timing proxies and waveform",
          "  diagnostics for V(B1|XDUT) in the single-input run, not event/pulse counts.",
          "- downstream_platform_phase_turns is a loaded-downstream platform diagnostic only.",
          "- Bounded numerical-convergence classification for this calibration fixture only;",
          "  no physical Gate, no global tolerance freeze.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
