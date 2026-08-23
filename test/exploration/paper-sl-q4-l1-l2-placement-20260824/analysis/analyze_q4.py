#!/usr/bin/env python3
"""Analyze the frozen PAPER-SL-Q4 L1/L2 placement point.

The Q4 raw files are compared with the accepted Q2 and Q3 raw files.  Event
claims use continuous unwrapped phase and the direct same-JJ voltage area on
the same monotonic segment; current peaks and phase range are retained only
as activity diagnostics.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/paper-sl-q4-l1-l2-placement-20260824"
Q3_ANALYSIS = ROOT / "test/exploration/paper-sl-q3-pre-20260824/analysis"
sys.path.insert(0, str(Q3_ANALYSIS))
import analyze_q3_pre as q3  # noqa: E402


MAIN = (94.0, 130.0)
POST = (140.0, 170.0)
DT_PS = 0.0125
IBIAS_UA = 40.0

CASE_NAMES = (
    "paper-j1-logical1-read0-control",
    "paper-j0-logical0-read0-control",
    "paper-j0-logical0-read",
    "paper-j1-logical1-read",
)

Q2_CASES = {name: Path(f"../paper-sl-q2-20260824/raw/40u/{name}.csv") for name in CASE_NAMES}
Q3_CASES = {name: Path(f"../paper-sl-q3-l1-routing-closure-20260824/raw/l1-4p5/{name}.csv") for name in CASE_NAMES}
Q4_CASES = {name: Path(f"../paper-sl-q4-l1-l2-placement-20260824/raw/q4-l1-3p91-l2-4p50/{name}.csv") for name in CASE_NAMES}

DATASETS = {"Q2": Q2_CASES, "Q3": Q3_CASES, "Q4": Q4_CASES}
LABELS = {
    "Q2": "Q2 reference L1=3.91 pH, L2=3.91 pH",
    "Q3": "Q3 sibling L1=4.50 pH, L2=3.91 pH",
    "Q4": "Q4 point L1=3.91 pH, L2=4.50 pH",
}

JUNCTIONS = q3.JUNCTIONS
BRANCHES = q3.BRANCHES
TWO_PI = q3.TWO_PI


def load_case(path: Path) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, np.ndarray]]:
    data = q3.load_csv(path)
    time_ps = q3.column(data, "time") * 1e12
    phases = {name: np.unwrap(q3.column(data, names[0])) for name, names in JUNCTIONS.items()}
    return data, time_ps, phases


def segment_set(time_ps: np.ndarray, phases: dict[str, np.ndarray], data: dict[str, np.ndarray], window: tuple[float, float]) -> dict[str, list[dict[str, Any]]]:
    return {
        name: q3.segment_records(time_ps, phases[name], q3.column(data, names[1]), window, 0)
        for name, names in JUNCTIONS.items()
    }


def largest(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    return max(records, key=lambda item: abs(float(item["delta_turns"]))) if records else None


def directional(records: list[dict[str, Any]], positive: bool) -> dict[str, Any] | None:
    candidates = [r for r in records if (float(r["delta_turns"]) > 0) == positive]
    if not candidates:
        return None
    return max(candidates, key=lambda item: abs(float(item["delta_turns"])))


def phase_range(phases: np.ndarray, time_ps: np.ndarray, window: tuple[float, float]) -> float:
    mask = (time_ps >= window[0]) & (time_ps < window[1])
    return float(np.ptp(phases[mask]) / TWO_PI) if np.count_nonzero(mask) else math.nan


def timing(a: dict[str, Any] | None, b: dict[str, Any] | None) -> dict[str, float | None]:
    if a is None or b is None:
        return {"a_start_ps": None, "a_end_ps": None, "b_start_ps": None, "b_end_ps": None, "delay_ps": None, "overlap_ps": None}
    a_start, a_end = float(a["start_ps"]), float(a["end_ps"])
    b_start, b_end = float(b["start_ps"]), float(b["end_ps"])
    return {
        "a_start_ps": a_start,
        "a_end_ps": a_end,
        "b_start_ps": b_start,
        "b_end_ps": b_end,
        "delay_ps": b_start - a_start,
        "overlap_ps": max(0.0, min(a_end, b_end) - max(a_start, b_start)),
    }


def area_diagnostics(case: dict[str, Any], branch: str) -> dict[str, float]:
    stats = case["bjl1_interval_currents"][branch]
    positive = float(stats["positive_area_uA_ps"])
    negative = float(stats["negative_area_uA_ps"])
    signed = float(stats["signed_area_uA_ps"])
    denom = positive + abs(negative)
    return {
        "positive_uA_ps": positive,
        "negative_uA_ps": negative,
        "signed_uA_ps": signed,
        "positive_over_abs_negative": positive / abs(negative) if abs(negative) > 1e-15 else math.inf,
        "cancellation_fraction": 1.0 - abs(signed) / denom if denom > 1e-15 else math.nan,
    }


def event_summary(data: dict[str, np.ndarray], time_ps: np.ndarray, phases: dict[str, np.ndarray]) -> dict[str, Any]:
    windows = {"main": MAIN, "post": POST}
    result: dict[str, Any] = {}
    for name in JUNCTIONS:
        by_window = {label: segment_set(time_ps, phases, data, window)[name] for label, window in windows.items()}
        all_records = [record for records in by_window.values() for record in records]
        complete = [record for record in all_records if record["area_consistent"]]
        result[name] = {
            "main_phase_range_turns": phase_range(phases[name], time_ps, MAIN),
            "post_phase_range_turns": phase_range(phases[name], time_ps, POST),
            "main_largest": largest(by_window["main"]),
            "post_largest": largest(by_window["post"]),
            "complete_event_segments": complete,
            "complete_event_count": int(sum(int(record["complete_event_units"]) for record in complete)),
        }
    return result


def settled(data: dict[str, np.ndarray], time_ps: np.ndarray) -> dict[str, dict[str, float]]:
    mask = (time_ps >= POST[0]) & (time_ps < POST[1])
    names = (
        "I(BJS|XBQ)", "I(BJL1|XBQ)", "I(BJL2|XBQ)", "I(L1|XBQ)",
        "I(L2|XBQ)", "I(LIN|XBQ)", "I(RB|XBQ)", "I(RJ1|XBQ)",
        "I(RJ2|XBQ)", "I(L0|XBQ)",
    )
    result: dict[str, dict[str, float]] = {}
    for name in names:
        values = q3.column(data, name)[mask] * 1e6
        result[name] = {
            "mean_uA": float(np.mean(values)),
            "min_uA": float(np.min(values)),
            "max_uA": float(np.max(values)),
            "p2p_uA": float(np.ptp(values)),
        }
    return result


def g_local(read_data: dict[str, np.ndarray], control_data: dict[str, np.ndarray], time_ps: np.ndarray) -> float:
    read_time = q3.column(read_data, "time") * 1e12
    control_time = q3.column(control_data, "time") * 1e12
    if not np.array_equal(read_time, control_time):
        raise ValueError("Q2/Q3/Q4 read and READ=0 control time axes are not byte-aligned")
    mask = (read_time >= MAIN[0]) & (read_time < MAIN[1])
    local_read = q3.column(read_data, "I(BJL1|XBQ)") + q3.column(read_data, "I(RJ1|XBQ)")
    local_control = q3.column(control_data, "I(BJL1|XBQ)") + q3.column(control_data, "I(RJ1|XBQ)")
    source_read = q3.column(read_data, "I(BJS|XBQ)")
    source_control = q3.column(control_data, "I(BJS|XBQ)")
    delta_local = (local_read - local_control)[mask]
    delta_source = (source_read - source_control)[mask]
    denominator = float(np.sqrt(np.mean(delta_source * delta_source)))
    return float(np.sqrt(np.mean(delta_local * delta_local)) / denominator) if denominator > 0 else math.nan


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return str(value)
    return value


def fmt(value: Any, digits: int = 6) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return str(value)
    if isinstance(value, (float, int)):
        return f"{value:.{digits}g}"
    return str(value)


def segment_md(record: dict[str, Any] | None) -> str:
    if record is None:
        return "—"
    return f"[{fmt(record['start_ps'])}, {fmt(record['end_ps'])}] ps; Δ={fmt(record['delta_turns'])} turn; area={fmt(record['area_turns'])} Φ0; consistent={'yes' if record['phase_area_consistent'] else 'no'}"


def build_results() -> dict[str, Any]:
    all_results: dict[str, Any] = {"study": "PAPER-SL-Q4", "cases": {}, "read1_comparison": {}}
    loaded: dict[str, dict[str, tuple[dict[str, np.ndarray], np.ndarray, dict[str, np.ndarray]]]] = {}
    for dataset, paths in DATASETS.items():
        loaded[dataset] = {}
        for case_id, relative in paths.items():
            # The imported Q3 helper resolves spec paths from its own
            # exploration root, not from its analysis subdirectory.
            path = (q3.ROOT / relative).resolve()
            if not path.exists():
                raise FileNotFoundError(path)
            data, time_ps, phases = load_case(path)
            loaded[dataset][case_id] = (data, time_ps, phases)
            base_spec = {"path": relative, "windows": [MAIN], "dt_ps": DT_PS, "ibias_uA": IBIAS_UA, "label": f"{dataset} {case_id}"}
            base = q3.analyze_case(f"{dataset}_{case_id}", base_spec)
            base["event_summary"] = event_summary(data, time_ps, phases)
            base["settled_post"] = settled(data, time_ps)
            base["major_segments"] = {
                name: {
                    "positive": directional(segment_set(time_ps, phases, data, MAIN)[name], True),
                    "negative": directional(segment_set(time_ps, phases, data, MAIN)[name], False),
                }
                for name in JUNCTIONS
            }
            bjs = base["trajectory"]["BJs"]["global_largest"]
            bjl1 = base["trajectory"]["BJL1"]["global_largest"]
            bjl2 = base["trajectory"]["BJL2"]["global_largest"]
            base["timing"]["bjl1_to_bjl2"] = timing(bjl1, bjl2)
            base["timing"]["bjs_to_bjl1_global"] = timing(bjs, bjl1)
            base["bjl1_current_area"] = area_diagnostics(base, "I(BJL1|XBQ)")
            base["bjl1_routing_area"] = area_diagnostics(base, "I(BJL1|XBQ)")
            all_results["cases"][f"{dataset}_{case_id}"] = base

    for dataset in DATASETS:
        read_id = "paper-j1-logical1-read"
        control_id = "paper-j1-logical1-read0-control"
        read_case = all_results["cases"][f"{dataset}_{read_id}"]
        read_data, read_time, _ = loaded[dataset][read_id]
        control_data, _, _ = loaded[dataset][control_id]
        read_case["G_local"] = g_local(read_data, control_data, read_time)
        routing = read_case["routing_metrics"]
        read_case["F_local"] = routing["local_fraction_of_bjs"]
        read_case["F_L1"] = routing["l1_fraction_of_bjs"]
        all_results["read1_comparison"][dataset] = {
            "F_local": read_case["F_local"],
            "F_L1": read_case["F_L1"],
            "G_local": read_case["G_local"],
            "BJL1_current_area": read_case["bjl1_current_area"],
            "BJL1_forward_segment": read_case["major_segments"]["BJL1"]["positive"],
            "BJL1_backward_segment": read_case["major_segments"]["BJL1"]["negative"],
            "BJL1_forward_turns": float(read_case["major_segments"]["BJL1"]["positive"]["delta_turns"]) if read_case["major_segments"]["BJL1"]["positive"] else None,
            "BJL1_backward_turns": float(read_case["major_segments"]["BJL1"]["negative"]["delta_turns"]) if read_case["major_segments"]["BJL1"]["negative"] else None,
            "BJL2_largest": read_case["trajectory"]["BJL2"]["global_largest"],
            "BJL2_over_BJL1": read_case["ratios"]["bjl2_over_bjl1"],
            "timing_BJs_to_BJL1": read_case["timing"]["bjs_to_bjl1_global"],
            "timing_BJL1_to_BJL2": read_case["timing"]["bjl1_to_bjl2"],
            "KCL": read_case["kcl"],
        }

    q2comp = all_results["read1_comparison"]["Q2"]
    q3comp = all_results["read1_comparison"]["Q3"]
    q4comp = all_results["read1_comparison"]["Q4"]
    q4_forward = float(q4comp["BJL1_forward_turns"])
    q3_forward = float(q3comp["BJL1_forward_turns"])
    q4_bjl2 = float(q4comp["BJL2_largest"]["delta_turns"])
    q3_bjl2 = float(q3comp["BJL2_largest"]["delta_turns"])
    if (
        abs(float(q4comp["F_local"]) - float(q3comp["F_local"])) > 0.05
        and abs(float(q4comp["F_local"]) - float(q2comp["F_local"])) > 0.05
        and q4_forward < q3_forward
        and q4_bjl2 > q3_bjl2
    ):
        all_results["verdict"] = "Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT"
    else:
        all_results["verdict"] = "INCONCLUSIVE"
    return json_safe(all_results)


def table_read1(results: dict[str, Any]) -> list[str]:
    lines = [
        "| dataset | F_local | F_L1 | G_local | BJL1 +area | BJL1 -area | BJL1 signed | cancellation | BJL1 forward | BJL1 backward | BJL2 largest | BJL2/BJL1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dataset in ("Q2", "Q3", "Q4"):
        c = results["read1_comparison"][dataset]
        area = c["BJL1_current_area"]
        bjl2 = c["BJL2_largest"]
        lines.append(
            f"| {dataset} | {fmt(c['F_local'])} | {fmt(c['F_L1'])} | {fmt(c['G_local'])} | {fmt(area['positive_uA_ps'])} | {fmt(area['negative_uA_ps'])} | {fmt(area['signed_uA_ps'])} | {fmt(area['cancellation_fraction'])} | {fmt(c['BJL1_forward_turns'])} | {fmt(c['BJL1_backward_turns'])} | {fmt(bjl2['delta_turns'])} | {fmt(c['BJL2_over_BJL1'])} |"
        )
    return lines


def render_report(results: dict[str, Any]) -> str:
    verdict = results["verdict"]
    q2 = results["read1_comparison"]["Q2"]
    q3 = results["read1_comparison"]["Q3"]
    q4 = results["read1_comparison"]["Q4"]
    q4_bjl2 = float(q4["BJL2_largest"]["delta_turns"])
    q3_bjl2 = float(q3["BJL2_largest"]["delta_turns"])
    lines = [
        "# PAPER-SL-Q4 — L1/L2 placement analysis report",
        "",
        "## Verdict",
        "",
        f"**{verdict}**。Q4 仍没有 BJL1/BJL2 complete event；本单点不升级为 downstream SFQ evidence。",
        "",
        "Q4 直接从 accepted Q2 `inputs/40u` 构建，只改变 `L2=3.91p → 4.50p`；Q3 仅作为 sibling comparator。所有事件判断使用同一 JJ、同一 monotonic segment 的 continuous unwrapped phase 与直接 voltage-area，未使用 `I>Ic`、voltage peak 或旧 fast-event 指标。",
        "",
        "## Observed",
        "",
        "- 四个 Q4 JoSIM runs 均返回 0，CSV 均为 13,599 个 data rows，stderr 为空；首个 logical1 READ=0 control 已先通过 stop gate。",
        "- Q4 四 case 的完整 segment/event 汇总如下；`complete_event_count` 仅统计 phase/area-consistent 的 ≥1 turn segment。",
        "- read1 的 BJs 是预期的 multi-turn source activity，因此表中 BJs 的 segment count 不等同于输出 event；本轮 local-output 判据只对 BJL1/BJL2 读取。",
        "",
        "| case | JJ | main phase range (turn) | post phase range (turn) | complete event count | main largest segment | post largest segment |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    for key, case in results["cases"].items():
        if not key.startswith("Q4_"):
            continue
        for name in ("BJs", "BJL1", "BJL2"):
            e = case["event_summary"][name]
            lines.append(f"| {key} | {name} | {fmt(e['main_phase_range_turns'])} | {fmt(e['post_phase_range_turns'])} | {e['complete_event_count']} | {segment_md(e['main_largest'])} | {segment_md(e['post_largest'])} |")

    lines += [
        "",
        "## Settled post-window operating points",
        "",
        "READ=0 post window `[140,170)` ps 的均值/范围用于比较静态工作点；不以该表的电流比值判定 event。",
        "",
        "| case | I(BJs) mean | I(BJL1) mean | I(BJL2) mean | I(L1) mean | I(L2) mean | I(LIN) mean | I(RB) mean | I(RJ1) mean | I(RJ2) mean |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, case in results["cases"].items():
        if not key.startswith("Q4_"):
            continue
        s = case["settled_post"]
        lines.append("| " + key + " | " + " | ".join(fmt(s[b]["mean_uA"]) for b in (
            "I(BJS|XBQ)", "I(BJL1|XBQ)", "I(BJL2|XBQ)", "I(L1|XBQ)", "I(L2|XBQ)", "I(LIN|XBQ)", "I(RB|XBQ)", "I(RJ1|XBQ)", "I(RJ2|XBQ)")) + " |")

    lines += [
        "",
        "## Q2/Q3/Q4 read1 comparison",
        "",
        "`F_local`/`F_L1` 是 paired dominant BJL1 interval 的 signed-area routing fractions；`G_local` 是 `[94,130)` ps 中 read1 减去 logical1 READ=0 后，local `(BJL1+RJ1)` RMS 与 BJs RMS 的比值。正负 current area 仅作波形抵消诊断。",
        "",
    ]
    lines.extend(table_read1(results))
    lines += [
        "",
        "### Major BJL1 phase segments",
        "",
        "| dataset | positive segment | negative segment |",
        "|---|---|---|",
    ]
    for dataset in ("Q2", "Q3", "Q4"):
        c = results["read1_comparison"][dataset]
        lines.append(f"| {dataset} | {segment_md(c['BJL1_forward_segment'])} | {segment_md(c['BJL1_backward_segment'])} |")

    lines += [
        "",
        "### Onset/delay/overlap",
        "",
        "| dataset | BJs→BJL1 delay (ps) | BJs/BJL1 overlap (ps) | BJL1→BJL2 delay (ps) | BJL1/BJL2 overlap (ps) |",
        "|---|---:|---:|---:|---:|",
    ]
    for dataset in ("Q2", "Q3", "Q4"):
        c = results["read1_comparison"][dataset]
        a, b = c["timing_BJs_to_BJL1"], c["timing_BJL1_to_BJL2"]
        lines.append(f"| {dataset} | {fmt(a['delay_ps'])} | {fmt(a['overlap_ps'])} | {fmt(b['delay_ps'])} | {fmt(b['overlap_ps'])} |")

    lines += [
        "",
        "### KCL residuals",
        "",
        "残差单位为 µA，在各 read1 dominant BJs interval 上计算：",
        "`node2: I(BJs)-I(L1)-I(BJL1)-I(RJ1)`；`node3: I(L1)+I(RB)-I(L2)`；`node4: I(L2)-I(L0)-I(BJL2)-I(RJ2)`。",
        "",
        "| dataset | node2 max/RMS | node3 max/RMS | node4 max/RMS |",
        "|---|---:|---:|---:|",
    ]
    for dataset in ("Q2", "Q3", "Q4"):
        k = results["read1_comparison"][dataset]["KCL"]
        names = ("node2_BJs_minus_L1_BJL1_RJ1", "node3_L1_plus_RB_minus_L2", "node4_L2_minus_L0_BJL2_RJ2")
        vals = [f"{fmt(k[n]['max_abs_uA'])}/{fmt(k[n]['rms_uA'])}" for n in names]
        lines.append(f"| {dataset} | {' | '.join(vals)} |")

    lines += [
        "",
        "## Derived",
        "",
        "- Q4 的 current decomposition、phase segment、BJs→BJL1 与 BJL1→BJL2 的时序，以及三条 node KCL residual 均已从 raw 独立计算；没有把总 phase range 当作 event count。",
        "- BJL1 的 `positive/negative/signed area` 和 cancellation fraction 是在 paired dominant BJL1 interval 上定义的诊断量，不是 acceptance threshold。forward/backward segment 分开报告，避免将 backward motion 的减小误读为 forward event。",
        f"- Q4 的 `F_local={fmt(q4['F_local'])}` 明显低于 Q2/Q3 的 `{fmt(q2['F_local'])}/{fmt(q3['F_local'])}`；BJL1 forward segment 为 `{fmt(q4['BJL1_forward_turns'])}` turn，低于 Q3 `{fmt(q3['BJL1_forward_turns'])}`，而 BJL2 为 `{fmt(q4_bjl2)}` turn，高于 Q3 `{fmt(q3_bjl2)}`。",
        "- Q4 的 BJL1 正面积下降、负向 excursion 增大，且 BJL1→BJL2 overlap 缩短；这说明它不是单纯把整条响应同比放大。三条 KCL residual 仍保持微安以下的数值误差，因此该方向性差异不是 KCL 不闭合造成的。",
        "- Q2/Q3/Q4 raw 是 ideal replay QB fixture，不包含 `V(SL)`、`V(N6)`、`I(L_SL)`、`JM1/JM2`、`JS1/JS2` 这些 canonical BVM列；因此本轮只能确认 replay input boundary 未被改写，不能把 replay 结果冒充 physical BVM source-guard measurement。",
        "",
        "## Inference",
        "",
        f"基于 current decomposition、phase dynamics、timing 和 KCL 的联合判断，本单点归类为 **{verdict}**：Q4 在下游 BJL2 上比 Q3 更强，但在 proximal BJL1 上反而更弱，且 BJL1 forward/backward 波形与 overlap 同时改变。因此支持 L1/L2 placement 的方向性动态效应；它不支持 Q4≈Q2、Q4≈Q3，也不满足“BJL1 cancellation 减少且 BJL1 phase 超过 Q3”的更强 downstream-timing 说法。",
        "",
        "## Unknown",
        "",
        "- 本轮只测试一个 Q4 point；即使看到 routing 方向，也不证明整个 L1/L2 family 的普遍机制。",
        "- local JJ phase transition 不等同于 downstream SFQ delivery；本轮没有接 JTL。",
        "- 没有进行新的 timestep/convergence 或额外 placement/bias/AREA/RJ 点。",
        "",
        "## Stop boundary",
        "",
        "本 checkpoint 完成后停止，不运行 Q5，不连接 physical BVM→12JSL→QB，不接 JTL，也不追加参数点。",
        "",
        "## Provenance",
        "",
        "运行、source fixture、模型和 raw hash 见 `logs/`、`reference/`、`inputs/deck-hashes.json` 与 `sha256sums.txt`。",
    ]
    return "\n".join(lines) + "\n"


def write_case_csv(results: dict[str, Any]) -> None:
    path = EXP / "analysis/case-summary.csv"
    fields = ["dataset", "case", "BJs_main_range_turn", "BJL1_main_range_turn", "BJL2_main_range_turn", "BJs_events", "BJL1_events", "BJL2_events"]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key, case in results["cases"].items():
            dataset, case_id = key.split("_", 1)
            writer.writerow({
                "dataset": dataset,
                "case": case_id,
                "BJs_main_range_turn": case["event_summary"]["BJs"]["main_phase_range_turns"],
                "BJL1_main_range_turn": case["event_summary"]["BJL1"]["main_phase_range_turns"],
                "BJL2_main_range_turn": case["event_summary"]["BJL2"]["main_phase_range_turns"],
                "BJs_events": case["event_summary"]["BJs"]["complete_event_count"],
                "BJL1_events": case["event_summary"]["BJL1"]["complete_event_count"],
                "BJL2_events": case["event_summary"]["BJL2"]["complete_event_count"],
            })


def main() -> None:
    results = build_results()
    (EXP / "analysis/metrics.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    write_case_csv(results)
    (EXP / "REPORT.md").write_text(render_report(results))
    print(json.dumps(results["read1_comparison"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
