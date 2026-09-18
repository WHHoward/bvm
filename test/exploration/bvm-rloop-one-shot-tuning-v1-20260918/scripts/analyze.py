#!/usr/bin/env python3
"""Mechanical, raw-only analysis for the one-shot tuning platform."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

SERIES = Path(__file__).resolve().parents[1]
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
WINDOWS = {
    "idle_0_50": (0.0, 50.0),
    "write0_50_61": (50.0, 61.0),
    "settle0_61_70": (61.0, 70.0),
    "zero_read_control_70_81": (70.0, 81.0),
    "settle1_81_90": (81.0, 90.0),
    "write1_90_101": (90.0, 101.0),
    "settle_101_110": (101.0, 110.0),
    "final_read_110_121": (110.0, 121.0),
    "recovery_121_130": (121.0, 130.0),
    "tail_150_200": (150.0, 200.0),
    "whole_0_200": (0.0, 200.0),
}
STATE_WINDOWS = ("write0_50_61", "zero_read_control_70_81", "write1_90_101", "settle_101_110", "final_read_110_121", "recovery_121_130", "tail_150_200")
R_WINDOW = "final_read_110_121"
R_RECOVERY = "recovery_121_130"
MASK_ORDER = ("0000", "0001", "0011", "0111", "1111")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    import hashlib
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def repo_rel(path: Path) -> str:
    repo = next(item for item in (SERIES, *SERIES.parents) if (item / ".git").exists())
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def rms(values: list[float]) -> float | None:
    return math.sqrt(sum(value * value for value in values) / len(values)) if values else None


def p2p(values: list[float]) -> float | None:
    return max(values) - min(values) if values else None


def unwrap(values: list[float]) -> list[float]:
    if not values:
        return []
    result = [values[0]]
    offset = 0.0
    for previous, current in zip(values, values[1:]):
        delta = current - previous
        if delta > math.pi:
            offset -= TWO_PI
        elif delta < -math.pi:
            offset += TWO_PI
        result.append(current + offset)
    return result


def window_indices(times_ps: list[float], window: tuple[float, float]) -> list[int]:
    start, end = window
    return [index for index, time_ps in enumerate(times_ps) if start <= time_ps < end]


def trapezoid(times_ps: list[float], values: list[float]) -> float:
    if len(times_ps) < 2:
        return 0.0
    return sum((times_ps[index + 1] - times_ps[index]) * 1.0e-12 * (values[index] + values[index + 1]) * 0.5 for index in range(len(values) - 1))


def threshold_crossings(times_ps: list[float], values: list[float], threshold_turns: float) -> list[float]:
    if not values:
        return []
    origin = values[0]
    previous = abs((values[0] - origin) / TWO_PI) >= threshold_turns
    crossings: list[float] = []
    for time_ps, value in zip(times_ps[1:], values[1:]):
        current = abs((value - origin) / TWO_PI) >= threshold_turns
        if current and not previous:
            crossings.append(time_ps)
        previous = current
    return crossings


def activity_clusters(times_ps: list[float], values: list[float]) -> dict[str, Any]:
    """Describe voltage activity; this is not an event counter."""
    if not values:
        return {"threshold_v": None, "clusters": [], "first_activity_ps": None, "peak_v": None}
    peak = max(abs(value) for value in values)
    threshold = 0.20 * peak
    active = [abs(value) >= threshold for value in values]
    clusters: list[dict[str, Any]] = []
    start: int | None = None
    for index, is_active in enumerate(active + [False]):
        if is_active and start is None:
            start = index
        elif not is_active and start is not None:
            stop = index - 1
            segment = values[start:stop + 1]
            peak_index = max(range(start, stop + 1), key=lambda item: abs(values[item]))
            clusters.append({"start_ps": times_ps[start], "end_ps": times_ps[stop], "peak_ps": times_ps[peak_index], "peak_v": values[peak_index], "sample_count": len(segment)})
            start = None
    return {"threshold_v": threshold, "clusters": clusters, "first_activity_ps": clusters[0]["start_ps"] if clusters else None, "peak_v": max(values, key=abs) if values else None, "definition": "contiguous samples with |V| >= 0.20*max(|V|); descriptive activity only"}


def load_raw(path: Path) -> tuple[list[str], list[list[float]]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        headers = next(reader)
        rows = [[float(value) for value in row] for row in reader if row]
    return headers, rows


def column(headers: list[str], rows: list[list[float]], name: str) -> list[float] | None:
    try:
        index = headers.index(name)
    except ValueError:
        return None
    return [row[index] for row in rows]


def signal_metric(headers: list[str], rows: list[list[float]], times_ps: list[float], name: str, window_name: str) -> dict[str, Any]:
    values = column(headers, rows, name)
    if values is None:
        return {"signal": name, "window": window_name, "status": "NOT_EMITTED"}
    indices = window_indices(times_ps, WINDOWS[window_name])
    ts = [times_ps[index] for index in indices]
    selected = [values[index] for index in indices]
    metric: dict[str, Any] = {"signal": name, "window": window_name, "status": "PRESENT", "sample_count": len(selected), "time_start_ps": ts[0] if ts else None, "time_end_ps": ts[-1] if ts else None, "value_start": selected[0] if selected else None, "value_end": selected[-1] if selected else None, "min": min(selected) if selected else None, "max": max(selected) if selected else None, "mean": mean(selected), "rms": rms(selected), "p2p": p2p(selected), "integral_si": trapezoid(ts, selected)}
    if name.startswith("P("):
        unwrapped = unwrap(selected)
        metric.update({"phase_raw_start_rad": selected[0] if selected else None, "phase_raw_end_rad": selected[-1] if selected else None, "phase_unwrapped_start_rad": unwrapped[0] if unwrapped else None, "phase_unwrapped_end_rad": unwrapped[-1] if unwrapped else None, "phase_delta_rad": (unwrapped[-1] - unwrapped[0]) if len(unwrapped) >= 2 else None, "phase_delta_turns": (unwrapped[-1] - unwrapped[0]) / TWO_PI if len(unwrapped) >= 2 else None, "phase_p2p_turns": (max(unwrapped) - min(unwrapped)) / TWO_PI if unwrapped else None, "voltage_area_turns": None})
    if name.startswith("V("):
        metric["voltage_area_turns"] = metric["integral_si"] / PHI0
    return metric


def phase_voltage_crosscheck(headers: list[str], rows: list[list[float]], times_ps: list[float], prefix: str, window_name: str) -> dict[str, Any]:
    phase = signal_metric(headers, rows, times_ps, f"P({prefix})", window_name)
    voltage = signal_metric(headers, rows, times_ps, f"V({prefix})", window_name)
    return {"phase": phase, "voltage": voltage, "same_jj_mapping": True, "signed_residual_turns": (phase.get("phase_delta_turns") - voltage.get("voltage_area_turns")) if phase.get("phase_delta_turns") is not None and voltage.get("voltage_area_turns") is not None else None}


def r_loop_metric(headers: list[str], rows: list[list[float]], times_ps: list[float], prefix: str) -> dict[str, Any]:
    phase_name = f"P({prefix})"
    voltage_name = f"V({prefix})"
    current_name = f"I({prefix})"
    phase = column(headers, rows, phase_name)
    voltage = column(headers, rows, voltage_name)
    current = column(headers, rows, current_name)
    indices = window_indices(times_ps, WINDOWS[R_WINDOW])
    ts = [times_ps[index] for index in indices]
    p_values = [phase[index] for index in indices] if phase is not None else []
    v_values = [voltage[index] for index in indices] if voltage is not None else []
    i_values = [current[index] for index in indices] if current is not None else []
    unwrapped = unwrap(p_values)
    crossings = {str(threshold): threshold_crossings(ts, unwrapped, threshold) for threshold in (0.5, 1.0, 1.5, 2.0)}
    activity = activity_clusters(ts, v_values)
    return {"junction": prefix, "window": R_WINDOW, "phase_at_110_rad": p_values[0] if p_values else None, "phase_at_121_rad": p_values[-1] if p_values else None, "net_turns_110_121": (unwrapped[-1] - unwrapped[0]) / TWO_PI if len(unwrapped) >= 2 else None, "p2p_turns_110_121": (max(unwrapped) - min(unwrapped)) / TWO_PI if unwrapped else None, "navigation_crossings": crossings, "voltage": {"min_v": min(v_values) if v_values else None, "max_v": max(v_values) if v_values else None, "rms_v": rms(v_values), "area_turns": trapezoid(ts, v_values) / PHI0}, "current": {"min_a": min(i_values) if i_values else None, "max_a": max(i_values) if i_values else None, "rms_a": rms(i_values)}, "activity": activity, "same_jj_voltage_area": phase_voltage_crosscheck(headers, rows, times_ps, prefix, R_WINDOW), "post_first_activity_settling_ps": (WINDOWS[R_RECOVERY][1] - activity["clusters"][0]["end_ps"]) if activity.get("clusters") else None, "second_large_progression": len(activity.get("clusters", [])) >= 2, "mechanical_label": "AMBIGUOUS", "label_reason": "No scientific one-shot classifier or fixed acceptance threshold is frozen; raw navigation/activity metrics are reported for human review."}


def bvm_state_metrics(headers: list[str], rows: list[list[float]], times_ps: list[float], index: int) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for junction in ("B_JM1", "B_JM2"):
        prefix = f"{junction}|XBVM{index}"
        result[junction] = {}
        for window in STATE_WINDOWS:
            phase = signal_metric(headers, rows, times_ps, f"P({prefix})", window)
            phase["voltage_metric"] = signal_metric(headers, rows, times_ps, f"V({prefix})", window)
            phase["current_metric"] = signal_metric(headers, rows, times_ps, f"I({prefix})", window)
            result[junction][window] = phase
        result[junction]["voltage_area_crosschecks"] = {window: phase_voltage_crosscheck(headers, rows, times_ps, prefix, window) for window in STATE_WINDOWS}
    for branch in ("L_M1", "L_M2", "L_M3", "L_PM"):
        prefix = f"{branch}|XBVM{index}"
        result[branch] = {window: {"current": signal_metric(headers, rows, times_ps, f"I({prefix})", window), "voltage": signal_metric(headers, rows, times_ps, f"V({prefix})", window)} for window in STATE_WINDOWS}
    return result


def population_metric(headers: list[str], rows: list[list[float]], times_ps: list[float]) -> dict[str, Any]:
    name = "I(B_JSL8)"
    values = column(headers, rows, name)
    if values is None:
        return {"signal": name, "status": "NOT_EMITTED"}
    indices = window_indices(times_ps, WINDOWS[R_WINDOW])
    ts = [times_ps[index] for index in indices]
    selected = [values[index] for index in indices]
    positive = [value for value in selected if value > 0.0]
    negative = [value for value in selected if value < 0.0]
    crossings = sum(1 for left, right in zip(selected, selected[1:]) if (left <= 0 < right) or (left >= 0 > right))
    return {"signal": name, "status": "PRESENT", "window": R_WINDOW, "peak_positive_a": max(positive) if positive else 0.0, "peak_negative_a": min(negative) if negative else 0.0, "signed_area_wb": trapezoid(ts, selected), "signed_area_phi0": trapezoid(ts, selected) / PHI0, "absolute_area_wb": trapezoid(ts, [abs(value) for value in selected]), "absolute_area_phi0": trapezoid(ts, [abs(value) for value in selected]) / PHI0, "rms_a": rms(selected), "positive_support_ps": sum(0.1 for value in selected if value > 0.0), "negative_support_ps": sum(0.1 for value in selected if value < 0.0), "major_positive_lobe_time_ps": ts[positive.index(max(positive))] if positive else None, "major_negative_lobe_time_ps": ts[negative.index(min(negative))] if negative else None, "zero_crossings": crossings}


def raw_qa(raw_record: dict[str, Any], raw_path: Path, headers: list[str], rows: list[list[float]]) -> dict[str, Any]:
    reasons: list[str] = []
    if not raw_path.is_file() or raw_path.stat().st_size == 0:
        reasons.append("raw missing or empty")
    if len(headers) < 2:
        reasons.append("raw header has fewer than two columns")
    if len(rows) != 1999:
        reasons.append(f"expected 1999 samples for JoSIM grid 0..199.9 ps at 0.1 ps, got {len(rows)}")
    times = [row[0] * 1.0e12 for row in rows] if rows else []
    if times and (abs(times[0]) > 1.0e-9 or abs(times[-1] - 199.9) > 1.0e-6):
        reasons.append(f"unexpected time grid endpoints {times[0]}..{times[-1]} ps")
    if any(right <= left for left, right in zip(times, times[1:])):
        reasons.append("time grid is not strictly increasing")
    expected_hash = raw_record.get("raw", {}).get("sha256")
    if expected_hash and expected_hash != sha256(raw_path):
        reasons.append("raw hash differs from metadata")
    return {"status": "PASS" if not reasons else "FAIL", "path": repo_rel(raw_path), "sha256": sha256(raw_path) if raw_path.is_file() else None, "sample_count": len(rows), "column_count": len(headers), "reasons": reasons}


def write_case_summary(case_root: Path, params: dict[str, Any], run_summaries: list[dict[str, Any]], population: list[dict[str, Any]], monotonicity: dict[str, Any]) -> None:
    lines = [f"# {params['CASE_ID']} review summary", "", "No scientific interpretation performed.", "", "## CASE", "", f"- Parameters: JS1_AREA={params['JS1_AREA']}, JS2_AREA={params['JS2_AREA']}, RSH_JS1={params['RSH_JS1']}, RSH_JS2={params['RSH_JS2']}", f"- Mode: {params['MODE']}", f"- Masks: {', '.join(params['MASKS'])}", "- Phase output: raw radians; turns are navigation only.", "", "## S-LOOP", "", "| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |", "|---|---:|---:|---:|---:|---:|---|"]
    for item in run_summaries:
        mask = item["mask"]
        for bvm in item["active_bvms"] or [1]:
            jm1 = item["state"][str(bvm)]["B_JM1"]
            lines.append(f"| {mask} | BVM{bvm} | {jm1['write0_50_61'].get('phase_delta_turns')} | {jm1['zero_read_control_70_81'].get('phase_delta_turns')} | {jm1['write1_90_101'].get('phase_delta_turns')} | {jm1['settle_101_110'].get('phase_delta_turns')} | REVIEW_REQUIRED |" )
    lines.extend(["", "WRITE0 state: reported by windowed JM1/JM2 phase and LM1/LM2/LM3/LPM I/V metrics.", "CONTROL retention: reported; no fixed percentage threshold applied.", "WRITE1 transition: reported; no functional-family classifier applied.", "PRE-READ state: reported for 101–110 ps.", "POST-READ state: reported for recovery and tail windows.", "TAIL state: reported for 150–200 ps.", "Gate-S: REVIEW_REQUIRED", "", "## R-LOOP", "", "| mask | BVM | JS1 110→121 turns | JS1 p2p turns | JS2 110→121 turns | JS2 p2p turns | label |", "|---|---:|---:|---:|---:|---:|---|"])
    for item in run_summaries:
        for bvm in item["active_bvms"] or [1]:
            js1 = item["r_loop"][str(bvm)]["B_JS1"]
            js2 = item["r_loop"][str(bvm)]["B_JS2"]
            lines.append(f"| {item['mask']} | BVM{bvm} | {js1['net_turns_110_121']} | {js1['p2p_turns_110_121']} | {js2['net_turns_110_121']} | {js2['p2p_turns_110_121']} | AMBIGUOUS |")
    lines.extend(["", "JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.", "JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.", "LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.", "settling: descriptive post-first-activity timing only.", "Gate-R: AMBIGUOUS", "", "## OUTPUT", "", "| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |", "|---|---:|---:|---:|---:|---:|"])
    for item in population:
        lines.append(f"| {item['mask']} | {item['metrics'].get('peak_positive_a')} | {item['metrics'].get('peak_negative_a')} | {item['metrics'].get('signed_area_phi0')} | {item['metrics'].get('absolute_area_phi0')} | {item['metrics'].get('zero_crossings')} |")
    lines.extend(["", f"population monotonicity (mechanical nondecreasing check): {json.dumps(monotonicity, ensure_ascii=False, sort_keys=True)}", "No strict 1:2:3:4 requirement or automatic verdict.", "", "No scientific interpretation performed.", ""])
    (case_root / "REVIEW_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")


def analyze_case(case_root: Path) -> dict[str, Any]:
    case_manifest = read_json(case_root / "case_manifest.json")
    params = case_manifest["parameters"]
    run_summaries: list[dict[str, Any]] = []
    qa_rows: list[dict[str, Any]] = []
    window_rows: list[dict[str, Any]] = []
    population_rows: list[dict[str, Any]] = []
    for run_id in case_manifest["run_order"]:
        run_dir = case_root / "cases" / run_id
        metadata = read_json(run_dir / "metadata.json")
        raw_path = run_dir / "raw.csv"
        headers, rows = load_raw(raw_path)
        times_ps = [row[0] * 1.0e12 for row in rows]
        qa = raw_qa(metadata, raw_path, headers, rows)
        qa_rows.append({"run_id": run_id, **qa})
        state = {str(index): bvm_state_metrics(headers, rows, times_ps, index) for index in range(1, 5)}
        r_loop = {str(index): {"B_JS1": r_loop_metric(headers, rows, times_ps, f"B_JS1|XBVM{index}"), "B_JS2": r_loop_metric(headers, rows, times_ps, f"B_JS2|XBVM{index}")} for index in range(1, 5)}
        for index in range(1, 5):
            for signal in (f"P(B_JM1|XBVM{index})", f"V(B_JM1|XBVM{index})", f"I(B_JM1|XBVM{index})", f"P(B_JM2|XBVM{index})", f"V(B_JM2|XBVM{index})", f"I(B_JM2|XBVM{index})", f"P(B_JS1|XBVM{index})", f"V(B_JS1|XBVM{index})", f"I(B_JS1|XBVM{index})", f"P(B_JS2|XBVM{index})", f"V(B_JS2|XBVM{index})", f"I(B_JS2|XBVM{index})", f"I(L_S1|XBVM{index})", f"V(L_S1|XBVM{index})", f"I(L_S2|XBVM{index})", f"V(L_S2|XBVM{index})", f"I(L_S3|XBVM{index})", f"V(L_S3|XBVM{index})", f"I(R_S|XBVM{index})", f"V(R_S|XBVM{index})", f"I(L_M1|XBVM{index})", f"V(L_M1|XBVM{index})", f"I(L_M2|XBVM{index})", f"V(L_M2|XBVM{index})", f"I(L_M3|XBVM{index})", f"V(L_M3|XBVM{index})", f"I(L_PM|XBVM{index})", f"V(L_PM|XBVM{index})"):
                for window_name in WINDOWS:
                    metric = signal_metric(headers, rows, times_ps, signal, window_name)
                    window_rows.append({"run_id": run_id, "mask": metadata["mask"], "bvm": index, **metric})
        population_rows.append({"run_id": run_id, "mask": metadata["mask"], "metrics": population_metric(headers, rows, times_ps)})
        run_summaries.append({"run_id": run_id, "mask": metadata["mask"], "active_bvms": [index for index in range(1, 5) if metadata["mask"][index - 1] == "1"], "state": state, "r_loop": r_loop, "population": population_rows[-1]["metrics"], "qa": qa})
    monotonicity = population_monotonicity(population_rows)
    write_case_summary(case_root, params, run_summaries, population_rows, monotonicity)
    return {"case_id": params["CASE_ID"], "parameters": params, "run_order": case_manifest["run_order"], "runs": run_summaries, "population": population_rows, "population_monotonicity": monotonicity, "window_rows": window_rows, "qa": qa_rows, "status": "PASS" if all(row["status"] == "PASS" for row in qa_rows) else "FAIL"}


def population_monotonicity(population_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_mask = {item["mask"]: item["metrics"] for item in population_rows}
    ordered = [by_mask[mask] for mask in MASK_ORDER if mask in by_mask]
    checks: dict[str, Any] = {}
    for field in ("peak_positive_a", "signed_area_phi0", "absolute_area_phi0"):
        values = [row.get(field) for row in ordered]
        checks[field] = {"masks": [mask for mask in MASK_ORDER if mask in by_mask], "values": values, "nondecreasing": all(left <= right for left, right in zip(values, values[1:])) if values else None}
    return checks


def difference(candidate: dict[str, Any], reference: dict[str, Any], key: str) -> float | None:
    left, right = candidate.get(key), reference.get(key)
    return left - right if isinstance(left, (int, float)) and isinstance(right, (int, float)) else None


def gate_s_comparison(results: list[dict[str, Any]]) -> dict[str, Any]:
    reference = next((item for item in results if item["case_id"] == "A000_CANONICAL"), None)
    if reference is None:
        return {"status": "REFERENCE_NOT_AVAILABLE", "reference_case": "A000_CANONICAL", "cases": []}
    reference_runs = {run["mask"]: run for run in reference["runs"]}
    comparisons = []
    for candidate in results:
        if candidate["case_id"] == "A000_CANONICAL":
            continue
        rows = []
        for run in candidate["runs"]:
            ref_run = reference_runs.get(run["mask"])
            if ref_run is None:
                continue
            bvm_rows = []
            for bvm in range(1, 5):
                state_diffs: dict[str, Any] = {}
                for junction in ("B_JM1", "B_JM2"):
                    state_diffs[junction] = {}
                    for window in STATE_WINDOWS:
                        c = run["state"][str(bvm)][junction].get(window, {})
                        r = ref_run["state"][str(bvm)][junction].get(window, {})
                        state_diffs[junction][window] = {"phase_delta_turns_diff": difference(c, r, "phase_delta_turns"), "phase_end_rad_diff": difference(c, r, "phase_raw_end_rad"), "voltage_rms_diff": difference(c.get("voltage_metric", {}), r.get("voltage_metric", {}), "rms"), "current_rms_diff": difference(c.get("current_metric", {}), r.get("current_metric", {}), "rms"), "voltage_area_turns_diff": difference(c.get("voltage_metric", {}), r.get("voltage_metric", {}), "voltage_area_turns")}
                for branch in ("L_M1", "L_M2", "L_M3", "L_PM"):
                    state_diffs[branch] = {}
                    for window in STATE_WINDOWS:
                        c = run["state"][str(bvm)][branch].get(window, {})
                        r = ref_run["state"][str(bvm)][branch].get(window, {})
                        state_diffs[branch][window] = {"current_end_diff": difference(c.get("current", {}), r.get("current", {}), "value_end"), "voltage_rms_diff": difference(c.get("voltage", {}), r.get("voltage", {}), "rms"), "current_rms_diff": difference(c.get("current", {}), r.get("current", {}), "rms")}
                bvm_rows.append({"bvm": bvm, "differences": state_diffs})
            rows.append({"mask": run["mask"], "bvm": bvm_rows})
        comparisons.append({"case_id": candidate["case_id"], "parameters": candidate["parameters"], "status": "REVIEW_REQUIRED", "runs": rows})
    return {"status": "REFERENCE_READY", "reference_case": "A000_CANONICAL", "comparison_semantics": "candidate minus A000 mechanical window arithmetic; no fixed threshold or Gate verdict", "cases": comparisons}


def write_window_csv(rows: list[dict[str, Any]], path: Path) -> None:
    fields = sorted({key for row in rows for key in row})
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze completed one-shot tuning case(s) without changing raw")
    parser.add_argument("--case", action="append", dest="case_ids")
    args = parser.parse_args()
    roots = [SERIES / "runs" / case_id for case_id in args.case_ids] if args.case_ids else sorted(path for path in (SERIES / "runs").iterdir() if path.is_dir() and (path / "case_manifest.json").is_file())
    if not roots:
        raise RuntimeError("no completed candidate case found")
    all_results = []
    all_window_rows: list[dict[str, Any]] = []
    all_population_rows: list[dict[str, Any]] = []
    all_qa_rows: list[dict[str, Any]] = []
    for root in roots:
        if not (root / "case_manifest.json").is_file():
            raise RuntimeError(f"case is not complete or has no manifest: {root}")
        result = analyze_case(root)
        all_results.append(result)
        for run in result["runs"]:
            all_qa_rows.append({"case_id": result["case_id"], "run_id": run["run_id"], **run["qa"]})
        for item in result["population"]:
            all_population_rows.append({"case_id": result["case_id"], "run_id": item["run_id"], "mask": item["mask"], **item["metrics"]})
        all_window_rows.extend({"case_id": result["case_id"], **item} for item in result["window_rows"])
    analysis_dir = SERIES / "analysis"
    gate_s = gate_s_comparison(all_results)
    write_json(analysis_dir / "case_metrics.json", {"schema": "bvm-rloop-one-shot-case-metrics-v1", "cases": all_results, "gate_s_comparison": gate_s, "scientific_interpretation_performed": False, "phase_semantics": "raw radians; rad/(2*pi) navigation only; not formal SFQ counts"})
    write_json(analysis_dir / "gate_s_comparison.json", gate_s)
    write_window_csv(all_window_rows, analysis_dir / "per_signal_window_metrics.csv")
    write_window_csv(all_population_rows, analysis_dir / "population_metrics.csv")
    raw_qa = {"schema": "bvm-rloop-one-shot-raw-qa-v1", "status": "PASS" if all(row["status"] == "PASS" for row in all_qa_rows) else "FAIL", "run_count": len(all_qa_rows), "rows": all_qa_rows, "raw_immutable": True}
    write_json(SERIES / "qa" / "raw_qa.json", raw_qa)
    analysis_manifest = {"schema": "bvm-rloop-one-shot-analysis-manifest-v1", "generated_at": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"), "case_count": len(all_results), "solve_count": len(all_qa_rows), "raw_qa": repo_rel(SERIES / "qa" / "raw_qa.json"), "case_metrics": repo_rel(analysis_dir / "case_metrics.json"), "gate_s_comparison": repo_rel(analysis_dir / "gate_s_comparison.json"), "window_metrics": repo_rel(analysis_dir / "per_signal_window_metrics.csv"), "population_metrics": repo_rel(analysis_dir / "population_metrics.csv"), "scientific_interpretation_performed": False, "automatic_follow_up": False}
    write_json(analysis_dir / "analysis_manifest.json", analysis_manifest)
    result_path = SERIES / "result.json"
    result = read_json(result_path) if result_path.is_file() else {}
    result.update({"status": "ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW", "artifact_status": "VALID" if raw_qa["status"] == "PASS" else "INVALID", "actual_physical_solve_count": len(all_qa_rows), "qa": {"status": raw_qa["status"], "raw_qa": repo_rel(SERIES / "qa" / "raw_qa.json")}, "analysis": {"status": "PASS" if raw_qa["status"] == "PASS" else "FAIL", "manifest": repo_rel(analysis_dir / "analysis_manifest.json")}, "scientific_interpretation_performed": False, "automatic_follow_up": False, "stop": {"final_marker": None}})
    write_json(result_path, result)
    print(json.dumps({"status": raw_qa["status"], "cases": [result["case_id"] for result in all_results], "physical_solve_count": len(all_qa_rows), "scientific_interpretation": "NOT_PERFORMED"}, ensure_ascii=False, indent=2))
    return 0 if raw_qa["status"] == "PASS" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
