#!/usr/bin/env python3
"""M8 (JH-20260812-M8-001) bounded timestep-convergence analysis.

Deterministic task-local analyzer. Uses the frozen, read-only
scripts/sfq_metrics_v2.py for window statistics, control correction and
same-JJ phase/voltage-area cross-check, and computes the two waveform
diagnostics (activity peak time / FWHM) directly from the raw CSV per the
preregistration wording. Windows and bands come verbatim from
preregistration.yaml; they are fixed before execution and must not be moved.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[6] / "scripts"))
import sfq_metrics_v2 as m2  # noqa: E402  (frozen read-only import)

BASE = pathlib.Path(__file__).resolve().parents[1] / "runs"
OUT = pathlib.Path(__file__).resolve().parent

WINDOWS = {
    "pre": [6.0e-12, 9.0e-12],
    "activity": [9.0e-12, 30.0e-12],
    "post": [35.0e-12, 50.0e-12],
    "phase_area_crosscheck": [6.0e-12, 50.0e-12],
}

BANDS = {
    "dut_platform_phase_turns": 0.01,
    "dut_voltage_area_turns": 0.01,
    "dut_phase_area_residual_turns": 0.005,
    "activity_peak_time_ps": 0.25,
    "activity_fwhm_ps": 0.25,
    "downstream_platform_phase_turns": 0.01,
}

DIRECTIONS = {f"P(B{jn}|X{s})": 1 for s in ("DUT", "LOAD") for jn in (1, 2)}
VOLT_MAP = {
    f"P(B{jn}|X{s})": {
        "voltage_column": f"V(B{jn}|X{s})",
        "orientation": 1,
        "endpoint_window": "phase_area_crosscheck",
    }
    for s in ("DUT", "LOAD")
    for jn in (1, 2)
}


def raw_csv(case: str, dt: str) -> pathlib.Path:
    rid = f"m8-jtl-conv-{case}-{dt}-20260812-01"
    return BASE / rid / "raw" / f"{rid}.csv"


def activity_peak_fwhm(csv_path: str) -> dict:
    """Activity-timing proxy + waveform diagnostic for V(B1|XDUT), single run.

    peak_time_ps: actual CSV time of the EARLIEST maximum |V| inside activity.
    fwhm_ps: width from first to last actual sampled time at or above half of
    the maximum |V| inside activity, WITHOUT interpolation.
    Both are activity proxies / waveform diagnostics, never event counts.
    """
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    start, end = WINDOWS["activity"]
    times = [float(r["time"]) for r in rows if start <= float(r["time"]) < end]
    vals = [abs(float(r["V(B1|XDUT)"])) for r in rows if start <= float(r["time"]) < end]
    if not times or len(times) != len(vals):
        raise ValueError("activity window has no samples")
    max_abs = max(vals)
    peak_idx = next(i for i, v in enumerate(vals) if v == max_abs)  # earliest max
    half = [i for i, v in enumerate(vals) if v >= 0.5 * max_abs]
    return {
        "max_abs_voltage_V": max_abs,
        "activity_peak_time_ps": times[peak_idx] * 1e12,
        "peak_sample_index": peak_idx,
        "fwhm_first_sample_time_ps": times[half[0]] * 1e12,
        "fwhm_last_sample_time_ps": times[half[-1]] * 1e12,
        "activity_fwhm_ps": (times[half[-1]] - times[half[0]]) * 1e12,
        "half_max_sample_count": len(half),
        "wording": "activity-timing proxy / waveform diagnostic; not an event or pulse count",
    }


def main() -> int:
    plan_w = {
        "schema_version": 1,
        "windows_s": {k: v for k, v in WINDOWS.items() if k in ("pre", "activity", "post")},
        "phase_directions": DIRECTIONS,
        "activity_threshold_rad": 0.3,
    }
    plan_va = {
        "schema_version": 1,
        "windows_s": WINDOWS,
        "voltage_area": VOLT_MAP,
    }

    results: dict = {}
    for dt in ("0.1ps", "0.05ps", "0.025ps"):
        s_csv = str(raw_csv("single", dt))
        z_csv = str(raw_csv("zero", dt))
        w = m2.windowed_analyze(s_csv, plan_w, control_csv=z_csv)
        va = m2.voltage_area_analyze(s_csv, plan_va, control_csv=z_csv)
        cc = va["control_corrected"]
        platform = w["control_corrected"]
        wf = activity_peak_fwhm(s_csv)
        results[dt] = {
            "dut_platform_phase_turns": {
                jn: platform[f"P(B{jn}|XDUT)"]["corrected_delta_turns"] for jn in (1, 2)
            },
            "dut_voltage_area_turns": {
                jn: cc[f"P(B{jn}|XDUT)"]["corrected_area_turns"] for jn in (1, 2)
            },
            "dut_phase_area_residual_turns": {
                jn: cc[f"P(B{jn}|XDUT)"]["corrected_residual_turns"] for jn in (1, 2)
            },
            "downstream_platform_phase_turns": {
                jn: platform[f"P(B{jn}|XLOAD)"]["corrected_delta_turns"] for jn in (1, 2)
            },
            "activity_peak_time_ps": wf["activity_peak_time_ps"],
            "activity_fwhm_ps": wf["activity_fwhm_ps"],
            "waveform": wf,
        }

    # Adjacent-refinement differences and band classification
    lvl = ("0.1ps", "0.05ps", "0.025ps")
    table: dict = {}
    verdicts: list[str] = []
    for a, b in ((lvl[0], lvl[1]), (lvl[1], lvl[2])):
        row: dict = {}
        for obs in BANDS:
            ra, rb = results[a][obs], results[b][obs]
            if isinstance(ra, dict):
                diffs = {jn: abs(rb[jn] - ra[jn]) for jn in ra}
                row[obs] = {
                    "absolute_difference_per_junction": diffs,
                    "band": BANDS[obs],
                    "within_band": all(d <= BANDS[obs] for d in diffs.values()),
                }
            else:
                d = abs(rb - ra)
                row[obs] = {"absolute_difference": d, "band": BANDS[obs], "within_band": d <= BANDS[obs]}
        ok = all(v["within_band"] for v in row.values())
        table[f"{a}->{b}"] = {"within_band_all": ok, "observables": row}
        verdicts.append(f"{a}->{b}: {'WITHIN_BAND' if ok else 'OUTSIDE_BAND'}")

    all_pass = all(t["within_band_all"] for t in table.values())
    classification = "CONVERGED" if all_pass else "INCONCLUSIVE"

    package = {
        "preregistration_sha256": None,  # filled by wrapper with file hash
        "windows_s": WINDOWS,
        "bands": BANDS,
        "raw_scalars_by_dt": results,
        "adjacent_refinement": table,
        "classification": classification,
        "classification_wording": (
            "CONVERGED: all six runs passed QA, every registered scalar is computable and "
            "both adjacent pairs are within their preregistered task-local bands. "
            "INCONCLUSIVE: any valid required scalar is missing/ambiguous/outside its band "
            "at the maximum registered depth. This is a bounded numerical-convergence "
            "classification for this calibration fixture only; not a physical Gate, not a "
            "global tolerance freeze (M9 owns METRIC_SPEC_V2)."
        ),
        "disclaimer": (
            "downstream_count remains NOT_APPLICABLE (M9 has not frozen a downstream "
            "event-counting semantic; this task must not invent one)."
        ),
    }

    (OUT / "m8-convergence.json").write_text(json.dumps(package, indent=2) + "\n")
    md = _render_markdown(package, verdicts)
    (OUT / "m8-convergence.md").write_text(md)
    print("classification:", classification)
    for v in verdicts:
        print(" ", v)
    return 0


def _render_markdown(pkg: dict, verdicts: list[str]) -> str:
    lines = [
        "# M8 bounded timestep-convergence (JH-20260812-M8-001) — A01 analysis",
        "",
        "## Classification",
        "",
        f"**{pkg['classification']}**",
        "",
        pkg["classification_wording"],
        "",
        pkg["disclaimer"],
        "",
        "## Raw scalars by dt (control-corrected, turns unless noted)",
        "",
        "| dt | junction | platform turns | voltage-area turns | residual turns | downstream platform turns |",
        "|---|---|---|---|---|---|",
    ]
    for dt, r in pkg["raw_scalars_by_dt"].items():
        for jn in (1, 2):
            lines.append(
                f"| {dt} | B{jn} | {r['dut_platform_phase_turns'][jn]:.12g} | "
                f"{r['dut_voltage_area_turns'][jn]:.12g} | "
                f"{r['dut_phase_area_residual_turns'][jn]:.12g} | "
                f"{r['downstream_platform_phase_turns'][jn]:.12g} |"
            )
    lines += [
        "",
        "| dt | activity peak time (ps) | activity FWHM (ps) |",
        "|---|---|---|",
    ]
    for dt, r in pkg["raw_scalars_by_dt"].items():
        lines.append(f"| {dt} | {r['activity_peak_time_ps']:.9g} | {r['activity_fwhm_ps']:.9g} |")
    lines += ["", "## Adjacent-refinement comparison", ""]
    for pair, t in pkg["adjacent_refinement"].items():
        lines.append(f"### {pair} — {'WITHIN_BAND' if t['within_band_all'] else 'OUTSIDE_BAND'}")
        lines.append("")
        lines.append("| observable | difference | band | within band |")
        lines.append("|---|---|---|---|")
        for obs, v in t["observables"].items():
            if "absolute_difference_per_junction" in v:
                d = ", ".join(f"B{k}={x:.6g}" for k, x in v["absolute_difference_per_junction"].items())
            else:
                d = f"{v['absolute_difference']:.6g}"
            lines.append(f"| {obs} | {d} | {v['band']} | {v['within_band']} |")
        lines.append("")
    lines += [
        "## Wording limits",
        "",
        "- `activity_peak_time_ps` / `activity_fwhm_ps` are activity-timing proxies and",
        "  waveform diagnostics for V(B1|XDUT) in the single-input run, not event or pulse counts.",
        "- `downstream_platform_phase_turns` is a loaded-downstream platform diagnostic only.",
        "- This is a bounded numerical-convergence classification for this calibration fixture",
        "  and these registered observables; no physical Gate, no global tolerance freeze.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
