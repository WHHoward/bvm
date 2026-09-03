#!/usr/bin/env python3
"""Build the compact matrix/protection summaries from per-run metrics."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


EXP = Path(__file__).resolve().parents[1]
RJ = (("R12", 12.0), ("R11P5", 11.5), ("R11", 11.0))
TIMESTEPS = ("T100", "T050", "T025", "T0125")


def load_metrics() -> dict[str, dict[str, Any]]:
    manifest = json.loads((EXP / "analysis/effective_run_manifest.json").read_text(encoding="utf-8"))
    return {
        str(item["run_id"]): json.loads(
            (EXP / "runs" / str(item["run_id"]) / "analysis/metrics.json").read_text(encoding="utf-8")
        )
        for item in manifest["runs"]
    }


def f(value: Any, digits: int = 6) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f}"


def four(run_id: str, metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return metrics[run_id]


def fine_pair(rkey: str, metrics: dict[str, dict[str, Any]]) -> dict[str, Any]:
    left = metrics[f"F4_{rkey}_T025"]
    right = metrics[f"F4_{rkey}_T0125"]
    lf = left["four_bvm_summary"]
    rf = right["four_bvm_summary"]
    lp = lf["BJ2_principal_event"]
    rp = rf["BJ2_principal_event"]
    lstage = left["transport"]["stages"]
    rstage = right["transport"]["stages"]
    event_count_same = (
        lf["BJ2_READ1_complete_segment_count"] == rf["BJ2_READ1_complete_segment_count"]
        and lf["BJ2_READ1_clean_separated_event_count"] == rf["BJ2_READ1_clean_separated_event_count"]
    )
    polarity_same = bool(lp and rp and lp["direction"] == rp["direction"])
    late_presence_same = bool(lf["late_complete_count_after_principal"]) == bool(rf["late_complete_count_after_principal"])
    late_candidate_presence_same = bool(lf["late_candidate_count_after_principal"]) == bool(rf["late_candidate_count_after_principal"])
    flux_diff = abs(float(lf["BJ2_principal_flux_turns"]) - float(rf["BJ2_principal_flux_turns"]))
    phase_diff = abs(float(lf["BJ2_principal_phase_step_turns"]) - float(rf["BJ2_principal_phase_step_turns"]))
    onset_diff = abs(float(lf["BJ2_principal_onset_ps"]) - float(rf["BJ2_principal_onset_ps"]))
    stage_count_same = all(
        (
            lstage[f"JTL{stage}"]["B02_complete_segment_count"],
            lstage[f"JTL{stage}"]["B02_clean_separated_event_count"],
        )
        == (
            rstage[f"JTL{stage}"]["B02_complete_segment_count"],
            rstage[f"JTL{stage}"]["B02_clean_separated_event_count"],
        )
        for stage in range(1, 7)
    )
    stage_order_same = (
        bool(left["transport"]["B02_principal_onset_strictly_increasing"])
        == bool(right["transport"]["B02_principal_onset_strictly_increasing"])
    )
    criteria = {
        "read_local_event_count_same": event_count_same,
        "polarity_same": polarity_same,
        "late_complete_event_presence_same": late_presence_same,
        "late_candidate_presence_same": late_candidate_presence_same,
        "principal_flux_diff_le_0.02_phi0": flux_diff <= 0.02,
        "principal_phase_step_diff_le_0.02_turn": phase_diff <= 0.02,
        "principal_onset_diff_le_0.5_ps": onset_diff <= 0.5,
        "jtl_b02_stage_count_same": stage_count_same,
        "jtl_b02_order_flag_same": stage_order_same,
    }
    return {
        "rj1_key": rkey,
        "left_run": left["run_id"],
        "right_run": right["run_id"],
        "criteria": criteria,
        "all_fine_pair_criteria_pass": all(criteria.values()),
        "principal_flux_diff_phi0": flux_diff,
        "principal_phase_step_diff_turn": phase_diff,
        "principal_onset_diff_ps": onset_diff,
        "stage_count_sequence_T025": [
            [lstage[f"JTL{stage}"]["B02_complete_segment_count"], lstage[f"JTL{stage}"]["B02_clean_separated_event_count"]]
            for stage in range(1, 7)
        ],
        "stage_count_sequence_T0125": [
            [rstage[f"JTL{stage}"]["B02_complete_segment_count"], rstage[f"JTL{stage}"]["B02_clean_separated_event_count"]]
            for stage in range(1, 7)
        ],
    }


def late_phase_residual(metrics_item: dict[str, Any]) -> list[float]:
    four_result = metrics_item["four_bvm_summary"]
    bj2 = metrics_item["junctions"]["BJ2"]
    principal = four_result["BJ2_principal_event"]
    if principal is None:
        return []
    return [
        float(item["phase_turns"])
        for item in bj2["segments"]
        if float(item["start_time_ps"]) > float(principal["end_time_ps"])
        and float(item["start_time_ps"]) < 170.0
        and abs(float(item["phase_turns"])) >= 0.2
    ]


def make_four_matrix(metrics: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# FOUR_BVM_MATRIX",
        "",
        "范围：historical BVMSim 4-BVM accumulated sensing line → BVMSim-compatible QB → six-stage JTL；只改变 RJ1 与 `.tran` timestep。有效 four-BVM raw 是每个 run 的 `attempt-03`，`attempt-01`/`attempt-02` 保留为探针不完整或路径失败的历史尝试。",
        "",
        "`READ1_RESPONSE` 为 `[110,170)` ps。`BJ1/BJ2/JTL` 的 net turns 是窗口端点轨迹，不是 SFQ count；event 列只来自同一 JJ、同一连续单调 segment 的 phase/area/retrap 检查。",
        "",
        "| RJ1 (ohm) | timestep (ps) | BJ1 net trajectory (turns) | BJ2 net trajectory (turns) | late BJ2 complete / candidate | JTL1 B02 (net; complete/clean) | JTL6 B02 (net; complete/clean) | branch observation |",
        "|---:|---:|---:|---:|---|---|---|---|",
    ]
    for rkey, ohm in RJ:
        for timestep in TIMESTEPS:
            item = metrics[f"F4_{rkey}_{timestep}"]
            summary = item["four_bvm_summary"]
            stages = item["transport"]["stages"]
            lines.append(
                f"| {ohm:g} | {item['timestep_ps']:g} | {f(summary['BJ1_READ1_net_turns'])} | {f(summary['BJ2_READ1_net_turns'])} | {summary['late_complete_count_after_principal']}/{summary['late_candidate_count_after_principal']} | {f(stages['JTL1']['B02_net_phase_turns'])}; {stages['JTL1']['B02_complete_segment_count']}/{stages['JTL1']['B02_clean_separated_event_count']} | {f(stages['JTL6']['B02_net_phase_turns'])}; {stages['JTL6']['B02_complete_segment_count']}/{stages['JTL6']['B02_clean_separated_event_count']} | `{summary['branch_observation']}` |")
    lines.extend(
        [
            "",
            "## 关键观察（pre-review）",
            "",
            "- 三个 RJ1 在 0.025/0.0125 ps 的 BJ2 都是约 4.023–4.024 turn 的主连续 segment；READ1 净轨迹约 4.999 turn。两者不能互换为“四个/五个 SFQ”。",
            "- RJ1=12 在 0.1 ps 约 4-turn、0.05 ps 已约 5-turn；RJ1=11.5 和 11 在 0.1/0.05 ps 约 4-turn，但在两个 fine timestep 也约 5-turn。变化首先已出现在 BJ1/BJ2 的 QB-level trajectory，不能归因于 JTL 图形 alone；因果机制仍未知。",
            "- fine pair 的 strict complete/clean count、极性、late-complete presence、主 event phase/area/onset 与六级 B02 count sequence 需见 `analysis/RJ1_ROBUSTNESS_SUMMARY.md`；这只是 exploratory engineering comparison，不是 convergence proof。",
            "- fine BJ2 principal 后仍有一个 sub-unit late candidate（约 0.97 turn 量级），但没有被 strict complete 标为额外完整 event；因此不能写成“late excursion 消失”。",
            "",
            "## Boundary",
            "",
            "该表不证明 canonical BVM、single-BVM full six-stage Gate、paper mechanism identity 或 process margin；最终分类待 Sol XHigh reviewer。",
            "",
        ]
    )
    return "\n".join(lines)


def make_protection(metrics: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# SINGLE_BVM_PROTECTION",
        "",
        "范围：既有 single historical BVMSim BVM → 12-JJ sensing line → QB → six-stage JTL-loaded fixture；读窗口按既有 `[70,82)` ps。S0 false trigger 只在 S0 行判定；S1 行展示 BJ2 与 JTL B02 的同段 phase/area candidate。",
        "",
        "| RJ1 (ohm) | timestep (ps) | S0 false trigger / extra | S1 BJ2 phase / flux (turns / Phi0) | JTL1 B02 candidate phase / flux; complete | JTL6 B02 phase / flux; complete/clean | protection verdict |",
        "|---:|---:|---|---|---|---|---|",
    ]
    for rkey, ohm in RJ:
        for timestep in ("T025", "T0125"):
            s0 = metrics[f"S1B_{rkey}_{timestep}_S0"]["single_bvm_protection"]
            s1 = metrics[f"S1B_{rkey}_{timestep}_S1"]["single_bvm_protection"]
            timestep_ps = 0.025 if timestep == "T025" else 0.0125
            j1 = s1["jtl_B02_read"][0]
            j6 = s1["jtl_B02_read"][5]
            verdict = f"{s0['protection_verdict']} + {s1['protection_verdict']}"
            lines.append(
                f"| {ohm:g} | {timestep_ps:g} | {s0['S0_false_trigger_or_extra']} | {f(s1['BJ2_principal_phase_turns'])} / {f(s1['BJ2_principal_flux_turns'])} | {f(j1['principal_candidate_phase_turns'])} / {f(j1['principal_candidate_area_turns'])}; {j1['complete_count_read']} | {f(j6['principal_phase_turns'])} / {f(j6['principal_area_turns'])}; {j6['complete_count_read']}/{j6['clean_count_read']} | `{verdict}` |")
    lines.extend(
        [
            "",
            "## 关键观察",
            "",
            "- 12/11.5/11 ohm 的 S0 均没有 strict complete BJ2/JTL B02 read/post trigger；这是有限 fixture 下的 bounded observation，不是普适无 false-trigger 保证。",
            "- 三个 RJ1 的 S1 BJ2 都保持约 1.0035–1.0075 turn phase 与 1.0036–1.0075 Phi0 area；这支持 QB source-level approximately-one candidate 在本矩阵内没有明显破坏。",
            "- JTL1–JTL5 B02 约 0.91 turn candidate，未达到本实验 complete ≥1 turn；JTL6 B02 约 1.067 turn 且 clean。因而 full six-stage one-event protection 在本 strict criteria 下是 `INCONCLUSIVE`，不能只凭 JTL6 宣称逐级保持。",
            "",
            "## Boundary",
            "",
            "S1 source-level candidate、local JTL activity 和 downstream identity 是不同证据层；表格不升级为 system Gate。",
            "",
        ]
    )
    return "\n".join(lines)


def make_robustness(metrics: dict[str, dict[str, Any]]) -> str:
    pair_rows = {rkey: fine_pair(rkey, metrics) for rkey, _ in RJ}
    lines = [
        "# RJ1_ROBUSTNESS_SUMMARY",
        "",
        "状态：`PRELIMINARY_PENDING_SOL_XHIGH_REVIEW`。本文件在 reviewer 前生成；不会因为预期的 4→5 现象而提前选出 winner。",
        "",
        "## 总体结论（当前证据层）",
        "",
        "- 三个 RJ1 的 0.025 vs 0.0125 ps fine pair 都满足本实验预注册的数值/计数一致性检查；这说明 tested fine pair 内部没有看到该指标层面的 timestep mismatch。它不等于 timestep convergence proof。",
        "- 三个 RJ1 都从 coarse 的约 4-turn net trajectory 转到 fine 的约 5-turn net trajectory；fine BJ2 本身仍是约 4-turn continuous multi-turn segment 加 late sub-unit residual，而不是四个 separated SFQ。",
        "- RJ1=11.5 和 11 在 fine pair 上没有从这些数据获得比彼此更强的 robustness 证据；11.5 不能在 reviewer 前被称为 winner。",
        "- single-BVM S0 在三个 RJ1 均没有 strict complete false trigger；S1 BJ2 约 1 Phi0 保持，但 JTL1–JTL5 B02 只到约 0.91-turn candidate，故 full six-stage protection 仍是 `INCONCLUSIVE`，三者均不能升级为 protected PASS。",
        "",
        "## RJ1 × fine timestep criteria",
        "",
        "| RJ1 | pair | count same | polarity | late complete presence | late candidate presence | flux diff (Phi0) | phase diff (turn) | onset diff (ps) | JTL count/order flags | fine-pair result |",
        "|---:|---|---|---|---|---|---:|---:|---:|---|---|",
    ]
    for rkey, ohm in RJ:
        row = pair_rows[rkey]
        c = row["criteria"]
        flags = "PASS" if c["jtl_b02_stage_count_same"] and c["jtl_b02_order_flag_same"] else "MISMATCH"
        lines.append(
            f"| {ohm:g} | T025 vs T0125 | {c['read_local_event_count_same']} | {c['polarity_same']} | {c['late_complete_event_presence_same']} | {c['late_candidate_presence_same']} | {f(row['principal_flux_diff_phi0'])} | {f(row['principal_phase_step_diff_turn'])} | {f(row['principal_onset_diff_ps'], 4)} | {flags} | `{('FINE_PAIR_ROBUST_OBSERVED' if row['all_fine_pair_criteria_pass'] else 'TIMESTEP_ROBUSTNESS_FAIL_OR_INCONCLUSIVE')}` |")
    lines.extend(["", "## 分 RJ1 回答", ""])
    for rkey, ohm in RJ:
        fine025 = metrics[f"F4_{rkey}_T025"]
        fine0125 = metrics[f"F4_{rkey}_T0125"]
        coarse100 = metrics[f"F4_{rkey}_T100"]
        coarse050 = metrics[f"F4_{rkey}_T050"]
        f025 = fine025["four_bvm_summary"]
        f0125 = fine0125["four_bvm_summary"]
        p025 = f025["BJ2_principal_event"]
        p0125 = f0125["BJ2_principal_event"]
        s1s = [metrics[f"S1B_{rkey}_{t}_S1"]["single_bvm_protection"] for t in ("T025", "T0125")]
        s0s = [metrics[f"S1B_{rkey}_{t}_S0"]["single_bvm_protection"] for t in ("T025", "T0125")]
        lines.extend(
            [
                f"### RJ1 = {ohm:g} ohm",
                "",
                f"- fine-step branch: T025/T0125 BJ2 net `{f(f025['BJ2_READ1_net_turns'])}` / `{f(f0125['BJ2_READ1_net_turns'])}` turn；principal same-segment phase/area `{f(f025['BJ2_principal_phase_step_turns'])}` / `{f(f025['BJ2_principal_flux_turns'])}` 与 `{f(f0125['BJ2_principal_phase_step_turns'])}` / `{f(f0125['BJ2_principal_flux_turns'])}`；两者均 continuous multi-turn，非 separated event count。",
                f"- timestep robustness: fine pair criteria `{pair_rows[rkey]['all_fine_pair_criteria_pass']}`；但 T100/T050 → fine 的 net branch 变化为 `{f(coarse100['four_bvm_summary']['BJ2_READ1_net_turns'])}` / `{f(coarse050['four_bvm_summary']['BJ2_READ1_net_turns'])}` → `{f(f025['BJ2_READ1_net_turns'])}`，所以不能把 coarse/fine 差异简单宣称为已解释的 timestep-induced branch mechanism。",
                f"- late excursion: fine BJ2 principal 后仍有 candidate phases `{[f(x,4) for x in late_phase_residual(fine025)]}`（T025），complete late event count `{f025['late_complete_count_after_principal']}`；不是“完全消失”。",
                f"- single-BVM protection: S0 flags `{[s['S0_false_trigger_or_extra'] for s in s0s]}`；S1 BJ2 phase/flux `{[f(s['BJ2_principal_phase_turns'],4) for s in s1s]}` / `{[f(s['BJ2_principal_flux_turns'],4) for s in s1s]}`；full six-stage protection `{[s['protection_verdict'] for s in s1s]}`，故当前为 bounded source-level preservation + full-chain inconclusive。",
                "- preliminary classification: `INCONCLUSIVE_PENDING_SOL_XHIGH_REVIEW`；没有据此推荐 11.5 或 11 为 winner。",
                "",
            ]
        )
    lines.extend(
        [
            "## Observed / Derived / Inference / Unknown",
            "",
            "- **Observed:** 24 个有效 solver raw、实际 timestep/grid、per-run phase/area/event-list/KCL、120 张独立图和 7 张 comparison 已生成；四-BVM 细步长的 BJ2 主段为约 4-turn continuous segment，net trajectory 约 5 turns；single S1 BJ2 约 1 Phi0。",
            "- **Derived:** fine pair 的数值/strict count comparison 如上；KCL 使用共享 `scripts/bvmtools/kcl.py`，不是本地重写。",
            "- **Inference:** 可以把各 RJ1 的 fine pair 描述为 `FINE_PAIR_ROBUST_OBSERVED`，但还不足以定义 final `ROBUST_CANDIDATE`；JTL local B02 序列没有建立完整 cross-junction event identity。",
            "- **Unknown:** 4→5 net branch 的真正动力学归因、是否只是 solver branch selection、11.5/11 的 margin/over-damping 机制、canonical BVM compatibility、paper mechanism identity 和更细 timestep behavior。",
            "",
            "## Allowed next options（不在本轮执行）",
            "",
            "1. Sol XHigh review 后决定是否把某一 RJ1 进入新的 candidate validation。",
            "2. 若 reviewer 认为有必要，设计独立 branch-attribution diagnostic；不得把本轮 net trajectory 直接当 SFQ count。",
            "3. 只有重新授权后才考虑更细 timestep、参数点或 canonical BVM 路线。",
            "",
            "## Gate",
            "",
            "`AWAITING_USER_REVIEW`；`user_reviewed=false`；`next_step_authorized=false`；`automatic_next_experiment=false`。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--timestamp", default=None)
    args = parser.parse_args()
    timestamp = args.timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    metrics = load_metrics()
    (EXP / "analysis/FOUR_BVM_MATRIX.md").write_text(make_four_matrix(metrics), encoding="utf-8")
    (EXP / "analysis/SINGLE_BVM_PROTECTION.md").write_text(make_protection(metrics), encoding="utf-8")
    (EXP / "analysis/RJ1_ROBUSTNESS_SUMMARY.md").write_text(make_robustness(metrics), encoding="utf-8")
    json_payload = {
        "generated_at": timestamp,
        "status": "PRELIMINARY_PENDING_SOL_XHIGH_REVIEW",
        "fine_pair": {rkey: fine_pair(rkey, metrics) for rkey, _ in RJ},
        "summary_files": [
            "analysis/FOUR_BVM_MATRIX.md",
            "analysis/SINGLE_BVM_PROTECTION.md",
            "analysis/RJ1_ROBUSTNESS_SUMMARY.md",
        ],
        "net_turns_are_not_sfq_counts": True,
    }
    path = EXP / "analysis/summary_metrics.json"
    path.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": json_payload["status"], "summaries": 3}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
