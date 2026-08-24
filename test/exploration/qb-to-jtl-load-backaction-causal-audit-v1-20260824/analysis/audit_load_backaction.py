#!/usr/bin/env python3
"""Causal current-partition audit for the frozen Q0 load-boundary fixtures."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
EXP = HERE.parent
REPO = EXP.parents[2]
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi

MATRIX_ANALYZER = REPO / "test/exploration/qb-load-boundary-matrix-20260824/analysis/analyze_matrix.py"
spec = importlib.util.spec_from_file_location("matrix_analyzer", MATRIX_ANALYZER)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load accepted matrix parser")
matrix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(matrix)

CASES: dict[str, Path] = {
    "Q0_10ohm": REPO / "test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv",
    "Q0_OPEN": REPO / "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/A-q0-open/scaled-iin-68p4u.csv",
    "Q0_JTL_ONLY": REPO / "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/B-q0-jtl-only/scaled-iin-68p4u.csv",
    "Q0_10ohm_PARALLEL_JTL": REPO / "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.csv",
    "M3_SERIES_10ohm_JTL": REPO / "test/exploration/parallel-qb-jtl-interface-mechanism-20260824/raw-v2/M3-rseries10/run.csv",
}

PULSE5_ACTIVITY = (210.0, 235.0)
PULSE5_POST = (235.0, 259.0)
PULSE5_PRE = (208.0, 210.0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_raw(path: Path) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    # The Q0 standalone parent is comma CSV; the load-boundary and M3 runs
    # are JoSIM fixed-width output with progress text before the data header.
    first_data = next((line for line in path.read_text().splitlines() if line.startswith("time")), None)
    if first_data is not None and "," in first_data:
        lines = path.read_text().splitlines()
        header_index = next(i for i, line in enumerate(lines) if line.startswith("time,"))
        names = next(csv.reader([lines[header_index]]))
        rows: list[list[float]] = []
        for line in lines[header_index + 1 :]:
            if not line.strip():
                continue
            values = next(csv.reader([line]))
            if len(values) == len(names):
                try:
                    rows.append([float(value) for value in values])
                except ValueError:
                    pass
        matrix_data = np.asarray(rows, dtype=float)
        arrays = {name: matrix_data[:, index] for index, name in enumerate(names)}
        time_ps = arrays.pop("time") * 1e12
    else:
        time_ps, arrays, _ = matrix.load_raw(path)
    if len(time_ps) < 2 or not np.all(np.isfinite(time_ps)) or not np.all(np.diff(time_ps) > 0):
        raise ValueError(f"invalid time axis: {path}")
    if any(not np.all(np.isfinite(values)) for values in arrays.values()):
        raise ValueError(f"non-finite data: {path}")
    return time_ps, arrays


def get(arrays: dict[str, np.ndarray], name: str) -> np.ndarray | None:
    if name in arrays:
        return arrays[name]
    normalized = {"".join(key.split()).lower(): key for key in arrays}
    return arrays.get(normalized.get("".join(name.split()).lower(), ""))


def mask(time_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (time_ps >= window[0]) & (time_ps < window[1])


def trapz(time_ps: np.ndarray, values: np.ndarray) -> float:
    return float(np.trapezoid(values, time_ps * 1e-12))


def stats(values: np.ndarray, scale: float = 1.0) -> dict[str, float]:
    values = values * scale
    return {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "rms": float(np.sqrt(np.mean(values * values))),
        "p2p": float(np.ptp(values)),
    }


def phase_segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                   window: tuple[float, float]) -> list[dict[str, Any]]:
    active = mask(time_ps, window)
    return matrix.monotonic_segments(time_ps, np.unwrap(phase), voltage, active)


def phase_summary(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray,
                  current: np.ndarray, window: tuple[float, float]) -> dict[str, Any]:
    active = mask(time_ps, window)
    phase_u = np.unwrap(phase)
    records = phase_segments(time_ps, phase, voltage, window)
    forward = [x for x in records if x["direction"] == "positive"]
    backward = [x for x in records if x["direction"] == "negative"]
    largest = max(records, key=lambda x: x["magnitude_turns"], default=None)
    largest_forward = max(forward, key=lambda x: x["magnitude_turns"], default=None)
    largest_backward = max(backward, key=lambda x: x["magnitude_turns"], default=None)
    qualifying = [x for x in records if matrix.qualifies(x)]
    return {
        "window_ps": list(window),
        "phase_range_turns": float(np.ptp(phase_u[active]) / TWO_PI),
        "window_delta_turns": float((phase_u[np.flatnonzero(active)[-1]] - phase_u[np.flatnonzero(active)[0]]) / TWO_PI),
        "window_area_turns": float(trapz(time_ps[active], voltage[active]) / PHI0),
        "window_phase_area_residual_turns": float(
            trapz(time_ps[active], voltage[active]) / PHI0
            - (phase_u[np.flatnonzero(active)[-1]] - phase_u[np.flatnonzero(active)[0]]) / TWO_PI
        ),
        "largest_segment": largest,
        "largest_forward": largest_forward,
        "largest_backward": largest_backward,
        "complete_event_count": int(len(qualifying)),
        "complete_event_units": int(sum(math.floor(abs(x["delta_turns"])) for x in qualifying)),
        "current_uA": stats(current[active], 1e6),
        "voltage_uV": stats(voltage[active], 1e6),
    }


def current_partition(time_ps: np.ndarray, arrays: dict[str, np.ndarray],
                      window: tuple[float, float]) -> dict[str, Any]:
    active = mask(time_ps, window)
    result: dict[str, Any] = {"window_ps": list(window)}
    for label, column in (
        ("I_L2", "I(L2|XBQ)"),
        ("I_L0", "I(L0|XBQ)"),
        ("I_BJL2", "I(BJL2|XBQ)"),
        ("I_RJ2", "I(RJ2|XBQ)"),
        ("V_OUT", "V(OUT)"),
    ):
        values = get(arrays, column)
        if values is not None:
            result[label] = stats(values[active], 1e6 if label.startswith("I_") else 1e6)
    l2, l0, bjl2, rj2 = (get(arrays, x) for x in ("I(L2|XBQ)", "I(L0|XBQ)", "I(BJL2|XBQ)", "I(RJ2|XBQ)"))
    if all(x is not None for x in (l2, l0, bjl2, rj2)):
        residual = l2[active] - l0[active] - bjl2[active] - rj2[active]
        result["node4_kcl_residual_uA"] = stats(residual, 1e6)
    for label, column in (
        ("JTL_input_I", "I(L1|XJTL1)"),
        ("I_RLOAD", "I(R_LOAD)"),
        ("I_RSER", "I(R_SER)"),
    ):
        values = get(arrays, column)
        if values is not None:
            result[label] = stats(values[active], 1e6)
    # Dissipation is ∫ I^2 R dt. Values are reported in pJ.
    for label, column, resistance in (
        ("E_RJ2_pJ", "I(RJ2|XBQ)", 22.0),
        ("E_RLOAD_pJ", "I(R_LOAD)", 10.0),
        ("E_RSER_pJ", "I(R_SER)", 10.0),
    ):
        values = get(arrays, column)
        if values is not None:
            energy_j = trapz(time_ps[active], values[active] ** 2 * resistance)
            result[label] = float(energy_j * 1e12)
    return result


def jtl_summary(time_ps: np.ndarray, arrays: dict[str, np.ndarray]) -> dict[str, Any] | None:
    names = ("B1|XJTL1", "B2|XJTL1", "B1|XJTL2", "B2|XJTL2")
    result: dict[str, Any] = {}
    present = False
    for name in names:
        phase = get(arrays, f"P({name})")
        voltage = get(arrays, f"V({name})")
        current = get(arrays, f"I({name})")
        if phase is None or voltage is None or current is None:
            continue
        present = True
        result[name] = phase_summary(time_ps, phase, voltage, current, PULSE5_ACTIVITY)
    return result if present else None


def main() -> None:
    loaded: dict[str, tuple[np.ndarray, dict[str, np.ndarray]]] = {}
    for name, path in CASES.items():
        loaded[name] = load_raw(path)

    ref_time, ref_arrays = loaded["Q0_10ohm"]
    ref_segments = phase_segments(ref_time, get(ref_arrays, "P(BJL2|XBQ)"), get(ref_arrays, "V(BJL2|XBQ)"), PULSE5_ACTIVITY)
    ref_events = [x for x in ref_segments if matrix.qualifies(x)]
    if len(ref_events) != 1:
        raise RuntimeError(f"expected one registered Q0+10ohm pulse-5 BJL2 segment, found {len(ref_events)}")
    ref_event = ref_events[0]
    crossing = (float(ref_event["start_ps"]), float(ref_event["end_ps"]))
    regions = {
        "pre_crossing": (PULSE5_PRE[0], crossing[0]),
        "crossing": crossing,
        "retrap_post": (crossing[1], PULSE5_POST[1]),
    }

    cases: dict[str, Any] = {}
    for name, (time_ps, arrays) in loaded.items():
        phase = get(arrays, "P(BJL2|XBQ)")
        voltage = get(arrays, "V(BJL2|XBQ)")
        current = get(arrays, "I(BJL2|XBQ)")
        if any(x is None for x in (phase, voltage, current)):
            raise RuntimeError(f"missing BJL2 probe in {name}")
        cases[name] = {
            "raw": str(CASES[name].relative_to(REPO)),
            "raw_sha256": sha256(CASES[name]),
            "rows": len(time_ps),
            "time_ps": [float(time_ps[0]), float(time_ps[-1])],
            "bjl2": {
                "activity": phase_summary(time_ps, phase, voltage, current, PULSE5_ACTIVITY),
                "pre": phase_summary(time_ps, phase, voltage, current, PULSE5_PRE),
                "post": phase_summary(time_ps, phase, voltage, current, PULSE5_POST),
            },
            "regions": {key: current_partition(time_ps, arrays, window) for key, window in regions.items()},
            "jtl": jtl_summary(time_ps, arrays),
            "available": sorted(arrays),
        }

    payload = {
        "parent_head": "8bb86f61c3243655467d61f00680977349b41cf3",
        "reference_event": ref_event,
        "regions_ps": {key: list(value) for key, value in regions.items()},
        "cases": cases,
    }
    (EXP / "analysis" / "results.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (EXP / "analysis" / "REFERENCE_EVENT.md").write_text(
        "# Registered Q0+10Ω pulse-5 reference event\n\n"
        f"Source: `{CASES['Q0_10ohm'].relative_to(REPO)}`\n\n"
        f"The single qualifying BJL2 segment is `{ref_event['start_ps']:.9g}..{ref_event['end_ps']:.9g} ps`, "
        f"delta `{ref_event['delta_turns']:.9g} turn`, direct area `{ref_event['area_turns']:.9g} Phi0`, "
        f"residual `{ref_event['area_residual_turns']:.9g} turn`.\n",
        encoding="utf-8",
    )
    (EXP / "analysis" / "REPORT.md").write_text(make_report(payload), encoding="utf-8")
    print(json.dumps({"reference_event": ref_event, "regions": regions, "cases": list(cases)}, indent=2))


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, (int, float)):
        return f"{value:.{digits}g}"
    return str(value)


def segment_text(segment: dict[str, Any] | None) -> str:
    if not segment:
        return "—"
    return f"{segment['direction']} {segment['delta_turns']:.6g} turn / {segment['area_turns']:.6g} Φ0 ({segment['start_ps']:.6g}–{segment['end_ps']:.6g} ps)"


def make_report(payload: dict[str, Any]) -> str:
    cases = payload["cases"]
    ref = payload["reference_event"]
    lines = [
        "# QB_TO_JTL_LOAD_BACKACTION_CAUSAL_AUDIT_V1",
        "",
        f"parent accepted HEAD: `{payload['parent_head']}`  ",
        "本报告只审计已接受 raw；没有参数 sweep、没有 topology 改动、没有新 JoSIM run。",
        "所有 phase 为 raw rad 解包后换算的 turns；电压面积使用同一 JJ、同一窗口和 CSV 实际时间轴。",
        "",
        "## 1. Registered reference and regions",
        "",
        f"Q0+10Ω pulse-5 reference BJL2 segment: `{ref['start_ps']:.6g}–{ref['end_ps']:.6g} ps`, "
        f"`{ref['delta_turns']:.6g} turn`, same-segment area `{ref['area_turns']:.6g} Φ0`, residual `{ref['area_residual_turns']:.6g} turn`.",
        "",
        "| region | window (ps) | meaning |",
        "|---|---:|---|",
    ]
    for name, window in payload["regions_ps"].items():
        meaning = {"pre_crossing": "settled state before registered crossing", "crossing": "same reference event interval", "retrap_post": "event end through registered post window"}[name]
        lines.append(f"| {name} | `{window[0]:g}–{window[1]:g}` | {meaning} |")

    lines += [
        "",
        "## 2. Local fixture verdicts",
        "",
        "| case | BJL2 activity range | largest segment | same-window phase / area | complete event units | JTL local status |",
        "|---|---:|---|---:|---:|---|",
    ]
    for name, case in cases.items():
        activity = case["bjl2"]["activity"]
        jtl_status = "not attached"
        if case["jtl"] is not None:
            jtl_status = "; ".join(
                f"{jj}: {fmt(v['largest_segment']['delta_turns'] if v['largest_segment'] else None, 4)} turn/{v['complete_event_count']}"
                for jj, v in case["jtl"].items()
            )
        lines.append(
            f"| {name} | {fmt(activity['phase_range_turns'], 8)} turn | {segment_text(activity['largest_segment'])} | "
            f"{fmt(activity['window_delta_turns'], 8)} / {fmt(activity['window_area_turns'], 8)} | "
            f"{activity['complete_event_units']} | {jtl_status} |"
        )

    lines += [
        "",
        "## 3. Node-4 current partition and KCL",
        "",
        "Values are region min/max/mean/p2p in µA. The requested KCL is `I(L2)=I(L0)+I(BJL2)+I(RJ2)`; residuals are reported as `L2−L0−BJL2−RJ2`.",
        "",
        "| case | region | I(L2) mean/p2p | I(L0) mean/p2p | I(BJL2) mean/p2p | I(RJ2) mean/p2p | KCL RMS/max µA |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for name, case in cases.items():
        for region in ("pre_crossing", "crossing", "retrap_post"):
            d = case["regions"][region]
            def mp(k: str) -> str:
                x = d.get(k)
                return "—" if not x else f"{x['mean']:.6g}/{x['p2p']:.6g}"
            res = d.get("node4_kcl_residual_uA")
            residual = "—" if not res else f"{res['rms']:.4g}/{max(abs(res['min']),abs(res['max'])):.4g}"
            lines.append(f"| {name} | {region} | {mp('I_L2')} | {mp('I_L0')} | {mp('I_BJL2')} | {mp('I_RJ2')} | {residual} |")

    lines += [
        "",
        "## 4. Interface branch and dissipation",
        "",
        "Current values are mean/p2p in µA; energies are pJ over the registered region. Missing branches are not inferred.",
        "",
        "| case | region | JTL input I mean/p2p | R_LOAD I mean/p2p | R_SER I mean/p2p | E_RJ2 | E_RLOAD | E_RSER |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, case in cases.items():
        for region in ("pre_crossing", "crossing", "retrap_post"):
            d = case["regions"][region]
            def branch(k: str) -> str:
                x = d.get(k)
                return "—" if not x else f"{x['mean']:.6g}/{x['p2p']:.6g}"
            lines.append(f"| {name} | {region} | {branch('JTL_input_I')} | {branch('I_RLOAD')} | {branch('I_RSER')} | {fmt(d.get('E_RJ2_pJ'),5)} | {fmt(d.get('E_RLOAD_pJ'),5)} | {fmt(d.get('E_RSER_pJ'),5)} |")

    lines += [
        "",
        "## 5. Observed",
        "",
        "- accepted Q0+10Ω 在 pulse 5 的 BJL2 有一个约 `1.0960 turn / 1.0965 Φ0` 的同段 local event；节点 4 KCL residual 在 crossing 的 RMS 约 `1.35e-5 µA`，说明当前 probe 方向闭合。",
        "- Q0 OPEN 的同一窗口最大 BJL2 段约 `3.1477 turn`，对应约三个 event units；它不是 exactly-one 边界。",
        "- Q0 JTL-only 与 Q0 10Ω||JTL 在 crossing 前已处于不同 settled load-line：`I(L0)` 约 `−18.53 µA`、`I(BJL2)` 约 `33.27 µA`，而 accepted 10Ω 是约 `0`/`19.88 µA`。两者的 BJL2 最大段分别约 `0.3567`/`0.3115 turn`，无 complete event。",
        "- M3 series-10Ω→JTL 在 crossing 前接近 accepted Q0+10Ω 的 settled partition；BJL2 仍有约 `1.0889 turn / 1.0894 Φ0` local event，但 series branch 在 crossing 承担约 `90.05 µA` p2p/mean量级的 transient，JTL仍未形成 complete transport event。",
        "- Q0 10Ω、M3、OPEN 的 crossing 中 `I(L2)`、`I(L0)`/interface branch、`I(BJL2)` 和 `I(RJ2)` 都发生同步重分配；因此单一静态阻抗不能描述全部行为。",
        "",
        "## 6. Derived",
        "",
        "- `I(L2)=I(L0)+I(BJL2)+I(RJ2)` 在所有可审计区间的数值 residual 为 pA/亚-pA 量级到数十 pA（显示单位为 µA），与 JoSIM 输出精度相容；未把 residual 设为零。",
        "- 直接 JTL-only/parallel 的 pre-crossing bias split 已改变，说明 load boundary 在 barrier crossing 之前就改变了 operating point，而不是仅影响 event 后 retrap。",
        "- M3 保留 BJL2 event 但 JTL 未触发，说明“BJL2 local event 被保存”和“JTL 接收”是两个独立证据层；series branch 的 event preservation 不能升级为 transport success。",
        "",
        "## 7. Inference",
        "",
        "- 最符合本冻结矩阵的机制是 `MIXED_DYNAMIC_LOADING`：直接/并联 JTL 先改变 settled current partition，再在 crossing 中分流并改变 `L2→L0/BJL2/RJ2` 轨迹；M3 则显示一个不同的 series boundary 可保留 local event，但仍不足以给 JTL 标准输入事件。",
        "- 证据不支持把失败只归因于 retrap：direct/parallel 在 complete BJL2 crossing 之前已经没有完整 crossing；也不支持把 Q0 event loss 简化成一个等效电阻。",
        "",
        "## 8. Unknown / limits",
        "",
        "- 本审计只覆盖已接受的 Q0 fixtures；没有新的 probe-only rerun，没有 canonical BVM，也没有 transformer/interface optimization。",
        "- Q0 OPEN 的多 event 与 accepted 10Ω 的 exactly-one 差异支持 boundary causality，但不冻结一个普适 one-shot load specification。",
        "- M3 JTL 仍是 subthreshold/未传播；本报告没有把其 local BJL2 event称为 downstream SFQ delivery。",
        "",
        "## 9. Final bounded mechanism classification",
        "",
        "`MIXED_DYNAMIC_LOADING`",
        "",
        "停止于本包；不设计或调节 transformer、R/L/Ic/bias，不接 T1。",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
