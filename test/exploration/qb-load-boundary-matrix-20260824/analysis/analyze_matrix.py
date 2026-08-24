#!/usr/bin/env python3
"""Audit the Q0/Q5 output-load boundary matrix from raw JoSIM traces.

The parser intentionally finds JoSIM's data header instead of treating the
progress bar as CSV.  Event evidence is limited to same-JJ, same-monotonic-
segment phase and direct voltage-area agreement; no legacy fast-event counter
is used.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/qb-load-boundary-matrix-20260824"
RAW = EXP / "raw-v2"
ANALYSIS = EXP / "analysis"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi

Q0_PULSE_STARTS = [10.0, 60.0, 110.0, 160.0, 210.0, 260.0]
Q0_ACTIVITY = 25.0
Q0_POST = 24.0
Q5_WINDOWS = {"pre": (85.0, 94.0), "activity": (94.0, 130.0), "post": (130.0, 165.0)}

QB_JJS = ("BJs", "BJL1", "BJL2")
JTL_JJS = ("B1|XJTL1", "B2|XJTL1", "B1|XJTL2", "B2|XJTL2")
QB_COLUMNS = {
    "BJs": ("P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}

FIXTURES = {
    "A-q0-open": {"kind": "q0", "files": ["scaled-iin-68p4u.csv"]},
    "B-q0-jtl-only": {"kind": "q0-jtl", "files": ["scaled-iin-68p4u.csv"]},
    "C-q0-10ohm-parallel-jtl": {"kind": "q0-jtl", "files": ["scaled-iin-68p4u.csv"]},
    "D-q5-open": {
        "kind": "q5",
        "files": [
            "paper-j0-logical0-read.csv",
            "paper-j0-logical0-read0-control.csv",
            "paper-j1-logical1-read.csv",
            "paper-j1-logical1-read0-control.csv",
        ],
    },
    "E-q5-jtl-only": {
        "kind": "q5-jtl",
        "files": [
            "paper-j0-logical0-read.csv",
            "paper-j0-logical0-read0-control.csv",
            "paper-j1-logical1-read.csv",
            "paper-j1-logical1-read0-control.csv",
        ],
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_raw(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray], list[str]]:
    """Read JoSIM fixed-width output after its progress text."""
    lines = path.read_text().splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.startswith("time ")), None)
    if header_index is None:
        raise ValueError(f"missing JoSIM data header: {path}")
    names = [token.strip('"') for token in lines[header_index].split()]
    rows: list[list[float]] = []
    for line in lines[header_index + 1 :]:
        values = line.split()
        if len(values) != len(names):
            continue
        try:
            rows.append([float(value) for value in values])
        except ValueError:
            continue
    if len(rows) < 2:
        raise ValueError(f"too few numeric rows: {path}")
    matrix = np.asarray(rows, dtype=float)
    # A repeated probe can produce a repeated header name.  JoSIM's last value
    # is retained, matching ordinary DictReader behavior; the repeated probe
    # is the same physical branch and is not a scientific variable here.
    arrays = {name: matrix[:, index] for index, name in enumerate(names)}
    time_ps = arrays.pop("time") * 1e12
    if not np.all(np.isfinite(time_ps)) or not np.all(np.diff(time_ps) > 0):
        raise ValueError(f"invalid/non-monotonic time axis: {path}")
    if any(not np.all(np.isfinite(values)) for values in arrays.values()):
        raise ValueError(f"non-finite output: {path}")
    return time_ps, arrays, names


def integrate_phi0(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    if hasattr(np, "trapezoid"):
        integral = np.trapezoid(voltage, time_ps * 1e-12)
    else:
        integral = np.trapz(voltage, time_ps * 1e-12)
    return float(integral / PHI0)


def stats(values: np.ndarray, scale: float = 1.0) -> dict[str, float]:
    values = np.asarray(values, dtype=float) * scale
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "p2p": float(np.ptp(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
    }


def monotonic_segments(
    time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, active: np.ndarray
) -> list[dict[str, Any]]:
    """Return sign-consistent raw-phase runs, preserving their direct area."""
    indices = np.flatnonzero(active)
    if indices.size < 2:
        return []
    selected_phase = phase[indices]
    delta = np.diff(selected_phase)
    records: list[dict[str, Any]] = []
    for sign, direction in ((1.0, "positive"), (-1.0, "negative")):
        good = sign * delta >= 0.0
        cursor = 0
        while cursor < good.size:
            while cursor < good.size and not good[cursor]:
                cursor += 1
            if cursor >= good.size:
                break
            end_cursor = cursor
            while end_cursor + 1 < good.size and good[end_cursor + 1]:
                end_cursor += 1
            left = int(indices[cursor])
            right = int(indices[end_cursor + 1])
            delta_turns = float((phase[right] - phase[left]) / TWO_PI)
            area_turns = integrate_phi0(time_ps[left : right + 1], voltage[left : right + 1])
            residual = float(area_turns - delta_turns)
            records.append(
                {
                    "direction": direction,
                    "start_ps": float(time_ps[left]),
                    "end_ps": float(time_ps[right]),
                    "duration_ps": float(time_ps[right] - time_ps[left]),
                    "delta_turns": delta_turns,
                    "magnitude_turns": abs(delta_turns),
                    "area_turns": float(area_turns),
                    "area_residual_turns": residual,
                    "area_tolerance_turns": float(max(0.02, 0.05 * abs(delta_turns))),
                }
            )
            cursor = end_cursor + 1
    return records


def qualifies(segment: dict[str, Any]) -> bool:
    magnitude = abs(float(segment["delta_turns"]))
    area = float(segment["area_turns"])
    residual = abs(float(segment["area_residual_turns"]))
    return (
        magnitude >= 1.0
        and area * float(segment["delta_turns"]) > 0.0
        and residual <= max(0.02, 0.05 * magnitude)
    )


def largest(records: list[dict[str, Any]], direction: str | None = None) -> dict[str, Any] | None:
    selected = records if direction is None else [r for r in records if r["direction"] == direction]
    return max(selected, key=lambda item: item["magnitude_turns"], default=None)


def phase_window(
    time_ps: np.ndarray,
    arrays: dict[str, np.ndarray],
    phase_name: str,
    voltage_name: str,
    current_name: str,
    window: tuple[float, float],
) -> dict[str, Any]:
    active = (time_ps >= window[0]) & (time_ps < window[1])
    indices = np.flatnonzero(active)
    phase = np.unwrap(arrays[phase_name])
    records = monotonic_segments(time_ps, phase, arrays[voltage_name], active)
    post_records = []
    qualifying_records = [r for r in records if qualifies(r)]
    phase_selected = phase[active]
    largest_record = largest(records)
    return {
        "window_ps": [float(window[0]), float(window[1])],
        "phase_range_turns": float(np.ptp(phase_selected) / TWO_PI),
        "window_delta_turns": float((phase[indices[-1]] - phase[indices[0]]) / TWO_PI),
        "segments": records,
        "largest_segment": largest_record,
        "largest_positive_segment": largest(records, "positive"),
        "largest_negative_segment": largest(records, "negative"),
        "complete_event_count": int(sum(qualifies(r) for r in records)),
        "complete_event_units": int(sum(math.floor(abs(r["delta_turns"])) for r in qualifying_records)),
        "current_uA": stats(arrays[current_name][active], 1e6),
        "voltage_V": stats(arrays[voltage_name][active]),
        "phase_unwrapped_start_turn": float(phase[indices[0]] / TWO_PI),
        "phase_unwrapped_end_turn": float(phase[indices[-1]] / TWO_PI),
    }


def post_window(
    time_ps: np.ndarray,
    arrays: dict[str, np.ndarray],
    phase_name: str,
    voltage_name: str,
    current_name: str,
    window: tuple[float, float],
) -> dict[str, Any]:
    metric = phase_window(time_ps, arrays, phase_name, voltage_name, current_name, window)
    metric["post_complete_event_count"] = metric["complete_event_count"]
    return metric


def q0_pulse_metric(
    time_ps: np.ndarray,
    arrays: dict[str, np.ndarray],
    phase_name: str,
    voltage_name: str,
    current_name: str,
) -> dict[str, Any]:
    pulses: list[dict[str, Any]] = []
    for start in Q0_PULSE_STARTS:
        activity = phase_window(time_ps, arrays, phase_name, voltage_name, current_name, (start, start + Q0_ACTIVITY))
        post = post_window(time_ps, arrays, phase_name, voltage_name, current_name, (start + Q0_ACTIVITY, start + Q0_ACTIVITY + Q0_POST))
        activity["pulse_start_ps"] = start
        post["pulse_start_ps"] = start
        pulses.append({"activity": activity, "post": post})
    activity_records = [s for pulse in pulses for s in pulse["activity"]["segments"]]
    post_records = [s for pulse in pulses for s in pulse["post"]["segments"]]
    return {
        "pulses": pulses,
        "activity_complete_event_count": int(sum(p["activity"]["complete_event_count"] for p in pulses)),
        "activity_complete_event_units": int(sum(p["activity"]["complete_event_units"] for p in pulses)),
        "post_complete_event_count": int(sum(p["post"]["complete_event_count"] for p in pulses)),
        "largest_activity_segment": largest(activity_records),
        "largest_positive_activity_segment": largest(activity_records, "positive"),
        "largest_negative_activity_segment": largest(activity_records, "negative"),
        "largest_post_segment": largest(post_records),
        "activity_range_max_turns": float(max(p["activity"]["phase_range_turns"] for p in pulses)),
        "current_activity_uA_min": float(min(p["activity"]["current_uA"]["min"] for p in pulses)),
        "current_activity_uA_max": float(max(p["activity"]["current_uA"]["max"] for p in pulses)),
    }


def fixed_metric(
    time_ps: np.ndarray,
    arrays: dict[str, np.ndarray],
    phase_name: str,
    voltage_name: str,
    current_name: str,
    kind: str,
) -> dict[str, Any]:
    phase = np.unwrap(arrays[phase_name])
    if kind.startswith("q0"):
        return q0_pulse_metric(time_ps, arrays, phase_name, voltage_name, current_name)
    activity = phase_window(time_ps, arrays, phase_name, voltage_name, current_name, Q5_WINDOWS["activity"])
    post = post_window(time_ps, arrays, phase_name, voltage_name, current_name, Q5_WINDOWS["post"])
    pre = phase_window(time_ps, arrays, phase_name, voltage_name, current_name, Q5_WINDOWS["pre"])
    return {
        "pre": pre,
        "activity": activity,
        "post": post,
        "post_phase_p2p_turns": post["phase_range_turns"],
        "activity_complete_event_count": activity["complete_event_count"],
        "activity_complete_event_units": activity["complete_event_units"],
        "post_complete_event_count": post["complete_event_count"],
        "largest_activity_segment": activity["largest_segment"],
        "largest_positive_activity_segment": activity["largest_positive_segment"],
        "largest_negative_activity_segment": activity["largest_negative_segment"],
        "activity_range_turns": activity["phase_range_turns"],
        "current_activity_uA_min": activity["current_uA"]["min"],
        "current_activity_uA_max": activity["current_uA"]["max"],
    }


def signal_stats(time_ps: np.ndarray, arrays: dict[str, np.ndarray], names: list[str], kind: str) -> dict[str, Any]:
    windows = {"full": (float(time_ps[0]), float(time_ps[-1]))}
    if kind.startswith("q0"):
        windows.update({
            f"pulse{i+1}_activity": (start, start + Q0_ACTIVITY)
            for i, start in enumerate(Q0_PULSE_STARTS)
        })
        windows["post"] = (Q0_PULSE_STARTS[-1] + Q0_ACTIVITY, float(time_ps[-1]))
    else:
        windows.update(Q5_WINDOWS)
    output: dict[str, Any] = {}
    for name in names:
        if name not in arrays:
            continue
        scale = 1e6 if name.startswith("I(") else 1.0
        output[name] = {label: stats(arrays[name][(time_ps >= left) & (time_ps < right)], scale) for label, (left, right) in windows.items()}
    return output


def analyze_case(fixture: str, filename: str) -> dict[str, Any]:
    kind = FIXTURES[fixture]["kind"]
    path = RAW / fixture / filename
    time_ps, arrays, header_names = load_raw(path)
    for _, (p, v, i) in QB_COLUMNS.items():
        for name in (p, v, i):
            if name not in arrays:
                raise ValueError(f"{path}: missing {name}")
    has_jtl = "jtl" in kind
    if has_jtl:
        for jj in JTL_JJS:
            for prefix in ("P", "V", "I"):
                name = f"{prefix}({jj})"
                if name not in arrays:
                    raise ValueError(f"{path}: missing {name}")
    qb = {
        jj: fixed_metric(time_ps, arrays, *QB_COLUMNS[jj], kind) for jj in QB_JJS
    }
    jtl = {}
    if has_jtl:
        jtl = {
            jj: fixed_metric(
                time_ps,
                arrays,
                f"P({jj})",
                f"V({jj})",
                f"I({jj})",
                kind,
            )
            for jj in JTL_JJS
        }
    requested_signals = [
        "V(OUT)", "I(L0|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(RB|XBQ)",
        "I(RJ1|XBQ)", "I(RJ2|XBQ)", "I(R_LOAD)", "I(L1|XJTL1)",
        "V(JTL_MID)", "V(JTL_OUT)", "I(R_TERM)",
    ]
    signals = signal_stats(time_ps, arrays, requested_signals, kind)
    return {
        "fixture": fixture,
        "kind": kind,
        "case": filename.removesuffix(".csv"),
        "raw": str(path.relative_to(ROOT)),
        "raw_sha256": sha256(path),
        "rows": int(time_ps.size),
        "time_start_ps": float(time_ps[0]),
        "time_end_ps": float(time_ps[-1]),
        "dt_median_ps": float(np.median(np.diff(time_ps))),
        "has_load_probe": "I(R_LOAD)" in arrays,
        "header_field_count": len(header_names),
        "qb": qb,
        "jtl": jtl,
        "signals": signals,
    }


def q0_local_verdict(case: dict[str, Any]) -> str:
    bjl2 = case["qb"]["BJL2"]
    vector = [p["activity"]["complete_event_units"] for p in bjl2["pulses"]]
    post = bjl2["post_complete_event_count"]
    if post:
        return "Q0_MULTIEVENT"
    if any(v > 1 for v in vector):
        return "Q0_MULTIEVENT"
    if all(v == 1 for v in vector):
        if case["kind"] == "q0":
            return "Q0_OPEN_EVENT_PRESERVED"
        jtl = case["jtl"]
        jtl_vectors = {
            jj: [p["activity"]["complete_event_units"] for p in metric["pulses"]]
            for jj, metric in jtl.items()
        }
        if all(all(v == 1 for v in values) for values in jtl_vectors.values()):
            return "Q0_JTL_PROPAGATION_PASS"
        if all(sum(values) == 0 for values in jtl_vectors.values()):
            return "Q0_EVENT_NOT_PROPAGATED"
        return "Q0_PARTIAL_JTL_PROPAGATION"
    if sum(vector) == 0:
        return "Q0_OPEN_NO_COMPLETE_EVENT" if case["kind"] == "q0" else "Q0_EVENT_LOST_UNDER_LOAD"
    return "Q0_INCONCLUSIVE_OR_PARTIAL"


def q5_local_verdict(case: dict[str, Any], all_cases: dict[str, dict[str, Any]]) -> str:
    read1 = all_cases["paper-j1-logical1-read.csv"]
    read0 = all_cases["paper-j0-logical0-read.csv"]
    controls = [all_cases["paper-j1-logical1-read0-control.csv"], all_cases["paper-j0-logical0-read0-control.csv"]]
    read1_bjl2 = read1["qb"]["BJL2"]["activity_complete_event_units"]
    read0_bjl2 = read0["qb"]["BJL2"]["activity_complete_event_units"]
    control_bjl2 = [c["qb"]["BJL2"]["activity_complete_event_units"] for c in controls]
    if read0_bjl2 or any(control_bjl2):
        return "Q5_NONSELECTIVE_OR_MULTIFIRE_FAILURE"
    if read1_bjl2 > 1:
        return "Q5_MULTIFIRE"
    if case["kind"] == "q5" and read1_bjl2 == 1:
        return "Q5_OPEN_SELECTIVE_LOCAL_ONE_SHOT"
    read1_jtl = [read1["jtl"][jj]["activity_complete_event_units"] for jj in JTL_JJS]
    read0_jtl = [read0["jtl"][jj]["activity_complete_event_units"] for jj in JTL_JJS]
    control_jtl = [[c["jtl"][jj]["activity_complete_event_units"] for jj in JTL_JJS] for c in controls]
    if any(read0_jtl) or any(v for row in control_jtl for v in row):
        return "Q5_NONSELECTIVE_OR_MULTIFIRE_FAILURE"
    if all(v == 1 for v in read1_jtl):
        return "Q5_JTL_SELECTIVE_PASS"
    if not any(read1_jtl):
        return "Q5_NO_JTL_TRIGGER"
    return "Q5_PARTIAL_JTL_PROPAGATION"


def add_verdicts(results: dict[str, list[dict[str, Any]]]) -> dict[str, str]:
    verdicts: dict[str, str] = {}
    for fixture in ("A-q0-open", "B-q0-jtl-only", "C-q0-10ohm-parallel-jtl"):
        verdicts[fixture] = q0_local_verdict(results[fixture][0])
    for fixture in ("D-q5-open", "E-q5-jtl-only"):
        by_case = {case["case"] + ".csv": case for case in results[fixture]}
        verdicts[fixture] = q5_local_verdict(results[fixture][0], by_case)
    return verdicts


def fmt(value: Any, digits: int = 7) -> str:
    if value is None:
        return "—"
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return "—"
        return f"{float(value):.{digits}g}"
    return str(value)


def largest_text(metric: dict[str, Any] | None) -> str:
    if not metric:
        return "—"
    return f"{fmt(metric['delta_turns'])} / {fmt(metric['area_turns'])} / {fmt(metric['area_residual_turns'])}"


def q0_event_table(cases: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| fixture | JJ | pulse event units | activity largest Δturn/area | post complete |",
        "|---|---|---|---|---:|",
    ]
    for case in cases:
        for jj in QB_JJS:
            m = case["qb"][jj]
            vector = ",".join(str(p["activity"]["complete_event_units"]) for p in m["pulses"])
            lines.append(f"| {case['fixture']} | {jj} | `{vector}` | {largest_text(m['largest_activity_segment'])} | {m['post_complete_event_count']} |")
        if case["jtl"]:
            for jj in JTL_JJS:
                m = case["jtl"][jj]
                vector = ",".join(str(p["activity"]["complete_event_units"]) for p in m["pulses"])
                lines.append(f"| {case['fixture']} | {jj} | `{vector}` | {largest_text(m['largest_activity_segment'])} | {m['post_complete_event_count']} |")
    return lines


def q5_event_table(cases: list[dict[str, Any]]) -> list[str]:
    lines = [
        "| fixture | case | JJ | activity range (turn) | largest Δturn/area | complete | post complete |",
        "|---|---|---|---:|---|---:|---:|",
    ]
    for case in cases:
        for jj in QB_JJS:
            m = case["qb"][jj]
            lines.append(f"| {case['fixture']} | {case['case']} | {jj} | {fmt(m['activity_range_turns'])} | {largest_text(m['largest_activity_segment'])} | {m['activity_complete_event_units']} | {m['post_complete_event_count']} |")
        if case["jtl"]:
            for jj in JTL_JJS:
                m = case["jtl"][jj]
                lines.append(f"| {case['fixture']} | {case['case']} | {jj} | {fmt(m['activity_range_turns'])} | {largest_text(m['largest_activity_segment'])} | {m['activity_complete_event_units']} | {m['post_complete_event_count']} |")
    return lines


def q0_summary(case: dict[str, Any]) -> str:
    bjl2 = case["qb"]["BJL2"]
    vector = ",".join(str(p["activity"]["complete_event_units"]) for p in bjl2["pulses"])
    return f"{case['fixture']}: BJL2 `{vector}`, max post p2p={fmt(max(p['post']['phase_range_turns'] for p in bjl2['pulses']))} turn"


def q5_summary(case: dict[str, Any]) -> str:
    bjl2 = case["qb"]["BJL2"]
    return f"{case['fixture']}/{case['case']}: BJL2 largest={largest_text(bjl2['largest_activity_segment'])}, complete={bjl2['activity_complete_event_units']}"


def directional_text(metric: dict[str, Any]) -> tuple[str, str]:
    """Compactly expose forward/backward segments without hiding polarity."""
    if "pulses" in metric:
        positive = "; ".join(
            fmt((pulse["activity"]["largest_positive_segment"] or {}).get("delta_turns"))
            for pulse in metric["pulses"]
        )
        negative = "; ".join(
            fmt((pulse["activity"]["largest_negative_segment"] or {}).get("delta_turns"))
            for pulse in metric["pulses"]
        )
        return positive, negative
    return (
        fmt((metric["activity"]["largest_positive_segment"] or {}).get("delta_turns")),
        fmt((metric["activity"]["largest_negative_segment"] or {}).get("delta_turns")),
    )


def matrix_cell(label: str, verdict: str, details: str) -> str:
    return f"`{label}` — **{verdict}**; {details}"


def render_report(results: dict[str, list[dict[str, Any]]], verdicts: dict[str, str]) -> str:
    a, b, c = (results[name][0] for name in ("A-q0-open", "B-q0-jtl-only", "C-q0-10ohm-parallel-jtl"))
    d, e = results["D-q5-open"], results["E-q5-jtl-only"]
    d_map = {x["case"]: x for x in d}
    e_map = {x["case"]: x for x in e}
    r1d, r0d = d_map["paper-j1-logical1-read"], d_map["paper-j0-logical0-read"]
    r1e, r0e = e_map["paper-j1-logical1-read"], e_map["paper-j0-logical0-read"]
    lines = [
        "# QB load-boundary matrix：Q0/Q5 output boundary compatibility",
        "",
        "## 主结论",
        "",
        "本报告只覆盖五个 preregistered output-boundary fixtures。每个 fixture 先独立判定，再做矩阵比较；不做参数优化，也不把局部 JJ event自动解释为 downstream SFQ delivery。",
        "",
        "## Artifact validity",
        "",
        "- v2 raw 使用 JoSIM `v2.7.2837d13`；所有 11 个 v2 jobs exit=0、stderr 为空、时间轴严格递增。",
        "- v1 A/B/D/E raw 保留在 `raw/`，但因删除 `R_LOAD` 后遗留 `.print I(R_LOAD)` 导致 invalid probe，完全排除；C v1 也不作为本次 matched package 的来源。详见 `ATTEMPT-01-INVALID.md`。",
        "- v2 parser 从 JoSIM data header开始读取，未把 progress text当成数据；Q0 为 2999 rows、0.1 ps，Q5 为 13599 rows、0.0125 ps。",
        "",
        "## Local verdicts",
        "",
        "| fixture | independent local verdict | key BJL2 result |",
        "|---|---|---|",
        f"| A Q0 OPEN | **{verdicts['A-q0-open']}** | {q0_summary(a)} |",
        f"| B Q0 JTL-only | **{verdicts['B-q0-jtl-only']}** | {q0_summary(b)} |",
        f"| C Q0 10Ω || JTL | **{verdicts['C-q0-10ohm-parallel-jtl']}** | {q0_summary(c)} |",
        f"| D Q5 OPEN | **{verdicts['D-q5-open']}** | {q5_summary(r1d)}; read0 {q5_summary(r0d)} |",
        f"| E Q5 JTL-only | **{verdicts['E-q5-jtl-only']}** | {q5_summary(r1e)}; read0 {q5_summary(r0e)} |",
        "",
        "## Q0：六个 registered pulses",
        "",
    ]
    lines.extend(q0_event_table([a, b, c]))
    lines += [
        "",
        "Q0 的完整 local event 只在 BJL2 的同一 pulse、同一 monotonic segment 中计数；JTL 的四颗 JJ分别计数。",
        "",
        "## Q0 JTL propagation details",
        "",
        "| fixture | pulse | JTL JJ | largest segment (turn) | area (Φ0) | events | onset (ps) | final output signal |",
        "|---|---:|---|---:|---:|---:|---:|---:|",
    ]
    for case in (b, c):
        for pulse_index in range(6):
            for jj in JTL_JJS:
                m = case["jtl"][jj]["pulses"][pulse_index]
                seg = m["activity"]["largest_segment"] or {}
                lines.append(
                    f"| {case['fixture']} | {pulse_index + 1} | {jj} | {fmt(seg.get('delta_turns'))} | {fmt(seg.get('area_turns'))} | {m['activity']['complete_event_units']} | {fmt(seg.get('start_ps'))} | {fmt(case['signals'].get('V(JTL_OUT)', {}).get(f'pulse{pulse_index+1}_activity', {}).get('p2p'))} V |"
                )
    lines += [
        "",
        "## Q5：四个 matched cases",
        "",
    ]
    lines.extend(q5_event_table(d + e))
    lines += [
        "",
        "## BJL1/BJL2 directional activity",
        "",
        "正、负 monotonic segment 分开报告；Q0 单元格按 pulse 1→6 排列。负值不是事件失败或成功的替代判据，只用于识别方向与 cancellation。",
        "",
        "| fixture/case | BJL1 forward Δturn | BJL1 backward Δturn | BJL2 forward Δturn | BJL2 backward Δturn |",
        "|---|---|---|---|---|",
    ]
    for case in [a, b, c] + d + e:
        bjl1_pos, bjl1_neg = directional_text(case["qb"]["BJL1"])
        bjl2_pos, bjl2_neg = directional_text(case["qb"]["BJL2"])
        lines.append(f"| {case['fixture']}/{case['case']} | `{bjl1_pos}` | `{bjl1_neg}` | `{bjl2_pos}` | `{bjl2_neg}` |")
    lines += [
        "",
        "## Output boundary / ringing signals",
        "",
        "| fixture/case | V(OUT) activity p2p | I(L0) activity p2p (µA) | I(R_LOAD) activity p2p (µA) | JTL input I(L1) activity p2p (µA) | V(JTL_OUT) activity p2p (µV) | I(R_TERM) activity p2p (µA) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in [a, b, c] + d + e:
        sig = case["signals"]
        activity_key = "pulse1_activity" if case["kind"].startswith("q0") else "activity"
        def value(name: str, scale: float = 1.0) -> str:
            return fmt(sig.get(name, {}).get(activity_key, {}).get("p2p", None) * scale if name in sig and sig[name].get(activity_key) else None)
        lines.append(
            f"| {case['fixture']}/{case['case']} | {value('V(OUT)')} | {value('I(L0|XBQ)', 1.0)} | {value('I(R_LOAD)', 1.0)} | {value('I(L1|XJTL1)', 1.0)} | {value('V(JTL_OUT)', 1e6)} | {value('I(R_TERM)', 1.0)} |"
        )
    lines += [
        "",
        "## Required comparison matrix",
        "",
        "| QB source | 10Ω | OPEN | JTL-only | 10Ω || JTL |",
        "|---|---|---|---|---|",
        f"| Q0 true-event | accepted Q0: BJL2 one per pulse | {matrix_cell('A', verdicts['A-q0-open'], 'open boundary result')} | {matrix_cell('B', verdicts['B-q0-jtl-only'], 'direct JTL result')} | {matrix_cell('C', verdicts['C-q0-10ohm-parallel-jtl'], 'parallel-load result')} |",
        f"| Q5 near-event | accepted Q5: BJL2≈0.968179 turn, zero complete event | {matrix_cell('D', verdicts['D-q5-open'], 'open boundary result')} | {matrix_cell('E', verdicts['E-q5-jtl-only'], 'direct JTL result')} | accepted Q6: `NO_JTL_TRIGGER` |",
        "",
        "## Observed",
        "",
        f"- A：{q0_summary(a)}。",
        f"- B：{q0_summary(b)}。",
        f"- C：{q0_summary(c)}。",
        f"- D read1：{q5_summary(r1d)}；E read1：{q5_summary(r1e)}。",
        "- 所有 BJs/BJL1/BJL2 与 JTL JJ 的 event 计数均来自 continuous unwrapped phase、同一 monotonic segment 和同一 JJ 直接电压面积；phase total range、current peak、voltage peak 不单独构成 event。",
        "",
        "## Derived",
        "",
        "- phase turns = raw `P(...)` 的连续 unwrap 后的 Δphase/(2π)。",
        "- 同段 voltage area = `∫V_sameJJ dt / Φ0`；candidate 至少 1 turn、area 同号，残差阈值为 `max(0.02, 0.05×|Δturn|)` turn。该阈值是本探索的 analysis rule，不是器件 universal threshold。",
        "- Q0 local event vector按六个 pulse分别报告；Q5按四个 matched case分别报告。",
        "",
        "## Inference",
        "",
        "- A 与 accepted Q0 的对比表明：10Ω 不是 Q0 产生 local BJL2 phase/area transition 的必要条件，但在本 frozen point 下它把 OPEN 的约 3-unit/pulse multi-event 行为压到 accepted 的 exactly-one/pulse；因此 10Ω 对 one-shot/retrap 边界具有因果影响。",
        "- B/C 对比区分 direct JTL loading 与 `10Ω || JTL` 并联 loading；若两者都丢失而 A 保留，支持 JTL input boundary/interface mismatch，而不是把 Q0 standalone event否定。",
        "- D/E 与 accepted Q5/Q6 显示 near-event 对 load boundary 极敏感：OPEN 变成 read1-selective multi-event，而 JTL-only 与 `10Ω || JTL` 均不给出完整 JTL event；这支持“Q5 near-event 的 margin 小于 Q0 true-event”，但不是整个 QB/JTL family 的普遍不可能性。",
        "- B/C 均未出现完整 Q0 BJL2 或 JTL JJ event，且 C 相比 B 仅改变保留的 10Ω 并联支路；在本已验证 JTL chain 下，这支持 direct JTL input boundary 对 Q0 true-event 的强加载/接口不兼容解释，而不否定 Q0 在 10Ω isolated boundary 下的 local event。",
        "",
        "## Unknown / limits",
        "",
        "- 本矩阵没有连接 canonical BVM，也没有 physical BVM back-action evidence；Q5仍是 frozen replay fixture。",
        "- R11-A 的 standard-JTL positive control provenance被复用，本矩阵不重复运行该 positive control。",
        "- OPEN 是无 downstream load的边界诊断，不代表实际封装或后端接口。",
        "- 本报告不把 Q0 BJL2 local event自动称作 downstream SFQ delivery；只有 JTL四颗 JJ的事件序列达到完整、面积一致、时序合理且无 post event时，才称 tested-chain propagation。",
        "",
        "## Stop",
        "",
        "本 bounded matrix 已完成；不调 QB/JTL 参数、不加 conditioner、不接 T1、不连接 physical BVM。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    results: dict[str, list[dict[str, Any]]] = {}
    for fixture, definition in FIXTURES.items():
        results[fixture] = [analyze_case(fixture, filename) for filename in definition["files"]]
    verdicts = add_verdicts(results)
    metrics = {
        "run_id": "qb-load-boundary-matrix-20260824",
        "parent_head": "30590c9d9d4831f98c2a3f1db28ee7f6813eee59",
        "binary": "build/josim-cli",
        "binary_version": "v2.7.2837d13",
        "metric_rule": "same-JJ same-monotonic-segment >=1 turn; area same sign; residual <= max(0.02,0.05*abs(delta)) turn",
        "fixtures": results,
        "local_verdicts": verdicts,
    }
    (ANALYSIS / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    rows: list[dict[str, Any]] = []
    for fixture, cases in results.items():
        for case in cases:
            row = {
                "fixture": fixture,
                "case": case["case"],
                "verdict": verdicts[fixture],
                "BJL2_activity_complete_units": case["qb"]["BJL2"]["activity_complete_event_units"],
                "BJL2_post_complete_events": case["qb"]["BJL2"]["post_complete_event_count"],
                "BJL2_largest_delta_turns": (case["qb"]["BJL2"]["largest_activity_segment"] or {}).get("delta_turns"),
                "BJL2_largest_area_turns": (case["qb"]["BJL2"]["largest_activity_segment"] or {}).get("area_turns"),
            }
            if case["kind"].startswith("q0"):
                row["BJL2_event_vector"] = ",".join(str(p["activity"]["complete_event_units"]) for p in case["qb"]["BJL2"]["pulses"])
            rows.append(row)
    with (ANALYSIS / "case-summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (ANALYSIS / "REPORT.md").write_text(render_report(results, verdicts))
    print(json.dumps({"local_verdicts": verdicts, "cases": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
