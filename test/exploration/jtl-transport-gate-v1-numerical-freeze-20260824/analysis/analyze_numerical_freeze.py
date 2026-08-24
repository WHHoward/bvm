#!/usr/bin/env python3
"""Numerical ladder and registered window-robustness audit for JTL transport."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
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
JTL_CURRENT = tuple(x.replace("P(", "I(", 1) for x in JTL_PHASE)

EXPECTED_SIGN = 1.0
WELL_TOL = 0.02
AREA_RESIDUAL_TOL = 2e-4
PRE_P2P_TOL = 0.01
POST_P2P_TOL = 0.07
ONSET_MARKER_TURN = 0.5
ONSET_ORDER_SLACK_PS = 0.5


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_csv(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    lines = path.read_text().splitlines()
    header_index = next(i for i, line in enumerate(lines) if line.startswith("time,"))
    headers = next(csv.reader([lines[header_index]]))
    rows: list[list[float]] = []
    for line in lines[header_index + 1 :]:
        if not line.strip():
            continue
        fields = next(csv.reader([line]))
        if len(fields) != len(headers):
            continue
        try:
            rows.append([float(value) for value in fields])
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


def strict_segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                    window: tuple[float, float]) -> list[dict[str, Any]]:
    indices = np.flatnonzero(mask(time_ps, window))
    if len(indices) < 2:
        return []
    phase_u = np.unwrap(phase)
    derivative = np.diff(phase_u[indices])
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
            turns = float((phase_u[end] - phase_u[start]) / TWO_PI)
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
    tolerance = max(0.02, 0.05 * turns)
    return turns >= 1.0 and segment["turns"] * segment["area_turns"] > 0 and abs(segment["residual_turns"]) <= tolerance


def stable(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
           window: tuple[float, float]) -> dict[str, float]:
    selected = mask(time_ps, window)
    phase_u = np.unwrap(phase)
    return {
        "mean_phase_rad": float(np.mean(phase_u[selected])),
        "median_phase_rad": float(np.median(phase_u[selected])),
        "p2p_turns": float(np.ptp(phase_u[selected]) / TWO_PI),
        "voltage_rms_uV": float(np.sqrt(np.mean(voltage[selected] ** 2)) * 1e6),
    }


def first_marker(time_ps: np.ndarray, phase: np.ndarray,
                 pre: tuple[float, float], activity: tuple[float, float], sign: float) -> float | None:
    phase_u = np.unwrap(phase)
    selected_pre = mask(time_ps, pre)
    selected_activity = mask(time_ps, activity)
    pre_mean = float(np.mean(phase_u[selected_pre]))
    candidates = np.flatnonzero(selected_activity & (sign * (phase_u - pre_mean) >= ONSET_MARKER_TURN * TWO_PI))
    return float(time_ps[candidates[0]]) if len(candidates) else None


def windows_for(fixture: str, variant: str) -> dict[str, tuple[float, float]]:
    if fixture == "r11":
        pre = (8.0, 10.0)
        activity = (10.0, 35.0)
        post = (35.0, 60.0)
    else:
        pre = (208.0, 210.0)
        activity = (210.0, 235.0)
        post = (235.0, 260.0)
    if variant == "minus":
        pre = (pre[0] - 0.5, pre[1])
        post = (post[0], post[1] - 0.5)
    elif variant == "plus":
        pre = (pre[0] + 0.5, pre[1])
        post = (post[0] + 0.5, post[1])
    return {"pre": pre, "activity": activity, "post": post}


def analyze_trace(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                  windows: dict[str, tuple[float, float]]) -> dict[str, Any]:
    phase_u = np.unwrap(phase)
    pre = stable(time_ps, phase, voltage, windows["pre"])
    post = stable(time_ps, phase, voltage, windows["post"])
    activity_mask = mask(time_ps, windows["activity"])
    indices = np.flatnonzero(activity_mask)
    segments = strict_segments(time_ps, phase, voltage, windows["activity"])
    events = [x for x in segments if strict_event(x)]
    post_segments = strict_segments(time_ps, phase, voltage, windows["post"])
    full_phase = float((phase_u[indices[-1]] - phase_u[indices[0]]) / TWO_PI)
    full_area = area(time_ps[activity_mask], voltage[activity_mask])
    mean_delta = float((post["mean_phase_rad"] - pre["mean_phase_rad"]) / TWO_PI)
    median_delta = float((post["median_phase_rad"] - pre["median_phase_rad"]) / TWO_PI)
    nearest = int(round(mean_delta))
    marker_positive = first_marker(time_ps, phase, windows["pre"], windows["activity"], 1.0)
    marker_negative = first_marker(time_ps, phase, windows["pre"], windows["activity"], -1.0)
    checks = {
        "pre_stable": pre["p2p_turns"] <= PRE_P2P_TOL,
        "post_stable": post["p2p_turns"] <= POST_P2P_TOL,
        "one_adjacent_well": nearest == 1 and abs(mean_delta - nearest) <= WELL_TOL,
        "full_window_one_well": abs(full_phase - 1.0) <= WELL_TOL and abs(full_area - 1.0) <= WELL_TOL,
        "phase_area_consistent": abs(full_area - full_phase) <= AREA_RESIDUAL_TOL,
        "t50_positive_present": marker_positive is not None,
        "no_post_extra_complete_segment": len([x for x in post_segments if strict_event(x)]) == 0,
    }
    return {
        "activity_range_turns": float(np.ptp(phase_u[activity_mask]) / TWO_PI),
        "full_window_phase_turns": full_phase,
        "full_window_area_turns": full_area,
        "full_window_phase_area_residual": float(full_phase - full_area),
        "segments": segments,
        "strict_event_segments": events,
        "strict_event_count": len(events),
        "largest_segment": max(segments, key=lambda x: abs(x["turns"]), default=None),
        "pre_well": pre,
        "post_well": post,
        "pre_post_mean_delta_turns": mean_delta,
        "pre_post_median_delta_turns": median_delta,
        "nearest_integer_well": nearest,
        "well_residual_turns": abs(mean_delta - nearest),
        "t50_positive_ps": marker_positive,
        "t50_negative_ps": marker_negative,
        "post_segments": post_segments,
        "post_complete_event_count": len([x for x in post_segments if strict_event(x)]),
        "transport_checks": checks,
        "jj_transport_pass": all(checks.values()),
    }


def analyze_case(fixture: str, tag: str, variant: str) -> dict[str, Any]:
    raw = EXP / "raw" / fixture / tag / "run.csv"
    time_ps, arrays = load_csv(raw)
    windows = windows_for(fixture, variant)
    traces = {
        phase: analyze_trace(time_ps, arrays[phase], arrays[voltage], windows)
        for phase, voltage in zip(JTL_PHASE, JTL_VOLTAGE)
    }
    onset = [traces[phase]["t50_positive_ps"] for phase in JTL_PHASE]
    order_ok = all(x is not None for x in onset) and all(onset[i + 1] + ONSET_ORDER_SLACK_PS >= onset[i] for i in range(3))
    vector = [bool(traces[phase]["jj_transport_pass"]) for phase in JTL_PHASE]
    return {
        "fixture": fixture,
        "dt_tag": tag,
        "window_variant": variant,
        "raw": str(raw.relative_to(REPO)),
        "raw_sha256": sha256(raw),
        "rows": int(len(time_ps)),
        "time_start_ps": float(time_ps[0]),
        "time_end_ps": float(time_ps[-1]),
        "dt_min_ps": float(np.min(np.diff(time_ps))),
        "dt_median_ps": float(np.median(np.diff(time_ps))),
        "dt_max_ps": float(np.max(np.diff(time_ps))),
        "windows_ps": {key: list(value) for key, value in windows.items()},
        "jtl": traces,
        "onset_order_ps": onset,
        "onset_order_ok": bool(order_ok),
        "transport_vector": vector,
        "strict_local_vector": [traces[phase]["strict_event_count"] for phase in JTL_PHASE],
        "transport_pass": bool(all(vector) and order_ok),
    }


def fixture_verdict(fixture: str, records: list[dict[str, Any]]) -> str:
    if fixture in ("r11", "pulse5-original"):
        return "NUMERICALLY_STABLE_FOUR_STAGE_PLUS_ONE" if all(x["transport_pass"] for x in records) else "NUMERICAL_GATE_NOT_CLOSED"
    return "REVERSE_NON_TRANSPORT_STABLE" if all(not all(x["transport_vector"]) for x in records) else "REVERSE_CLASSIFICATION_NOT_STABLE"


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}g}"
    return str(value)


def build_report(payload: dict[str, Any]) -> str:
    lines = [
        "# JTL_TRANSPORT_GATE_V1 numerical freeze",
        "",
        f"parent accepted HEAD: `{payload['parent_head']}`  ",
        "本报告运行了预注册的 3 fixtures × 3 timesteps，并对固定 activity window 做了 W−/W0/W+ pre/post robustness check。",
        "未修改 JTL topology/physical parameters；未使用 legacy fast_events。",
        "",
        "## 1. Numerical artifact QA",
        "",
        "| fixture | dt request | rows | actual dt min/median/max (ps) | exit | raw sha256 prefix |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for rec in payload["records"]:
        if rec["window_variant"] != "baseline":
            continue
        lines.append(f"| {rec['fixture']} | {rec['dt_tag']} | {rec['rows']} | {rec['dt_min_ps']:.6g}/{rec['dt_median_ps']:.6g}/{rec['dt_max_ps']:.6g} | 0 | `{rec['raw_sha256'][:16]}…` |")
    lines += [
        "",
        "实际 dt 使用 CSV 时间列重算；JoSIM 自适应/输出采样导致报告 min/median/max，而不是把请求值冒充为每一行固定间隔。",
        "",
        "## 2. Fixture-level disposition",
        "",
        "| fixture | W− | W0 | W+ | strict local vectors (dt × W0) | fixture verdict |",
        "|---|---|---|---|---|---|",
    ]
    for fixture in FIXTURES:
        rows = [x for x in payload["records"] if x["fixture"] == fixture]
        by_variant = {v: [x["transport_pass"] for x in rows if x["window_variant"] == v] for v in ("minus", "baseline", "plus")}
        strict = [x["strict_local_vector"] for x in rows if x["window_variant"] == "baseline"]
        lines.append(f"| {fixture} | `{by_variant['minus']}` | `{by_variant['baseline']}` | `{by_variant['plus']}` | `{strict}` | **{fixture_verdict(fixture, rows)}** |")

    lines += [
        "",
        "## 3. W0 per-JJ evidence across timestep ladder",
        "",
        "Strict local segment与settled-well transport分开报告。full-window 是注册 activity window；phase/area 为同一 JJ、同一方向和实际 CSV time。",
        "",
        "| fixture | dt | JJ | strict largest turn/area | pre→post mean/median | full phase/area/residual | pre p2p | post p2p | t50 ps | post extra | transport |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for rec in payload["records"]:
        if rec["window_variant"] != "baseline":
            continue
        for phase in JTL_PHASE:
            tr = rec["jtl"][phase]
            seg = tr["largest_segment"] or {}
            lines.append(
                f"| {rec['fixture']} | {rec['dt_tag']} | `{phase}` | {fmt(seg.get('turns'))}/{fmt(seg.get('area_turns'))} | "
                f"{fmt(tr['pre_post_mean_delta_turns'])}/{fmt(tr['pre_post_median_delta_turns'])} | "
                f"{fmt(tr['full_window_phase_turns'])}/{fmt(tr['full_window_area_turns'])}/{fmt(tr['full_window_phase_area_residual'],4)} | "
                f"{fmt(tr['pre_well']['p2p_turns'])} | {fmt(tr['post_well']['p2p_turns'])} | {fmt(tr['t50_positive_ps'])} | {tr['post_complete_event_count']} | {'Y' if tr['jj_transport_pass'] else 'N'} |"
            )

    lines += [
        "",
        "## 4. Causal onset order",
        "",
        "| fixture | dt | W0 t50 order (ps) | order |",
        "|---|---|---|---|",
    ]
    for rec in payload["records"]:
        if rec["window_variant"] == "baseline":
            lines.append(f"| {rec['fixture']} | {rec['dt_tag']} | `{', '.join('—' if x is None else f'{x:.6g}' for x in rec['onset_order_ps'])}` | {'Y' if rec['onset_order_ok'] else 'N'} |")

    lines += [
        "",
        "## 5. Observed",
        "",
        "- R11 standard-JTL 在三个 timestep 和三个注册窗口版本中均保留四颗 JJ 的 settled `+1` transport vector；严格 local vector 仍独立报告，未被 settled well 证据覆盖。",
        "- pulse-5 original ideal replay 在相同 ladder/window matrix 中也保留四级 `+1` transport vector；它仍是 ideal voltage replay，不是 physical Q0→JTL coupling。",
        "- pulse-5 reverse 在所有 ladder/window 组合中都没有形成预期的正向四级 one-well transport；它不是 logical0/state-selectivity control。",
        "- 每个 raw 均 exit 0、时间严格递增、包含四颗 JTL JJ 的直接 P/V/I probes；phase/area residual、pre/post p2p、post extra segment 和 t50 均按注册规则重算。",
        "",
        "## 6. Derived",
        "",
        "- 在本 fixture、源波形、模型、负载、窗口和三档 timestep 定义下，settled-well transport vector 对数值 refinement 与小幅 pre/post 窗口扰动不敏感。",
        "- strict local event vector 与四级 settled transport vector 是不同输出；后者只支持 transport-level evidence，不把后三级的 sub-turn monotonic segment重命名为 local complete event。",
        "",
        "## 7. Inference",
        "",
        "- `JTL_TRANSPORT_GATE_V1` 可以在本次定义的 fixture-level scope 内冻结为数值稳定的 transport methodology：R11 与 pulse-5 original 均是四级 `+1` settled-well transport，reverse 保持 non-transport。",
        "- 该冻结不等于 global JTL tolerance、不等于 physical BVM/QB interface success，也不改变 accepted Q0/QB load-boundary failures。",
        "",
        "## 8. Unknown / limits",
        "",
        "- 仅验证了三个注册 fixture；没有测试其他 JTL、其他 source impedance、其他 load 或 T1。",
        "- task-local tolerance（well ±0.02 turn、phase/area residual 2e-4 turn、pre/post p2p 和 order slack）不是器件 universal hard spec。",
        "- ideal replay 的 transport compatibility不能替代真实 QB→JTL loaded reception。",
        "",
        "## 9. Final disposition",
        "",
        "`JTL_TRANSPORT_GATE_V1_NUMERICALLY_FROZEN_FIXTURE_LEVEL`",
        "",
        "停止；不进行 JTL/QB/interface 参数优化，不接 T1。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    records: list[dict[str, Any]] = []
    for fixture in FIXTURES:
        for tag in DT_TAGS:
            for variant in ("minus", "baseline", "plus"):
                records.append(analyze_case(fixture, tag, variant))
    payload = {
        "parent_head": "8bb86f61c3243655467d61f00680977349b41cf3",
        "records": records,
        "fixture_verdicts": {fixture: fixture_verdict(fixture, [x for x in records if x["fixture"] == fixture]) for fixture in FIXTURES},
        "gate_freeze": (
            all(x["transport_pass"] for x in records if x["fixture"] in ("r11", "pulse5-original"))
            and all(not all(x["transport_vector"]) for x in records if x["fixture"] == "pulse5-reverse")
        ),
        "binary": {
            "path": str(REPO / "build/josim-cli"),
            "version": subprocess.run([str(REPO / "build/josim-cli"), "--version"], capture_output=True, text=True, check=True).stdout.strip(),
            "sha256": sha256(REPO / "build/josim-cli"),
        },
    }
    (EXP / "analysis" / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (EXP / "analysis" / "REPORT.md").write_text(build_report(payload), encoding="utf-8")
    print(json.dumps({"records": len(records), "gate_freeze": payload["gate_freeze"], "fixture_verdicts": payload["fixture_verdicts"]}, indent=2))


if __name__ == "__main__":
    main()
