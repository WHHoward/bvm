#!/usr/bin/env python3
"""Direct phase/voltage-area audit for the QB-Q0 standalone fixtures.

This script deliberately does not call scripts/sfq_metrics.py.  It reports raw
phase activity and a task-local, explicitly unfrozen phase/area candidate rule.
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
RAW_ROOT = ROOT / "raw"
ANALYSIS_ROOT = ROOT / "analysis"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
PULSE_STARTS_PS = [10.0, 60.0, 110.0, 160.0, 210.0, 260.0]

JUNCTIONS = {
    "BJs": ("P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}

MODEL_PARAMETERS = [
    ("scaled", "BJs", 0.50, 50.0, 35.0, 32.0, 320.0),
    ("scaled", "BJL1", 0.36, 36.0, 25.2, 44.444444, 444.444444),
    ("scaled", "BJL2", 0.54, 54.0, 37.8, 29.629630, 296.296296),
    ("paper", "BJs", 1.33, 133.0, 93.1, 12.030075, 120.300752),
    ("paper", "BJL1", 1.12, 112.0, 78.4, 14.285714, 142.857143),
    ("paper", "BJL2", 1.89, 189.0, 132.3, 8.465608, 84.656085),
]

CASES = [
    ("scaled", "iin-0", 0.0, "iin-0.csv"),
    ("scaled", "iin-45u", 45.0, "iin-45u.csv"),
    ("scaled", "iin-68p4u", 68.4, "iin-68p4u.csv"),
    ("scaled", "iin-90u", 90.0, "iin-90u.csv"),
    ("paper", "iin-0", 0.0, "iin-0.csv"),
    ("paper", "iin-68p4u", 68.4, "iin-68p4u.csv"),
    ("paper", "iin-90u", 90.0, "iin-90u.csv"),
]


def finite_float(value: str) -> float:
    return float(value.strip())


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = list(reader)
    names = [item.strip() for item in header]
    data: dict[str, list[float]] = {name: [] for name in names}
    for row in rows:
        if len(row) != len(names):
            continue
        try:
            values = [finite_float(item) for item in row]
        except ValueError:
            continue
        for name, value in zip(names, values):
            data[name].append(value)
    arrays = {name: np.asarray(values, dtype=float) for name, values in data.items()}
    if not arrays or "time" not in arrays:
        raise ValueError(f"missing JoSIM time column in {path}")
    time = arrays["time"]
    if len(time) < 2 or not np.all(np.isfinite(time)):
        raise ValueError(f"invalid time series in {path}")
    if not np.all(np.diff(time) > 0):
        raise ValueError(f"time is not strictly increasing in {path}")
    return arrays


def column(data: dict[str, np.ndarray], requested: str) -> np.ndarray:
    if requested in data:
        return data[requested]
    normalized = {re.sub(r"\s+", "", key).lower(): key for key in data}
    key = normalized.get(re.sub(r"\s+", "", requested).lower())
    if key is None:
        raise KeyError(f"column {requested!r} not found; available={list(data)}")
    return data[key]


def safe_stats(values: np.ndarray) -> dict[str, float | None]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"min": None, "max": None, "p2p": None, "mean": None}
    return {
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "p2p": float(np.max(finite) - np.min(finite)),
        "mean": float(np.mean(finite)),
    }


def sign_runs(unwrapped: np.ndarray) -> list[tuple[int, int]]:
    """Return inclusive monotonic runs over one selected window."""
    if unwrapped.size < 2:
        return []
    differences = np.diff(unwrapped)
    signs = np.sign(differences)
    nonzero = np.flatnonzero(signs)
    if nonzero.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = 0
    current = int(signs[nonzero[0]])
    for pos in nonzero[1:]:
        sign = int(signs[pos])
        if sign != current:
            runs.append((start, int(pos)))
            start = int(pos)
            current = sign
    runs.append((start, unwrapped.size - 1))
    return [(left, right) for left, right in runs if right > left]


def area_turns(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    time_s = time_ps * 1e-12
    if hasattr(np, "trapezoid"):
        integral = np.trapezoid(voltage, time_s)
    else:
        integral = np.trapz(voltage, time_s)
    return float(integral / PHI0)


def segment_records(
    time_ps: np.ndarray,
    unwrapped: np.ndarray,
    voltage: np.ndarray,
    mask: np.ndarray,
) -> list[dict[str, Any]]:
    selected = np.flatnonzero(mask)
    if selected.size < 2:
        return []
    local_phase = unwrapped[selected]
    records: list[dict[str, Any]] = []
    for left, right in sign_runs(local_phase):
        indices = selected[left : right + 1]
        delta_turns = float((unwrapped[indices[-1]] - unwrapped[indices[0]]) / TWO_PI)
        area = area_turns(time_ps[indices], voltage[indices])
        residual = float(area - delta_turns)
        tolerance = max(0.05, 0.10 * abs(delta_turns))
        area_sign_matches = abs(area) > 1e-12 and delta_turns * area > 0
        phase_candidate = abs(delta_turns) >= 1.0
        area_consistent = phase_candidate and area_sign_matches and abs(residual) <= tolerance
        complete_event_units = int(math.floor(abs(delta_turns))) if area_consistent else 0
        records.append(
            {
                "start_ps": float(time_ps[indices[0]]),
                "end_ps": float(time_ps[indices[-1]]),
                "delta_turns": delta_turns,
                "area_turns": float(area),
                "area_residual_turns": residual,
                "area_tolerance_turns": float(tolerance),
                "phase_candidate": bool(phase_candidate),
                "area_consistent": bool(area_consistent),
                "complete_event_units": complete_event_units,
            }
        )
    return records


def largest_segment(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not records:
        return None
    return max(records, key=lambda item: abs(float(item["delta_turns"])))


def analyze_junction(
    data: dict[str, np.ndarray],
    phase_name: str,
    voltage_name: str,
    current_name: str,
) -> dict[str, Any]:
    time_ps = column(data, "time") * 1e12
    phase = column(data, phase_name)
    voltage = column(data, voltage_name)
    current = column(data, current_name)
    unwrapped = np.unwrap(phase)
    pulses: list[dict[str, Any]] = []
    for start in PULSE_STARTS_PS:
        activity_mask = (time_ps >= start) & (time_ps < min(start + 25.0, 300.0))
        post_mask = (time_ps >= start + 25.0) & (time_ps < min(start + 49.0, 300.0))
        activity = segment_records(time_ps, unwrapped, voltage, activity_mask)
        post = segment_records(time_ps, unwrapped, voltage, post_mask)
        activity_phase_candidates = [x for x in activity if x["phase_candidate"]]
        activity_area_candidates = [x for x in activity if x["area_consistent"]]
        post_candidates = [x for x in post if x["area_consistent"]]
        activity_phase = unwrapped[activity_mask]
        post_phase = unwrapped[post_mask]
        pulses.append(
            {
                "start_ps": start,
                "activity": {
                    "segments": activity,
                    "phase_candidate_count": len(activity_phase_candidates),
                    "area_candidate_count": len(activity_area_candidates),
                    "complete_event_units": sum(x["complete_event_units"] for x in activity),
                    "phase_p2p_turns": float((np.ptp(activity_phase) / TWO_PI) if activity_phase.size else 0.0),
                    "largest_segment": largest_segment(activity),
                    "current_uA": safe_stats(column(data, current_name)[activity_mask] * 1e6),
                },
                "post": {
                    "segments": post,
                    "area_candidate_count": len(post_candidates),
                    "complete_event_units": sum(x["complete_event_units"] for x in post),
                    "phase_p2p_turns": float((np.ptp(post_phase) / TWO_PI) if post_phase.size else 0.0),
                    "largest_segment": largest_segment(post),
                },
            }
        )
    activity_records = [record for pulse in pulses for record in pulse["activity"]["segments"]]
    post_records = [record for pulse in pulses for record in pulse["post"]["segments"]]
    activity_phase_candidates = [x for x in activity_records if x["phase_candidate"]]
    activity_area_candidates = [x for x in activity_records if x["area_consistent"]]
    post_area_candidates = [x for x in post_records if x["area_consistent"]]
    pre_mask = time_ps < PULSE_STARTS_PS[0] - 1.0
    post_all_mask = time_ps >= PULSE_STARTS_PS[-1] + 25.0
    return {
        "raw_phase_rad": {"min": float(np.min(phase)), "max": float(np.max(phase))},
        "raw_voltage_V": safe_stats(voltage),
        "raw_current_A": safe_stats(current),
        "pre_phase_turns": safe_stats(unwrapped[pre_mask] / TWO_PI),
        "post_phase_turns": safe_stats(unwrapped[post_all_mask] / TWO_PI),
        "pulses": pulses,
        "activity_phase_candidate_count": len(activity_phase_candidates),
        "activity_area_candidate_count": len(activity_area_candidates),
        "activity_complete_event_units": sum(x["complete_event_units"] for x in activity_records),
        "post_area_candidate_count": len(post_area_candidates),
        "post_complete_event_units": sum(x["complete_event_units"] for x in post_records),
        "largest_activity_segment": largest_segment(activity_records),
        "largest_post_segment": largest_segment(post_records),
    }


def classify_case(input_uA: float, junctions: dict[str, Any]) -> str:
    bjl2 = junctions["BJL2"]
    activity_counts = [pulse["activity"]["complete_event_units"] for pulse in bjl2["pulses"]]
    phase_counts = [pulse["activity"]["phase_candidate_count"] for pulse in bjl2["pulses"]]
    post_count = int(bjl2["post_complete_event_units"])
    if post_count:
        return "FREE_RUNNING"
    if input_uA == 0.0:
        return "ZERO_EVENT" if sum(activity_counts) == 0 else "FREE_RUNNING"
    if any(count > 1 for count in activity_counts) or sum(activity_counts) > len(PULSE_STARTS_PS):
        return "MULTI_EVENT"
    if all(count == 1 for count in activity_counts):
        return "EXACTLY_ONE"
    if any(count > 0 for count in phase_counts):
        return "INCONCLUSIVE_AREA"
    return "NO_COMPLETE_EVENT"


def summarize_case(group: str, case_id: str, input_uA: float, filename: str) -> dict[str, Any]:
    path = RAW_ROOT / group / filename
    data = load_csv(path)
    junctions = {
        name: analyze_junction(data, *columns) for name, columns in JUNCTIONS.items()
    }
    output = {
        "group": group,
        "case_id": case_id,
        "input_uA": input_uA,
        "raw_file": str(path.relative_to(ROOT)),
        "classification": classify_case(input_uA, junctions),
        "junctions": junctions,
    }
    for name in ("I(I_IN)", "I(I_IBIAS)", "V(IN)", "V(OUT)", "I(R_LOAD)"):
        try:
            values = column(data, name)
        except KeyError:
            continue
        units = 1e6 if name.startswith("I(") else 1.0
        output.setdefault("top_level", {})[name] = safe_stats(values * units)
    return output


def compact_row(case: dict[str, Any]) -> dict[str, Any]:
    row: dict[str, Any] = {
        "group": case["group"],
        "case_id": case["case_id"],
        "input_uA": case["input_uA"],
        "classification": case["classification"],
    }
    for name in JUNCTIONS:
        jj = case["junctions"][name]
        row[f"N_{name}_phase"] = sum(
            pulse["activity"]["phase_candidate_count"] for pulse in jj["pulses"]
        )
        row[f"N_{name}_area_segments"] = jj["activity_area_candidate_count"]
        row[f"N_{name}_event_units"] = jj["activity_complete_event_units"]
        row[f"{name}_activity_p2p_max_turns"] = max(
            pulse["activity"]["phase_p2p_turns"] for pulse in jj["pulses"]
        )
        largest = jj["largest_activity_segment"] or {}
        row[f"{name}_largest_delta_turns"] = largest.get("delta_turns")
        row[f"{name}_largest_area_turns"] = largest.get("area_turns")
        row[f"{name}_largest_residual_turns"] = largest.get("area_residual_turns")
        row[f"{name}_post_area_candidates"] = jj["post_area_candidate_count"]
    return row


def fmt(value: Any, digits: int = 5) -> str:
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}g}"
    return str(value)


def report_markdown(results: list[dict[str, Any]]) -> str:
    lines = [
        "# QB-Q0 standalone current-to-quantized-event re-audit",
        "",
        "## Verdict",
        "",
        "This is an exploratory local-JJ phase/voltage-area audit. It does not test canonical BVM compatibility or downstream SFQ delivery.",
        "",
        "## Core result",
        "",
        "| fixture | Iin (µA) | N(BJs) | N(BJL1) | N(BJL2) | BJL2 per-pulse | classification |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for case in results:
        bjl2 = case["junctions"]["BJL2"]
        counts = [p["activity"]["complete_event_units"] for p in bjl2["pulses"]]
        counts_text = ",".join(str(x) for x in counts)
        lines.append(
            f"| {case['group']} | {fmt(case['input_uA'])} | "
            f"{case['junctions']['BJs']['activity_complete_event_units']} | "
            f"{case['junctions']['BJL1']['activity_complete_event_units']} | "
            f"{bjl2['activity_complete_event_units']} | `{counts_text}` | `{case['classification']}` |"
        )
    lines += [
        "",
        "`N(...)` counts complete turn units inside same-JJ, same-segment phase/area-consistent candidates; it is a local diagnostic count, not an SFQ-delivery count. Candidate segment counts are retained in the CSV/JSON.",
        "",
        "## Actual jjmit scaling used",
        "",
        "The copied model is `jjmit(RTYPE=1, VG=2.8m, CAP=0.07p, r0=160, rn=16, icrit=0.1m)`. These values are reconstructed from the actual model's first-order AREA scaling, not from the old fast-event analysis.",
        "",
        "| fixture | JJ | AREA | Ic (µA) | C (fF) | RN (Ω) | R0 (Ω) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for fixture, name, area, ic, cap, rn, r0 in MODEL_PARAMETERS:
        lines.append(f"| {fixture} | {name} | {area:g} | {ic:g} | {cap:g} | {rn:g} | {r0:g} |")
    lines += [
        "",
        "## BJL2 pulse-by-pulse/reset audit",
        "",
        "| fixture | Iin (µA) | complete units per pulse | max post-window phase p2p (turn) | post complete units | event-count repeatability |",
        "|---|---:|---|---:|---:|---|",
    ]
    for case in results:
        bjl2 = case["junctions"]["BJL2"]
        event_vector = [p["activity"]["complete_event_units"] for p in bjl2["pulses"]]
        post_p2p = max(p["post"]["phase_p2p_turns"] for p in bjl2["pulses"])
        post_units = sum(p["post"]["complete_event_units"] for p in bjl2["pulses"])
        repeatability = "stable" if len(set(event_vector)) == 1 else "varied"
        lines.append(
            f"| {case['group']} | {fmt(case['input_uA'])} | `{','.join(str(x) for x in event_vector)}` | "
            f"{fmt(post_p2p)} | {post_units} | {repeatability} |"
        )
    lines += [
        "",
        "## Activity and same-JJ area",
        "",
        "| fixture | Iin (µA) | JJ | max activity p2p (turn) | largest Δphase (turn) | same-segment area (Φ0) | residual (turn) |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for case in results:
        for name in JUNCTIONS:
            jj = case["junctions"][name]
            largest = jj["largest_activity_segment"] or {}
            p2p = max(p["activity"]["phase_p2p_turns"] for p in jj["pulses"])
            lines.append(
                f"| {case['group']} | {fmt(case['input_uA'])} | {name} | {fmt(p2p)} | "
                f"{fmt(largest.get('delta_turns'))} | {fmt(largest.get('area_turns'))} | "
                f"{fmt(largest.get('area_residual_turns'))} |"
            )
    lines += [
        "",
        "## Observed",
        "",
        "- The table reports direct `P`, `V`, and `I` traces from the same JJ and the same monotonic segment.",
        "- The input is periodic: six starts at 10, 60, 110, 160, 210, and 260 ps. Per-pulse vectors are retained in `q0-execution-metrics.json`.",
        "- A voltage peak or a current above a nominal Ic is not used as event evidence.",
        "",
        "## Derived",
        "",
        "- Phase turns are `ΔP/(2π)` from raw JoSIM phase in radians.",
        "- Same-segment voltage area is `∫Vdt/Φ0` using the direct JJ voltage column.",
        "- The exploratory candidate rule is `|Δturn|≥1`, matching area sign, and residual within `max(0.05, 0.10|Δturn|)` turn. It is task-local and explicitly unfrozen.",
        "",
        "## Inference",
        "",
        "- `EXACTLY_ONE` means one complete turn unit in BJL2 in every nonzero ideal-current pulse window, with no post-window candidate; a single approximately 2-turn monotonic segment is therefore `MULTI_EVENT`, not exactly-one.",
        "- `NO_COMPLETE_EVENT` means no qualifying local BJL2 phase/area candidate was found under this exploratory rule; it is not a universal impossibility result.",
        "",
        "## Unknown / limits",
        "",
        "- No canonical BVM, transformer, DCSFQ, JTL, or T1 is connected.",
        "- The periodic six-pulse fixture is a historical re-audit, not a single-pulse reset characterization or a convergence study.",
        "- The paper comparison uses 90 µA bias from the historical BVM-paper fixture as provenance, while replacing the BVM input with an ideal-current source; it is not a reproduction of the paper's full experiment.",
        "- No parameter optimization or automatic follow-up was performed.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    results = [summarize_case(*case) for case in CASES]
    metrics_path = ANALYSIS_ROOT / "q0-execution-metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "run_id": "qb-q0-standalone-current-quantized-event-20260824",
                "metric_spec": "docs/research/METRIC_SPEC_V2.md@2.0.0",
                "event_rule_status": "UNFROZEN_TASK_LOCAL",
                "cases": results,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    rows = [compact_row(case) for case in results]
    csv_path = ANALYSIS_ROOT / "q0-case-summary.csv"
    fields = list(rows[0])
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (ANALYSIS_ROOT / "QB_Q0_REPORT.md").write_text(report_markdown(results))
    print(json.dumps({"cases": len(results), "summary": rows}, indent=2))


if __name__ == "__main__":
    main()
