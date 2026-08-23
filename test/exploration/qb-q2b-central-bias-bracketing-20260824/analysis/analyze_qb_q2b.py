#!/usr/bin/env python3
"""Audit Q2B IBIAS-only canonical replay cases with phase/area evidence."""

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
BIAS_POINTS = [30, 40]
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
    names = [name.strip() for name in header]
    data: dict[str, list[float]] = {name: [] for name in names}
    duplicates: dict[str, list[list[float]]] = {name: [] for name in set(names)}
    for name in names:
        duplicates[name].append([])
    seen: dict[str, int] = {name: 0 for name in set(names)}
    for row in rows:
        if len(row) != len(names):
            raise ValueError(f"row/header mismatch in {path}")
        for index, name in enumerate(names):
            value = float(row[index])
            data[name].append(value)
            duplicate_index = seen[name]
            duplicates[name][duplicate_index].append(value)
            seen[name] += 1
        seen = {name: 0 for name in set(names)}
    arrays = {name: np.asarray(values, dtype=float) for name, values in data.items()}
    for name, series in duplicates.items():
        if len(series) > 1:
            first = np.asarray(series[0])
            if not all(np.array_equal(first, np.asarray(other)) for other in series[1:]):
                raise ValueError(f"non-identical duplicate column {name!r} in {path}")
    if "time" not in arrays or arrays["time"].size < 2:
        raise ValueError(f"missing time in {path}")
    if not np.all(np.diff(arrays["time"]) > 0) or not np.all(np.isfinite(arrays["time"])):
        raise ValueError(f"invalid time in {path}")
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


def runs(x: np.ndarray) -> list[tuple[int, int]]:
    if x.size < 2:
        return []
    signs = np.sign(np.diff(x))
    nonzero = np.flatnonzero(signs)
    if nonzero.size == 0:
        return []
    out: list[tuple[int, int]] = []
    start = 0
    current = int(signs[nonzero[0]])
    for pos in nonzero[1:]:
        sign = int(signs[pos])
        if sign != current:
            out.append((start, int(pos)))
            start = int(pos)
            current = sign
    out.append((start, x.size - 1))
    return [(left, right) for left, right in out if right > left]


def area_turns(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    t = time_ps * 1e-12
    integral = np.trapezoid(voltage, t) if hasattr(np, "trapezoid") else np.trapz(voltage, t)
    return float(integral / PHI0)


def segment_records(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, mask: np.ndarray) -> list[dict[str, Any]]:
    indices = np.flatnonzero(mask)
    if indices.size < 2:
        return []
    selected = phase[indices]
    out: list[dict[str, Any]] = []
    for left, right in runs(selected):
        idx = indices[left : right + 1]
        delta = float((phase[idx[-1]] - phase[idx[0]]) / TWO_PI)
        area = area_turns(time_ps[idx], voltage[idx])
        residual = float(area - delta)
        tolerance = max(0.05, 0.10 * abs(delta))
        candidate = abs(delta) >= 1.0
        consistent = candidate and delta * area > 0 and abs(residual) <= tolerance
        out.append({
            "start_ps": float(time_ps[idx[0]]),
            "end_ps": float(time_ps[idx[-1]]),
            "delta_turns": delta,
            "area_turns": float(area),
            "residual_turns": residual,
            "phase_candidate": candidate,
            "area_consistent": consistent,
            "complete_event_units": int(math.floor(abs(delta))) if consistent else 0,
        })
    return out


def analyze_jj(data: dict[str, np.ndarray], names: tuple[str, str, str]) -> dict[str, Any]:
    time_ps = col(data, "time") * 1e12
    phase = np.unwrap(col(data, names[0]))
    voltage = col(data, names[1])
    current = col(data, names[2])
    results: dict[str, Any] = {}
    for window_name, (start, end) in {"pre": (80.0, 90.0), "activity": (94.0, 130.0), "post": (150.0, 170.0)}.items():
        mask = (time_ps >= start) & (time_ps < end)
        selected = phase[mask]
        records = segment_records(time_ps, phase, voltage, mask)
        results[window_name] = {
            "window_ps": [start, end],
            "segments": records,
            "phase_p2p_turns": float(np.ptp(selected) / TWO_PI) if selected.size else 0.0,
            "current_uA": stat(current[mask] * 1e6),
            "phase_candidate_count": sum(x["phase_candidate"] for x in records),
            "area_candidate_count": sum(x["area_consistent"] for x in records),
            "complete_event_units": sum(x["complete_event_units"] for x in records),
        }
    all_activity = results["activity"]["segments"]
    return {
        "raw_phase_rad": stat(col(data, names[0])),
        "raw_voltage_V": stat(voltage),
        "raw_current_A": stat(current),
        "windows": results,
        "largest_activity_segment": max(all_activity, key=lambda x: abs(x["delta_turns"])) if all_activity else None,
        "activity_complete_event_units": results["activity"]["complete_event_units"],
        "post_complete_event_units": results["post"]["complete_event_units"],
    }


def analyze_case(bias: int, case: str) -> dict[str, Any]:
    path = RAW / f"IBIAS{bias}" / f"{case}.csv"
    data = load_csv(path)
    junctions = {name: analyze_jj(data, names) for name, names in JUNCTIONS.items()}
    return {
        "raw_file": str(path.relative_to(ROOT)),
        "junctions": junctions,
        "input_voltage_V": stat(col(data, "V(IN)")),
        "input_current_A": stat(col(data, "I(V_REPLAY)")),
        "lin_current_A": stat(col(data, "I(LIN|XBQ)")),
        "branch_currents_uA": {name: stat(col(data, name) * 1e6) for name in ["I(RB|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(Lin|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)"]},
    }


def fmt(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, (float, int)):
        return f"{value:.6g}"
    return str(value)


def report(result: dict[str, Any]) -> str:
    lines = [
        "# QB-Q2B central-bias bracketing report",
        "",
        f"## Verdict: `{result['verdict']}`",
        "",
        result["explanation"],
        "",
        "The 35 µA C/C0 result is the accepted QB-Q2A baseline and was not rerun. All Q2B cases use frozen canonical source-isolated voltage replays; only IBIAS changes.",
        "",
        "## Case summary",
        "",
        "| bias (µA) | case | BJs units | BJL1 units | BJL2 units | BJL1 largest Δturn | BJL1 area | BJL2 largest Δturn | classification |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for bias in BIAS_POINTS:
        for case in CASES:
            if case not in result["points"][str(bias)]:
                continue
            item = result["points"][str(bias)][case]
            bjl1 = item["junctions"]["BJL1"]
            bjl2 = item["junctions"]["BJL2"]
            l1 = bjl1["largest_activity_segment"] or {}
            l2 = bjl2["largest_activity_segment"] or {}
            lines.append(f"| {bias} | {case} | {item['junctions']['BJs']['activity_complete_event_units']} | {bjl1['activity_complete_event_units']} | {bjl2['activity_complete_event_units']} | {fmt(l1.get('delta_turns'))} | {fmt(l1.get('area_turns'))} | {fmt(l2.get('delta_turns'))} | `{item['classification']}` |")
    lines += [
        "",
        "## Settled operating points",
        "",
        "The settled window is `[80,90) ps`; currents are in the declared element directions.",
        "",
        "| bias | case | I(RB) µA | I(L1) µA | I(L2) µA | I(BJL1) µA | I(BJL2) µA | I(BJs) µA |",
        "|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for bias in BIAS_POINTS:
        for case in CASES:
            if case not in result["points"][str(bias)]:
                continue
            item = result["points"][str(bias)][case]
            vals = {}
            for jj, key in [("BJs", "I(BJs|XBQ)"), ("BJL1", "I(BJL1|XBQ)"), ("BJL2", "I(BJL2|XBQ)")]:
                vals[jj] = item["junctions"][jj]["windows"]["pre"]["current_uA"]["mean"]
            branch = item["branch_currents_uA"]
            lines.append(f"| {bias} | {case} | {fmt(branch['I(RB|XBQ)']['mean'])} | {fmt(branch['I(L1|XBQ)']['mean'])} | {fmt(branch['I(L2|XBQ)']['mean'])} | {fmt(vals['BJL1'])} | {fmt(vals['BJL2'])} | {fmt(vals['BJs'])} |")
    lines += [
        "",
        "## Event evidence boundary",
        "",
        "A complete event requires a same-JJ continuous monotonic phase segment of at least one turn, same-segment direct voltage-area consistency, and bounded post behavior. Current above Ic, voltage peaks and phase activity alone are not event evidence.",
        "",
        "## Observed",
        "",
        "- Q2B changes only IBIAS at 30 and 40 µA; the source replay and all QB passive/JJ parameters are frozen.",
        "- READ=0 controls were run before READ cases at each point.",
        "- Raw P/V/I for BJs/BJL1/BJL2 and branch currents are retained.",
        "",
        "## Derived",
        "",
        "- Turns are raw `P()` phase differences divided by `2π`; voltage areas use the actual time column and direct same-JJ voltage.",
        "- The Q2A 35 µA baseline remains the comparison point; Q2B does not claim a continuous bias threshold from two extra points.",
        "",
        "## Inference / unknown",
        "",
        f"- {result['inference']}",
        "- No BVM source guard is applicable because this is still standalone source-replay diagnosis; physical BVM reconnection is outside this Exploration.",
        "- No further bias, AREA, L, R or load point is authorized by this run.",
    ]
    return "\n".join(lines) + "\n"


def classify_case(case: str, item: dict[str, Any]) -> str:
    bjl1 = item["junctions"]["BJL1"]
    bjl2 = item["junctions"]["BJL2"]
    if bjl1["post_complete_event_units"] or bjl2["post_complete_event_units"]:
        return "FREE_RUNNING_OR_UNBOUNDED"
    if "read0-control" in case and (bjl1["activity_complete_event_units"] or bjl2["activity_complete_event_units"]):
        return "NONSELECTIVE_CONTROL_EVENT"
    if "logical0-read" == case and (bjl1["activity_complete_event_units"] or bjl2["activity_complete_event_units"]):
        return "NONSELECTIVE_READ0_EVENT"
    if case == "logical1-read" and bjl1["activity_complete_event_units"]:
        return "READ1_BJL1_EVENT"
    if bjl1["windows"]["activity"]["phase_candidate_count"] or bjl2["windows"]["activity"]["phase_candidate_count"]:
        return "SUBTURN_OR_AREA_INCONCLUSIVE"
    return "BOUNDED_NO_COMPLETE_EVENT"


def main() -> None:
    result: dict[str, Any] = {"run_id": "qb-q2b-central-bias-bracketing-20260824", "points": {}}
    for bias in BIAS_POINTS:
        point: dict[str, Any] = {}
        for case in CASES:
            path = RAW / f"IBIAS{bias}" / f"{case}.csv"
            if not path.exists():
                continue
            item = analyze_case(bias, case)
            item["classification"] = classify_case(case, item)
            point[case] = item
        result["points"][str(bias)] = point
    complete = all(set(point) == set(CASES) for point in result["points"].values())
    control_bad = any(item["classification"] in {"FREE_RUNNING_OR_UNBOUNDED", "NONSELECTIVE_CONTROL_EVENT"} for point in result["points"].values() for case, item in point.items() if "read0-control" in case)
    read1_event = any(point.get("logical1-read", {}).get("classification") == "READ1_BJL1_EVENT" for point in result["points"].values())
    read0_event = any(point.get("logical0-read", {}).get("classification") == "NONSELECTIVE_READ0_EVENT" for point in result["points"].values())
    if not complete:
        result["verdict"] = "PARTIAL_GUARD_MATRIX"
        result["explanation"] = "Only part of the preregistered matrix is present; no final bias verdict is assigned."
        result["inference"] = "Guard-first execution is incomplete."
    elif control_bad or read0_event:
        result["verdict"] = "NONSELECTIVE_OR_FREE_RUNNING"
        result["explanation"] = "A control/read0 case produced unbounded or complete activity; the bias direction is nonselective under this frozen replay."
        result["inference"] = "Bias-only movement did not preserve the required logical separation."
    elif read1_event:
        result["verdict"] = "BJL1_SELECTIVE_EVENT"
        result["explanation"] = "At least one selected bias point produced a bounded read1 BJL1 event while read0 and controls remained event-free."
        result["inference"] = "This would establish a local BJs→BJL1 bias-assisted transition, not BJL2 quantization or downstream SFQ delivery."
    else:
        result["verdict"] = "BIAS_BRACKET_NO_BJL1_EVENT"
        result["explanation"] = "The selected 30/40 µA bracket did not produce a qualifying read1 BJL1 event while the guards remained bounded."
        result["inference"] = "Within this two-point, frozen-source bracket, central bias movement alone did not close the BJL1 dynamic gap."
    (ANALYSIS / "qb-q2b-metrics.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    with (ANALYSIS / "qb-q2b-case-summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["bias_uA", "case", "classification", "BJs_units", "BJL1_units", "BJL2_units", "BJL1_largest_delta_turns", "BJL1_largest_area_turns", "BJL2_largest_delta_turns", "BJL2_largest_area_turns"])
        for bias in BIAS_POINTS:
            for case, item in result["points"][str(bias)].items():
                l1 = item["junctions"]["BJL1"]["largest_activity_segment"] or {}
                l2 = item["junctions"]["BJL2"]["largest_activity_segment"] or {}
                writer.writerow([bias, case, item["classification"], item["junctions"]["BJs"]["activity_complete_event_units"], item["junctions"]["BJL1"]["activity_complete_event_units"], item["junctions"]["BJL2"]["activity_complete_event_units"], l1.get("delta_turns"), l1.get("area_turns"), l2.get("delta_turns"), l2.get("area_turns")])
    (ANALYSIS / "QB_Q2B_REPORT.md").write_text(report(result))
    print(json.dumps({"verdict": result["verdict"], "points": {bias: {case: item["classification"] for case, item in point.items()} for bias, point in result["points"].items()}}, indent=2))


if __name__ == "__main__":
    main()
