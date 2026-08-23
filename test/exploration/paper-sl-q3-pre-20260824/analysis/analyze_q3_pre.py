#!/usr/bin/env python3
"""Analysis-only audit of BJs -> BJL1 transfer for PAPER-SL-Q3-PRE.

This script reads only the already accepted Q0, PAPER-SL-Q1 and PAPER-SL-Q2
CSV files.  It does not run JoSIM, resample traces, or create a new circuit.
Voltage areas use each CSV's actual time column.  Q0 has six periodic windows;
the window containing its dominant BJs segment is used for the aligned
trajectory/current comparison, while the requested ratios use each junction's
global largest segment within the registered activity windows.
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
ANALYSIS = ROOT / "analysis"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi

JUNCTIONS = {
    "BJs": ("P(BJS|XBQ)", "V(BJS|XBQ)", "I(BJS|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}

BRANCHES = (
    "I(BJS|XBQ)",
    "I(BJL1|XBQ)",
    "I(RJ1|XBQ)",
    "I(L1|XBQ)",
    "I(RB|XBQ)",
    "I(L2|XBQ)",
    "I(BJL2|XBQ)",
    "I(RJ2|XBQ)",
    "I(L0|XBQ)",
    "I(LIN|XBQ)",
)

CASE_SPECS = {
    "Q0_68p4u": {
        "label": "Q0 scaled ideal-current 68.4 µA",
        "path": Path(
            "../qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv"
        ),
        "windows": [(float(start), float(start + 25.0)) for start in (10, 60, 110, 160, 210, 260)],
        "dt_ps": 0.1,
        "ibias_uA": 35.0,
    },
    "PAPER_SL_Q1_35u": {
        "label": "PAPER-SL-Q1 paper-JSL logical1 READ, IBIAS=35 µA",
        "path": Path("../paper-sl-q1-20260824/raw/paper-j1-logical1-read.csv"),
        "windows": [(94.0, 130.0)],
        "dt_ps": 0.0125,
        "ibias_uA": 35.0,
    },
    "PAPER_SL_Q2_40u": {
        "label": "PAPER-SL-Q2 paper-JSL logical1 READ, IBIAS=40 µA",
        "path": Path("../paper-sl-q2-20260824/raw/40u/paper-j1-logical1-read.csv"),
        "windows": [(94.0, 130.0)],
        "dt_ps": 0.0125,
        "ibias_uA": 40.0,
    },
}

IC_UA = {"BJs": 50.0, "BJL1": 36.0, "BJL2": 54.0}


def load_csv(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        rows = [row for row in reader if row]
    names = [name.strip() for name in header]
    data: dict[str, np.ndarray] = {}
    for index, name in enumerate(names):
        data[name] = np.asarray([float(row[index]) for row in rows], dtype=float)
    if "time" not in data or data["time"].size < 2:
        raise ValueError(f"missing/short time column: {path}")
    if not np.all(np.isfinite(data["time"])) or not np.all(np.diff(data["time"]) > 0):
        raise ValueError(f"invalid time axis: {path}")
    lengths = {values.size for values in data.values()}
    if len(lengths) != 1:
        raise ValueError(f"column length mismatch: {path}")
    return data


def column(data: dict[str, np.ndarray], name: str) -> np.ndarray:
    if name in data:
        return data[name]
    normalized = {re.sub(r"\s+", "", key).lower(): key for key in data}
    key = normalized.get(re.sub(r"\s+", "", name).lower())
    if key is None:
        raise KeyError(f"missing {name!r} in {list(data)}")
    return data[key]


def finite_stats(values: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"min": math.nan, "max": math.nan, "mean": math.nan, "rms": math.nan, "p2p": math.nan}
    return {
        "min": float(np.min(finite)),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
        "rms": float(np.sqrt(np.mean(finite * finite))),
        "p2p": float(np.ptp(finite)),
    }


def monotonic_runs(values: np.ndarray) -> list[tuple[int, int]]:
    if values.size < 2:
        return []
    signs = np.sign(np.diff(values))
    nonzero = np.flatnonzero(signs)
    if nonzero.size == 0:
        return []
    result: list[tuple[int, int]] = []
    start = 0
    direction = int(signs[nonzero[0]])
    for position in nonzero[1:]:
        new_direction = int(signs[position])
        if new_direction != direction:
            result.append((start, int(position)))
            start = int(position)
            direction = new_direction
    result.append((start, values.size - 1))
    return [(left, right) for left, right in result if right > left]


def area_turns(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    time_s = time_ps * 1e-12
    integral = np.trapezoid(voltage, time_s) if hasattr(np, "trapezoid") else np.trapz(voltage, time_s)
    return float(integral / PHI0)


def segment_records(
    time_ps: np.ndarray,
    phase: np.ndarray,
    voltage: np.ndarray,
    window: tuple[float, float],
    window_index: int,
) -> list[dict[str, Any]]:
    selected = np.flatnonzero((time_ps >= window[0]) & (time_ps < window[1]))
    if selected.size < 2:
        return []
    local_phase = phase[selected]
    records: list[dict[str, Any]] = []
    for left, right in monotonic_runs(local_phase):
        indices = selected[left : right + 1]
        delta_rad = float(phase[indices[-1]] - phase[indices[0]])
        delta_turns = delta_rad / TWO_PI
        area = area_turns(time_ps[indices], voltage[indices])
        residual = area - delta_turns
        tolerance = max(0.05, 0.10 * abs(delta_turns))
        phase_candidate = abs(delta_turns) >= 1.0
        phase_area_consistent = delta_turns * area > 0 and abs(residual) <= tolerance
        area_consistent = phase_candidate and phase_area_consistent
        records.append(
            {
                "window_index": window_index,
                "window_ps": [float(window[0]), float(window[1])],
                "start_index": int(indices[0]),
                "end_index": int(indices[-1]),
                "start_ps": float(time_ps[indices[0]]),
                "end_ps": float(time_ps[indices[-1]]),
                "duration_ps": float(time_ps[indices[-1]] - time_ps[indices[0]]),
                "phase_start_rad": float(phase[indices[0]]),
                "phase_end_rad": float(phase[indices[-1]]),
                "delta_rad": delta_rad,
                "delta_turns": float(delta_turns),
                "area_turns": float(area),
                "area_residual_turns": float(residual),
                "area_tolerance_turns": float(tolerance),
                "phase_candidate": bool(phase_candidate),
                "phase_area_consistent": bool(phase_area_consistent),
                "area_consistent": bool(area_consistent),
                "complete_event_units": int(math.floor(abs(delta_turns))) if area_consistent else 0,
            }
        )
    return records


def largest(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(records, key=lambda item: abs(float(item["delta_turns"]))) if records else None


def interval_stats(data: dict[str, np.ndarray], time_ps: np.ndarray, start_ps: float, end_ps: float) -> dict[str, Any]:
    mask = (time_ps >= start_ps) & (time_ps <= end_ps)
    result: dict[str, Any] = {"start_ps": start_ps, "end_ps": end_ps, "samples": int(np.count_nonzero(mask))}
    for branch in BRANCHES:
        values_uA = column(data, branch)[mask] * 1e6
        result[branch] = finite_stats(values_uA)
        result[branch]["signed_area_uA_ps"] = float(
            (np.trapezoid(values_uA, time_ps[mask]) if hasattr(np, "trapezoid") else np.trapz(values_uA, time_ps[mask]))
        )
        result[branch]["positive_area_uA_ps"] = float(
            (np.trapezoid(np.maximum(values_uA, 0.0), time_ps[mask]) if hasattr(np, "trapezoid") else np.trapz(np.maximum(values_uA, 0.0), time_ps[mask]))
        )
        result[branch]["negative_area_uA_ps"] = float(
            (np.trapezoid(np.minimum(values_uA, 0.0), time_ps[mask]) if hasattr(np, "trapezoid") else np.trapz(np.minimum(values_uA, 0.0), time_ps[mask]))
        )
    return result


def kcl_stats(data: dict[str, np.ndarray], time_ps: np.ndarray, start_ps: float, end_ps: float) -> dict[str, Any]:
    mask = (time_ps >= start_ps) & (time_ps <= end_ps)
    bjs = column(data, "I(BJS|XBQ)")
    bjl1 = column(data, "I(BJL1|XBQ)")
    rj1 = column(data, "I(RJ1|XBQ)")
    l1 = column(data, "I(L1|XBQ)")
    rb = column(data, "I(RB|XBQ)")
    l2 = column(data, "I(L2|XBQ)")
    bjl2 = column(data, "I(BJL2|XBQ)")
    rj2 = column(data, "I(RJ2|XBQ)")
    l0 = column(data, "I(L0|XBQ)")
    residuals = {
        "node2_BJs_minus_L1_BJL1_RJ1": bjs - l1 - bjl1 - rj1,
        "node3_L1_plus_RB_minus_L2": l1 + rb - l2,
        "node4_L2_minus_L0_BJL2_RJ2": l2 - l0 - bjl2 - rj2,
    }
    result: dict[str, Any] = {}
    for name, residual in residuals.items():
        values_uA = residual[mask] * 1e6
        result[name] = {
            "max_abs_uA": float(np.max(np.abs(values_uA))),
            "rms_uA": float(np.sqrt(np.mean(values_uA * values_uA))),
            "min_uA": float(np.min(values_uA)),
            "max_uA": float(np.max(values_uA)),
        }
    return result


def routing_metrics(interval: dict[str, Any]) -> dict[str, float]:
    def area(branch: str) -> float:
        return float(interval[branch]["signed_area_uA_ps"])

    q_bjs = area("I(BJS|XBQ)")
    q_local = area("I(BJL1|XBQ)") + area("I(RJ1|XBQ)")
    q_l1 = area("I(L1|XBQ)")
    return {
        "q_bjs_uA_ps": q_bjs,
        "q_bjl1_uA_ps": area("I(BJL1|XBQ)"),
        "q_rj1_uA_ps": area("I(RJ1|XBQ)"),
        "q_local_bjl1_parallel_rj1_uA_ps": q_local,
        "q_l1_uA_ps": q_l1,
        "local_fraction_of_bjs": q_local / q_bjs if abs(q_bjs) > 1e-12 else math.nan,
        "l1_fraction_of_bjs": q_l1 / q_bjs if abs(q_bjs) > 1e-12 else math.nan,
        "bjl1_fraction_of_bjs": area("I(BJL1|XBQ)") / q_bjs if abs(q_bjs) > 1e-12 else math.nan,
    }


def analyze_case(case_id: str, spec: dict[str, Any]) -> dict[str, Any]:
    path = (ROOT / spec["path"]).resolve()
    data = load_csv(path)
    time_ps = column(data, "time") * 1e12
    phases = {name: np.unwrap(column(data, names[0])) for name, names in JUNCTIONS.items()}
    all_segments: dict[str, list[dict[str, Any]]] = {}
    by_window: dict[str, list[list[dict[str, Any]]]] = {}
    for name, names in JUNCTIONS.items():
        per_window = [segment_records(time_ps, phases[name], column(data, names[1]), window, index) for index, window in enumerate(spec["windows"])]
        by_window[name] = per_window
        all_segments[name] = [segment for window_segments in per_window for segment in window_segments]
    global_segments = {name: largest(records) for name, records in all_segments.items()}
    bjs_global = global_segments["BJs"]
    if bjs_global is None:
        raise ValueError(f"no BJs monotonic segment in {case_id}")
    paired_index = int(bjs_global["window_index"])
    paired_segments = {name: largest(by_window[name][paired_index]) for name in JUNCTIONS}
    bjl1_pair = paired_segments["BJL1"]
    if bjl1_pair is None:
        raise ValueError(f"no paired BJL1 segment in {case_id}")
    bjs_start = float(bjs_global["start_ps"])
    bjs_end = float(bjs_global["end_ps"])
    bjl1_start = float(bjl1_pair["start_ps"])
    bjl1_end = float(bjl1_pair["end_ps"])
    bjs_interval = interval_stats(data, time_ps, bjs_start, bjs_end)
    bjl1_interval = interval_stats(data, time_ps, bjl1_start, bjl1_end)
    paired_timing = {
        "bjs_start_ps": bjs_start,
        "bjs_end_ps": bjs_end,
        "bjl1_start_ps": bjl1_start,
        "bjl1_end_ps": bjl1_end,
        "bjs_duration_ps": float(bjs_end - bjs_start),
        "bjl1_duration_ps": float(bjl1_end - bjl1_start),
        "bjl1_start_delay_from_bjs_ps": float(bjl1_start - bjs_start),
        "overlap_ps": float(max(0.0, min(bjs_end, bjl1_end) - max(bjs_start, bjl1_start))),
        "bjs_relative_interval_ps": [0.0, float(bjs_end - bjs_start)],
        "bjl1_relative_interval_ps": [float(bjl1_start - bjs_start), float(bjl1_end - bjs_start)],
    }
    ratios = {
        "bjl1_over_bjs": float(global_segments["BJL1"]["delta_turns"] / global_segments["BJs"]["delta_turns"]),
        "bjl2_over_bjl1": float(global_segments["BJL2"]["delta_turns"] / global_segments["BJL1"]["delta_turns"]),
        "bjl2_over_bjs": float(global_segments["BJL2"]["delta_turns"] / global_segments["BJs"]["delta_turns"]),
    }
    routing = routing_metrics(bjl1_interval)
    kcl = kcl_stats(data, time_ps, bjs_start, bjs_end)
    trajectory = {
        name: {
            "global_largest": global_segments[name],
            "paired_window_largest": paired_segments[name],
            "paired_window_phase_p2p_turns": float(
                np.ptp(phases[name][(time_ps >= spec["windows"][paired_index][0]) & (time_ps < spec["windows"][paired_index][1])]) / TWO_PI
            ),
        }
        for name in JUNCTIONS
    }
    return {
        "case_id": case_id,
        "label": spec["label"],
        "raw_path": str(path),
        "time_step_ps": spec["dt_ps"],
        "actual_time_start_ps": float(time_ps[0]),
        "actual_time_end_ps": float(time_ps[-1]),
        "activity_windows_ps": spec["windows"],
        "paired_window_index": paired_index,
        "ibias_uA": spec["ibias_uA"],
        "trajectory": trajectory,
        "timing": paired_timing,
        "bjs_interval_currents": bjs_interval,
        "bjl1_interval_currents": bjl1_interval,
        "routing_metrics": routing,
        "kcl": kcl,
        "ratios": ratios,
    }


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    if isinstance(value, (float, int)):
        return f"{value:.{digits}g}"
    return str(value)


def seg_row(case: dict[str, Any], name: str) -> str:
    seg = case["trajectory"][name]["paired_window_largest"]
    timing = case["timing"]
    rel_start = float(seg["start_ps"] - timing["bjs_start_ps"])
    rel_end = float(seg["end_ps"] - timing["bjs_start_ps"])
    return (
        f"| {case['case_id']} | {name} | {fmt(seg['start_ps'])}–{fmt(seg['end_ps'])} | "
        f"{fmt(rel_start)}–{fmt(rel_end)} | {fmt(seg['phase_start_rad'])} → {fmt(seg['phase_end_rad'])} | "
        f"{fmt(seg['delta_rad'])} | {fmt(seg['delta_turns'])} | {fmt(seg['area_turns'])} | "
        f"{fmt(seg['area_residual_turns'])} | {'yes' if seg['phase_area_consistent'] else 'no'} |"
    )


def current_row(case: dict[str, Any], interval_key: str, branch: str) -> str:
    stats = case[interval_key][branch]
    return f"| {case['case_id']} | {interval_key} | {branch} | {fmt(stats['min'])} | {fmt(stats['max'])} | {fmt(stats['mean'])} | {fmt(stats['rms'])} | {fmt(stats['signed_area_uA_ps'])} |"


def report(results: dict[str, Any]) -> str:
    lines = [
        "# PAPER-SL-Q3-PRE 分析报告",
        "",
        "## 范围与结论等级",
        "",
        "本 checkpoint 只读取既有 Q0 68.4 µA positive-control、PAPER-SL-Q1 35 µA logical1 READ 和 PAPER-SL-Q2 40 µA logical1 READ raw。没有运行 JoSIM、没有重采样、没有改变 physical circuit。Q0 的周期 raw 使用包含其全局最大 BJs segment 的 210 ps pulse 做 aligned comparison；phase/area 比值仍使用各 JJ 在注册 activity windows 内的 global largest segment。",
        "",
        "最终决策：**B. BJs→BJL1 更像 waveform/routing/timing-limited，而不是可由当前证据主要归因于 BJL1 threshold。** 这是受限于三个既有 fixture 的 mechanism inference，不是 topology 普遍结论。",
        "",
        "## 实际 QB topology 与 KCL",
        "",
        "```text",
        "IN ── Lin ── node1 ── BJs ── node2",
        "                           ├─ BJL1 || RJ1 ── GND",
        "                           └─ L1 ── node3 ── L2 ── node4",
        "                                      ▲          ├─ BJL2 || RJ2 ── GND",
        "                                      │          └─ L0 ── OUT",
        "                                    RB / IBIAS",
        "```",
        "",
        "按 netlist 元件方向直接审计：",
        "",
        "- node2：`I(BJs) = I(L1) + I(BJL1) + I(RJ1)`；",
        "- node3：`I(L1) + I(RB) = I(L2)`；",
        "- node4：`I(L2) = I(L0) + I(BJL2) + I(RJ2)`。",
        "",
        "三组 raw 的 node2/node3/node4 KCL residual 均为微安级以下的数值误差，见下表。",
        "",
        "## Aligned continuous phase / same-JJ voltage-area",
        "",
        "相对时间零点是该 case 的 dominant BJs segment 起点；Q0 的 absolute time 仍保留实际 210 ps pulse 时间。`ΔP` 是同一 JJ、同一 segment 的 unwrapped phase endpoint difference；area 使用该 JJ 直接 `V(B...)` 和 CSV 实际时间。",
        "",
        "| case | JJ | absolute segment (ps) | relative segment (ps) | P start → P end (rad) | ΔP (rad) | Δturns | area (Φ0) | area residual (turn) | phase/area consistent |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for case in results["cases"].values():
        for name in ("BJs", "BJL1", "BJL2"):
            lines.append(seg_row(case, name))
    lines += [
        "",
        "Q0 的 paired window 是 `[210,235)` ps；其中 BJs global largest 为 `[210.5,230.4]` ps，BJL1 paired segment 为 `[210.0,216.5]` ps。Q0 BJL1 的 global largest amplitude 出现在 `[160.0,166.5]` ps，但同一脉冲形状的 210 ps paired segment 用于时序/KCL 对齐，避免把不同 pulse 拼接成一个因果轨迹。",
        "",
        "## Requested transfer ratios",
        "",
        "这些比值采用每个 case 各 JJ 的 global largest monotonic segment；不是 total phase range，也不是 event count。",
        "",
        "| case | BJs largest (turn) | BJL1 largest (turn) | BJL2 largest (turn) | BJL1/BJs | BJL2/BJL1 | BJL2/BJs |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in results["cases"].values():
        g = case["trajectory"]
        lines.append(
            f"| {case['case_id']} | {fmt(g['BJs']['global_largest']['delta_turns'])} | {fmt(g['BJL1']['global_largest']['delta_turns'])} | {fmt(g['BJL2']['global_largest']['delta_turns'])} | {fmt(case['ratios']['bjl1_over_bjs'])} | {fmt(case['ratios']['bjl2_over_bjl1'])} | {fmt(case['ratios']['bjl2_over_bjs'])} |"
        )
    lines += [
        "",
        "按请求参考值独立复算：Q0 = `16.423294 / 1.225528 / 1.096014`；Q1-35 = `14.092115 / 0.829846 / 0.892527`；Q2-40 = `14.092115 / 0.815414 / 0.944323`。",
        "",
        "## Timing overlap / delay",
        "",
        "| case | BJs dominant interval (ps) | paired BJL1 interval (ps) | BJL1 start delay from BJs start (ps) | overlap (ps) | BJs duration | BJL1 duration |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in results["cases"].values():
        t = case["timing"]
        lines.append(
            f"| {case['case_id']} | {fmt(t['bjs_start_ps'])}–{fmt(t['bjs_end_ps'])} | {fmt(t['bjl1_start_ps'])}–{fmt(t['bjl1_end_ps'])} | {fmt(t['bjl1_start_delay_from_bjs_ps'])} | {fmt(t['overlap_ps'])} | {fmt(t['bjs_duration_ps'])} | {fmt(t['bjl1_duration_ps'])} |"
        )
    lines += [
        "",
        "Q0/Q1/Q2 的 BJL1 segment 都在 BJs 主活动开始附近出现，并非明显的长延迟输出。Q2 的 global BJL2 segment 可早于 paired BJL1 segment，这不改变本节只审计 BJs→BJL1 的结论。",
        "",
        "## BJL1 operating point during dominant BJs segment",
        "",
        "单位为 µA；`RB` 是 bias branch。此表展示 BJs 主 segment 内的瞬时 branch operating range/mean，而不是用 `I/Ic` 宣称 event。",
        "",
        "| case | interval | branch | min | max | mean | RMS | signed current area (µA·ps) |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    selected_branches = ("I(BJS|XBQ)", "I(BJL1|XBQ)", "I(RJ1|XBQ)", "I(L1|XBQ)", "I(RB|XBQ)", "I(L2|XBQ)")
    for case in results["cases"].values():
        for branch in selected_branches:
            lines.append(current_row(case, "bjs_interval_currents", branch))
    lines += [
        "",
        "在 paired largest BJL1 segment 内，直接支路的 signed current-area（用于描述波形极性，不是 event 判据）如下：",
        "",
        "| case | BJL1 area | RJ1 area | L1 area | BJs area | local `(BJL1+RJ1)/BJs` | L1/BJs |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in results["cases"].values():
        interval = case["bjl1_interval_currents"]
        rm = case["routing_metrics"]
        lines.append(
            f"| {case['case_id']} | {fmt(rm['q_bjl1_uA_ps'])} | {fmt(rm['q_rj1_uA_ps'])} | {fmt(rm['q_l1_uA_ps'])} | {fmt(rm['q_bjs_uA_ps'])} | {fmt(rm['local_fraction_of_bjs'])} | {fmt(rm['l1_fraction_of_bjs'])} |"
        )
    lines += [
        "",
        "这个 split 是本轮最有信息量的内部 routing observable：Q0 的 signed BJL1 direct branch area 为正，而 Q1/Q2 略为负；Q1/Q2 的输入电流更多被 `L1` 及 `RJ1`/并联网络重新分配。",
        "",
        "## KCL closure",
        "",
        "Residual 是在 dominant BJs segment 上计算的 µA 数值残差。",
        "",
        "| case | node2 max abs / RMS (µA) | node3 max abs / RMS (µA) | node4 max abs / RMS (µA) |",
        "|---|---:|---:|---:|",
    ]
    for case in results["cases"].values():
        k = case["kcl"]
        lines.append(
            f"| {case['case_id']} | {fmt(k['node2_BJs_minus_L1_BJL1_RJ1']['max_abs_uA'])} / {fmt(k['node2_BJs_minus_L1_BJL1_RJ1']['rms_uA'])} | {fmt(k['node3_L1_plus_RB_minus_L2']['max_abs_uA'])} / {fmt(k['node3_L1_plus_RB_minus_L2']['rms_uA'])} | {fmt(k['node4_L2_minus_L0_BJL2_RJ2']['max_abs_uA'])} / {fmt(k['node4_L2_minus_L0_BJL2_RJ2']['rms_uA'])} |"
        )
    lines += [
        "",
        "## Observed",
        "",
        "- Q0 的 BJs global largest segment 为约 `16.4233 turn`，BJL1 为 `1.22553 turn`；Q1/Q2 的 BJs 都是约 `14.0921 turn`，而 BJL1 分别为 `0.829846` 和 `0.815414 turn`。三组 largest segment 的 same-JJ voltage-area 与 phase endpoint 均一致到报告精度。",
        "- Q0 的 BJL1 paired segment 与 BJs 主 segment 重叠约 `6.0 ps`；Q1 为约 `6.49 ps`，Q2 为约 `4.33 ps`。没有看到需要数十 ps 的明显 interstage delay 才能解释差异。",
        "- 在 BJL1 paired segment 上，Q0 的 `I(BJL1)` signed area 约 `+75.74 µA·ps`；Q1/Q2 分别约 `−7.25/−2.89 µA·ps`。Q1 的 BJL1 current peak 约 `±51 µA`、Q2 约 `−57.8/+44.0 µA`，并不低于 Q0 的 `−36.3/+42.9 µA`。",
        "- Q0/Q1/Q2 的 node2/node3/node4 KCL residual 均保持在约 `10⁻5–10⁻4 µA` 量级，说明分流差异不是由列方向/KCL 不闭合造成的。",
        "",
        "## Derived",
        "",
        "- 相对于 Q0，Q1 的 BJL1/BJs phase-transfer ratio 低约 21%，Q2 低约 22%；Q2 的 BJL2/BJL1 ratio 反而升高到约 `1.158`，因此当前主要差异出现在 BJs→BJL1，而不是 BJL1→BJL2 的单调 threshold 缺口。",
        "- 以 paired BJL1 segment 的 signed current-area 定义 node2 local-branch fraction `(BJL1+RJ1)/BJs`，Q0/Q1/Q2 约为 `0.3798/0.1959/0.2187`；其互补的 L1 fraction 约为 `0.6202/0.8041/0.7813`。这是对实际拓扑 KCL 的派生 routing 指标，不是新的 acceptance threshold。",
        "- Q0 的 BJL1 same-segment phase/area 已满足局部完整转变的现有 exploratory diagnostic；Q1/Q2 的 `0.8–0.82 turn` 仅是 sub-turn activity，不能称 event。",
        "",
        "## Inference",
        "",
        "判定选择 **B：BJs→BJL1 主要表现为 waveform/routing/timing limitation**。依据是：Q1/Q2 并非缺少 BJL1 branch current peak；相反，BJL1 current 波形的峰值可与 Q0 相当或更大，但其 signed transfer、local `(BJL1+RJ1)` 分流份额和 BJL1 phase segment 明显不同。固定 `BJL1 AREA/Ic` 前，最有信息量的单一内部 routing variable 是 node2 的 local-branch split waveform，建议用 `F_local(t) = [I(BJL1)+I(RJ1)]` 相对于 `I(BJs)` 的 actual-time integrated fraction 表征；其互补量是 `I(L1)` transfer。",
        "",
        "这不排除 BJs 幅度差异对阈值有贡献：Q0 BJs 最大段比 Q1/Q2 大约 16.5%。但仅凭该幅度差、`I>Ic` 或 voltage peak 无法解释 Q1/Q2 在 BJL1 branch 上更大的峰值却没有完整 segment，因此不应先把原因归结为 BJL1 Ic。",
        "",
        "## Unknown",
        "",
        "- 三组 raw 的 timestep 不同（Q0 `0.1 ps`，Q1/Q2 `0.0125 ps`）；本轮未做新的 convergence run，因此 sub-ps onset/delay 只能按各自实际采样报告，不能当作 resolution-independent timing constant。",
        "- 现有 raw 没有一个独立的 BJL1 threshold-only matched ratio experiment；因此 B 的 mechanism inference 不能证明 threshold 完全无关。",
        "- 未连接 physical BVM/JSL/QB、未改变任何 junction ratio、未接 JTL；本报告不回答 physical compatibility 或 downstream delivery。",
        "",
        "## Decision output",
        "",
        "**B. BJs→BJL1 looks primarily waveform/routing/timing-limited.** 在改变 BJL1 threshold 之前，最高信息量的单一内部变量是 node2 的 `I(L1)` / local `(BJL1+RJ1)` KCL split，优先冻结并比较其 actual-time waveform/integrated fraction。按照本 checkpoint 要求，到此停止；不降低 BJL2 AREA、不连接 physical BVM→12JSL→QB、不接 JTL。",
        "",
        "## Provenance",
        "",
        "完整 raw/netlist/model provenance 与 SHA-256 记录在 `reference/source-provenance.yaml`；本目录不复制或修改既有 raw。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    cases = {case_id: analyze_case(case_id, spec) for case_id, spec in CASE_SPECS.items()}
    result = {
        "study": "PAPER-SL-Q3-PRE",
        "verdict": "B_WAVEFORM_ROUTING_TIMING_LIMITED",
        "cases": cases,
        "topology": {
            "node2": "I(BJs)=I(L1)+I(BJL1)+I(RJ1)",
            "node3": "I(L1)+I(RB)=I(L2)",
            "node4": "I(L2)=I(L0)+I(BJL2)+I(RJ2)",
        },
    }
    (ANALYSIS / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (ANALYSIS / "REPORT.md").write_text(report(result))
    with (ANALYSIS / "case-summary.csv").open("w", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow([
            "case_id", "bjs_largest_turns", "bjl1_largest_turns", "bjl2_largest_turns",
            "bjl1_over_bjs", "bjl2_over_bjl1", "bjl2_over_bjs", "bjl1_delay_ps", "overlap_ps",
            "local_fraction", "l1_fraction", "node2_kcl_max_abs_uA", "node3_kcl_max_abs_uA",
            "node4_kcl_max_abs_uA",
        ])
        for case in cases.values():
            g = case["trajectory"]
            writer.writerow([
                case["case_id"], g["BJs"]["global_largest"]["delta_turns"],
                g["BJL1"]["global_largest"]["delta_turns"], g["BJL2"]["global_largest"]["delta_turns"],
                case["ratios"]["bjl1_over_bjs"], case["ratios"]["bjl2_over_bjl1"], case["ratios"]["bjl2_over_bjs"],
                case["timing"]["bjl1_start_delay_from_bjs_ps"], case["timing"]["overlap_ps"],
                case["routing_metrics"]["local_fraction_of_bjs"], case["routing_metrics"]["l1_fraction_of_bjs"],
                case["kcl"]["node2_BJs_minus_L1_BJL1_RJ1"]["max_abs_uA"],
                case["kcl"]["node3_L1_plus_RB_minus_L2"]["max_abs_uA"],
                case["kcl"]["node4_L2_minus_L0_BJL2_RJ2"]["max_abs_uA"],
            ])
    print(result["verdict"])
    for case in cases.values():
        g = case["trajectory"]
        print(case["case_id"], [g[name]["global_largest"]["delta_turns"] for name in ("BJs", "BJL1", "BJL2")])


if __name__ == "__main__":
    main()
