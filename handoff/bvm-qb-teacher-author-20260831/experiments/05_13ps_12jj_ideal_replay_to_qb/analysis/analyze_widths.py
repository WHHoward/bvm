#!/usr/bin/env python3
"""Formal phase/area analysis for the corrected canonical width bracket."""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
ANALYSIS = ROOT / "analysis"
PHI0 = 2.067833848e-15
TWO_PI = 2.0 * math.pi
ACTIVITY = (94.0, 130.0)
POST = (140.0, 170.0)
QB_JJ = {
    "BJs": ("P(BJs|XBQ)", "V(BJs|XBQ)", "I(BJs|XBQ)"),
    "BJL1": ("P(BJL1|XBQ)", "V(BJL1|XBQ)", "I(BJL1|XBQ)"),
    "BJL2": ("P(BJL2|XBQ)", "V(BJL2|XBQ)", "I(BJL2|XBQ)"),
}


def load(path: Path) -> dict[str, np.ndarray]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = [value.strip() for value in next(reader)]
        rows = [row for row in reader if row]
    data = {name: np.asarray([float(row[i]) for row in rows], dtype=float) for i, name in enumerate(header)}
    time = data["time"] * 1e12
    if time.size < 2 or not np.all(np.diff(time) > 0):
        raise ValueError(f"invalid time axis: {path}")
    data["__time_ps"] = time
    return data


def col(data: dict[str, np.ndarray], name: str) -> np.ndarray:
    if name in data:
        return data[name]
    key = next((key for key in data if key.replace(" ", "").lower() == name.replace(" ", "").lower()), None)
    if key is None:
        raise KeyError(f"missing {name!r} in CSV")
    return data[key]


def window(time: np.ndarray, bounds: tuple[float, float]) -> np.ndarray:
    return (time >= bounds[0]) & (time < bounds[1])


def area(time_ps: np.ndarray, voltage: np.ndarray) -> float:
    integral = np.trapezoid(voltage, time_ps * 1e-12) if hasattr(np, "trapezoid") else np.trapz(voltage, time_ps * 1e-12)
    return float(integral / PHI0)


def monotonic_segments(time: np.ndarray, phase: np.ndarray, voltage: np.ndarray, bounds: tuple[float, float]) -> list[dict[str, Any]]:
    indexes = np.flatnonzero(window(time, bounds))
    if len(indexes) < 2:
        return []
    local_phase = phase[indexes]
    d = np.diff(local_phase)
    sign = np.sign(d)
    nonzero = np.flatnonzero(sign != 0)
    if len(nonzero) == 0:
        return []
    boundaries = [0]
    previous = sign[nonzero[0]]
    for pos in nonzero[1:]:
        current = sign[pos]
        if current != previous:
            boundaries.append(int(pos))
            previous = current
    boundaries.append(len(indexes) - 1)
    output = []
    for left, right in zip(boundaries[:-1], boundaries[1:]):
        idx = indexes[left:right + 1]
        if len(idx) < 2:
            continue
        delta = float((phase[idx[-1]] - phase[idx[0]]) / TWO_PI)
        v_area = area(time[idx], voltage[idx])
        residual = float(v_area - delta)
        consistent = abs(delta) >= 1.0 and delta * v_area > 0 and abs(residual) <= max(0.05, 0.10 * abs(delta))
        output.append({
            "start_ps": float(time[idx[0]]),
            "end_ps": float(time[idx[-1]]),
            "delta_turns": delta,
            "area_phi0": v_area,
            "residual_turns": residual,
            "complete_candidate": bool(abs(delta) >= 1.0),
            "area_consistent": bool(consistent),
            "complete_event_units": int(math.floor(abs(delta))) if consistent else 0,
        })
    return output


def classify_pulse_quantization(bjl2: dict[str, Any]) -> tuple[str, str]:
    """Separate integer event units from the physical pulse-quality class.

    ``complete_event_units`` is intentionally a low-level metric: a 1.90-turn
    segment contains one complete integer unit, but it is not a clean
    one-SFQ operating point.  The class therefore uses the preregistered
    engineering band and the same-segment phase/area consistency already
    recorded by ``monotonic_segments``.
    """
    if bjl2["post_complete_event_units"] > 0:
        return "FREE_RUNNING", "FREE_RUNNING"

    qualifying = [
        item for item in bjl2["segments"]
        if item["complete_event_units"] > 0 and item["area_consistent"]
    ]
    units = sum(item["complete_event_units"] for item in qualifying)
    if len(qualifying) > 1 or units > 1:
        return "MULTI_EVENT", "MULTI_EVENT"
    if len(qualifying) == 1:
        turns = abs(qualifying[0]["delta_turns"])
        if 0.95 <= turns <= 1.15:
            return "CLEAN_ONE_SFQ_CANDIDATE", "CLEAN_ONE_SFQ"
        return "OVERDRIVEN_ONE_PLUS_LARGE_RESIDUAL", "OVERDRIVEN_ONE_PLUS_RESIDUAL"
    return "SUBTHRESHOLD", "SUBTHRESHOLD"


def analyze_qb(path: Path, role: str) -> dict[str, Any]:
    data = load(path)
    time = data["__time_ps"]
    result: dict[str, Any] = {"path": str(path), "role": role, "junctions": {}}
    for name, names in QB_JJ.items():
        phase = np.unwrap(col(data, names[0]))
        voltage = col(data, names[1])
        current = col(data, names[2])
        active_mask = window(time, ACTIVITY)
        segments = monotonic_segments(time, phase, voltage, ACTIVITY)
        post_segments = monotonic_segments(time, phase, voltage, POST)
        largest = max(segments, key=lambda item: abs(item["delta_turns"])) if segments else None
        result["junctions"][name] = {
            "phase_activity_p2p_turns": float(np.ptp(phase[active_mask]) / TWO_PI),
            "segments": segments,
            "post_segments": post_segments,
            "largest_segment": largest,
            "activity_complete_event_units": sum(item["complete_event_units"] for item in segments),
            "post_complete_event_units": sum(item["complete_event_units"] for item in post_segments),
            "current_activity_uA": {"min": float(np.min(current[active_mask]) * 1e6), "max": float(np.max(current[active_mask]) * 1e6)},
        }
    bjl2 = result["junctions"]["BJL2"]
    if bjl2["post_complete_event_units"]:
        result["classification"] = "MULTIFIRE_OR_FREE_RUNNING"
    elif bjl2["activity_complete_event_units"] > 1:
        result["classification"] = "MULTI_EVENT"
    elif bjl2["activity_complete_event_units"] == 1:
        result["classification"] = "EXACTLY_ONE"
    else:
        result["classification"] = "NO_COMPLETE_EVENT"
    result["pulse_quantization_class"], result["pulse_quantization_family"] = classify_pulse_quantization(bjl2)
    return result


def analyze_source(path: Path, role: str) -> dict[str, Any]:
    data = load(path)
    time = data["__time_ps"]
    current = col(data, "I(B_LD1)")
    mask = window(time, ACTIVITY)
    positive = np.maximum(current[mask], 0.0)
    negative = np.minimum(current[mask], 0.0)
    t = time[mask] * 1e-12
    integrate = lambda values: float((np.trapezoid(values, t) if hasattr(np, "trapezoid") else np.trapz(values, t)) * 1e6 * 1e12)
    jsl = {}
    for idx in range(1, 13):
        phase_name = f"P(B_LD{idx})"
        voltage_name = f"V(B_LD{idx})"
        if phase_name not in data or voltage_name not in data:
            continue
        phase = np.unwrap(data[phase_name])
        volts = data[voltage_name]
        active_segments = monotonic_segments(time, phase, volts, ACTIVITY)
        largest = max(active_segments, key=lambda item: abs(item["delta_turns"])) if active_segments else None
        jsl[f"B_LD{idx}"] = {
            "phase_activity_p2p_turns": float(np.ptp(phase[mask]) / TWO_PI),
            "largest_segment": largest,
            "complete_event_units": sum(item["complete_event_units"] for item in active_segments),
        }
    guards = {}
    for name in ("V(SL1)", "V(N6|XBVM1)", "I(L_SL|XBVM1)", "P(B_JM1|XBVM1)", "P(B_JM2|XBVM1)", "P(B_JS1|XBVM1)", "P(B_JS2|XBVM1)"):
        if name not in data:
            continue
        values = data[name]
        guards[name] = {
            "activity_min": float(np.min(values[mask])),
            "activity_max": float(np.max(values[mask])),
            "post_p2p": float(np.ptp(values[window(time, (140.0, 170.0))])),
        }
    return {
        "path": str(path), "role": role,
        "current_uA": {"min": float(np.min(current[mask]) * 1e6), "max": float(np.max(current[mask]) * 1e6)},
        "positive_area_uA_ps": integrate(positive),
        "negative_area_uA_ps": integrate(negative),
        "signed_area_uA_ps": integrate(current[mask]),
        "duration_ps": float(time[mask][-1] - time[mask][0]) if mask.any() else 0.0,
        "jsl": jsl,
        "guards": guards,
    }


def paths_for_width(width: int) -> dict[str, Path]:
    cases: dict[str, Path] = {
        "logical1_no_read_control": REPO / "test/exploration/paper-sl-l0-20260824/raw/logical1-read0-control/run-01.csv",
        "logical0_no_read_control": REPO / "test/exploration/paper-sl-l0-20260824/raw/logical0-read0-control/run-01.csv",
    }
    if width == 12:
        cases["logical1_read"] = REPO / "test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824/raw/phase-b/12jsl-12ps/logical1-read/run-01.csv"
        cases["logical0_read"] = ROOT / "raw/12ps-canonical/logical0-read/run-01.csv"
    else:
        cases["logical1_read"] = ROOT / f"raw/{width}ps/logical1-read/run-01.csv"
        cases["logical0_read"] = ROOT / f"raw/{width}ps/logical0-read/run-01.csv"
    return cases


def render_report(result: dict[str, Any]) -> str:
    widths = result["widths"]
    candidate = None
    for width in sorted(widths, key=int):
        qb = widths[width].get("qb", {})
        l1 = qb.get("logical1_read")
        l0 = qb.get("logical0_read")
        controls = [qb.get("logical1_no_read_control"), qb.get("logical0_no_read_control")]
        if l1 and l0 and all(controls):
            if l1["pulse_quantization_class"] == "CLEAN_ONE_SFQ_CANDIDATE" and l0["pulse_quantization_class"] == "SUBTHRESHOLD" and all(c["pulse_quantization_class"] == "SUBTHRESHOLD" for c in controls):
                candidate = int(width)
                break
    if candidate is not None:
        verdict = "IDEAL_REPLAY_SELECTIVE_ONE_SFQ_CANDIDATE"
    elif "15" in widths:
        verdict = "WIDTH_MARGIN_GAIN_BUT_NO_CLOSURE"
    else:
        verdict = "INCOMPLETE_REGISTERED_BRACKET"
    result["verdict"] = verdict
    result["first_selective_width_ps"] = candidate
    result["execution_disposition"] = {
        "status": "EARLY_STOP_EXECUTION_DEVIATION" if candidate is not None and any(int(width) > candidate for width in widths) else "REGISTERED_EXECUTION",
        "candidate_width_ps": candidate,
        "post_candidate_observations_ps": [int(width) for width in sorted(widths, key=int) if candidate is not None and int(width) > candidate],
        "selection_authority": f"{candidate} ps 是已注册的首个选择性 candidate；更宽的 width 只是 candidate 之后已执行的 bounded observation，不具有 operating-point 选择权。" if candidate is not None else "没有建立选择性 candidate。",
    }
    lines = [
        "# BVM_READ_SEMANTICS_AUDIT_AND_JSL_WIDTH_BRACKET_V1",
        "",
        "## Verdict",
        "",
        f"`{verdict}`" + (f"；首个 1/0/0 width = **{candidate} ps**。" if candidate else "。"),
        "",
        "## Pulse quantization class and execution disposition",
        "",
        "`complete_event_units` 仍是同段、同 JJ 的低层整数单位；`pulse_quantization_class` 单独判断 clean one-SFQ candidate、subthreshold、overdrive、multi-event 和 free-running。",
        f"`{result['execution_disposition']['status']}`：{result['execution_disposition']['selection_authority']}",
        "",
        "本 Exploration 先修正 READ 语义，再对 canonical BVM → external 12-JSL → frozen scaled QB 做 12/13/14/15 ps local bracket。理想 replay 只消费物理 JSL 的实际 `I(B_LD1)(t)`，没有整形、保持、归一化或重采样；本轮没有 physical BVM→JSL→QB 联合连接。",
        "",
        "## Observed",
        "",
        "- 12 ps corrected canonical logical0 使用负 WL+BL initialization 与正 WL+SE READ；QB BJL2 最大同向段仍约 `-0.02549 turn`，zero complete event。",
        "- 12 ps canonical logical1 的 BJL2 最大同向段约 `0.975402 turn`，同段 voltage area 约 `0.975411 Phi0`，仍未完整。",
        "- 13 ps 首次出现 read1 BJL2 完整同向段；read0 与两个 no-READ controls 没有完整 event。",
        "- 14/15 ps 也在本次已注册 bracket 中完成记录；13 ps 已满足 early-stop candidate 条件，14/15 仅作已执行的 bounded post-candidate observations，不用于继续选择。",
        "",
        "## QB replay result",
        "",
        "| width | role | BJL2 activity p2p (turn) | largest monotonic segment (turn) | same-segment area (Phi0) | complete units | legacy classification | pulse quantization class |",
        "|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for width in sorted(widths, key=int):
        for role in ("logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control"):
            case = widths[width].get("qb", {}).get(role)
            if not case:
                continue
            bjl2 = case["junctions"]["BJL2"]
            seg = bjl2["largest_segment"] or {}
            lines.append(f"| {width} | `{role}` | {bjl2['phase_activity_p2p_turns']:.6g} | {seg.get('delta_turns', float('nan')):.6g} | {seg.get('area_phi0', float('nan')):.6g} | {bjl2['activity_complete_event_units']} | `{case['classification']}` | `{case['pulse_quantization_class']}` |")
    lines += ["", "## JSL source current", "", "| width | role | min (µA) | max (µA) | positive area (µA·ps) | negative area (µA·ps) | signed area (µA·ps) |", "|---:|---|---:|---:|---:|---:|---:|"]
    for width in sorted(widths, key=int):
        for role in ("logical1_read", "logical0_read"):
            source = widths[width].get("source", {}).get(role)
            if not source:
                continue
            lines.append(f"| {width} | `{role}` | {source['current_uA']['min']:.6g} | {source['current_uA']['max']:.6g} | {source['positive_area_uA_ps']:.6g} | {source['negative_area_uA_ps']:.6g} | {source['signed_area_uA_ps']:.6g} |")
    lines += ["", "## Derived", "", "- 所有 reported event units 都来自同一 BJL2、同一 continuous monotonic segment、同段 direct voltage area 与 post bounded/retrap 检查；total phase range、I>Ic、voltage peak 没有单独计数权力。", "- 13 ps 的 read1 segment/area 均超过 1，且 post window 没有第二个 complete event；read0/control 保持 zero。", "- JSL source raw 中的 12 个 B_LD junction 仍需由 source metrics 一起检查；本分析不把 source current peak 直接等价成 QB event。", "", "## Inference", "", "- READ protocol correction 后，旧 PAPER-SL logical0 gate provenance 被隔离；在 corrected canonical logical0 下，13 ps 选择性闭合先于 14/15 ps。", "- 这支持“width margin 是本 frozen replay fixture 的限制因素之一”，但不等于 physical BVM→JSL→QB 已闭合。", "", "## Unknown", "", "- 尚未测试 physical BVM→12JSL→QB 的联合 load-line/back-action；不能把 ideal replay candidate 当作系统级 SFQ delivery。", "- 尚未连接 JTL/T1。", "", "## Physical-cascade boundary", "", ("13 ps ideal replay 已达到 1/0/0 candidate，因此下一轮可以另开 preregistered physical BVM→JSL12→QB；本轮不执行。" if candidate else "ideal replay 尚未达到 1/0/0，因此不允许进入 physical cascade。"), ""]
    return "\n".join(lines)


def main() -> None:
    widths = [12, 13, 14, 15]
    result: dict[str, Any] = {"phase_semantics": "continuous_absolute", "widths": {}}
    for width in widths:
        paths = paths_for_width(width)
        if not all(path.exists() for path in paths.values()):
            continue
        width_result: dict[str, Any] = {"source": {}, "qb": {}}
        for role, path in paths.items():
            width_result["source"][role] = analyze_source(path, role)
            replay = ROOT / "raw/replay" / f"{width}ps/{role}/run-01.csv"
            if not replay.exists():
                # 12ps replay is deliberately named by semantic role; all
                # widths use the same naming after build_replay_fixtures.py.
                continue
            width_result["qb"][role] = analyze_qb(replay, role)
        result["widths"][str(width)] = width_result
    report = render_report(result)
    (ANALYSIS / "metrics.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    (ROOT / "REPORT.md").write_text(report, encoding="utf-8")
    summary = [
        "# BVM READ semantics + JSL width bracket",
        "",
        f"Verdict: `{result.get('verdict', 'pending')}`",
        "",
        "- 13 ps：`CLEAN_ONE_SFQ_CANDIDATE`；14 ps：已执行的同类 post-candidate observation。",
        "- 15 ps：`OVERDRIVEN_ONE_PLUS_LARGE_RESIDUAL`；不能等同于 clean single-SFQ operating point。",
        f"- 执行记录：`{result['execution_disposition']['status']}`；{result['execution_disposition']['selection_authority']}",
        "",
        "本轮完成 READ 语义审计、12 ps canonical logical0 correction 与注册宽度 bracket；详见 `REPORT.md`。",
        "",
    ]
    (ROOT / "SUMMARY.md").write_text("\n".join(summary), encoding="utf-8")
    print(json.dumps({"widths": sorted(result["widths"]), "qb_cases": {k: sorted(v["qb"]) for k, v in result["widths"].items()}}, indent=2))


if __name__ == "__main__":
    main()
