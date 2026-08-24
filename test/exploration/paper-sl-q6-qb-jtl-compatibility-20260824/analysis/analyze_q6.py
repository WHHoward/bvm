#!/usr/bin/env python3
"""Direct phase/voltage-area analysis for PAPER-SL-Q6.

This is deliberately independent of the legacy fast-event counter.  A
qualifying event is a same-JJ, same-segment monotonic phase transition of at
least one turn whose direct voltage area is consistent with that phase change.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


PHI0 = 2.067833848e-15
ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824"
RAW = EXP / "raw/q6-q5-to-two-cell-jtl"
ANALYSIS = EXP / "analysis"
Q5_METRICS = ROOT / "test/exploration/paper-sl-q5-l1-l2-factorial-20260824/analysis/metrics.json"

WINDOWS = {"pre": (85.0, 94.0), "activity": (94.0, 130.0), "post": (130.0, 165.0)}
CASES = (
    "paper-j1-logical1-read0-control",
    "paper-j1-logical1-read",
    "paper-j0-logical0-read",
    "paper-j0-logical0-read0-control",
)

QB_JJS = ("BJS", "BJL1", "BJL2")
JTL_JJS = ("B1|XJTL1", "B2|XJTL1", "B1|XJTL2", "B2|XJTL2")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_csv(path: Path):
    with path.open(newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"empty CSV: {path}")
    fields = list(rows[0].keys())
    arrays = {k: np.asarray([float(row[k]) for row in rows], dtype=float) for k in fields if k != "time"}
    time_ps = np.asarray([float(row["time"]) * 1e12 for row in rows], dtype=float)
    if not np.all(np.isfinite(time_ps)) or not all(np.all(np.isfinite(v)) for v in arrays.values()):
        raise ValueError(f"non-finite data: {path}")
    if not np.all(np.diff(time_ps) > 0):
        raise ValueError(f"time is not strictly increasing: {path}")
    return time_ps, arrays, fields


def mask(time_ps: np.ndarray, window: tuple[float, float]) -> np.ndarray:
    return (time_ps >= window[0]) & (time_ps < window[1])


def integrate(time_ps: np.ndarray, values: np.ndarray) -> float:
    return float(np.trapezoid(values, time_ps * 1e-12) / PHI0)


def p2p(values: np.ndarray) -> float:
    return float(np.max(values) - np.min(values)) if len(values) else float("nan")


def median(values: np.ndarray) -> float:
    return float(np.median(values)) if len(values) else float("nan")


def basic(time_ps: np.ndarray, arrays: dict[str, np.ndarray], col: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for name, window in WINDOWS.items():
        v = arrays[col][mask(time_ps, window)]
        out[f"{name}_min"] = float(np.min(v))
        out[f"{name}_max"] = float(np.max(v))
        out[f"{name}_p2p"] = p2p(v)
        out[f"{name}_median"] = median(v)
    return out


def monotonic_segments(time_ps: np.ndarray, phase: np.ndarray, voltage: np.ndarray, active: np.ndarray) -> list[dict[str, Any]]:
    """Return all sign-consistent monotonic runs in an analysis window."""
    indices = np.flatnonzero(active)
    if len(indices) < 2:
        return []
    out: list[dict[str, Any]] = []
    dphi = np.diff(phase[indices])
    for sign, direction in ((1.0, "positive"), (-1.0, "negative")):
        good = sign * dphi >= 0.0
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
            delta_turns = float((phase[end] - phase[start]) / (2.0 * math.pi))
            area_turns = integrate(time_ps[start : end + 1], voltage[start : end + 1])
            out.append({
                "direction": direction,
                "start_ps": float(time_ps[start]),
                "end_ps": float(time_ps[end]),
                "delta_turns": delta_turns,
                "magnitude_turns": abs(delta_turns),
                "area_turns": area_turns,
                "area_residual_turns": float(area_turns - delta_turns),
                "duration_ps": float(time_ps[end] - time_ps[start]),
            })
            i = j + 1
    return out


def qualifying(segment: dict[str, Any]) -> bool:
    magnitude = abs(float(segment["delta_turns"]))
    residual = abs(float(segment["area_residual_turns"]))
    tolerance = max(0.02, 0.05 * magnitude)
    return magnitude >= 1.0 and residual <= tolerance


def phase_metrics(time_ps: np.ndarray, arrays: dict[str, np.ndarray], name: str) -> dict[str, Any]:
    pcol = f"P({name})"
    vcol = f"V({name})"
    phase = np.unwrap(arrays[pcol])
    act = mask(time_ps, WINDOWS["activity"])
    post = mask(time_ps, WINDOWS["post"])
    segments = monotonic_segments(time_ps, phase, arrays[vcol], act)
    post_segments = monotonic_segments(time_ps, phase, arrays[vcol], post)
    largest = max(segments, key=lambda x: x["magnitude_turns"], default={
        "direction": "none", "start_ps": None, "end_ps": None,
        "delta_turns": 0.0, "magnitude_turns": 0.0, "area_turns": 0.0,
        "area_residual_turns": 0.0, "duration_ps": 0.0,
    })
    first = int(np.flatnonzero(act)[0])
    last = int(np.flatnonzero(act)[-1])
    return {
        "activity_range_turns": float((np.max(phase[act]) - np.min(phase[act])) / (2.0 * math.pi)),
        "activity_window_phase_turns": float((phase[last] - phase[first]) / (2.0 * math.pi)),
        "activity_window_v_area_turns": integrate(time_ps[first : last + 1], arrays[vcol][first : last + 1]),
        "pre_to_post_turns": float((median(phase[post]) - median(phase[mask(time_ps, WINDOWS["pre"])])) / (2.0 * math.pi)),
        "post_phase_p2p_turns": float(p2p(phase[post]) / (2.0 * math.pi)),
        "largest_monotonic_segment": largest,
        "segments": segments,
        "post_segments": post_segments,
        "complete_event_count": int(sum(qualifying(s) for s in segments)),
        "post_complete_event_count": int(sum(qualifying(s) for s in post_segments)),
    }


def case_result(case: str) -> dict[str, Any]:
    raw = RAW / f"{case}.csv"
    time_ps, arrays, fields = load_csv(raw)
    required = []
    for name in QB_JJS:
        scoped = f"{name}|XBQ"
        required += [f"P({scoped})", f"V({scoped})", f"I({scoped})"]
    for name in JTL_JJS:
        required += [f"P({name})", f"V({name})", f"I({name})"]
    required += ["V(OUT)", "I(R_LOAD)", "I(L0|XBQ)", "V(JTL_MID)", "V(JTL_OUT)", "I(R_TERM)"]
    missing = [c for c in required if c not in arrays]
    if missing:
        raise ValueError(f"{case}: missing fields {missing}")
    qb = {name: phase_metrics(time_ps, arrays, f"{name}|XBQ") for name in QB_JJS}
    jtl = {name: phase_metrics(time_ps, arrays, name) for name in JTL_JJS}
    signal_cols = ["V(OUT)", "I(R_LOAD)", "I(L0|XBQ)", "V(JTL_MID)", "V(JTL_OUT)", "I(R_TERM)", "I(L1|XJTL1)"]
    signals = {col: basic(time_ps, arrays, col) for col in signal_cols}
    currents = {}
    for name in QB_JJS:
        currents[f"I({name}|XBQ)"] = basic(time_ps, arrays, f"I({name}|XBQ)")
    for name in JTL_JJS:
        currents[f"I({name})"] = basic(time_ps, arrays, f"I({name})")
    return {
        "case": case,
        "raw": str(raw.relative_to(ROOT)),
        "raw_sha256": sha256(raw),
        "rows": len(time_ps),
        "time_start_ps": float(time_ps[0]),
        "time_end_ps": float(time_ps[-1]),
        "dt_median_ps": float(np.median(np.diff(time_ps))),
        "qb": qb,
        "jtl": jtl,
        "signals": signals,
        "currents": currents,
    }


def fmt(value: Any, digits: int = 8) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (float, np.floating)):
        if not math.isfinite(float(value)):
            return "n/a"
        return f"{float(value):.{digits}g}"
    return str(value)


def classify(results: dict[str, Any]) -> str:
    r1 = results["cases"]["paper-j1-logical1-read"]
    read0 = results["cases"]["paper-j0-logical0-read"]
    controls = [
        results["cases"]["paper-j1-logical1-read0-control"],
        results["cases"]["paper-j0-logical0-read0-control"],
    ]
    r1_counts = [r1["jtl"][name]["complete_event_count"] for name in JTL_JJS]
    read0_counts = [read0["jtl"][name]["complete_event_count"] for name in JTL_JJS]
    control_counts = [[c["jtl"][name]["complete_event_count"] for name in JTL_JJS] for c in controls]
    if any(v != 0 for v in read0_counts) or any(v != 0 for row in control_counts for v in row):
        return "NONSELECTIVE_OR_MULTIFIRE_FAILURE"
    if any(v > 1 for v in r1_counts):
        return "NONSELECTIVE_OR_MULTIFIRE_FAILURE"
    if r1_counts == [1, 1, 1, 1]:
        onset = [r1["jtl"][name]["largest_monotonic_segment"]["start_ps"] for name in JTL_JJS]
        if any(onset[i] > onset[i + 1] + 0.2 for i in range(3)):
            return "INCONCLUSIVE"
        if r1["qb"]["BJL2"]["complete_event_count"] == 1:
            return "COUPLED_QB_JTL_CLOSURE"
        return "JTL_REGENERATIVE_PASS"
    return "NO_JTL_TRIGGER"


def render_event_table(results: dict[str, Any]) -> str:
    lines = [
        "| case | JJ | activity range (turn) | largest monotonic (turn) | same-segment area (Φ0) | residual (turn) | complete events | post complete | onset→end (ps) | post p2p (turn) |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for case in CASES:
        for name in JTL_JJS:
            m = results["cases"][case]["jtl"][name]
            s = m["largest_monotonic_segment"]
            lines.append(
                f"| {case} | `{name}` | {fmt(m['activity_range_turns'])} | {fmt(s['delta_turns'])} | {fmt(s['area_turns'])} | {fmt(s['area_residual_turns'])} | {m['complete_event_count']} | {m['post_complete_event_count']} | {fmt(s['start_ps'])}→{fmt(s['end_ps'])} | {fmt(m['post_phase_p2p_turns'])} |"
            )
    return "\n".join(lines)


def render_qb_table(results: dict[str, Any]) -> str:
    lines = [
        "| case | BJs largest / source activity | BJL1 largest / area / events | BJL2 largest / area / events | OUT activity p2p (V) | L0 activity p2p (A) | JTL input I(L1) activity p2p (A) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in CASES:
        r = results["cases"][case]
        bjs = r["qb"]["BJS"]
        bjl1 = r["qb"]["BJL1"]
        bjl2 = r["qb"]["BJL2"]
        lines.append(
            f"| {case} | {fmt(bjs['largest_monotonic_segment']['delta_turns'])} / source | {fmt(bjl1['largest_monotonic_segment']['delta_turns'])} / {fmt(bjl1['largest_monotonic_segment']['area_turns'])} / {bjl1['complete_event_count']} | {fmt(bjl2['largest_monotonic_segment']['delta_turns'])} / {fmt(bjl2['largest_monotonic_segment']['area_turns'])} / {bjl2['complete_event_count']} | {fmt(r['signals']['V(OUT)']['activity_p2p'])} | {fmt(r['signals']['I(L0|XBQ)']['activity_p2p'])} | {fmt(r['signals']['I(L1|XJTL1)']['activity_p2p'])} |"
        )
    return "\n".join(lines)


def render_load_table(results: dict[str, Any]) -> str:
    lines = [
        "| case | I(R_LOAD) pre median (µA) | activity p2p (µA) | I(L0|XBQ) pre median (µA) | JTL mid p2p (µV) | JTL out p2p (µV) | I(R_TERM) activity p2p (µA) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for case in CASES:
        s = results["cases"][case]["signals"]
        lines.append(
            f"| {case} | {fmt(s['I(R_LOAD)']['pre_median']*1e6)} | {fmt(s['I(R_LOAD)']['activity_p2p']*1e6)} | {fmt(s['I(L0|XBQ)']['pre_median']*1e6)} | {fmt(s['V(JTL_MID)']['activity_p2p']*1e6)} | {fmt(s['V(JTL_OUT)']['activity_p2p']*1e6)} | {fmt(s['I(R_TERM)']['activity_p2p']*1e6)} |"
        )
    return "\n".join(lines)


def render_report(results: dict[str, Any]) -> str:
    verdict = results["verdict"]
    r1 = results["cases"]["paper-j1-logical1-read"]
    q5 = json.loads(Q5_METRICS.read_text())["read1_comparison"]["Q5"]
    all_jtl_one = all(r1["jtl"][name]["complete_event_count"] == 1 for name in JTL_JJS)
    bjl2_event = r1["qb"]["BJL2"]["complete_event_count"]
    lines = [
        "# PAPER-SL-Q6 report：frozen Q5 QB → standard two-cell JTL",
        "",
        f"主 verdict：**`{verdict}`**",
        "",
        "本报告只分析 Q6 coupling fixture 的 raw CSV；没有重跑 JTL positive control。positive-control provenance 与同一两-cell standard chain 的有效性来自 accepted R11-A。Q5 的 `R_LOAD OUT 0 10Ω` 在 Q6 中保留，并与第一 cell input network 并联。",
        "",
        "## Artifact / execution",
        "",
        "- 四个 case 均应有 exit=0、stderr 空、13,599 个 data rows；时间来自 CSV，median `dt=0.0125 ps`，不得用旧 `fast_events`。",
        "- Q5 QB、`IBIAS=40 µA`、replay、所有 QB L/R/AREA/model 参数未改；新增只有标准 `JTL.cir` include、两 cell、`R_TERM=1Ω` 和 probes。",
        "- 这是 Q5 replay fixture，不是 physical BVM connection；因此本报告不声称新的 `SL/N6/JM/JS` source guard。",
        "",
        "## Event evidence: four standard-JTL junctions",
        "",
        render_event_table(results),
        "",
        "其中 `complete events` 只统计 continuous unwrapped phase 的单调 segment：幅度至少 1 turn，且同一 JJ/同一 segment 的 direct voltage area 与 phase 的 residual 在预注册容差内。phase range、voltage peak、I>Ic 不能单独形成 event。",
        "",
        "## QB local response and output loading",
        "",
        render_qb_table(results),
        "",
        render_load_table(results),
        "",
        f"Q5 isolated replay 的 accepted read1 reference 是 BJL1 forward `{q5['BJL1_forward_turns']:.8g}` turn、BJL2 largest `{q5['BJL2_largest']['delta_turns']:.8g}` turn、BJL2 complete count=0；Q6 的 coupling 结果必须与这些值分开解释。Q6 read1 BJL2 complete count={bjl2_event}，四颗 JTL JJ 是否各 exactly-one：`{all_jtl_one}`。",
        "",
        "## Observed",
        "",
        f"- verdict 对应的 JTL count 向量为：read1 `{[r1['jtl'][n]['complete_event_count'] for n in JTL_JJS]}`；read0 `{[results['cases']['paper-j0-logical0-read']['jtl'][n]['complete_event_count'] for n in JTL_JJS]}`；两个 READ=0 controls 分别 `{[[results['cases'][c]['jtl'][n]['complete_event_count'] for n in JTL_JJS] for c in (CASES[0], CASES[3])]}`。",
        "- 逐颗 JJ 的最大 monotonic segment、同段 area、onset/end 和 post p2p 已在上表给出；QB BJs 的 multi-turn source activity不被当作 JTL delivery。",
        "- `R_LOAD` 与 JTL input branch 的活动电流分开记录，未把 OUT 电流默认归属于任一 branch。",
        "",
        "## Derived",
        "",
        "- 若四颗 JTL JJ 都 exactly-one 且 onset 顺序为 `XJTL1.B1 → XJTL1.B2 → XJTL2.B1 → XJTL2.B2`，才构成 full tested chain 的 propagated event；否则不能称 propagated success。",
        "- `COUPLED_QB_JTL_CLOSURE` 需要额外满足 read1 的 BJL2 也有一个同段 phase/area-consistent complete event；JTL 成功本身不自动证明 isolated QB event。",
        "",
        "## Inference",
        "",
        f"在本固定 Q5 load + standard JTL input 边界下，结果属于 `{verdict}`。该结论只覆盖这一 coupling point；若 JTL 无触发，表示 frozen Q5 output 在该真实 load boundary 下不足以触发标准 JTL，不否定其他带 conditioner 的 receiver。若 JTL 触发，也只能称耦合系统的 regenerative compatibility，不能回写为 isolated QB SFQ generation。",
        "",
        "## Unknown / boundary",
        "",
        "- 没有 physical BVM、12-JSL 或 canonical SL/N6 raw 参与本轮，故不报告 BVM back-action；Q6 是 accepted paper-JSL-shaped replay 到 JTL 的 coupling probe。",
        "- 保留 10Ω load 会让 OUT 同时承受 Q5 external load 与 JTL input network；这是 preregistered load choice，不是对 JTL 或 QB 的参数优化。",
        "- 本轮停止后不调 JTL/QB，不接 T1，不把单点结果升级为 architecture-wide theorem。",
        "",
        "## Stop rule",
        "",
        "本 checkpoint 完成后停止，不提出或执行下一枚参数点。",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    results = {"study": "PAPER-SL-Q6", "cases": {case: case_result(case) for case in CASES}}
    results["verdict"] = classify(results)
    results["jtl_junctions"] = list(JTL_JJS)
    results["windows_ps"] = WINDOWS
    results["q5_reference_metrics"] = str(Q5_METRICS.relative_to(ROOT))
    (ANALYSIS / "metrics.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    (ANALYSIS / "case-summary.csv").write_text(
        "case,jtl_b1_xjtl1,jtl_b2_xjtl1,jtl_b1_xjtl2,jtl_b2_xjtl2,qb_bjl2\n" +
        "\n".join(
            ",".join([
                case,
                *[str(results["cases"][case]["jtl"][name]["complete_event_count"]) for name in JTL_JJS],
                str(results["cases"][case]["qb"]["BJL2"]["complete_event_count"]),
            ]) for case in CASES
        ) + "\n"
    )
    (EXP / "REPORT.md").write_text(render_report(results))
    print(json.dumps({"verdict": results["verdict"], "jtl_event_counts": {case: [results["cases"][case]["jtl"][name]["complete_event_count"] for name in JTL_JJS] for case in CASES}}, indent=2))


if __name__ == "__main__":
    main()
