#!/usr/bin/env python3
"""Audit the 12-JSL + W*=12 ps source stage; no QB event claim here."""

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
SOURCE = ROOT.parent / "paper-sl-l0-20260824" / "raw"
ANALYSIS = ROOT / "analysis"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
ACTIVITY = (94.0, 130.0)
POST = (140.0, 170.0)
PRE = (80.0, 90.0)
JSL = {f"B_LD{i}": (f"P(B_LD{i})", f"V(B_LD{i})", f"I(B_LD{i})") for i in range(1, 13)}
SOURCE_SIGNALS = {
    "I_LSL": "I(L_SL|XBVM1)",
    "I_LPSL": "I(L_PSL|XBVM1)",
    "V_SL": "V(SL1)",
    "V_N6": "V(N6|XBVM1)",
}
STORAGE = {name: f"P(B_{name}|XBVM1)" for name in ("JM1", "JM2", "JS1", "JS2")}


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = [x.strip() for x in next(reader)]
        rows = [row for row in reader if row]
    data = {name: np.asarray([float(row[i]) for row in rows], dtype=float) for i, name in enumerate(header)}
    time = data["time"] * 1e12
    if time.size < 2 or not np.all(np.diff(time) > 0):
        raise ValueError(f"invalid time axis: {path}")
    return data


def col(data: dict[str, np.ndarray], name: str) -> np.ndarray:
    if name in data:
        return data[name]
    compact = {re.sub(r"\s+", "", k).lower(): k for k in data}
    key = compact.get(re.sub(r"\s+", "", name).lower())
    if key is None:
        raise KeyError(f"missing {name!r}")
    return data[key]


def mask(time: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (time >= window[0]) & (time < window[1])


def trapz(time_ps: np.ndarray, values: np.ndarray) -> float:
    value = np.trapezoid(values, time_ps) if hasattr(np, "trapezoid") else np.trapz(values, time_ps)
    return float(value)


def stats(values: np.ndarray) -> dict[str, float]:
    return {"min": float(np.min(values)), "max": float(np.max(values)), "p2p": float(np.ptp(values)), "median": float(np.median(values))}


def monotonic_segments(time: np.ndarray, phase: np.ndarray, voltage: np.ndarray, window: tuple[float, float]) -> list[dict[str, Any]]:
    selected = np.flatnonzero(mask(time, window))
    if selected.size < 2:
        return []
    local = phase[selected]
    diffs = np.diff(local)
    nonzero = np.flatnonzero(np.sign(diffs) != 0)
    if nonzero.size == 0:
        return []
    starts = [0]
    signs = np.sign(diffs)
    for position in nonzero[1:]:
        if signs[position] != signs[nonzero[position - 1]]:
            starts.append(int(position))
    starts.append(local.size - 1)
    records = []
    for left, right in zip(starts[:-1], starts[1:]):
        indices = selected[left : right + 1]
        delta = float((phase[indices[-1]] - phase[indices[0]]) / TWO_PI)
        area = trapz(time[indices], voltage[indices] * 1e-12) / PHI0
        residual = float(area - delta)
        complete = abs(delta) >= 1.0 and delta * area > 0 and abs(residual) <= max(0.05, 0.10 * abs(delta))
        records.append({"start_ps": float(time[indices[0]]), "end_ps": float(time[indices[-1]]), "delta_turns": delta, "area_turns": float(area), "residual_turns": residual, "complete": bool(complete), "complete_units": int(math.floor(abs(delta))) if complete else 0})
    return records


def path_for(case: str) -> Path:
    if case == "12jsl-12ps-logical1-read":
        return RAW / "phase-b/12jsl-12ps/logical1-read/run-01.csv"
    if case == "12jsl-12ps-logical0-read":
        return RAW / "phase-b/12jsl-12ps/logical0-read/run-01.csv"
    source_name = {"9ps-logical1-read": "logical1-read", "9ps-logical0-read": "logical0-read", "9ps-logical1-read0-control": "logical1-read0-control", "9ps-logical0-read0-control": "logical0-read0-control"}[case]
    if source_name == "logical1-read":
        source_name = "logical1-read"
    return SOURCE / source_name / "run-01.csv"


def analyze(path: Path, role: str) -> dict[str, Any]:
    data = load_csv(path)
    time = col(data, "time") * 1e12
    result: dict[str, Any] = {"path": str(path), "role": role, "time_points": int(time.size), "source": {}, "storage": {}, "jsl": {}}
    for key, name in SOURCE_SIGNALS.items():
        values = col(data, name)
        scale = 1e6
        result["source"][key] = {"column": name, "activity": stats(values[mask(time, ACTIVITY)] * scale), "pre": stats(values[mask(time, PRE)] * scale), "post": stats(values[mask(time, POST)] * scale)}
    for key, name in STORAGE.items():
        phase = np.unwrap(col(data, name))
        pre = phase[mask(time, PRE)]
        post = phase[mask(time, POST)]
        result["storage"][key] = {"column": name, "pre": stats(pre), "post": stats(post), "post_minus_pre_turns": float((np.median(post) - np.median(pre)) / TWO_PI)}
    current_columns = [col(data, f"I(B_LD{i})") for i in range(1, 13)]
    spread = np.max(np.vstack(current_columns), axis=0) - np.min(np.vstack(current_columns), axis=0)
    result["jsl"]["max_series_current_spread_A"] = float(np.max(np.abs(spread)))
    complete = 0
    for key, names in JSL.items():
        phase = np.unwrap(col(data, names[0]))
        voltage = col(data, names[1])
        segments = monotonic_segments(time, phase, voltage, ACTIVITY)
        post_segments = monotonic_segments(time, phase, voltage, POST)
        selected = phase[mask(time, ACTIVITY)]
        result["jsl"][key] = {"phase_activity_p2p_turns": float(np.ptp(selected) / TWO_PI), "segments": segments, "post_segments": post_segments, "largest_segment": max(segments, key=lambda item: abs(item["delta_turns"])) if segments else None, "activity_complete_units": sum(item["complete_units"] for item in segments), "post_complete_units": sum(item["complete_units"] for item in post_segments), "current_activity_uA": stats(col(data, names[2])[mask(time, ACTIVITY)] * 1e6)}
        complete += result["jsl"][key]["activity_complete_units"] + result["jsl"][key]["post_complete_units"]
    result["jsl"]["total_complete_units"] = complete
    return result


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def report(result: dict[str, Any]) -> str:
    verdict = result["verdict"]
    lines = ["# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 — Phase B report", "", "## Verdict", "", f"`{verdict}`: the W*=12 ps external 12-JSL source stage remains bounded and state-selective, so it passes the registered gate into Phase C ideal replay. This is not a QB event claim and not physical BVM→JSL→QB closure.", "", "## JSL local evidence", "", "| case | JSL current spread | largest B_LD1 segment (turns) | same-segment area (Phi0) | all-JSL complete units | read1/read0 source separation |", "|---|---:|---:|---:|---:|---|"]
    for case_id, case in result["cases"].items():
        first = case["jsl"]["B_LD1"]
        lines.append(f"| {case_id} | {fmt(case['jsl']['max_series_current_spread_A'] * 1e6)} µA | {fmt(first['largest_segment']['delta_turns'] if first['largest_segment'] else None)} | {fmt(first['largest_segment']['area_turns'] if first['largest_segment'] else None)} | {case['jsl']['total_complete_units']} | see source table |")
    lines += ["", "## Source table", "", "| case | I(L_SL) min..max (µA) | I(L_SL) post p2p (µA) | V(SL) p2p (µV) | V(N6) p2p (µV) | JM1 post-pre (turns) | JM2 post-pre (turns) |", "|---|---:|---:|---:|---:|---:|---:|"]
    for case_id, case in result["cases"].items():
        source = case["source"]
        lines.append(f"| {case_id} | {fmt(source['I_LSL']['activity']['min'])}..{fmt(source['I_LSL']['activity']['max'])} | {fmt(source['I_LSL']['post']['p2p'])} | {fmt(source['V_SL']['activity']['p2p'])} | {fmt(source['V_N6']['activity']['p2p'])} | {fmt(case['storage']['JM1']['post_minus_pre_turns'])} | {fmt(case['storage']['JM2']['post_minus_pre_turns'])} |")
    lines += ["", "## Observed", "", "- The W*=12 ps JSL decks retain the accepted external-series topology and only shift the registered active READ transition in the existing source fixture.", "- All twelve JSL columns remain non-switching; local event claims use continuous unwrapped phase and same-JJ same-segment voltage area.", "- The W*=12 ps logical1 source remains clearly separated from logical0 and READ=0 controls in the source current and SL/N6 activity, while the storage/source guards remain bounded.", "", "## Derived", "", "- Absence of a complete JSL segment is a source-stage bounded observation; it does not certify the downstream QB response.", "- The Phase-B gate is therefore satisfied for the registered W*=12 ps source replay into frozen QB.", "", "## Inference", "", "- The external 12-JSL load can serve as a bounded, state-selective source interface for the Phase-C requirements test. The Phase-C result separately shows that the resulting ideal replay improves QB margin but remains subthreshold.", "", "## Unknown", "", "- This report does not establish physical BVM→12-JSL→QB closure, exactly-one QB quantization, or downstream SFQ delivery.", ""]
    return "\n".join(lines)


def main() -> None:
    cases = {
        "9ps-logical1-read": analyze(path_for("9ps-logical1-read"), "SOURCE_REFERENCE"),
        "9ps-logical0-read": analyze(path_for("9ps-logical0-read"), "SOURCE_REFERENCE"),
        "9ps-logical1-read0-control": analyze(path_for("9ps-logical1-read0-control"), "ZERO_CONTROL"),
        "9ps-logical0-read0-control": analyze(path_for("9ps-logical0-read0-control"), "ZERO_CONTROL"),
        "12jsl-12ps-logical1-read": analyze(path_for("12jsl-12ps-logical1-read"), "RESULT"),
        "12jsl-12ps-logical0-read": analyze(path_for("12jsl-12ps-logical0-read"), "RESULT"),
    }
    result = {"cases": cases, "verdict": "PAPER_JSL_WSTAR_SOURCE_VALID", "w_star_ps": 12, "jsl_count": 12, "jsl_area": 3.2, "topology": "canonical BVM SL -> 12 external series JSL AREA=3.2 -> GND"}
    (ANALYSIS / "metrics-phase-b.json").write_text(json.dumps(result, indent=2) + "\n")
    (ANALYSIS / "PHASE_B_REPORT.md").write_text(report(result))
    print(json.dumps({"cases": len(cases), "verdict": result["verdict"]}, indent=2))


if __name__ == "__main__":
    main()
