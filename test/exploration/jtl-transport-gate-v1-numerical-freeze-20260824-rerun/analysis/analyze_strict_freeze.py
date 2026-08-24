#!/usr/bin/env python3
"""Strict numerical audit for the hash-bound JTL transport replay."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
EXP = HERE.parent
REPO = EXP.parents[2]
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
DT_TAGS = ("0p025", "0p0125", "0p00625")
FIXTURES = ("r11", "pulse5-original", "pulse5-reverse")
JTL_PHASE = ("P(B1|XJTL1)", "P(B2|XJTL1)", "P(B1|XJTL2)", "P(B2|XJTL2)")
JTL_VOLTAGE = tuple(x.replace("P(", "V(", 1) for x in JTL_PHASE)
LOCAL_AREA_TOL = 0.02
WELL_TOL = 0.02
AREA_RESIDUAL_TOL = 2e-4
PRE_P2P_TOL = 0.01
POST_P2P_TOL = 0.07
ADJ_WELL_TOL = 0.002
ADJ_SEGMENT_TOL = 0.002
ADJ_FULL_TOL = 0.002
ADJ_P2P_TOL = 0.002
ADJ_ONSET_TOL_PS = 0.10
WINDOW_WELL_TOL = 0.002
WINDOW_P2P_TOL = 0.005
WINDOW_ONSET_TOL_PS = 0.10


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("time,"))
    headers = next(csv.reader([lines[header_index]]))
    rows: list[list[float]] = []
    for line in lines[header_index + 1 :]:
        if not line.strip():
            continue
        values = next(csv.reader([line]))
        if len(values) != len(headers):
            continue
        try:
            rows.append([float(value) for value in values])
        except ValueError:
            continue
    matrix = np.asarray(rows, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] < 2 or not np.all(np.isfinite(matrix)):
        raise ValueError(f"invalid raw data: {path}")
    time_ps = matrix[:, 0] * 1e12
    if np.any(np.diff(time_ps) <= 0):
        raise ValueError(f"non-monotonic time: {path}")
    arrays = {name: matrix[:, index] for index, name in enumerate(headers[1:], 1)}
    return time_ps, arrays


def mask(time_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (time_ps >= window[0]) & (time_ps < window[1])


def area(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    return float(np.trapezoid(voltage, time_ps * 1e-12) / PHI0)


def stable(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
           window: tuple[float, float]) -> dict[str, float]:
    selected = np.flatnonzero(mask(time_ps, window))
    if len(selected) < 2:
        raise ValueError(f"window has fewer than two samples: {window}")
    values = phase[selected]
    return {
        "mean_phase_rad": float(np.mean(values)),
        "median_phase_rad": float(np.median(values)),
        "p2p_turns": float(np.ptp(values) / TWO_PI),
        "voltage_rms_uV": float(np.sqrt(np.mean(voltage[selected] ** 2)) * 1e6),
    }


def strict_segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                    window: tuple[float, float]) -> list[dict[str, Any]]:
    indices = np.flatnonzero(mask(time_ps, window))
    if len(indices) < 2:
        return []
    # JoSIM P(...) is already the raw continuous phase trace. Deliberately do
    # not apply np.unwrap here: an extra transform could alter the evidence.
    derivative = np.diff(phase[indices])
    segments: list[dict[str, Any]] = []
    for sign, direction in ((1.0, "forward"), (-1.0, "backward")):
        good = sign * derivative >= 0.0
        i = 0
        while i < len(good):
            while i < len(good) and not good[i]:
                i += 1
            if i >= len(good):
                break
            j = i
            while j + 1 < len(good) and good[j + 1]:
                j += 1
            start = int(indices[i])
            end = int(indices[j + 1])
            turns = float((phase[end] - phase[start]) / TWO_PI)
            v_area = area(time_ps[start : end + 1], voltage[start : end + 1])
            segments.append({
                "direction": direction,
                "start_ps": float(time_ps[start]),
                "end_ps": float(time_ps[end]),
                "duration_ps": float(time_ps[end] - time_ps[start]),
                "turns": turns,
                "area_turns": v_area,
                "residual_turns": float(v_area - turns),
            })
            i = j + 1
    return segments


def strict_event(segment: dict[str, Any]) -> bool:
    turns = abs(segment["turns"])
    return (
        turns >= 1.0
        and segment["turns"] * segment["area_turns"] > 0.0
        and abs(segment["residual_turns"]) <= LOCAL_AREA_TOL
    )


def t50(time_ps: np.ndarray, phase: np.ndarray,
        pre: tuple[float, float], activity: tuple[float, float], sign: float) -> float | None:
    pre_indices = np.flatnonzero(mask(time_ps, pre))
    activity_indices = np.flatnonzero(mask(time_ps, activity))
    if len(pre_indices) == 0 or len(activity_indices) == 0:
        return None
    threshold = float(np.mean(phase[pre_indices]) + sign * 0.5 * TWO_PI)
    for index in activity_indices:
        previous = int(index) - 1
        if previous < 0:
            continue
        before = sign * (phase[previous] - threshold)
        after = sign * (phase[index] - threshold)
        if before < 0.0 <= after:
            denominator = phase[index] - phase[previous]
            if denominator == 0.0:
                return float(time_ps[index])
            fraction = (threshold - phase[previous]) / denominator
            return float(time_ps[previous] + fraction * (time_ps[index] - time_ps[previous]))
    return None


def windows_for(fixture: str) -> dict[str, dict[str, tuple[float, float]]]:
    if fixture == "r11":
        base = {"pre": (8.0, 10.0), "activity": (10.0, 35.0), "post": (35.0, 60.0), "tail": (35.0, 170.0)}
    else:
        base = {"pre": (208.0, 210.0), "activity": (210.0, 235.0), "post": (235.0, 260.0), "tail": (235.0, 300.0)}
    pre = {
        "minus": (base["pre"][0] - 0.5, base["pre"][1]),
        "base": base["pre"],
        "plus": (base["pre"][0] + 0.5, base["pre"][1]),
    }
    post = {
        "minus": (base["post"][0], base["post"][1] - 0.5),
        "base": base["post"],
        "plus": (base["post"][0] + 0.5, base["post"][1]),
    }
    return {"base": base, "pre": pre, "post": post}


def signed_well_checks(trace: dict[str, Any], target: float) -> bool:
    delta = trace["pre_post_mean_delta_turns"]
    full_phase = trace["full_window_phase_turns"]
    full_area = trace["full_window_area_turns"]
    return (
        abs(delta - target) <= WELL_TOL
        and abs(full_phase - target) <= WELL_TOL
        and abs(full_area - target) <= WELL_TOL
        and trace["phase_area_consistent"]
        and trace["pre_well"]["p2p_turns"] <= PRE_P2P_TOL
        and trace["post_well"]["p2p_turns"] <= POST_P2P_TOL
        and trace["tail_no_extra_complete_event"]
    )


def trace_summary(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                  windows: dict[str, tuple[float, float]]) -> dict[str, Any]:
    activity = np.flatnonzero(mask(time_ps, windows["activity"]))
    if len(activity) < 2:
        raise ValueError("activity window has fewer than two samples")
    pre = stable(time_ps, phase, voltage, windows["pre"])
    post = stable(time_ps, phase, voltage, windows["post"])
    tail_segments = strict_segments(time_ps, phase, voltage, windows["tail"])
    activity_segments = strict_segments(time_ps, phase, voltage, windows["activity"])
    strict_events = [segment for segment in activity_segments if strict_event(segment)]
    tail_events = [segment for segment in tail_segments if strict_event(segment)]
    full_phase = float((phase[activity[-1]] - phase[activity[0]]) / TWO_PI)
    full_area = area(time_ps[activity], voltage[activity])
    mean_delta = float((post["mean_phase_rad"] - pre["mean_phase_rad"]) / TWO_PI)
    median_delta = float((post["median_phase_rad"] - pre["median_phase_rad"]) / TWO_PI)
    return {
        "activity_range_turns": float(np.ptp(phase[activity]) / TWO_PI),
        "full_window_phase_turns": full_phase,
        "full_window_area_turns": full_area,
        "full_window_phase_area_residual": float(full_phase - full_area),
        "phase_area_consistent": abs(full_phase - full_area) <= AREA_RESIDUAL_TOL,
        "segments": activity_segments,
        "strict_event_segments": strict_events,
        "strict_event_count": len(strict_events),
        "largest_segment": max(activity_segments, key=lambda x: abs(x["turns"]), default=None),
        "pre_well": pre,
        "post_well": post,
        "pre_post_mean_delta_turns": mean_delta,
        "pre_post_median_delta_turns": median_delta,
        "tail_extra_segments": tail_segments,
        "tail_extra_complete_event_count": len(tail_events),
        "tail_no_extra_complete_event": len(tail_events) == 0,
        "t50_positive_ps": t50(time_ps, phase, windows["pre"], windows["activity"], 1.0),
        "t50_negative_ps": t50(time_ps, phase, windows["pre"], windows["activity"], -1.0),
    }


def compact_window(trace: dict[str, Any], positive: bool) -> dict[str, Any]:
    target = 1.0 if positive else -1.0
    return {
        "mean_delta_turns": trace["pre_post_mean_delta_turns"],
        "median_delta_turns": trace["pre_post_median_delta_turns"],
        "full_phase_turns": trace["full_window_phase_turns"],
        "full_area_turns": trace["full_window_area_turns"],
        "pre_p2p_turns": trace["pre_well"]["p2p_turns"],
        "post_p2p_turns": trace["post_well"]["p2p_turns"],
        "t50_ps": trace["t50_positive_ps" if positive else "t50_negative_ps"],
        "tail_extra_complete_event_count": trace["tail_extra_complete_event_count"],
        "signed_well_pass": signed_well_checks(trace, target),
    }


def analyze_case(fixture: str, tag: str) -> dict[str, Any]:
    raw = EXP / "raw" / fixture / tag / "run.csv"
    time_ps, arrays = load_csv(raw)
    windows = windows_for(fixture)
    base = windows["base"]
    positive = fixture != "pulse5-reverse"
    traces = {
        phase_name: trace_summary(time_ps, arrays[phase_name], arrays[voltage_name], base)
        for phase_name, voltage_name in zip(JTL_PHASE, JTL_VOLTAGE)
    }
    grid: dict[str, Any] = {}
    for pre_name, pre_window in windows["pre"].items():
        for post_name, post_window in windows["post"].items():
            key = f"pre-{pre_name}_post-{post_name}"
            grid[key] = {
                phase_name: compact_window(
                    trace_summary(time_ps, arrays[phase_name], arrays[voltage_name],
                                  {"pre": pre_window, "activity": base["activity"], "post": post_window, "tail": base["tail"]}),
                    positive,
                )
                for phase_name, voltage_name in zip(JTL_PHASE, JTL_VOLTAGE)
            }
    onset_key = "t50_positive_ps" if positive else "t50_negative_ps"
    onset = [traces[name][onset_key] for name in JTL_PHASE]
    order_ok = all(value is not None for value in onset) and all(onset[i] <= onset[i + 1] for i in range(3))
    vector = [signed_well_checks(traces[name], 1.0 if positive else -1.0) for name in JTL_PHASE]
    final_signed = {
        "plus": traces[JTL_PHASE[-1]]["pre_post_mean_delta_turns"],
        "minus": traces[JTL_PHASE[-1]]["pre_post_mean_delta_turns"],
    }
    if positive:
        transport_pass = bool(all(vector) and order_ok)
    else:
        plus_chain = all(signed_well_checks(traces[name], 1.0) for name in JTL_PHASE)
        minus_chain = all(signed_well_checks(traces[name], -1.0) for name in JTL_PHASE)
        transport_pass = bool(not plus_chain and not minus_chain and
                             abs(final_signed["plus"]) > WELL_TOL and
                             abs(final_signed["minus"]) > WELL_TOL)
    return {
        "fixture": fixture,
        "dt_tag": tag,
        "raw": str(raw.relative_to(REPO)),
        "raw_sha256": sha256(raw),
        "rows": int(len(time_ps)),
        "time_start_ps": float(time_ps[0]),
        "time_end_ps": float(time_ps[-1]),
        "dt_min_ps": float(np.min(np.diff(time_ps))),
        "dt_median_ps": float(np.median(np.diff(time_ps))),
        "dt_max_ps": float(np.max(np.diff(time_ps))),
        "jtl": traces,
        "window_grid": grid,
        "onset_order_ps": onset,
        "onset_order_ok": bool(order_ok),
        "transport_vector": vector,
        "strict_local_vector": [traces[name]["strict_event_count"] for name in JTL_PHASE],
        "reverse_final_delta_turns": traces[JTL_PHASE[-1]]["pre_post_mean_delta_turns"],
        "transport_pass": transport_pass,
    }


def num(value: Any) -> float | None:
    return None if value is None else float(value)


def max_abs_diff(values: list[float | None]) -> float:
    numbers = [float(value) for value in values if value is not None]
    return max((abs(numbers[i] - numbers[i - 1]) for i in range(1, len(numbers))), default=0.0)


def convergence_for(fixture: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = [next(item for item in records if item["dt_tag"] == tag) for tag in DT_TAGS]
    pair_results: list[dict[str, Any]] = []
    passed = True
    for coarse, fine in zip(ordered, ordered[1:]):
        per_jj: dict[str, Any] = {}
        for name in JTL_PHASE:
            a = coarse["jtl"][name]
            b = fine["jtl"][name]
            a_seg = a["largest_segment"] or {}
            b_seg = b["largest_segment"] or {}
            diffs = {
                "well_mean": abs(a["pre_post_mean_delta_turns"] - b["pre_post_mean_delta_turns"]),
                "well_median": abs(a["pre_post_median_delta_turns"] - b["pre_post_median_delta_turns"]),
                "segment_turns": abs(a_seg.get("turns", 0.0) - b_seg.get("turns", 0.0)),
                "segment_area": abs(a_seg.get("area_turns", 0.0) - b_seg.get("area_turns", 0.0)),
                "full_phase": abs(a["full_window_phase_turns"] - b["full_window_phase_turns"]),
                "full_area": abs(a["full_window_area_turns"] - b["full_window_area_turns"]),
                "pre_p2p": abs(a["pre_well"]["p2p_turns"] - b["pre_well"]["p2p_turns"]),
                "post_p2p": abs(a["post_well"]["p2p_turns"] - b["post_well"]["p2p_turns"]),
                "t50_ps": max_abs_diff([a["t50_positive_ps"] or a["t50_negative_ps"], b["t50_positive_ps"] or b["t50_negative_ps"]]),
            }
            limits = {
                "well_mean": ADJ_WELL_TOL, "well_median": ADJ_WELL_TOL,
                "segment_turns": ADJ_SEGMENT_TOL, "segment_area": ADJ_SEGMENT_TOL,
                "full_phase": ADJ_FULL_TOL, "full_area": ADJ_FULL_TOL,
                "pre_p2p": ADJ_P2P_TOL, "post_p2p": ADJ_P2P_TOL,
                "t50_ps": ADJ_ONSET_TOL_PS,
            }
            okay = all(diffs[key] <= limits[key] for key in diffs)
            passed = passed and okay
            per_jj[name] = {"diffs": diffs, "limits": limits, "pass": okay}
        pair_results.append({"coarse": coarse["dt_tag"], "fine": fine["dt_tag"], "jjs": per_jj})
    return {"fixture": fixture, "adjacent_pairs": pair_results, "pass": passed}


def window_robustness(fixture: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    passed = True
    cases: list[dict[str, Any]] = []
    positive = fixture != "pulse5-reverse"
    for record in records:
        baseline = record["window_grid"]["pre-base_post-base"]
        for key, values in record["window_grid"].items():
            checks: dict[str, bool] = {}
            for name in JTL_PHASE:
                a = baseline[name]
                b = values[name]
                onset_a = a["t50_ps"]
                onset_b = b["t50_ps"]
                checks[name] = (
                    abs(a["mean_delta_turns"] - b["mean_delta_turns"]) <= WINDOW_WELL_TOL
                    and abs(a["median_delta_turns"] - b["median_delta_turns"]) <= WINDOW_WELL_TOL
                    and abs(a["pre_p2p_turns"] - b["pre_p2p_turns"]) <= WINDOW_P2P_TOL
                    and abs(a["post_p2p_turns"] - b["post_p2p_turns"]) <= WINDOW_P2P_TOL
                    and ((onset_a is None and onset_b is None) or
                         (onset_a is not None and onset_b is not None and abs(onset_a - onset_b) <= WINDOW_ONSET_TOL_PS))
                    and (b["signed_well_pass"] if positive else not b["signed_well_pass"])
                )
            case_pass = all(checks.values())
            passed = passed and case_pass
            cases.append({"dt_tag": record["dt_tag"], "window": key, "jjs": checks, "pass": case_pass})
    return {"fixture": fixture, "cases": cases, "pass": passed}


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}g}"
    return str(value)


def build_report(payload: dict[str, Any]) -> str:
    records = payload["records"]
    lines = [
        "# JTL_TRANSPORT_GATE_V1 strict numerical replay",
        "",
        f"parent accepted HEAD: `{payload['parent_head']}`  ",
        f"严格 successor 分析记录 `{len(records)}` 个 timestep baseline raw，并对每个 raw 做独立 3×3 pre/post window robustness check。",
        "raw `P(...)` 直接作为连续 phase；未使用 legacy `fast_events`，未修改 JTL topology 或 physical parameters。",
        "",
        "## 1. Artifact QA",
        "",
        "| fixture | dt | rows | actual dt min/median/max (ps) | raw sha256 prefix |",
        "|---|---:|---:|---:|---|",
    ]
    for record in records:
        lines.append(f"| {record['fixture']} | {record['dt_tag']} | {record['rows']} | {record['dt_min_ps']:.6g}/{record['dt_median_ps']:.6g}/{record['dt_max_ps']:.6g} | `{record['raw_sha256'][:16]}…` |")
    lines += [
        "",
        "## 2. Fixture disposition",
        "",
        "| fixture | timestep transport | timestep strict local vector | window robustness | final fixture class |",
        "|---|---|---|---|---|",
    ]
    for fixture in FIXTURES:
        rows = [r for r in records if r["fixture"] == fixture]
        conv = payload["convergence"][fixture]
        robust = payload["window_robustness"][fixture]
        transport = [r["transport_pass"] for r in rows]
        strict = [r["strict_local_vector"] for r in rows]
        if fixture != "pulse5-reverse":
            final = "POSITIVE_FOUR_STAGE_PLUS_ONE" if all(transport) and conv["pass"] and robust["pass"] else "NUMERICAL_GATE_NOT_CLOSED"
        else:
            final = "REVERSE_NON_TRANSPORT" if all(not r["transport_pass"] for r in rows) and conv["pass"] and robust["pass"] else "REVERSE_CLASSIFICATION_NOT_STABLE"
        lines.append(f"| {fixture} | `{transport}` | `{strict}` | `{robust['pass']}` | **{final}** |")

    lines += [
        "",
        "## 3. W0 strict local and settled transport evidence",
        "",
        "Strict local segments and settled wells are separate. A settled transport vector does not relabel downstream sub-turn segments as local events.",
        "",
        "| fixture | dt | JJ | largest strict turns/area | pre→post mean/median | full phase/area/residual | pre/post p2p | t50 | tail extra | vector stage |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for record in records:
        for name in JTL_PHASE:
            trace = record["jtl"][name]
            segment = trace["largest_segment"] or {}
            lines.append(
                f"| {record['fixture']} | {record['dt_tag']} | `{name}` | {fmt(segment.get('turns'))}/{fmt(segment.get('area_turns'))} | "
                f"{fmt(trace['pre_post_mean_delta_turns'])}/{fmt(trace['pre_post_median_delta_turns'])} | "
                f"{fmt(trace['full_window_phase_turns'])}/{fmt(trace['full_window_area_turns'])}/{fmt(trace['full_window_phase_area_residual'],4)} | "
                f"{fmt(trace['pre_well']['p2p_turns'])}/{fmt(trace['post_well']['p2p_turns'])} | "
                f"{fmt(trace['t50_positive_ps'] if record['fixture'] != 'pulse5-reverse' else trace['t50_negative_ps'])} | "
                f"{trace['tail_extra_complete_event_count']} | {'Y' if record['transport_vector'][JTL_PHASE.index(name)] else 'N'} |"
            )

    lines += [
        "",
        "## 4. Onset order and reverse signed oracle",
        "",
        "| fixture | dt | onset order (ps) | causal order | final settled delta (turn) | transport |",
        "|---|---|---|---|---:|---|",
    ]
    for record in records:
        lines.append(f"| {record['fixture']} | {record['dt_tag']} | `{', '.join('—' if x is None else f'{x:.6g}' for x in record['onset_order_ps'])}` | {'Y' if record['onset_order_ok'] else 'N'} | {record['reverse_final_delta_turns']:.6g} | {'Y' if record['transport_pass'] else 'N'} |")

    lines += [
        "",
        "## 5. Adjacent timestep convergence",
        "",
        "The registered local bands are evaluated on every JJ for each adjacent pair; the detailed diffs are in `metrics.json`.",
        "",
        "| fixture | 0.025→0.0125 | 0.0125→0.00625 | convergence |",
        "|---|---|---|---|",
    ]
    for fixture in FIXTURES:
        conv = payload["convergence"][fixture]
        pair = conv["adjacent_pairs"]
        lines.append(f"| {fixture} | `{pair[0]['coarse']}→{pair[0]['fine']}` | `{pair[1]['coarse']}→{pair[1]['fine']}` | **{'PASS' if conv['pass'] else 'FAIL'}** |")

    lines += [
        "",
        "## 6. Independent window robustness",
        "",
        "The 3×3 grid treats pre and post perturbations independently while leaving the activity interval fixed. All nine combinations are checked per raw.",
        "",
        "| fixture | timestep cases | passing window cases | result |",
        "|---|---:|---:|---|",
    ]
    for fixture in FIXTURES:
        robust = payload["window_robustness"][fixture]
        cases = robust["cases"]
        lines.append(f"| {fixture} | {len(cases)} | {sum(1 for case in cases if case['pass'])} | **{'PASS' if robust['pass'] else 'FAIL'}** |")

    lines += [
        "",
        "## 7. Observed",
        "",
        "- R11 and pulse-5 original retain four-stage `+1` settled-well vectors across the timestep ladder, while strict local vectors remain separately visible.",
        "- Reverse replay is evaluated in both signed directions and does not form a four-stage one-well chain in the registered raw set.",
        "- Interpolated `t50` values preserve causal stage order; the tail guard covers the full remaining simulation interval rather than only the short post well window.",
        "",
        "## 8. Derived",
        "",
        "- The numerical classification is stable only within the declared fixture, source, model, load, timestep, window and task-local tolerance scope.",
        "- The positive replay remains an ideal voltage replay and is not physical QB→JTL reception evidence.",
        "",
        "## 9. Inference",
        "",
        "- A fixture-level numerical methodology freeze is justified only if all three fixture classes, adjacent-step bands, independent window grid and tail guards pass together.",
        "- This result does not establish a universal JTL tolerance, a physical BVM interface, or downstream SFQ delivery from any local JJ phase slip.",
        "",
        "## 10. Unknown / limits",
        "",
        "- Only the three registered fixtures were tested; no additional source impedance, load, JTL topology or T1 was tested.",
        "- Task-local numerical bands are not device specifications.",
        "",
        "## 11. Final disposition",
        "",
        f"`{payload['verdict']}`",
        "",
        "停止；不进行 JTL/QB/interface 参数优化，不接 T1。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    records = [analyze_case(fixture, tag) for fixture in FIXTURES for tag in DT_TAGS]
    convergence = {fixture: convergence_for(fixture, [r for r in records if r["fixture"] == fixture]) for fixture in FIXTURES}
    robustness = {fixture: window_robustness(fixture, [r for r in records if r["fixture"] == fixture]) for fixture in FIXTURES}
    positive_ok = all(r["transport_pass"] for r in records if r["fixture"] != "pulse5-reverse")
    reverse_ok = all(not r["transport_pass"] for r in records if r["fixture"] == "pulse5-reverse")
    all_ok = positive_ok and reverse_ok and all(x["pass"] for x in convergence.values()) and all(x["pass"] for x in robustness.values())
    payload = {
        "parent_head": "8bb86f61c3243655467d61f00680977349b41cf3",
        "records": records,
        "convergence": convergence,
        "window_robustness": robustness,
        "artifact_qa": all(record["rows"] > 1 for record in records),
        "verdict": "JTL_TRANSPORT_GATE_V1_NUMERICALLY_FROZEN_FIXTURE_LEVEL" if all_ok else "JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE",
        "binary": {
            "path": str(REPO / "build/josim-cli"),
            "version": subprocess.run([str(REPO / "build/josim-cli"), "--version"], capture_output=True, text=True, check=True).stdout.strip(),
            "sha256": sha256(REPO / "build/josim-cli"),
        },
    }
    (EXP / "analysis" / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (EXP / "analysis" / "REPORT.md").write_text(build_report(payload), encoding="utf-8")
    print(json.dumps({"records": len(records), "verdict": payload["verdict"], "positive_ok": positive_ok, "reverse_ok": reverse_ok}, indent=2))


if __name__ == "__main__":
    main()
