#!/usr/bin/env python3
"""Phase/voltage-area audit for QB-Q2A replay cases.

This deliberately does not use scripts/sfq_metrics.py.  A/B/C/C0 are
requirements/counterfactual replay cases; only the local JJ evidence is
audited here.
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
PULSE_STARTS = [10.0, 60.0, 110.0, 160.0, 210.0, 260.0]
JUNCTIONS = {
    "BJs": ("P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}
CASES = {
    "A-q0-68p4u-positive-control": {
        "raw": "A-q0-68p4u-positive-control.csv",
        "kind": "periodic",
        "activity_windows": [(s, min(s + 25.0, 300.0)) for s in PULSE_STARTS],
        "post_windows": [(s + 25.0, min(s + 49.0, 300.0)) for s in PULSE_STARTS],
    },
    "B-q1-loaded-vsl-replay": {
        "raw": "B-q1-loaded-vsl-replay.csv",
        "kind": "single",
        "activity_windows": [(94.0, 130.0)],
        "post_windows": [(150.0, 170.0)],
    },
    "C-canonical-logical1-vsl-replay": {
        "raw": "C-canonical-logical1-vsl-replay.csv",
        "kind": "single",
        "activity_windows": [(94.0, 130.0)],
        "post_windows": [(150.0, 170.0)],
    },
    "C0-canonical-logical0-vsl-replay": {
        "raw": "C0-canonical-logical0-vsl-replay.csv",
        "kind": "single",
        "activity_windows": [(94.0, 130.0)],
        "post_windows": [(150.0, 170.0)],
    },
}


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    values: dict[str, list[float]] = {name.strip(): [] for name in header}
    duplicate_values: dict[str, list[list[float]]] = {}
    for index, name in enumerate(header):
        duplicate_values.setdefault(name.strip(), []).append([])
    for row in rows:
        if len(row) != len(header):
            raise ValueError(f"row/header length mismatch in {path}")
        for index, name in enumerate(header):
            value = float(row[index])
            values[name.strip()].append(value)
            duplicate_values[name.strip()][[h.strip() for h in header[: index + 1]].count(name.strip()) - 1].append(value)
    arrays = {name: np.asarray(series, dtype=float) for name, series in values.items()}
    for name, series in duplicate_values.items():
        if len(series) > 1:
            first = np.asarray(series[0])
            if not all(np.array_equal(first, np.asarray(other)) for other in series[1:]):
                raise ValueError(f"non-identical duplicate columns {name!r} in {path}")
    time_name = "time" if "time" in arrays else "time_ps" if "time_ps" in arrays else None
    if time_name is None or len(arrays[time_name]) < 2:
        raise ValueError(f"missing/short time series in {path}")
    time = arrays[time_name]
    if not np.all(np.isfinite(time)) or not np.all(np.diff(time) > 0):
        raise ValueError(f"invalid time axis in {path}")
    return arrays


def column(data: dict[str, np.ndarray], requested: str) -> np.ndarray:
    if requested in data:
        return data[requested]
    normalized = {re.sub(r"\s+", "", key).lower(): key for key in data}
    key = normalized.get(re.sub(r"\s+", "", requested).lower())
    if key is None:
        raise KeyError(f"missing {requested!r}; available={list(data)}")
    return data[key]


def stats(values: np.ndarray) -> dict[str, float | None]:
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {"min": None, "max": None, "p2p": None, "mean": None}
    return {"min": float(values.min()), "max": float(values.max()), "p2p": float(np.ptp(values)), "mean": float(values.mean())}


def monotonic_runs(values: np.ndarray) -> list[tuple[int, int]]:
    if values.size < 2:
        return []
    signs = np.sign(np.diff(values))
    nonzero = np.flatnonzero(signs)
    if nonzero.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = 0
    current = int(signs[nonzero[0]])
    for position in nonzero[1:]:
        sign = int(signs[position])
        if sign != current:
            runs.append((start, int(position)))
            start = int(position)
            current = sign
    runs.append((start, values.size - 1))
    return [(left, right) for left, right in runs if right > left]


def area_turns(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    time_s = time_ps * 1e-12
    integral = np.trapezoid(voltage, time_s) if hasattr(np, "trapezoid") else np.trapz(voltage, time_s)
    return float(integral / PHI0)


def segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, mask: np.ndarray) -> list[dict[str, Any]]:
    indices = np.flatnonzero(mask)
    if indices.size < 2:
        return []
    selected_phase = phase[indices]
    result: list[dict[str, Any]] = []
    for left, right in monotonic_runs(selected_phase):
        segment_indices = indices[left : right + 1]
        delta = float((phase[segment_indices[-1]] - phase[segment_indices[0]]) / TWO_PI)
        area = area_turns(time_ps[segment_indices], voltage[segment_indices])
        residual = float(area - delta)
        tolerance = max(0.05, 0.10 * abs(delta))
        phase_candidate = abs(delta) >= 1.0
        area_consistent = phase_candidate and delta * area > 0 and abs(residual) <= tolerance
        result.append({
            "start_ps": float(time_ps[segment_indices[0]]),
            "end_ps": float(time_ps[segment_indices[-1]]),
            "delta_turns": delta,
            "area_turns": float(area),
            "residual_turns": residual,
            "tolerance_turns": tolerance,
            "phase_candidate": phase_candidate,
            "area_consistent": area_consistent,
            "complete_event_units": int(math.floor(abs(delta))) if area_consistent else 0,
        })
    return result


def largest(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(items, key=lambda item: abs(float(item["delta_turns"]))) if items else None


def analyze_jj(data: dict[str, np.ndarray], case: dict[str, Any], names: tuple[str, str, str]) -> dict[str, Any]:
    time_ps = column(data, "time") * 1e12
    phase_raw = column(data, names[0])
    phase = np.unwrap(phase_raw)
    voltage = column(data, names[1])
    current = column(data, names[2])
    activity: list[dict[str, Any]] = []
    post: list[dict[str, Any]] = []
    for start, end in case["activity_windows"]:
        mask = (time_ps >= start) & (time_ps < end)
        recs = segments(time_ps, phase, voltage, mask)
        selected = phase[mask]
        activity.append({
            "window_ps": [start, end],
            "segments": recs,
            "phase_candidate_count": sum(item["phase_candidate"] for item in recs),
            "area_candidate_count": sum(item["area_consistent"] for item in recs),
            "complete_event_units": sum(item["complete_event_units"] for item in recs),
            "phase_p2p_turns": float(np.ptp(selected) / TWO_PI) if selected.size else 0.0,
            "current_uA": stats(current[mask] * 1e6),
        })
    for start, end in case["post_windows"]:
        mask = (time_ps >= start) & (time_ps < end)
        recs = segments(time_ps, phase, voltage, mask)
        selected = phase[mask]
        post.append({
            "window_ps": [start, end],
            "segments": recs,
            "area_candidate_count": sum(item["area_consistent"] for item in recs),
            "complete_event_units": sum(item["complete_event_units"] for item in recs),
            "phase_p2p_turns": float(np.ptp(selected) / TWO_PI) if selected.size else 0.0,
        })
    activity_segments = [item for window in activity for item in window["segments"]]
    post_segments = [item for window in post for item in window["segments"]]
    return {
        "raw_phase_rad": stats(phase_raw),
        "raw_voltage_V": stats(voltage),
        "raw_current_A": stats(current),
        "activity": activity,
        "post": post,
        "activity_phase_candidate_count": sum(item["phase_candidate"] for item in activity_segments),
        "activity_area_candidate_count": sum(item["area_consistent"] for item in activity_segments),
        "activity_complete_event_units": sum(item["complete_event_units"] for item in activity_segments),
        "post_area_candidate_count": sum(item["area_consistent"] for item in post_segments),
        "post_complete_event_units": sum(item["complete_event_units"] for item in post_segments),
        "largest_activity_segment": largest(activity_segments),
        "largest_post_segment": largest(post_segments),
    }


def classify(case_id: str, junctions: dict[str, Any]) -> str:
    bjl2 = junctions["BJL2"]
    if bjl2["post_complete_event_units"]:
        return "FREE_RUNNING"
    activity_units = [window["complete_event_units"] for window in bjl2["activity"]]
    if case_id.startswith("A-"):
        return "A_EXACTLY_ONE_POSITIVE_CONTROL" if activity_units == [1] * len(activity_units) else "REPLAY_FIXTURE_INVALID"
    if bjl2["activity_complete_event_units"] > 1:
        return "MULTI_EVENT"
    if bjl2["activity_complete_event_units"] == 1:
        return "EXACTLY_ONE"
    if bjl2["activity_phase_candidate_count"]:
        return "INCONCLUSIVE_AREA"
    return "NO_COMPLETE_EVENT"


def source_stats(path: Path) -> dict[str, Any]:
    data = load_csv(path)
    time_ps = column(data, "time_ps")
    return {
        "path": str(path.relative_to(ROOT)),
        "samples": int(time_ps.size),
        "time_ps": [float(time_ps[0]), float(time_ps[-1])],
        "v_sl_V": stats(column(data, "V_SL_V")),
        "companion_current_A": stats(column(data, next(name for name in data if name != "time_ps" and name != "V_SL_V"))),
    }


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.6g}"
    return str(value)


def report(results: dict[str, Any]) -> str:
    lines = [
        "# QB-Q2A source-decoupled waveform replay diagnosis",
        "",
        f"## Verdict: `{results['verdict']}`",
        "",
        results["verdict_explanation"],
        "",
        "This is a requirements/counterfactual replay result. B/C/C0 use ideal voltage-source replay and are not physical source-isolation hardware evidence.",
        "",
        "## Core table",
        "",
        "| case | BJs units | BJL1 units | BJL2 units | BJL2 largest Δturn | same-segment area (Φ0) | classification |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for case_id, item in results["cases"].items():
        largest_item = item["junctions"]["BJL2"]["largest_activity_segment"] or {}
        lines.append(
            f"| {case_id} | {item['junctions']['BJs']['activity_complete_event_units']} | "
            f"{item['junctions']['BJL1']['activity_complete_event_units']} | "
            f"{item['junctions']['BJL2']['activity_complete_event_units']} | "
            f"{fmt(largest_item.get('delta_turns'))} | {fmt(largest_item.get('area_turns'))} | `{item['classification']}` |"
        )
    lines += ["", "## Replay input actually delivered to QB", "", "| case | V(IN) min..max (V) | I(Lin) min..max (A) | replay-source current min..max (A) |", "|---|---:|---:|---:|"]
    for case_id, item in results["cases"].items():
        voltage = item["input_voltage_V"]
        lin = item["qb_lin_current_A"]
        source_current = item["input_current_A"]
        lines.append(f"| {case_id} | {fmt(voltage['min'])}..{fmt(voltage['max'])} | {fmt(lin['min'])}..{fmt(lin['max'])} | {fmt(source_current['min'])}..{fmt(source_current['max'])} |")
    lines += ["", "## Input provenance and source scale", "", "| source | samples | time range (ps) | V(SL) min..max (V) | companion current min..max (A) |", "|---|---:|---:|---:|---:|"]
    for name, item in results["sources"].items():
        v = item["v_sl_V"]
        c = item["companion_current_A"]
        lines.append(f"| {name} | {item['samples']} | {item['time_ps'][0]}..{item['time_ps'][1]} | {fmt(v['min'])}..{fmt(v['max'])} | {fmt(c['min'])}..{fmt(c['max'])} |")
    lines += [
        "",
        "## JJ phase/area detail",
        "",
        "| case | JJ | activity p2p (turn) | largest Δturn | same-segment area (Φ0) | residual (turn) | complete units |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for case_id, item in results["cases"].items():
        for jj_name in JUNCTIONS:
            jj = item["junctions"][jj_name]
            largest_item = jj["largest_activity_segment"] or {}
            p2p = max((window["phase_p2p_turns"] for window in jj["activity"]), default=0.0)
            lines.append(f"| {case_id} | {jj_name} | {fmt(p2p)} | {fmt(largest_item.get('delta_turns'))} | {fmt(largest_item.get('area_turns'))} | {fmt(largest_item.get('residual_turns'))} | {jj['activity_complete_event_units']} |")
    lines += [
        "",
        "## BJL2 event evidence",
        "",
        "The event candidate rule is local and exploratory: one same-JJ monotonic phase segment with `|Δturn|≥1`, same-sign direct voltage area, residual within `max(0.05,0.10|Δturn|)`, and bounded post behavior. Peaks, `I>Ic`, and activity range are not event counts.",
        "",
        "| case | activity p2p (turn) | post p2p (turn) | post complete units |",
        "|---|---:|---:|---:|",
    ]
    for case_id, item in results["cases"].items():
        jj = item["junctions"]["BJL2"]
        lines.append(f"| {case_id} | {fmt(max((w['phase_p2p_turns'] for w in jj['activity']), default=0.0))} | {fmt(max((w['phase_p2p_turns'] for w in jj['post']), default=0.0))} | {jj['post_complete_event_units']} |")
    lines += [
        "",
        "## Observed",
        "",
        "- A uses the Q0 68.4 µA ideal-current pulse and is a positive replay control; B/C/C0 are ideal voltage-source replays of committed source-port waveforms.",
        "- The replay source values retain their original polarity and all source CSV points; no rectification, hold, normalization or amplitude scaling was applied.",
        "- Direct BJs/BJL1/BJL2 P/V/I were saved for every case and the same-JJ phase/area segment analysis was applied.",
        "",
        "## Derived",
        "",
        "- `P()` is raw phase in radians; reported turns are `ΔP/(2π)`. Voltage areas use the actual CSV time column and the direct junction voltage column.",
        "- A is valid only as a local positive-control replay if all six Q0 pulse windows produce one BJL2 unit and no post candidate.",
        "",
        "## Inference",
        "",
        f"- {results['inference']}",
        "",
        "## Unknown / boundary",
        "",
        "- Ideal replay removes the physical source impedance and cannot by itself establish a realizable buffer, transformer or conditioner.",
        "- No QB parameter, source waveform, load, BVM, transformer, DCSFQ, JTL or T1 was optimized or modified.",
        "- This bounded result does not establish a universal QB threshold or impossibility of the QB family.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    output: dict[str, Any] = {"run_id": "qb-q2a-source-decoupled-waveform-replay-20260824", "cases": {}, "sources": {}}
    for case_id, case in CASES.items():
        if not (RAW / case["raw"]).exists():
            continue
        data = load_csv(RAW / case["raw"])
        item = {
            "raw_file": str((RAW / case["raw"]).relative_to(ROOT)),
            "kind": case["kind"],
            "junctions": {name: analyze_jj(data, case, names) for name, names in JUNCTIONS.items()},
            "input_voltage_V": stats(column(data, "V(IN)")),
            "qb_lin_current_A": stats(column(data, "I(LIN|XBQ)")),
            "input_current_A": stats(column(data, "I(V_REPLAY)" if "I(V_REPLAY)" in data else "I(I_IN)")),
            "output_voltage_V": stats(column(data, "V(OUT)")),
        }
        item["classification"] = classify(case_id, item["junctions"])
        output["cases"][case_id] = item
    source_map = {
        "B-q1-loaded": "B-q1-loaded-vsl.csv",
        "C-canonical-logical1": "C-canonical-logical1-vsl.csv",
        "C0-canonical-logical0": "C0-canonical-logical0-vsl.csv",
    }
    for name, filename in source_map.items():
        output["sources"][name] = source_stats(ROOT / "inputs" / "replay_sources" / filename)
    a = output["cases"].get("A-q0-68p4u-positive-control")
    c = output["cases"].get("C-canonical-logical1-vsl-replay")
    c0 = output["cases"].get("C0-canonical-logical0-vsl-replay")
    if a is None:
        verdict = "INCONCLUSIVE"
        explanation = "The required A positive-control raw artifact is not present."
        inference = "No replay case was interpreted."
    elif set(output["cases"]) != set(CASES):
        verdict = "A_POSITIVE_CONTROL_PENDING_MATRIX" if a["classification"] == "A_EXACTLY_ONE_POSITIVE_CONTROL" else "REPLAY_FIXTURE_INVALID"
        explanation = "A has been validated as the Q0 positive control; B/C/C0 are not yet present, so the Q2A matrix verdict is pending." if verdict == "A_POSITIVE_CONTROL_PENDING_MATRIX" else "The A positive control did not reproduce one bounded BJL2 local unit in every Q0 pulse window; B/C/C0 are not interpreted."
        inference = "The positive-control gate is complete; no source-isolation conclusion is authorized before the remaining replay cases." if verdict == "A_POSITIVE_CONTROL_PENDING_MATRIX" else "The replay fixture failed its predeclared positive-control validation."
    elif a["classification"] != "A_EXACTLY_ONE_POSITIVE_CONTROL":
        verdict = "REPLAY_FIXTURE_INVALID"
        explanation = "The A positive control did not reproduce one bounded BJL2 local unit in every Q0 pulse window; B/C/C0 are not interpreted."
        inference = "The replay fixture failed its predeclared positive-control validation."
    elif c["classification"] == "EXACTLY_ONE" and c0["classification"] == "NO_COMPLETE_EVENT":
        verdict = "SOURCE_ISOLATION_PRIMARY_LIMIT"
        explanation = "Canonical no-receiver logical1 replay gives one bounded BJL2 local event while canonical logical0 replay gives none; the Q1 direct failure is therefore primarily consistent with source loading/back-action."
        inference = "The canonical waveform is sufficient in this ideal source-isolated counterfactual, while Q1 direct galvanic loading is the leading bounded explanation for the direct failure."
    elif c["classification"] in {"NO_COMPLETE_EVENT", "INCONCLUSIVE_AREA"}:
        verdict = "QB_DYNAMIC_WINDOW_MISMATCH"
        explanation = "The source-isolated canonical logical1 replay remains below a complete BJL2 phase/area event under the frozen scaled QB."
        inference = "The canonical waveform, as replayed at the source port, does not meet the frozen QB dynamic window in this counterfactual fixture; this does not prove a universal QB impossibility."
    else:
        verdict = "INCONCLUSIVE"
        explanation = "The predeclared replay classifications do not form a unique source-isolation or dynamic-window diagnosis."
        inference = "B/C/C0 require a narrower follow-up interpretation; no architecture conclusion is authorized."
    output["verdict"] = verdict
    output["verdict_explanation"] = explanation
    output["inference"] = inference
    (ANALYSIS / "qb-q2a-metrics.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    with (ANALYSIS / "qb-q2a-case-summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["case", "classification", "BJs_units", "BJL1_units", "BJL2_units", "BJL2_largest_delta_turns", "BJL2_largest_area_turns", "BJL2_post_units"])
        for case_id, item in output["cases"].items():
            jj = item["junctions"]["BJL2"]
            largest_item = jj["largest_activity_segment"] or {}
            writer.writerow([case_id, item["classification"], item["junctions"]["BJs"]["activity_complete_event_units"], item["junctions"]["BJL1"]["activity_complete_event_units"], jj["activity_complete_event_units"], largest_item.get("delta_turns"), largest_item.get("area_turns"), jj["post_complete_event_units"]])
    (ANALYSIS / "QB_Q2A_REPORT.md").write_text(report(output))
    print(json.dumps({"verdict": verdict, "cases": {key: value["classification"] for key, value in output["cases"].items()}}, indent=2))


if __name__ == "__main__":
    main()
