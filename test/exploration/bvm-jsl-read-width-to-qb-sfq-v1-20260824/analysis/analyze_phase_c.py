#!/usr/bin/env python3
"""Audit frozen scaled-QB response to the W*=12 ps exact replay."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw/phase-c"
Q1 = ROOT.parent / "paper-sl-q1-20260824"
ANALYSIS = ROOT / "analysis"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
ACTIVITY = (94.0, 130.0)
POST = (140.0, 170.0)
JUNCTIONS = {
    "BJs": ("P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}


def load(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = [x.strip() for x in next(reader)]
        rows = [row for row in reader if row]
    data = {name: np.asarray([float(row[i]) for row in rows], dtype=float) for i, name in enumerate(header)}
    time = data["time"] * 1e12
    if time.size < 2 or not np.all(np.diff(time) > 0):
        raise ValueError(f"invalid time axis: {path}")
    return data


def mask(time: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return (time >= bounds[0]) & (time < bounds[1])


def column(data: dict[str, np.ndarray], requested: str) -> np.ndarray:
    if requested in data:
        return data[requested]
    normalized = {key.replace(" ", "").lower(): key for key in data}
    key = normalized.get(requested.replace(" ", "").lower())
    if key is None:
        raise KeyError(f"missing {requested!r}; available={list(data)}")
    return data[key]


def trapz(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    area = np.trapezoid(voltage, time_ps * 1e-12) if hasattr(np, "trapezoid") else np.trapz(voltage, time_ps * 1e-12)
    return float(area / PHI0)


def segments(time: np.ndarray, phase: np.ndarray, voltage: np.ndarray, bounds: tuple[float, float]) -> list[dict[str, Any]]:
    selected = np.flatnonzero(mask(time, bounds))
    if selected.size < 2:
        return []
    local = phase[selected]
    signs = np.sign(np.diff(local))
    nonzero = np.flatnonzero(signs != 0)
    if nonzero.size == 0:
        return []
    starts = [0]
    for pos in nonzero[1:]:
        if signs[pos] != signs[nonzero[np.searchsorted(nonzero, pos) - 1]]:
            starts.append(int(pos))
    starts.append(local.size - 1)
    output = []
    for left, right in zip(starts[:-1], starts[1:]):
        indices = selected[left : right + 1]
        delta = float((phase[indices[-1]] - phase[indices[0]]) / TWO_PI)
        area = trapz(time[indices], voltage[indices])
        residual = float(area - delta)
        consistent = abs(delta) >= 1.0 and delta * area > 0 and abs(residual) <= max(0.05, 0.10 * abs(delta))
        output.append({"start_ps": float(time[indices[0]]), "end_ps": float(time[indices[-1]]), "delta_turns": delta, "area_turns": area, "residual_turns": residual, "phase_candidate": abs(delta) >= 1.0, "area_consistent": consistent, "complete_event_units": int(math.floor(abs(delta))) if consistent else 0})
    return output


def analyze(path: Path, role: str) -> dict[str, Any]:
    data = load(path)
    time = data["time"] * 1e12
    result: dict[str, Any] = {"path": str(path), "role": role, "junctions": {}}
    for name, columns in JUNCTIONS.items():
        phase = np.unwrap(column(data, columns[0]))
        voltage = column(data, columns[1])
        current = column(data, columns[2])
        activity = segments(time, phase, voltage, ACTIVITY)
        post = segments(time, phase, voltage, POST)
        activity_phase = phase[mask(time, ACTIVITY)]
        result["junctions"][name] = {
            "phase_activity_p2p_turns": float(np.ptp(activity_phase) / TWO_PI),
            "activity_segments": activity,
            "post_segments": post,
            "largest_activity_segment": max(activity, key=lambda item: abs(item["delta_turns"])) if activity else None,
            "activity_complete_event_units": sum(item["complete_event_units"] for item in activity),
            "post_complete_event_units": sum(item["complete_event_units"] for item in post),
            "current_activity_uA": {"min": float(np.min(current[mask(time, ACTIVITY)] * 1e6)), "max": float(np.max(current[mask(time, ACTIVITY)] * 1e6))},
        }
    bjl2 = result["junctions"]["BJL2"]
    if bjl2["post_complete_event_units"]:
        result["classification"] = "MULTIEVENT_OR_FREE_RUNNING"
    elif bjl2["activity_complete_event_units"] > 1:
        result["classification"] = "MULTIEVENT"
    elif bjl2["activity_complete_event_units"] == 1:
        result["classification"] = "EXACTLY_ONE"
    else:
        result["classification"] = "NO_COMPLETE_EVENT"
    return result


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def main() -> None:
    cases = {}
    for case_id in ("wstar12-logical1-read", "wstar12-logical0-read", "wstar12-logical1-read0-control", "wstar12-logical0-read0-control"):
        cases[case_id] = analyze(RAW / f"{case_id}/run-01.csv", "RESULT")
    q1_metrics = json.loads((Q1 / "analysis/metrics.json").read_text())
    for case_id in ("paper-j1-logical1-read", "paper-j0-logical0-read", "paper-j1-logical1-read0-control", "paper-j0-logical0-read0-control"):
        source = Q1 / "raw" / f"{case_id}.csv"
        cases[f"q1-9ps-{case_id}"] = analyze(source, "ACCEPTED_COMPARATOR")
    read1 = cases["wstar12-logical1-read"]["classification"]
    read0 = cases["wstar12-logical0-read"]["classification"]
    controls = [cases[key]["classification"] for key in ("wstar12-logical1-read0-control", "wstar12-logical0-read0-control")]
    if read1 == "EXACTLY_ONE" and read0 == "NO_COMPLETE_EVENT" and controls == ["NO_COMPLETE_EVENT", "NO_COMPLETE_EVENT"]:
        verdict = "IDEAL_REPLAY_SELECTIVE_ONE_SFQ"
    elif read1 == "MULTIEVENT" or read1 == "MULTIEVENT_OR_FREE_RUNNING":
        verdict = "OVERDRIVEN_OR_MULTI_EVENT"
    elif read0 != "NO_COMPLETE_EVENT" or any(item != "NO_COMPLETE_EVENT" for item in controls):
        verdict = "NONSELECTIVE"
    else:
        largest = cases["wstar12-logical1-read"]["junctions"]["BJL2"]["largest_activity_segment"]
        verdict = "WIDTH_IMPROVES_QB_MARGIN_BUT_SUBTHRESHOLD" if largest and abs(largest["delta_turns"]) > 0.892527 else "READ_WIDTH_NOT_LIMITING_QB_CLOSURE"
    result = {"w_star_ps": 12, "verdict": verdict, "q1_metrics_source": str(Q1 / "analysis/metrics.json"), "q1_metrics_verdict": q1_metrics["verdict"], "cases": cases}
    (ANALYSIS / "metrics-phase-c.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 — Phase C report", "", f"## Verdict: `{verdict}`", "", "This is an ideal-current replay of the recorded 12-JSL + W*=12 ps source into the frozen scaled QB. It is not physical BVM→JSL→QB closure.", "", "| case | BJs activity (turns) | BJL1 activity (turns) | BJL2 largest segment (turns) | BJL2 same-segment area (Phi0) | BJL2 complete units | classification |", "|---|---:|---:|---:|---:|---:|---|"]
    for case_id, case in cases.items():
        bjs = case["junctions"]["BJs"]
        bjl1 = case["junctions"]["BJL1"]
        bjl2 = case["junctions"]["BJL2"]
        seg = bjl2["largest_activity_segment"] or {}
        lines.append(f"| {case_id} | {fmt(bjs['phase_activity_p2p_turns'])} | {fmt(bjl1['phase_activity_p2p_turns'])} | {fmt(seg.get('delta_turns'))} | {fmt(seg.get('area_turns'))} | {bjl2['activity_complete_event_units']} | `{case['classification']}` |")
    lines += ["", "## Observed", "", "- The W*=12 ps source replay retains the recorded time grid, polarity, amplitude, and waveform shape; no normalization, rectification, hold, smoothing, or resampling was applied.", "- Q1 9 ps rows are accepted comparator raw; Q0 positive-control status is inherited from PAPER-SL-Q1 and is not reinterpreted here.", "", "## Derived", "", "- Event counts use only continuous unwrapped phase, same-JJ same-segment direct voltage area, and the registered activity/post windows.", "- A BJL2 phase range above one would not alone count as an event; the table uses the largest monotonic segment.", "", "## Inference", "", "- The W*=12 ps replay changes the frozen QB operating trajectory only within this ideal source fixture; it does not prove physical current transfer or acceptable back-action.", "", "## Unknown", "", "- No timestep/repeat closure has been run for a candidate point; those are reserved for a later generation gate only if a candidate appears.", ""]
    (ANALYSIS / "PHASE_C_REPORT.md").write_text("\n".join(lines))
    print(json.dumps({"verdict": verdict, "cases": len(cases)}, indent=2))


if __name__ == "__main__":
    main()
