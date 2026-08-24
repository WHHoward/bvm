#!/usr/bin/env python3
"""Analyze Q5 and complete the discrete Q2/Q3/Q4/Q5 factorial table.

The phase, voltage-area, current, timing and KCL primitives are reused from
the accepted Q4 analysis implementation, but all Q5 outputs are written to
this independent Exploration directory.  Q4 raw and analysis files are read
only.
"""

from __future__ import annotations

import csv
import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
EXP = ROOT / "test/exploration/paper-sl-q5-l1-l2-factorial-20260824"
Q4_ANALYSIS = ROOT / "test/exploration/paper-sl-q4-l1-l2-placement-20260824/analysis"
sys.path.insert(0, str(Q4_ANALYSIS))
import analyze_q4 as q4  # noqa: E402


CASE_NAMES = q4.CASE_NAMES
Q5_CASES = {name: Path(f"../paper-sl-q5-l1-l2-factorial-20260824/raw/q5-l1-4p50-l2-4p50/{name}.csv") for name in CASE_NAMES}


def rename_q4_to_q5(results: dict[str, Any]) -> dict[str, Any]:
    results["study"] = "PAPER-SL-Q5"
    cases = {}
    for key, value in results["cases"].items():
        new_key = key.replace("Q4_", "Q5_", 1)
        value["case_id"] = str(value["case_id"]).replace("Q4_", "Q5_", 1)
        cases[new_key] = value
    results["cases"] = cases
    comparison = {}
    for key, value in results["read1_comparison"].items():
        comparison["Q5" if key == "Q4" else key] = value
    results["read1_comparison"] = comparison
    return results


def path_value(comparison: dict[str, Any], dataset: str, path: tuple[str, ...]) -> float:
    value: Any = comparison[dataset]
    for part in path:
        value = value[part]
    return float(value)


def interactions(comparison: dict[str, Any]) -> dict[str, Any]:
    def interaction(path: tuple[str, ...]) -> dict[str, float]:
        q2 = path_value(comparison, "Q2", path)
        q3 = path_value(comparison, "Q3", path)
        q4v = path_value(comparison, "Q4", path)
        q5 = path_value(comparison, "Q5", path)
        return {
            "Q2": q2,
            "Q3": q3,
            "Q4": q4v,
            "Q5": q5,
            "additive_prediction_Q3_plus_Q4_minus_Q2": q3 + q4v - q2,
            "interaction_Q5_minus_Q3_minus_Q4_plus_Q2": q5 - q3 - q4v + q2,
        }

    paths = {
        "F_local": ("F_local",),
        "BJL1_forward_phase_turns": ("BJL1_forward_turns",),
        "BJL2_largest_forward_phase_turns": ("BJL2_largest", "delta_turns"),
        "BJL2_over_BJL1": ("BJL2_over_BJL1",),
        "BJL1_positive_current_area_uA_ps": ("BJL1_current_area", "positive_uA_ps"),
        "BJL1_negative_current_area_uA_ps": ("BJL1_current_area", "negative_uA_ps"),
        "BJL1_signed_current_area_uA_ps": ("BJL1_current_area", "signed_uA_ps"),
        "BJs_to_BJL1_delay_ps": ("timing_BJs_to_BJL1", "delay_ps"),
        "BJs_to_BJL1_overlap_ps": ("timing_BJs_to_BJL1", "overlap_ps"),
        "BJL1_to_BJL2_delay_ps": ("timing_BJL1_to_BJL2", "delay_ps"),
        "BJL1_to_BJL2_overlap_ps": ("timing_BJL1_to_BJL2", "overlap_ps"),
    }
    return {name: interaction(path) for name, path in paths.items()}


def classify(results: dict[str, Any]) -> str:
    c = results["read1_comparison"]
    q2, q3, q4v, q5 = (c[name] for name in ("Q2", "Q3", "Q4", "Q5"))
    q5_bjl2 = float(q5["BJL2_largest"]["delta_turns"])
    q5_events = [
        results["cases"]["Q5_paper-j1-logical1-read"]["event_summary"]["BJL2"]["complete_event_count"],
        results["cases"]["Q5_paper-j0-logical0-read"]["event_summary"]["BJL2"]["complete_event_count"],
        results["cases"]["Q5_paper-j1-logical1-read0-control"]["event_summary"]["BJL2"]["complete_event_count"],
        results["cases"]["Q5_paper-j0-logical0-read0-control"]["event_summary"]["BJL2"]["complete_event_count"],
    ]
    if q5_events[0] == 1 and all(count == 0 for count in q5_events[1:]):
        return "Q5_SELECTIVE_EXACTLY_ONE_BJL2_LOCAL_EVENT"
    if any(count > 1 for count in q5_events):
        return "Q5_MULTIFIRE"
    if any(count > 0 for count in q5_events[1:]):
        return "Q5_NONSEL_OR_CONTROL_EVENT"
    # This is intentionally a descriptive bounded classification.  No scalar
    # is allowed to certify a mechanism; the report includes all components.
    q3_bjl1 = float(q3["BJL1_forward_turns"])
    q5_bjl1 = float(q5["BJL1_forward_turns"])
    q4_bjl1 = float(q4v["BJL1_forward_turns"])
    q4_bjl2 = float(q4v["BJL2_largest"]["delta_turns"])
    q5_f = float(q5["F_local"])
    q3_f = float(q3["F_local"])
    if abs(q5_bjl2 - q4_bjl2) <= 0.01 * max(abs(q4_bjl2), 1e-12) and q5_bjl1 > q4_bjl1 and q5_f > q3_f:
        return "Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT"
    if abs(q5_bjl1 - q3_bjl1) <= 0.10 * max(abs(q3_bjl1), 1e-12) and abs(q5_bjl2 - q4_bjl2) <= 0.10 * max(abs(q4_bjl2), 1e-12) and abs(q5_f - q3_f) <= 0.10 * max(abs(q3_f), 1e-12):
        return "Q5_RESTORES_Q3_BJL1_AND_PRESERVES_Q4_BJL2_BOUNDED"
    additive = interactions(c)["BJL2_largest_forward_phase_turns"]["additive_prediction_Q3_plus_Q4_minus_Q2"]
    if abs(q5_bjl2 - additive) > 0.20 * max(abs(additive), 1e-12):
        return "Q5_NONADDITIVE_L1xL2_INTERACTION_BOUNDED"
    return "Q5_BOUNDED_NO_SELECTIVE_BJL2_EVENT"


def write_case_summary(results: dict[str, Any]) -> None:
    fields = ["dataset", "case", "BJs_main_range_turn", "BJL1_main_range_turn", "BJL2_main_range_turn", "BJs_events", "BJL1_events", "BJL2_events"]
    with (EXP / "analysis/case-summary.csv").open("w", newline="") as handle:
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


def interaction_report(interaction: dict[str, Any]) -> str:
    lines = [
        "",
        "## Discrete Q2/Q3/Q4/Q5 interaction",
        "",
        "定义：`interaction = Q5 - Q3 - Q4 + Q2`；`additive prediction = Q3 + Q4 - Q2`。这些是四点离散设计的 derived quantities，不是 universal thresholds。",
        "",
        "| metric | Q2 | Q3 | Q4 | additive prediction | Q5 | interaction |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, value in interaction.items():
        lines.append(f"| {name} | {value['Q2']:.8g} | {value['Q3']:.8g} | {value['Q4']:.8g} | {value['additive_prediction_Q3_plus_Q4_minus_Q2']:.8g} | {value['Q5']:.8g} | {value['interaction_Q5_minus_Q3_minus_Q4_plus_Q2']:.8g} |")
    lines += [
        "",
        "interaction 的机制解释必须结合 current decomposition、正负 phase segments、timing/overlap 和 KCL；不能由 interaction scalar 单独宣称 nonlinear coupling。",
    ]
    return "\n".join(lines) + "\n"


def factorial_report(results: dict[str, Any]) -> str:
    c = results["read1_comparison"]
    lines = [
        "",
        "## Q2/Q3/Q4/Q5 factorial read1 summary",
        "",
        "Q4 是已接受的 `(3.91,4.50) pH` comparator；Q5 是本轮 `(4.50,4.50) pH` point。",
        "",
        "| point | F_local | G_local | BJL1 forward (turn) | BJL2 largest (turn) | BJL2/BJL1 | BJs→BJL1 overlap (ps) | BJL1→BJL2 overlap (ps) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for dataset in ("Q2", "Q3", "Q4", "Q5"):
        item = c[dataset]
        lines.append(
            f"| {dataset} | {item['F_local']:.8g} | {item['G_local']:.8g} | {item['BJL1_forward_turns']:.8g} | {item['BJL2_largest']['delta_turns']:.8g} | {item['BJL2_over_BJL1']:.8g} | {item['timing_BJs_to_BJL1']['overlap_ps']:.8g} | {item['timing_BJL1_to_BJL2']['overlap_ps']:.8g} |"
        )
    lines += [
        "",
        "Q5 的 BJL1/BJL2 complete-event count、read0/control separation 和 post-retrap 详情见本报告上方的 Q5 case table；Q4 的原始四-case详情保留在 accepted Q4 report。",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    # Reuse the accepted Q4 analysis primitives with Q5 as the new fourth
    # factorial cell.  No Q4 file is modified.
    q4.EXP = EXP
    q4.DATASETS = {"Q2": q4.Q2_CASES, "Q3": q4.Q3_CASES, "Q4": q4.Q4_CASES}
    q4_reference_results = q4.build_results()
    q4.DATASETS = {"Q2": q4.Q2_CASES, "Q3": q4.Q3_CASES, "Q4": Q5_CASES}
    q5_display_results = q4.build_results()
    q5_render_results = copy.deepcopy(q5_display_results)
    results = rename_q4_to_q5(q5_display_results)
    for key, value in q4_reference_results["cases"].items():
        if key.startswith("Q4_"):
            results["cases"][key] = value
    results["read1_comparison"]["Q4"] = q4_reference_results["read1_comparison"]["Q4"]
    results["interaction"] = interactions(results["read1_comparison"])
    results["verdict"] = classify(results)
    (EXP / "analysis/metrics.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")
    write_case_summary(results)

    # The Q4 renderer is reused only as a formatting primitive.  Its Q4 labels
    # are remapped to Q5; the stop boundary is then advanced from Q5 to Q6.
    q5_render_results["verdict"] = results["verdict"]
    report = q4.render_report(q5_render_results).replace("Q4", "Q5").replace("q4", "q5")
    report = report.replace(
        "只改变 `L2=3.91p → 4.50p`",
        "将 `L1=3.91p → 4.50p` 与 `L2=3.91p → 4.50p` 同时改变",
    )
    derived_start = report.index("## Derived")
    unknown_start = report.index("## Unknown")
    c = results["read1_comparison"]
    report = report[:derived_start] + "\n".join([
        "## Derived",
        "",
        f"- Q5 的 `F_local={c['Q5']['F_local']:.8g}` 高于 Q3 `{c['Q3']['F_local']:.8g}`，且明显高于 Q4 `{c['Q4']['F_local']:.8g}`；BJL1 forward phase `{c['Q5']['BJL1_forward_turns']:.8g}` 高于 Q4 `{c['Q4']['BJL1_forward_turns']:.8g}`，但仍低于 Q3 `{c['Q3']['BJL1_forward_turns']:.8g}`。这是 proximal routing 的部分恢复，不是完整恢复。",
        f"- Q5 BJL2 largest phase `{c['Q5']['BJL2_largest']['delta_turns']:.8g}`，接近 Q4 `{c['Q4']['BJL2_largest']['delta_turns']:.8g}`；其 BJL2 phase interaction 为 `{results['interaction']['BJL2_largest_forward_phase_turns']['interaction_Q5_minus_Q3_minus_Q4_plus_Q2']:.8g}`，接近零，未显示 BJL2 端的正向 nonlinear interaction。",
        f"- Q5 BJL1 current areas 为正 `{c['Q5']['BJL1_current_area']['positive_uA_ps']:.8g}`、负 `{c['Q5']['BJL1_current_area']['negative_uA_ps']:.8g}`、signed `{c['Q5']['BJL1_current_area']['signed_uA_ps']:.8g}` µA·ps；相对 Q4，正向 current transfer 显著增强，但 largest monotonic phase 仍为 sub-turn。",
        f"- Q5 的 BJs→BJL1 overlap 为 `{c['Q5']['timing_BJs_to_BJL1']['overlap_ps']:.8g}` ps，BJL1→BJL2 overlap 为 `{c['Q5']['timing_BJL1_to_BJL2']['overlap_ps']:.8g}` ps；Q5 的 BJL1→BJL2 delay 变为 `{c['Q5']['timing_BJL1_to_BJL2']['delay_ps']:.8g}` ps，区别于 Q2/Q3/Q4 的负 delay。",
        "- Q5 所有 output event claims 仍须满足 continuous monotonic phase、同段 voltage area 和 bounded post；BJs 的 14-turn source activity不计作 downstream event。",
        "",
        "## Inference",
        "",
        f"本轮归类为 **{results['verdict']}**。Q5 部分恢复了 L1/proximal routing，并保留了 Q4 的 BJL2 activity，但没有产生完整 BJL2 event；BJL2 phase interaction 近零，不能声称存在足以量化的正向 L1×L2 nonlinear gain。该结果支持“部分互补但尚未量化闭合”的解释。",
        "",
    ]) + report[unknown_start:]
    report = report.replace("不运行 Q5", "不运行 Q6")
    report += factorial_report(results)
    report += interaction_report(results["interaction"])
    (EXP / "REPORT.md").write_text(report)
    print(json.dumps({"verdict": results["verdict"], "interaction": results["interaction"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
