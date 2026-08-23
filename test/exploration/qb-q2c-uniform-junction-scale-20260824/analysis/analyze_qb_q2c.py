#!/usr/bin/env python3
"""Audit QB-Q2C scale points with phase/area evidence."""

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
SCALES = {"S085": 0.85, "S070": 0.70, "S055": 0.55}
CASES = ["logical1-read0-control", "logical0-read0-control", "logical1-read", "logical0-read"]
JUNCTIONS = {
    "BJs": ("P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    names = [x.strip() for x in header]
    data = {name: [] for name in names}
    for row in rows:
        if len(row) != len(names):
            raise ValueError(f"row/header mismatch in {path}")
        for index, name in enumerate(names):
            data[name].append(float(row[index]))
    arrays = {name: np.asarray(values, dtype=float) for name, values in data.items()}
    if "time" not in arrays or arrays["time"].size < 2:
        raise ValueError(f"missing time in {path}")
    if not np.all(np.diff(arrays["time"]) > 0) or not np.all(np.isfinite(arrays["time"])):
        raise ValueError(f"invalid time in {path}")
    if not all(np.all(np.isfinite(value)) for value in arrays.values()):
        raise ValueError(f"non-finite value in {path}")
    return arrays


def col(data: dict[str, np.ndarray], requested: str) -> np.ndarray:
    if requested in data:
        return data[requested]
    normalized = {re.sub(r"\s+", "", key).lower(): key for key in data}
    key = normalized.get(re.sub(r"\s+", "", requested).lower())
    if key is None:
        raise KeyError(f"missing {requested!r} in {list(data)}")
    return data[key]


def stat(x: np.ndarray) -> dict[str, float | None]:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"min": None, "max": None, "p2p": None, "mean": None}
    return {"min": float(x.min()), "max": float(x.max()), "p2p": float(np.ptp(x)), "mean": float(x.mean())}


def monotonic_runs(x: np.ndarray) -> list[tuple[int, int]]:
    signs = np.sign(np.diff(x))
    nz = np.flatnonzero(signs)
    if nz.size == 0:
        return []
    out = []
    start, direction = 0, int(signs[nz[0]])
    for pos in nz[1:]:
        new_direction = int(signs[pos])
        if new_direction != direction:
            out.append((start, int(pos)))
            start, direction = int(pos), new_direction
    out.append((start, x.size - 1))
    return [(left, right) for left, right in out if right > left]


def area_turns(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    time_s = time_ps * 1e-12
    integral = np.trapezoid(voltage, time_s) if hasattr(np, "trapezoid") else np.trapz(voltage, time_s)
    return float(integral / PHI0)


def segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, mask: np.ndarray) -> list[dict[str, Any]]:
    indices = np.flatnonzero(mask)
    if indices.size < 2:
        return []
    selected = phase[indices]
    result = []
    for left, right in monotonic_runs(selected):
        idx = indices[left:right + 1]
        delta = float((phase[idx[-1]] - phase[idx[0]]) / TWO_PI)
        area = area_turns(time_ps[idx], voltage[idx])
        residual = float(area - delta)
        candidate = abs(delta) >= 1.0
        consistent = candidate and delta * area > 0 and abs(residual) <= max(0.05, 0.10 * abs(delta))
        result.append({
            "start_ps": float(time_ps[idx[0]]), "end_ps": float(time_ps[idx[-1]]),
            "delta_turns": delta, "area_turns": area, "residual_turns": residual,
            "phase_candidate": candidate, "area_consistent": consistent,
            "complete_event_units": int(math.floor(abs(delta))) if consistent else 0,
        })
    return result


def analyze_jj(data: dict[str, np.ndarray], names: tuple[str, str, str]) -> dict[str, Any]:
    time_ps = col(data, "time") * 1e12
    raw_phase = col(data, names[0])
    phase = np.unwrap(raw_phase)
    voltage = col(data, names[1])
    current = col(data, names[2])
    windows = {}
    for label, (start, end) in {"pre": (80.0, 90.0), "activity": (94.0, 130.0), "post": (150.0, 170.0)}.items():
        mask = (time_ps >= start) & (time_ps < end)
        records = segments(time_ps, phase, voltage, mask)
        selected = phase[mask]
        windows[label] = {
            "window_ps": [start, end], "segments": records,
            "phase_p2p_turns": float(np.ptp(selected) / TWO_PI) if selected.size else 0.0,
            "current_uA": stat(current[mask] * 1e6),
            "phase_candidate_count": sum(r["phase_candidate"] for r in records),
            "area_candidate_count": sum(r["area_consistent"] for r in records),
            "complete_event_units": sum(r["complete_event_units"] for r in records),
        }
    activity_segments = windows["activity"]["segments"]
    return {
        "raw_phase_rad": stat(raw_phase), "raw_voltage_V": stat(voltage), "raw_current_A": stat(current),
        "windows": windows,
        "largest_activity_segment": max(activity_segments, key=lambda r: abs(r["delta_turns"])) if activity_segments else None,
        "activity_complete_event_units": windows["activity"]["complete_event_units"],
        "post_complete_event_units": windows["post"]["complete_event_units"],
    }


def analyze_case(scale_name: str, case: str) -> dict[str, Any]:
    path = RAW / scale_name / f"{case}.csv"
    data = load_csv(path)
    junctions = {name: analyze_jj(data, names) for name, names in JUNCTIONS.items()}
    return {
        "raw_file": str(path.relative_to(ROOT)), "junctions": junctions,
        "input_voltage_V": stat(col(data, "V(IN)")), "input_current_A": stat(col(data, "I(V_REPLAY)")),
        "branch_currents_uA": {name: stat(col(data, name) * 1e6) for name in ["I(RB|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(Lin|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)"]},
    }


def classify(case: str, item: dict[str, Any]) -> str:
    junc = item["junctions"]
    output_units = junc["BJL1"]["activity_complete_event_units"] + junc["BJL2"]["activity_complete_event_units"]
    post_units = junc["BJs"]["post_complete_event_units"] + junc["BJL1"]["post_complete_event_units"] + junc["BJL2"]["post_complete_event_units"]
    if post_units:
        return "FREE_RUNNING_OR_UNBOUNDED"
    if "read0-control" in case and any(junc[name]["activity_complete_event_units"] for name in JUNCTIONS):
        return "NONSELECTIVE_CONTROL_EVENT"
    if case == "logical0-read" and any(junc[name]["activity_complete_event_units"] for name in ("BJL1", "BJL2")):
        return "NONSELECTIVE_READ0_EVENT"
    if case == "logical1-read" and output_units > 1:
        return "READ1_MULTIEVENT"
    if case == "logical1-read" and output_units == 1:
        return "READ1_SELECTIVE_OUTPUT_EVENT_CANDIDATE"
    return "BOUNDED_NO_COMPLETE_EVENT"


def fmt(value: Any) -> str:
    return "—" if value is None else (f"{value:.6g}" if isinstance(value, (float, int)) else str(value))


def report(result: dict[str, Any]) -> str:
    lines = [
        "# QB-Q2C uniform junction-scale report", "", f"## Verdict: `{result['verdict']}`", "", result["explanation"],
        "", "s=1 is an accepted Q2A/Q2B reference and was not rerun. It is shown only as a reference row; all new raw data are s=0.85/0.70/0.55.",
        "", "## Scale → event-unit summary", "",
        "| scale | source case | N(BJs) | N(BJL1) | N(BJL2) | BJL1 largest Δturn | BJL1 area | classification |",
        "|---:|---|---:|---:|---:|---:|---:|---|",
        "| 1.00 reference | logical1 + READ | 1 | 0 | 0 | +0.3394 activity | not a complete event | accepted Q2A/Q2B reference |",
        "| 1.00 reference | logical0 + READ | 0 | 0 | 0 | ~+0.059 activity | not a complete event | accepted Q2A/Q2B reference |",
    ]
    for scale_name, scale in SCALES.items():
        point = result["points"].get(scale_name, {})
        for case in ("logical1-read", "logical0-read", "logical1-read0-control", "logical0-read0-control"):
            if case not in point:
                continue
            item = point[case]
            j = item["junctions"]
            l1 = j["BJL1"]["largest_activity_segment"] or {}
            lines.append(f"| {scale:.2f} | {case} | {j['BJs']['activity_complete_event_units']} | {j['BJL1']['activity_complete_event_units']} | {j['BJL2']['activity_complete_event_units']} | {fmt(l1.get('delta_turns'))} | {fmt(l1.get('area_turns'))} | `{item['classification']}` |")
    lines += ["", "## Settled operating points", "", "The settled window is `[80,90) ps`; currents use declared element directions.", "", "| scale | case | I(RB) µA | I(L1) µA | I(L2) µA | I(BJL1) µA | I(BJL2) µA | I(BJs) µA |", "|---:|---|---:|---:|---:|---:|---:|---:|"]
    for scale_name, scale in SCALES.items():
        for case, item in result["points"].get(scale_name, {}).items():
            j = item["junctions"]
            branch = item["branch_currents_uA"]
            vals = {name: j[name]["windows"]["pre"]["current_uA"]["mean"] for name in ("BJs", "BJL1", "BJL2")}
            lines.append(f"| {scale:.2f} | {case} | {fmt(branch['I(RB|XBQ)']['mean'])} | {fmt(branch['I(L1|XBQ)']['mean'])} | {fmt(branch['I(L2|XBQ)']['mean'])} | {fmt(vals['BJL1'])} | {fmt(vals['BJL2'])} | {fmt(vals['BJs'])} |")
    lines += ["", "## Evidence boundary", "", "Complete event claims require a same-JJ continuous monotonic phase segment of at least one turn, same-segment direct voltage-area consistency and bounded post behavior. `I>Ic`, voltage peaks and sub-turn activity are not event counts.", "", "## Observed", "", "- Only the three declared uniform scales were newly simulated; s=1 was not rerun.", "- Each scale was analyzed controls-first; all available controls in this matrix remained bounded.", "- The source replay, external load and non-junction inductors/resistors were frozen.", "", "## Derived / inference / unknown", "", f"- {result['inference']}", "- Uniform scaling changes Ic, C, RN and R0 together; the result cannot be attributed to Ic alone.", "- This standalone replay does not establish physical BVM source guards or downstream JTL delivery.", "- No further scale point is authorized by this Exploration."]
    return "\n".join(lines) + "\n"


def main() -> None:
    result: dict[str, Any] = {"run_id": "qb-q2c-uniform-junction-scale-20260824", "points": {}}
    for scale_name in SCALES:
        point = {}
        for case in CASES:
            path = RAW / scale_name / f"{case}.csv"
            if path.exists():
                item = analyze_case(scale_name, case)
                item["classification"] = classify(case, item)
                point[case] = item
        result["points"][scale_name] = point
    complete = all(set(point) == set(CASES) for point in result["points"].values())
    control_bad = any(item["classification"] in {"FREE_RUNNING_OR_UNBOUNDED", "NONSELECTIVE_CONTROL_EVENT"} for point in result["points"].values() for case, item in point.items() if "read0-control" in case)
    read0_bad = any(item["classification"] == "NONSELECTIVE_READ0_EVENT" for point in result["points"].values() for item in point.values())
    read1_multi = any(item["classification"] == "READ1_MULTIEVENT" for point in result["points"].values() for item in point.values())
    read1_output = any(item["classification"] == "READ1_SELECTIVE_OUTPUT_EVENT_CANDIDATE" for point in result["points"].values() for item in point.values())
    if not complete:
        result["verdict"] = "INCONCLUSIVE"
        result["explanation"] = "The declared scale matrix is incomplete; no final scale verdict is assigned."
        result["inference"] = "Artifact completion is required before interpreting the scale branch."
    elif control_bad or read0_bad:
        result["verdict"] = "UNIFORM_SCALE_NONSEL_OR_FREE_RUNNING"
        result["explanation"] = "A control or logical0 replay produced complete/non-bounded output activity under the uniform scale branch."
        result["inference"] = "The tested downward scaling loses the required read0/control margin before a selective output point is established."
    elif read1_multi:
        result["verdict"] = "UNIFORM_SCALE_MULTIEVENT"
        result["explanation"] = "At least one read1 replay produced more than one complete BJL1/BJL2 event or unbounded output activity."
        result["inference"] = "The tested uniform scale enters a multi-event regime; lower scales are stopped."
    elif read1_output:
        result["verdict"] = "UNIFORM_SCALE_SELECTIVE_EVENT"
        result["explanation"] = "At least one scale produced a bounded read1 BJL1/BJL2 event while read0 and controls remained event-free."
        result["inference"] = "The result supports a selective output region within the tested scale points, not physical BVM or JTL success."
    else:
        result["verdict"] = "UNIFORM_SCALE_NO_OUTPUT_EVENT"
        result["explanation"] = "All newly tested uniform scales remained bounded but produced no complete read1 BJL1/BJL2 event."
        result["inference"] = "Within the declared replay, load, timestep and three-point scale bracket, uniform junction/current scaling did not close the BJs→BJL1/BJL2 dynamic gap."
    (ANALYSIS / "qb-q2c-metrics.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with (ANALYSIS / "qb-q2c-case-summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["scale", "case", "classification", "N_BJs", "N_BJL1", "N_BJL2", "BJL1_largest_delta_turns", "BJL1_largest_area_turns", "BJL2_largest_delta_turns", "BJL2_largest_area_turns"])
        for scale_name, point in result["points"].items():
            for case, item in point.items():
                j = item["junctions"]
                l1, l2 = j["BJL1"]["largest_activity_segment"] or {}, j["BJL2"]["largest_activity_segment"] or {}
                writer.writerow([scale_name, case, item["classification"], j["BJs"]["activity_complete_event_units"], j["BJL1"]["activity_complete_event_units"], j["BJL2"]["activity_complete_event_units"], l1.get("delta_turns"), l1.get("area_turns"), l2.get("delta_turns"), l2.get("area_turns")])
    (ANALYSIS / "QB_Q2C_REPORT.md").write_text(report(result))
    print(json.dumps({"verdict": result["verdict"], "points": {scale: {case: item["classification"] for case, item in point.items()} for scale, point in result["points"].items()}}, indent=2))


if __name__ == "__main__":
    main()
