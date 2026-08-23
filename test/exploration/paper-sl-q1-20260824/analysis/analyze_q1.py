#!/usr/bin/env python3
"""Direct phase/voltage-area audit for PAPER-SL-Q1.

No legacy fast-event counter is used.  The event rule is local to this
Exploration: continuous unwrapped phase, a monotonic same-JJ segment of at
least one turn, and same-segment voltage-area consistency.
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
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
JUNCTIONS = {
    "BJs": ("P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}
CASE_META = {
    "q0-68p4u-positive-control": {"kind": "periodic", "windows": [(s, s + 25.0) for s in [10, 60, 110, 160, 210, 260]], "post": [(s + 25.0, min(s + 49.0, 300.0)) for s in [10, 60, 110, 160, 210, 260]]},
    "paper-j1-logical1-read": {"kind": "single", "windows": [(94.0, 130.0)], "post": [(140.0, 170.0)]},
    "paper-j0-logical0-read": {"kind": "single", "windows": [(94.0, 130.0)], "post": [(140.0, 170.0)]},
    "paper-j1-logical1-read0-control": {"kind": "single", "windows": [(94.0, 130.0)], "post": [(140.0, 170.0)]},
    "paper-j0-logical0-read0-control": {"kind": "single", "windows": [(94.0, 130.0)], "post": [(140.0, 170.0)]},
}


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        raw_header = next(reader)
        rows = [row for row in reader if row]
    names = [name.strip() for name in raw_header]
    occurrences: dict[str, list[list[float]]] = {}
    for name in names:
        occurrences.setdefault(name, []).append([])
    for row in rows:
        if len(row) != len(names):
            raise ValueError(f"row/header mismatch in {path}")
        counters: dict[str, int] = {}
        for name, text in zip(names, row):
            ordinal = counters.get(name, 0)
            occurrences[name][ordinal].append(float(text))
            counters[name] = ordinal + 1
    data: dict[str, np.ndarray] = {}
    for name, series in occurrences.items():
        first = np.asarray(series[0], dtype=float)
        for other in series[1:]:
            if not np.array_equal(first, np.asarray(other, dtype=float)):
                raise ValueError(f"non-identical duplicate column {name!r} in {path}")
        data[name] = first
    time = column(data, "time")
    if time.size < 2 or not np.all(np.diff(time) > 0):
        raise ValueError(f"invalid time axis in {path}")
    return data


def column(data: dict[str, np.ndarray], requested: str) -> np.ndarray:
    if requested in data:
        return data[requested]
    normalized = {re.sub(r"\s+", "", name).lower(): name for name in data}
    name = normalized.get(re.sub(r"\s+", "", requested).lower())
    if name is None:
        raise KeyError(f"missing {requested!r}; available={list(data)}")
    return data[name]


def stats(values: np.ndarray) -> dict[str, float | None]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"min": None, "max": None, "p2p": None, "mean": None}
    return {"min": float(finite.min()), "max": float(finite.max()), "p2p": float(np.ptp(finite)), "mean": float(finite.mean())}


def monotonic_runs(values: np.ndarray) -> list[tuple[int, int]]:
    if values.size < 2:
        return []
    signs = np.sign(np.diff(values))
    nonzero = np.flatnonzero(signs)
    if nonzero.size == 0:
        return []
    result: list[tuple[int, int]] = []
    start = 0
    current = int(signs[nonzero[0]])
    for position in nonzero[1:]:
        sign = int(signs[position])
        if sign != current:
            result.append((start, int(position)))
            start = int(position)
            current = sign
    result.append((start, values.size - 1))
    return [(left, right) for left, right in result if right > left]


def area_turns(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    time_s = time_ps * 1e-12
    integral = np.trapezoid(voltage, time_s) if hasattr(np, "trapezoid") else np.trapz(voltage, time_s)
    return float(integral / PHI0)


def segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, mask: np.ndarray) -> list[dict[str, Any]]:
    selected = np.flatnonzero(mask)
    if selected.size < 2:
        return []
    local = phase[selected]
    result: list[dict[str, Any]] = []
    for left, right in monotonic_runs(local):
        indices = selected[left : right + 1]
        delta = float((phase[indices[-1]] - phase[indices[0]]) / TWO_PI)
        area = area_turns(time_ps[indices], voltage[indices])
        residual = float(area - delta)
        tolerance = max(0.05, 0.10 * abs(delta))
        phase_candidate = abs(delta) >= 1.0
        area_consistent = phase_candidate and delta * area > 0 and abs(residual) <= tolerance
        result.append({
            "start_ps": float(time_ps[indices[0]]),
            "end_ps": float(time_ps[indices[-1]]),
            "delta_turns": delta,
            "area_turns": float(area),
            "residual_turns": residual,
            "phase_candidate": bool(phase_candidate),
            "area_consistent": bool(area_consistent),
            "complete_event_units": int(math.floor(abs(delta))) if area_consistent else 0,
        })
    return result


def largest(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(items, key=lambda item: abs(float(item["delta_turns"]))) if items else None


def analyze_junction(data: dict[str, np.ndarray], meta: dict[str, Any], names: tuple[str, str, str]) -> dict[str, Any]:
    time_ps = column(data, "time") * 1e12
    phase = np.unwrap(column(data, names[0]))
    voltage = column(data, names[1])
    current = column(data, names[2])
    activity: list[dict[str, Any]] = []
    post: list[dict[str, Any]] = []
    for start, end in meta["windows"]:
        mask = (time_ps >= start) & (time_ps < end)
        recs = segments(time_ps, phase, voltage, mask)
        selected = phase[mask]
        activity.append({
            "window_ps": [start, end],
            "segments": recs,
            "phase_p2p_turns": float(np.ptp(selected) / TWO_PI) if selected.size else 0.0,
            "phase_candidate_count": sum(item["phase_candidate"] for item in recs),
            "area_candidate_count": sum(item["area_consistent"] for item in recs),
            "complete_event_units": sum(item["complete_event_units"] for item in recs),
            "current_uA": stats(current[mask] * 1e6),
        })
    for start, end in meta["post"]:
        mask = (time_ps >= start) & (time_ps < end)
        recs = segments(time_ps, phase, voltage, mask)
        selected = phase[mask]
        post.append({
            "window_ps": [start, end],
            "segments": recs,
            "phase_p2p_turns": float(np.ptp(selected) / TWO_PI) if selected.size else 0.0,
            "area_candidate_count": sum(item["area_consistent"] for item in recs),
            "complete_event_units": sum(item["complete_event_units"] for item in recs),
        })
    activity_segments = [item for window in activity for item in window["segments"]]
    post_segments = [item for window in post for item in window["segments"]]
    return {
        "phase_rad": stats(column(data, names[0])),
        "voltage_V": stats(voltage),
        "current_A": stats(current),
        "activity": activity,
        "post": post,
        "activity_phase_candidate_count": sum(item["phase_candidate"] for item in activity_segments),
        "activity_area_candidate_count": sum(item["area_consistent"] for item in activity_segments),
        "activity_complete_event_units": sum(item["complete_event_units"] for item in activity_segments),
        "post_complete_event_units": sum(item["complete_event_units"] for item in post_segments),
        "largest_activity_segment": largest(activity_segments),
        "largest_post_segment": largest(post_segments),
    }


def classify(case_id: str, junctions: dict[str, Any]) -> str:
    bjl2 = junctions["BJL2"]
    if case_id == "q0-68p4u-positive-control":
        per_pulse = [window["complete_event_units"] for window in bjl2["activity"]]
        if per_pulse == [1] * len(per_pulse) and not bjl2["post_complete_event_units"]:
            return "Q0_POSITIVE_CONTROL_VALID"
        return "REPLAY_FIXTURE_INVALID"
    if bjl2["post_complete_event_units"]:
        return "MULTIEVENT_OR_FREE_RUNNING"
    units = bjl2["activity_complete_event_units"]
    if units > 1:
        return "MULTIEVENT"
    if units == 1:
        return "EXACTLY_ONE"
    return "NO_COMPLETE_EVENT"


def load_source_stats() -> dict[str, Any]:
    path = ROOT / "replay_sources/source-manifest.json"
    return json.loads(path.read_text())


def build_results() -> dict[str, Any]:
    result: dict[str, Any] = {"cases": {}, "source_manifest": load_source_stats()}
    for case_id, meta in CASE_META.items():
        raw_path = RAW / "q0-68p4u-positive-control/run-01.csv" if case_id == "q0-68p4u-positive-control" else RAW / f"{case_id}.csv"
        data = load_csv(raw_path)
        junctions = {name: analyze_junction(data, meta, columns) for name, columns in JUNCTIONS.items()}
        result["cases"][case_id] = {"classification": classify(case_id, junctions), "junctions": junctions}
    q0 = result["cases"]["q0-68p4u-positive-control"]["classification"]
    matched = {key: value["classification"] for key, value in result["cases"].items() if key != "q0-68p4u-positive-control"}
    if q0 != "Q0_POSITIVE_CONTROL_VALID":
        verdict = "REPLAY_FIXTURE_INVALID"
    elif matched["paper-j1-logical1-read"] in {"MULTIEVENT", "MULTIEVENT_OR_FREE_RUNNING"}:
        verdict = "PAPER_JSL_QB_MULTIEVENT"
    elif any(matched[key] not in {"NO_COMPLETE_EVENT"} for key in ["paper-j0-logical0-read", "paper-j1-logical1-read0-control", "paper-j0-logical0-read0-control"]):
        verdict = "PAPER_JSL_QB_NONSEL"
    elif matched["paper-j1-logical1-read"] == "EXACTLY_ONE":
        verdict = "PAPER_JSL_WAVEFORM_MATCHES_QB_ONE_SHOT"
    elif matched["paper-j1-logical1-read"] == "NO_COMPLETE_EVENT":
        verdict = "PAPER-SL_QB_SUBTHRESHOLD"
    else:
        verdict = "INCONCLUSIVE"
    result["verdict"] = verdict
    return result


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return f"{value:.6g}"
    return str(value)


def report(result: dict[str, Any]) -> str:
    lines = [
        "# PAPER-SL-Q1 analysis report",
        "",
        f"## Verdict: `{result['verdict']}`",
        "",
        "This is an ideal-current waveform-replay requirement result; it is not physical BVM-to-QB interface evidence.",
        "",
        "## Event summary",
        "",
        "| case | BJs complete units | BJL1 complete units | BJL2 complete units | BJL2 largest activity segment (turns) | BJL2 largest same-segment area (Phi0) | post complete units | classification |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for case_id, case in result["cases"].items():
        rows = []
        for name in ("BJs", "BJL1", "BJL2"):
            rows.append(case["junctions"][name]["activity_complete_event_units"])
        largest_seg = case["junctions"]["BJL2"]["largest_activity_segment"] or {}
        lines.append(f"| {case_id} | {rows[0]} | {rows[1]} | {rows[2]} | {fmt(largest_seg.get('delta_turns'))} | {fmt(largest_seg.get('area_turns'))} | {case['junctions']['BJL2']['post_complete_event_units']} | `{case['classification']}` |")
    lines += ["", "## Per-JJ activity details", ""]
    for case_id, case in result["cases"].items():
        lines += [f"### {case_id}", "", "| JJ | activity phase p2p (turns) | largest monotonic delta (turns) | same-segment area (Phi0) | current min..max (µA) |", "|---|---:|---:|---:|---:|"]
        for name in ("BJs", "BJL1", "BJL2"):
            jj = case["junctions"][name]
            seg = jj["largest_activity_segment"] or {}
            current = jj["activity"][0]["current_uA"]
            lines.append(f"| {name} | {fmt(jj['activity'][0]['phase_p2p_turns'])} | {fmt(seg.get('delta_turns'))} | {fmt(seg.get('area_turns'))} | {fmt(current.get('min'))} .. {fmt(current.get('max'))} |")
        lines.append("")
    lines += [
        "## Observed",
        "",
        "- The source builder used `I(B_LD1)` and verified the twelve series JSL branch-current columns were equal within the recorded numerical tolerance.",
        "- All replay source points retain the original PAPER-SL-L0 time grid, polarity, and amplitude; no shape transformation was applied.",
        "- Event counts above use only continuous phase, same-JJ monotonic segments, and same-segment voltage area.",
        "",
        "## Derived",
        "",
        "- A complete-unit count is the floor of the absolute phase change for an area-consistent monotonic segment; phase activity below one turn is not counted as an event.",
        "- The Q0 row is an independent fixture check and is not a paper-JSL source result.",
        "",
        "## Inference",
        "",
        "- The selected verdict is limited to waveform compatibility of the frozen scaled QB under these ideal current replays.",
        "- It does not establish that the physical twelve-JSL BVM load can supply the replay current into QB, nor that source loading/back-action is acceptable.",
        "",
        "## Unknown",
        "",
        "- The physical combined BVM/JSL/QB load-line and any reflected source disturbance were not tested.",
        "- A local BJL2 event, if present, is not downstream SFQ delivery because no JTL is connected.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    result = build_results()
    (ANALYSIS / "metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    (ANALYSIS / "REPORT.md").write_text(report(result))
    print(result["verdict"])
    for case_id, case in result["cases"].items():
        print(case_id, case["classification"], [case["junctions"][name]["activity_complete_event_units"] for name in ("BJs", "BJL1", "BJL2")])


if __name__ == "__main__":
    main()
