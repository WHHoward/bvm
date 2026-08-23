#!/usr/bin/env python3
"""PAPER-SL-Q2 direct phase/voltage-area audit and stop-rule classifier."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
CASES = (
    "paper-j1-logical1-read0-control",
    "paper-j0-logical0-read0-control",
    "paper-j0-logical0-read",
    "paper-j1-logical1-read",
)
JUNCTIONS = {
    "BJs": ("P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}
WINDOW = (94.0, 130.0)
POST = (140.0, 170.0)


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
        for name, value in zip(names, row):
            ordinal = counters.get(name, 0)
            occurrences[name][ordinal].append(float(value))
            counters[name] = ordinal + 1
    data: dict[str, np.ndarray] = {}
    for name, series in occurrences.items():
        first = np.asarray(series[0], dtype=float)
        for other in series[1:]:
            if not np.array_equal(first, np.asarray(other, dtype=float)):
                raise ValueError(f"non-identical duplicate column {name!r} in {path}")
        data[name] = first
    time = data["time"]
    if time.size < 2 or not np.all(np.isfinite(time)) or not np.all(np.diff(time) > 0):
        raise ValueError(f"invalid time axis in {path}")
    return data


def stats(values: np.ndarray) -> dict[str, float | None]:
    finite = values[np.isfinite(values)]
    if not finite.size:
        return {"min": None, "max": None, "p2p": None, "mean": None}
    return {"min": float(finite.min()), "max": float(finite.max()), "p2p": float(np.ptp(finite)), "mean": float(finite.mean())}


def monotonic_runs(values: np.ndarray) -> list[tuple[int, int]]:
    if values.size < 2:
        return []
    signs = np.sign(np.diff(values))
    nonzero = np.flatnonzero(signs)
    if not nonzero.size:
        return []
    result: list[tuple[int, int]] = []
    start = 0
    direction = int(signs[nonzero[0]])
    for position in nonzero[1:]:
        sign = int(signs[position])
        if sign != direction:
            result.append((start, int(position)))
            start = int(position)
            direction = sign
    result.append((start, values.size - 1))
    return [(left, right) for left, right in result if right > left]


def area_turns(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    time_s = time_ps * 1e-12
    integral = np.trapezoid(voltage, time_s) if hasattr(np, "trapezoid") else np.trapz(voltage, time_s)
    return float(integral / PHI0)


def segment_records(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, mask: np.ndarray) -> list[dict[str, Any]]:
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
        phase_candidate = abs(delta) >= 1.0
        area_consistent = phase_candidate and delta * area > 0 and abs(residual) <= max(0.05, 0.10 * abs(delta))
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


def analyze_jj(data: dict[str, np.ndarray], names: tuple[str, str, str]) -> dict[str, Any]:
    time_ps = data["time"] * 1e12
    phase_raw = data[names[0]]
    phase = np.unwrap(phase_raw)
    voltage = data[names[1]]
    current = data[names[2]]
    activity_mask = (time_ps >= WINDOW[0]) & (time_ps < WINDOW[1])
    post_mask = (time_ps >= POST[0]) & (time_ps < POST[1])
    activity_segments = segment_records(time_ps, phase, voltage, activity_mask)
    post_segments = segment_records(time_ps, phase, voltage, post_mask)
    selected = phase[activity_mask]
    largest = max(activity_segments, key=lambda item: abs(item["delta_turns"])) if activity_segments else None
    post_largest = max(post_segments, key=lambda item: abs(item["delta_turns"])) if post_segments else None
    return {
        "phase_rad": stats(phase_raw),
        "voltage_V": stats(voltage),
        "current_A": stats(current),
        "activity_phase_p2p_turns": float(np.ptp(selected) / TWO_PI) if selected.size else 0.0,
        "activity_segments": activity_segments,
        "post_segments": post_segments,
        "activity_complete_event_units": sum(item["complete_event_units"] for item in activity_segments),
        "post_complete_event_units": sum(item["complete_event_units"] for item in post_segments),
        "largest_activity_segment": largest,
        "largest_post_segment": post_largest,
    }


def classify_case(case_id: str, junctions: dict[str, Any]) -> str:
    bjl1 = junctions["BJL1"]
    bjl2 = junctions["BJL2"]
    activity = bjl1["activity_complete_event_units"] + bjl2["activity_complete_event_units"]
    post = bjl1["post_complete_event_units"] + bjl2["post_complete_event_units"]
    if post:
        return "FREE_RUNNING_OR_POST_EVENT"
    if bjl1["activity_complete_event_units"] > 1 or bjl2["activity_complete_event_units"] > 1:
        return "MULTIFIRE"
    if case_id == "paper-j1-logical1-read":
        if bjl2["activity_complete_event_units"] == 1:
            return "BJL2_EXACTLY_ONE"
        if bjl1["activity_complete_event_units"] >= 1:
            return "BJL1_ONLY"
        return "NO_COMPLETE_EVENT"
    return "NONSELECTIVE_EVENT" if activity else "NO_COMPLETE_EVENT"


def load_case(bias_dir: str, case_id: str) -> dict[str, Any]:
    path = RAW / bias_dir / f"{case_id}.csv"
    data = load_csv(path)
    junctions = {name: analyze_jj(data, columns) for name, columns in JUNCTIONS.items()}
    return {"path": str(path.relative_to(ROOT)), "classification": classify_case(case_id, junctions), "junctions": junctions}


def settled_op(bias_dir: str) -> dict[str, Any]:
    case_id = "paper-j1-logical1-read0-control"
    data = load_csv(RAW / bias_dir / f"{case_id}.csv")
    mask = (data["time"] * 1e12 >= POST[0]) & (data["time"] * 1e12 < POST[1])
    names = ["P(BJS|XBQ)", "P(BJL1|XBQ)", "P(BJL2|XBQ)", "I(LIN|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(RB|XBQ)", "I(BJL1|XBQ)", "I(BJL2|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)"]
    result: dict[str, float] = {}
    for name in names:
        scale = 1e6 if name.startswith("I(") else 1.0
        result[name] = float(median(data[name][mask]) * scale)
    return result


def inspect_bias(bias_dir: str) -> dict[str, Any]:
    cases = {case_id: load_case(bias_dir, case_id) for case_id in CASES if (RAW / bias_dir / f"{case_id}.csv").exists()}
    return {"bias_dir": bias_dir, "settled": settled_op(bias_dir) if "paper-j1-logical1-read0-control" in cases else {}, "cases": cases}


def full_verdict(results: list[dict[str, Any]]) -> tuple[str, str | None]:
    for result in results:
        cases = result["cases"]
        if len(cases) < 4:
            continue
        control_or_l0 = [cases[name] for name in CASES if name != "paper-j1-logical1-read"]
        if any(item["classification"] in {"NONSELECTIVE_EVENT", "MULTIFIRE", "FREE_RUNNING_OR_POST_EVENT"} for item in control_or_l0):
            return "NONSELECTIVE_OR_FREE_RUNNING", result["bias_dir"]
        read1 = cases["paper-j1-logical1-read"]
        if read1["classification"] == "BJL2_EXACTLY_ONE":
            return "PAPER_SL_QB_BIAS_ONE_SHOT", result["bias_dir"]
        if read1["classification"] == "BJL1_ONLY":
            return "BJL1_ONE_SHOT_BJL2_SUBTHRESHOLD", result["bias_dir"]
        if read1["classification"] in {"MULTIFIRE", "FREE_RUNNING_OR_POST_EVENT"}:
            return "NONSELECTIVE_OR_FREE_RUNNING", result["bias_dir"]
    return "BIAS_BRANCH_SUBTHRESHOLD", None


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.6g}"
    return str(value)


def report(result: dict[str, Any]) -> str:
    lines = [
        "# PAPER-SL-Q2 analysis report",
        "",
        f"## Verdict: `{result['verdict']}`",
        "",
        f"Executed bias directories: `{', '.join(result['executed_bias_dirs'])}`.",
        "Q1 replay source trajectories remain byte-identical; only IBIAS differs.",
        "The accepted 35 µA Q1 baseline was not rerun. A first 37.5 µA control attempt had an include-path artifact and produced no raw output; its logs and deck are preserved under `reference/invalid-attempt-01`; the retry used complete local include snapshots.",
        "",
        "## Case summary",
        "",
        "| bias | case | BJs units | BJL1 units | BJL2 units | BJs largest delta / area | BJL1 largest delta / area | BJL2 largest delta / area | post units | classification |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for bias_result in result["bias_results"]:
        bias = bias_result["bias_dir"]
        for case_id in CASES:
            if case_id not in bias_result["cases"]:
                continue
            case = bias_result["cases"][case_id]
            bjs = case["junctions"]["BJs"]
            j1 = case["junctions"]["BJL1"]
            j2 = case["junctions"]["BJL2"]
            ss = bjs["largest_activity_segment"] or {}
            s1 = j1["largest_activity_segment"] or {}
            s2 = j2["largest_activity_segment"] or {}
            post = j1["post_complete_event_units"] + j2["post_complete_event_units"]
            lines.append(f"| {bias} | {case_id} | {bjs['activity_complete_event_units']} | {j1['activity_complete_event_units']} | {j2['activity_complete_event_units']} | {fmt(ss.get('delta_turns'))} / {fmt(ss.get('area_turns'))} | {fmt(s1.get('delta_turns'))} / {fmt(s1.get('area_turns'))} | {fmt(s2.get('delta_turns'))} / {fmt(s2.get('area_turns'))} | {post} | `{case['classification']}` |")
    lines += ["", "## Settled operating points", "", "| bias | P(BJs) rad | P(BJL1) rad | P(BJL2) rad | I(RB) µA | I(BJL1) µA | I(BJL2) µA | I(L1) µA | I(L2) µA |", "|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for bias_result in result["bias_results"]:
        op = bias_result["settled"]
        lines.append(f"| {bias_result['bias_dir']} | {fmt(op.get('P(BJS|XBQ)'))} | {fmt(op.get('P(BJL1|XBQ)'))} | {fmt(op.get('P(BJL2|XBQ)'))} | {fmt(op.get('I(RB|XBQ)'))} | {fmt(op.get('I(BJL1|XBQ)'))} | {fmt(op.get('I(BJL2|XBQ)'))} | {fmt(op.get('I(L1|XBQ)'))} | {fmt(op.get('I(L2|XBQ)'))} |")
    lines += [
        "",
        "## Evidence boundary",
        "",
        "- Observed: phase and voltage-area results use the same JJ, same monotonic segment, actual CSV time, and the registered [94,130) ps window; post checks use [140,170) ps.",
        "- Derived: a BJL2 complete-unit count requires a segment of at least one turn with area consistency; current/Ic and voltage peaks are not used as event criteria.",
        "- Inference: any high-side bias effect is a local QB operating-point result under ideal paper-JSL replay, not physical BVM interface evidence.",
        "- Unknown: physical BVM/JSL source loading and whether this replay result transfers to a connected BVM.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--bias-dir")
    parser.add_argument("--case")
    args = parser.parse_args()
    if args.single:
        if not args.bias_dir or not args.case:
            raise SystemExit("--single requires --bias-dir and --case")
        result = load_case(args.bias_dir, args.case)
        print(json.dumps({"bias_dir": args.bias_dir, "case": args.case, **result}, indent=2))
        return
    bias_dirs = sorted(path.name for path in RAW.iterdir() if path.is_dir())
    bias_results = [inspect_bias(bias_dir) for bias_dir in bias_dirs]
    verdict, stop_bias = full_verdict(bias_results)
    result = {"verdict": verdict, "stop_bias_dir": stop_bias, "executed_bias_dirs": bias_dirs, "bias_results": bias_results}
    (ROOT / "analysis/metrics.json").write_text(json.dumps(result, indent=2) + "\n")
    (ROOT / "analysis/REPORT.md").write_text(report(result))
    with (ROOT / "analysis/case-summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["bias_dir", "case", "BJs_complete_units", "BJL1_complete_units", "BJL2_complete_units", "BJs_largest_delta_turns", "BJs_largest_area_turns", "BJL1_largest_delta_turns", "BJL1_largest_area_turns", "BJL2_largest_delta_turns", "BJL2_largest_area_turns", "post_complete_units", "classification"])
        for bias_result in bias_results:
            for case_id in CASES:
                if case_id not in bias_result["cases"]:
                    continue
                case = bias_result["cases"][case_id]
                bjs = case["junctions"]["BJs"]
                j1 = case["junctions"]["BJL1"]
                j2 = case["junctions"]["BJL2"]
                ss = bjs["largest_activity_segment"] or {}
                s1 = j1["largest_activity_segment"] or {}
                s2 = j2["largest_activity_segment"] or {}
                writer.writerow([bias_result["bias_dir"], case_id, bjs["activity_complete_event_units"], j1["activity_complete_event_units"], j2["activity_complete_event_units"], ss.get("delta_turns"), ss.get("area_turns"), s1.get("delta_turns"), s1.get("area_turns"), s2.get("delta_turns"), s2.get("area_turns"), j1["post_complete_event_units"] + j2["post_complete_event_units"], case["classification"]])
    print(verdict, stop_bias or "no stop bias")


if __name__ == "__main__":
    main()
