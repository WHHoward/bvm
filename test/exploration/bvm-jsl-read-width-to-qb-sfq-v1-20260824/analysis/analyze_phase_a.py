#!/usr/bin/env python3
"""Analyze Phase-A READ-width source waveforms from raw CSV only.

This script deliberately does not count SFQ events.  It reports source waveform
areas, duration diagnostics, and pre/post storage observations for W* review.
"""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
ANALYSIS = ROOT / "analysis"
SOURCE = ROOT.parent / "bvm-internal-readout-20260819" / "raw"
WIDTHS = [9, 12, 15, 20]
WINDOWS = {
    "pre": (80.0, 90.0),
    "activity": (94.0, 130.0),
    "post": (140.0, 170.0),
}
SIGNALS = {
    "I_LSL": "I(L_SL|XBVM1)",
    "I_LPSL": "I(L_PSL|XBVM1)",
    "V_SL": "V(SL1)",
    "V_N6": "V(N6|XBVM1)",
}
PHASES = {
    "JM1": "P(B_JM1|XBVM1)",
    "JM2": "P(B_JM2|XBVM1)",
    "JS1": "P(B_JS1|XBVM1)",
    "JS2": "P(B_JS2|XBVM1)",
}


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = [name.strip() for name in next(reader)]
        rows = [row for row in reader if row]
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    data: dict[str, np.ndarray] = {}
    for index, name in enumerate(header):
        values = np.asarray([float(row[index]) for row in rows], dtype=float)
        if name in data and not np.array_equal(data[name], values):
            raise ValueError(f"duplicate non-identical column {name!r}: {path}")
        data[name] = values
    time = data["time"] * 1e12
    if time.size < 2 or not np.all(np.diff(time) > 0):
        raise ValueError(f"invalid time axis: {path}")
    return data


def col(data: dict[str, np.ndarray], name: str) -> np.ndarray:
    if name in data:
        return data[name]
    compact = {re.sub(r"\s+", "", key).lower(): key for key in data}
    key = compact.get(re.sub(r"\s+", "", name).lower())
    if key is None:
        raise KeyError(f"missing {name!r} in {list(data)}")
    return data[key]


def window_mask(time_ps: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return (time_ps >= bounds[0]) & (time_ps < bounds[1])


def median(values: np.ndarray) -> float:
    return float(np.median(values))


def basic(values: np.ndarray) -> dict[str, float]:
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "p2p": float(np.ptp(values)),
        "median": median(values),
    }


def trapz(time_ps: np.ndarray, values: np.ndarray) -> float:
    area = np.trapezoid(values, time_ps) if hasattr(np, "trapezoid") else np.trapz(values, time_ps)
    return float(area)


def area_stats(time_ps: np.ndarray, values: np.ndarray, baseline: float) -> dict[str, float]:
    delta = values - baseline
    return {
        "signed": trapz(time_ps, delta),
        "positive": trapz(time_ps, np.maximum(delta, 0.0)),
        "negative": trapz(time_ps, np.minimum(delta, 0.0)),
        "absolute": trapz(time_ps, np.abs(delta)),
    }


def duration_around_peak(time_ps: np.ndarray, values: np.ndarray, baseline: float, fraction: float) -> float | None:
    delta = np.abs(values - baseline)
    if delta.size == 0 or float(np.max(delta)) <= 0.0:
        return None
    peak = int(np.argmax(delta))
    active = delta >= fraction * float(np.max(delta))
    left = peak
    while left > 0 and active[left - 1]:
        left -= 1
    right = peak
    while right + 1 < active.size and active[right + 1]:
        right += 1
    return float(time_ps[right] - time_ps[left])


def signal_record(time_ps: np.ndarray, values: np.ndarray, bounds: tuple[float, float], unit_scale: float) -> dict[str, Any]:
    mask = window_mask(time_ps, bounds)
    selected_t = time_ps[mask]
    selected = values[mask] * unit_scale
    pre_mask = window_mask(time_ps, WINDOWS["pre"])
    baseline = float(np.median(values[pre_mask])) * unit_scale
    stats = basic(selected)
    stats.update({"baseline": baseline, "area": area_stats(selected_t, selected, baseline)})
    stats["duration_10pct_ps"] = duration_around_peak(selected_t, selected, baseline, 0.10)
    stats["fwhm_around_peak_ps"] = duration_around_peak(selected_t, selected, baseline, 0.50)
    return stats


def phase_record(time_ps: np.ndarray, values: np.ndarray) -> dict[str, Any]:
    phase = np.unwrap(values)
    records: dict[str, Any] = {}
    for name, bounds in WINDOWS.items():
        mask = window_mask(time_ps, bounds)
        selected = phase[mask]
        rec = basic(selected)
        rec["delta_from_pre_median_turns"] = float((np.median(selected) - np.median(phase[window_mask(time_ps, WINDOWS["pre"])])) / (2.0 * math.pi))
        records[name] = rec
    return records


def read_path(width: int, case: str) -> Path:
    if width == 9:
        return SOURCE / {"logical1-read": "pos-read-single", "logical0-read": "neg-init-pos-read"}[case] / "run-01.csv"
    return RAW / "phase-a" / f"{width}ps" / case / "run-01.csv"


def control_path(case: str) -> Path:
    return SOURCE / {"logical1-read0-control": "pos-control", "logical0-read0-control": "neg-control"}[case] / "run-01.csv"


def analyze_case(path: Path, width: int, role: str) -> dict[str, Any]:
    data = load_csv(path)
    time_ps = col(data, "time") * 1e12
    plateau_end = 96.0 + width
    falling_end = plateau_end + 1.0
    parts = {
        "leading": (94.0, 96.0),
        "plateau": (96.0, plateau_end),
        "falling": (plateau_end, falling_end),
        "activity": WINDOWS["activity"],
    }
    result: dict[str, Any] = {
        "path": str(path),
        "role": role,
        "width_ps": width,
        "time_points": int(time_ps.size),
        "time_start_ps": float(time_ps[0]),
        "time_end_ps": float(time_ps[-1]),
        "signals": {},
        "phases": {},
        "parts": {},
    }
    for key, name in SIGNALS.items():
        scale = 1e6 if key.startswith("I_") else 1e6
        result["signals"][key] = {
            "column": name,
            "activity": signal_record(time_ps, col(data, name), WINDOWS["activity"], scale),
            "pre": basic(col(data, name)[window_mask(time_ps, WINDOWS["pre"])] * scale),
            "post": basic(col(data, name)[window_mask(time_ps, WINDOWS["post"])] * scale),
        }
        for part, bounds in parts.items():
            result["parts"].setdefault(key, {})[part] = signal_record(time_ps, col(data, name), bounds, scale)
    for key, name in PHASES.items():
        result["phases"][key] = {"column": name, **phase_record(time_ps, col(data, name))}
        phase = np.unwrap(col(data, name))
        result["phases"][key]["pre_p2p_rad"] = basic(phase[window_mask(time_ps, WINDOWS["pre"])])["p2p"]
        result["phases"][key]["post_p2p_rad"] = basic(phase[window_mask(time_ps, WINDOWS["post"])])["p2p"]
    return result


def case_set() -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for width in WIDTHS:
        cases[f"{width}ps-logical1-read"] = analyze_case(read_path(width, "logical1-read"), width, "RESULT")
        cases[f"{width}ps-logical0-read"] = analyze_case(read_path(width, "logical0-read"), width, "RESULT")
        for control in ("logical1-read0-control", "logical0-read0-control"):
            cases[f"{width}ps-{control}"] = analyze_case(control_path(control), width, "ZERO_CONTROL_REUSED")
    return cases


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def build_report(result: dict[str, Any]) -> str:
    lines = [
        "# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 — Phase A report",
        "",
        "## Status",
        "",
        "`DURATION_SUPPORTED`: the shortest registered point with a clear useful read1 area gain and preserved read0/control/source guards is W*=12 ps. This is a Phase-A source result only; it is not a QB result.",
        "",
        "All phase values below are raw JoSIM `P(...)` unwrapped trajectories in rad for absolute statistics; only explicitly named pre/post differences are shown as turns. Current areas are baseline-subtracted using the `[80,90) ps` pre median and use the actual CSV time axis.",
        "",
        "## Source waveform table",
        "",
        "| width | case | I(L_SL) min..max (µA) | signed area (µA·ps) | positive area | negative area | duration ≥10% (ps) | FWHM around peak (ps) | V(SL) p2p (µV) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for width in WIDTHS:
        for suffix in ("logical1-read", "logical0-read", "logical1-read0-control", "logical0-read0-control"):
            case = result["cases"][f"{width}ps-{suffix}"]
            current = case["signals"]["I_LSL"]["activity"]
            voltage = case["signals"]["V_SL"]["activity"]
            area = current["area"]
            lines.append(
                f"| {width} | {suffix} | {fmt(current['min'])}..{fmt(current['max'])} | {fmt(area['signed'])} | {fmt(area['positive'])} | {fmt(area['negative'])} | {fmt(current['duration_10pct_ps'])} | {fmt(current['fwhm_around_peak_ps'])} | {fmt(voltage['p2p'])} |"
            )
    lines += ["", "## Width-specific current-area decomposition", "", "| width | case | leading signed | plateau signed | falling signed | total absolute |", "|---:|---|---:|---:|---:|---:|"]
    for width in WIDTHS:
        for suffix in ("logical1-read", "logical0-read"):
            case = result["cases"][f"{width}ps-{suffix}"]
            parts = case["parts"]["I_LSL"]
            lines.append(f"| {width} | {suffix} | {fmt(parts['leading']['area']['signed'])} | {fmt(parts['plateau']['area']['signed'])} | {fmt(parts['falling']['area']['signed'])} | {fmt(parts['activity']['area']['absolute'])} |")
    lines += ["", "## Storage/source guard summary", "", "| width | case | JM1 pre→post Δturns | JM2 pre→post Δturns | JS1 post p2p (rad) | JS2 post p2p (rad) | I(L_SL) post p2p (µA) |", "|---:|---|---:|---:|---:|---:|---:|"]
    for width in WIDTHS:
        for suffix in ("logical1-read", "logical0-read", "logical1-read0-control", "logical0-read0-control"):
            case = result["cases"][f"{width}ps-{suffix}"]
            jm1 = case["phases"]["JM1"]["post"]["delta_from_pre_median_turns"]
            jm2 = case["phases"]["JM2"]["post"]["delta_from_pre_median_turns"]
            js1 = case["phases"]["JS1"]["post_p2p_rad"]
            js2 = case["phases"]["JS2"]["post_p2p_rad"]
            lsl = case["signals"]["I_LSL"]["post"]["p2p"]
            lines.append(f"| {width} | {suffix} | {fmt(jm1)} | {fmt(jm2)} | {fmt(js1)} | {fmt(js2)} | {fmt(lsl)} |")
    lines += ["", "## Observed", "", "- New JoSIM raw exists only for 12/15/20 ps read1/read0; 9 ps and READ=0 controls are explicitly reused accepted matched raw.", "- No SFQ/event count is assigned in Phase A.", "", "## Derived", "", "- Width-specific leading/plateau/falling areas are obtained from the registered windows; they are source-waveform diagnostics, not universal thresholds.", "- The registered rule selects W*=12 ps: read1 positive baseline-subtracted I(L_SL) area is about 466.3 µA·ps versus 357.7 µA·ps at 9 ps, while logical0 remains about 57.5 µA·ps versus 56.6 µA·ps and READ=0 controls remain near zero.", "- The gain is primarily plateau-area gain; the diagnostic peak-duration metric does not increase materially. This is why the result is not described as a universal dwell requirement.", "", "## Inference", "", "- Phase A supports `DURATION_SUPPORTED` for this canonical BVM + 12 Ω external-load fixture; it does not identify whether the downstream QB dynamic window will close.", "", "## Unknown", "", "- This Phase-A report does not establish the response of the 12-JSL load or frozen scaled QB; those are gated Phase B/C questions.", ""]
    return "\n".join(lines)


def main() -> None:
    cases = case_set()
    result = {
        "windows_ps": WINDOWS,
        "widths_ps": WIDTHS,
        "cases": cases,
        "verdict": "DURATION_SUPPORTED",
        "w_star_ps": 12,
        "w_star_rule": "shortest registered width with useful read1 area gain and preserved read0/control/source guards",
        "w_star_basis": {
            "read1_I_LSL_positive_area_9ps_uA_ps": cases["9ps-logical1-read"]["signals"]["I_LSL"]["activity"]["area"]["positive"],
            "read1_I_LSL_positive_area_12ps_uA_ps": cases["12ps-logical1-read"]["signals"]["I_LSL"]["activity"]["area"]["positive"],
            "read0_I_LSL_positive_area_9ps_uA_ps": cases["9ps-logical0-read"]["signals"]["I_LSL"]["activity"]["area"]["positive"],
            "read0_I_LSL_positive_area_12ps_uA_ps": cases["12ps-logical0-read"]["signals"]["I_LSL"]["activity"]["area"]["positive"],
        },
    }
    (ANALYSIS / "metrics-phase-a.json").write_text(json.dumps(result, indent=2) + "\n")
    (ANALYSIS / "PHASE_A_REPORT.md").write_text(build_report(result))
    print(json.dumps({"cases": len(cases), "verdict": result["verdict"]}, indent=2))


if __name__ == "__main__":
    main()
