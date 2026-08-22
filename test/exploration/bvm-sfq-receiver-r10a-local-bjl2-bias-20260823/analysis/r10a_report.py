#!/usr/bin/env python3
"""Render the R10-A raw-analysis summary into the immutable report."""

from __future__ import annotations

import json
from pathlib import Path


RUN = Path(__file__).resolve().parents[1]
REPO = RUN.parents[2]
summary = json.loads((RUN / "analysis/r10a-summary.json").read_text(encoding="utf-8"))
r9 = json.loads(
    (REPO / "test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/analysis/r9a-summary.json").read_text(encoding="utf-8")
)


def n(value, digits=6):
    if value is None:
        return "—"
    return f"{value:.{digits}f}"


def row(values):
    return "| " + " | ".join(str(value) for value in values) + " |\n"


def case_data(case):
    return summary["cases"][case]


def r9_case_data(case):
    return r9["cases"][case]


cases = ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]
lines = []
lines.append("# R10-A 结果报告：output-side local BJL2 bias routing\n")
lines.append("日期：2026-08-23（Asia/Shanghai）\n")
lines.append("父基线：R9-A，`333945981332f9b37b4228e71d82201427b782cd`\n")
lines.append("实验目录：`test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/`\n")
lines.append("\n## Verdict\n")
lines.append("**`BACK_ACTION_OR_NONSELECTIVE_FAILURE`**\n")
lines.append(
    "四个 matched case 都在 local feed ramp 后进入 BJL2 multi-turn running；两个 READ=0 control 也出现同等级完整连续 phase activity。"
    " 因此 read1/read0 selective local event、retrap 和 source guard 均未成立。这个结论只否定本实验的"
    " `214 µA / 21.4 mV / 100 Ω / 10 pH` 单点，不把整个 local-bias family 说成普遍不可能。\n"
)
lines.append("\n## 1. Topology and frozen boundary\n")
lines.append(
    "local feed 注入 native QB node 4（BJL2 上端）：`BIAS → R_LOCAL_BJL2=100 Ω → "
    "L_LOCAL_BJL2=10 pH → node4`，独立电压源 `V(BIAS)=21.4 mV` ramp 到 DC，负端回地。"
    " 这不是直接跨 BJL2 的 passive damping shunt；它是一个具有有限 DC/AC 源阻抗的主动 bias branch。"
    " 在 1.5 ps，`Z≈100+j41.89 Ω`，`|Z|≈108.42 Ω`。\n"
)
lines.append(
    "R9-A 的 `L1=L2=2.50 pH`、`IB=90 µA`、三颗 JJ AREA、`RJ1/RJ2`、R6-B transformer、"
    "canonical BVM、`OUT=10 Ω` 和 `dt=0.0125 ps` 全部保持。\n"
)
lines.append("\n## 2. Artifact QA\n")
lines.append(
f"四个 raw 均 `VALID`：每个 13599 rows / 44 fields，时间 `0–169.9875 ps` 严格递增，"
f"dt 为约 `0.0125/0.025 ps`，JoSIM stderr 为空；binary 为 `v2.7.2837d13`。分析使用实际 CSV 时间轴和直接同 JJ `P/V`。\n"
)
lines.append("\n## 3. Analytic selection versus actual dynamic behavior\n")
lines.append(
    "R10-A analytic precheck 的 calibrated static continuation 给出正向 coupled fold `216.223788 µA`，"
    "并选择 feed `214.0 µA`。预估静态 split 是 `I(BJL2)=187.97 µA`、`I(L2)=-26.03 µA`、"
    "`I(L1)=-116.03 µA`、`I(BJs)=-53.14 µA`、`I(BJL1)=62.89 µA`。这只用于选点。\n"
)
lines.append(
    "实际仿真没有形成这个 settled operating point：local source ramp 后就开始 running。"
    " `[80,90) ps` 的数值只是 running waveform 的 window median，不应称 settled OP。\n"
)
lines.append("\n| case | nominal `[80,90)` P(BJs) rad | P(BJL1) rad | P(BJL2) rad | I(BJs) µA | I(BJL1) µA | I(BJL2) µA | I(L1) µA | I(L2) µA | I(RB) µA | local feed µA |\n")
lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
for case in cases:
    q = case_data(case)
    lines.append(
        row(
            [
                case,
                n(q["junctions"]["BJs"]["pre_median_rad"], 5),
                n(q["junctions"]["BJL1"]["pre_median_rad"], 5),
                n(q["junctions"]["BJL2"]["pre_median_rad"], 5),
                n(q["junctions"]["BJs"]["pre_current_uA"], 3),
                n(q["junctions"]["BJL1"]["pre_current_uA"], 3),
                n(q["junctions"]["BJL2"]["pre_current_uA"], 3),
                n(q["branches"]["L1"]["pre_uA"], 3),
                n(q["branches"]["L2"]["pre_uA"], 3),
                n(q["branches"]["RB"]["pre_uA"], 3),
                n(q["branches"]["R_LOCAL_BJL2"]["pre_uA"], 3),
            ]
        )
    )
lines.append(
    "这些 running-window medians 与 analytic static split 明显不同；local branch 实际约 `205.9 µA`，"
    "且 `I(V_BJL2_BIAS)` 约为 `-205.9 µA`（JoSIM voltage-source branch sign）。不能把它们当作稳定 load-line。\n"
)

lines.append("\n## 4. BJL2 phase / same-JJ voltage-area evidence\n")
lines.append(
    "以下均为同一 BJL2、同一方向、同一 `[94,130) ps` activity window。`qualifying segment count` 是"
    "满足 phase/area 一致性的连续 segments 数，不是 event count；由于轨迹已 free-run，不能把它解释为多个合法 output events。\n"
)
lines.append("| case | activity range turn | largest monotonic segment turn | same-segment V-area turn | residual turn | qualifying segments | post p2p turn |\n")
lines.append("|---|---:|---:|---:|---:|---:|---:|\n")
for case in cases:
    q = case_data(case)["junctions"]["BJL2"]
    s = q["largest_segment"]
    lines.append(row([case, n(q["activity_range_turn"], 6), n(s["phase_delta_turns"], 6), n(s["area_turns"], 6), n(s["residual_turns"], 8), q["qualifying_complete_segment_count"], n(q["post_phase_p2p_turn"], 6)]))
lines.append(
    "read1 的最大 segment 约 `2.180741 turn`、同段面积约 `2.180801 turn`；read0 约 `2.181203/2.181258 turn`；"
    "两个 READ=0 control 约 `2.179977/2.180023 turn` 和 `2.179977/2.180026 turn`。"
    " phase/area consistency 证实的是连续 running 轨迹中的同 JJ 活动，不是 exactly-one。\n"
)
lines.append("\nBJL2 的 `[94,130) ps` activity range 与 `[150,170) ps` post p2p 都约 8–14 turns，四个 case 都没有 retrap 到 bounded superconducting state；这是 free-running，而不是 one-shot。\n")

lines.append("\n## 5. BJs/BJL1 and complete bias split\n")
lines.append("| case | BJs activity range turn | BJL1 activity range turn | BJL2 activity range turn | local-feed p2p µA | RJ1 p2p µA | RJ2 p2p µA |\n")
lines.append("|---|---:|---:|---:|---:|---:|---:|\n")
for case in cases:
    q = case_data(case)
    lines.append(row([case, n(q["junctions"]["BJs"]["activity_range_turn"], 6), n(q["junctions"]["BJL1"]["activity_range_turn"], 6), n(q["junctions"]["BJL2"]["activity_range_turn"], 6), n(q["branches"]["R_LOCAL_BJL2"]["activity"]["p2p"], 4), n(q["branches"]["RJ1"]["activity"]["p2p"], 4), n(q["branches"]["RJ2"]["activity"]["p2p"], 4)]))
lines.append(
    "BJs/BJL1 也随同一 running state 出现多圈 activity；这不是只在 BJL2 输出侧发生的受控 nonlinear gain。"
    " `RB` 的 DC current 仍显示为 90 µA，但 L1/L2/JJ branches 动态 redistributing。\n"
)

lines.append("\n## 6. Read discrimination and canonical BVM guard\n")
lines.append(
    "输出侧没有保持 read discrimination：BJL2 activity range 为 read1 `14.262288 turn`、read0 `14.281737 turn`、"
    "logical1 control `14.279923 turn`、logical0 control `14.279859 turn`；最大 segment 也都约 `2.18 turn`。"
    " controls 与 read cases 同等级，故判 nonselective/free-running。\n"
)
lines.append("相对 R9-A matched controls 的 post-window source disturbance：\n")
lines.append("| metric | R9-A logical1 READ=0 | R10-A logical1 READ=0 | R9-A logical0 READ=0 | R10-A logical0 READ=0 |\n")
lines.append("|---|---:|---:|---:|---:|\n")
for key, unit in [("V(SL1)", "µV"), ("V(N6|XBVM1)", "µV"), ("I(L_SL|XBVM1)", "µA")]:
    lines.append(row([key + " post p2p", n(r9_case_data("logical1-read0-control")["source"][key]["post"]["p2p"], 6), n(case_data("logical1-read0-control")["source"][key]["post"]["p2p"], 6), n(r9_case_data("logical0-read0-control")["source"][key]["post"]["p2p"], 6), n(case_data("logical0-read0-control")["source"][key]["post"]["p2p"], 6)]))
lines.append(
    "R10-A controls 的 `V(SL1)`/`V(N6)`/`I(L_SL)` post p2p 约 `200.5 µV / 84.6 µV / 15.0 µA`，"
    "而 R9-A controls 约 `0.0014 µV / 0.0029 µV / 0.000119 µA`。这直接显示 local-bias point 的 receiver-induced source loading。\n"
)
lines.append("R10-A read1 的绝对 JS1/JS2 phase drift 仍不能单独用作 receiver back-action，因为 canonical read1 本身约有 -3-turn running；但 R10-A controls 的 JS1/JS2 post p2p 约 `0.0171/0.0207 turn`，远高于 R9-A controls 的约 `6.6e-6/7.3e-7 turn`，与 source guard failure 一致。\n")

lines.append("\n## 7. Observed / Derived / Inference / Unknown\n")
lines.append("### Observed\n")
lines.append("- 四个 raw artifact 有效；local branch、source、native QB、BVM storage probes 全部存在。\n")
lines.append("- local feed ramp 后约 2–10 ps 已出现 BJL2 activity；在 read 尚未发生前，两个 READ=0 controls 也进入 running。\n")
lines.append("- `[94,130) ps` BJL2 最大同段 phase/area 约 2.18 turn，`[150,170) ps` 仍有约 8.07–8.07 turn 级 post p2p。\n")
lines.append("- read1、read0、两个 controls 的输出活动几乎相同；source/N6/SL post-window disturbance 相对 R9-A controls 显著增大。\n")
lines.append("### Derived\n")
lines.append("- `continuous phase + same-JJ voltage area` 的一致性存在，但它描述的是 repeated running segments；不支持 exactly-one output event。\n")
lines.append("- `[80,90) ps` 不能作为 settled OP：BJL2 在该窗仍有约 4.03 turn phase range。\n")
lines.append("- `RB=90 µA` 没有改变，但 local branch、L1/L2、BJs/BJL1/BJL2 的实际动态分流远离 analytic static split。\n")
lines.append("### Inference\n")
lines.append("- 该单点的主要失败模式是 **dynamic nonselective/free-running onset**，不是 read1 signal 不存在。\n")
lines.append("- 静态 coupled-fold 作为选点依据不足以保证动态稳定；startup ramp、有限源阻抗、JJ 电容/阻尼和完整 loop load-line 的瞬态共同把实际网络带入 running。具体单项因果贡献未被本单点分离。\n")
lines.append("- 该结果只 falsify 当前 `214 µA` local-feed instance；不把所有 output-side bias-routing 拓扑普遍否定。按 preregistration，不追加 local-bias sweep。\n")
lines.append("### Unknown\n")
lines.append("- 没有在本轮测试更低 feed、不同 ramp 或不同 source impedance，因此不知道是否存在 selective local-bias window。\n")
lines.append("- 没有 timestep refinement；没有 JTL/T1；没有 downstream SFQ delivery 证据。\n")

lines.append("\n## 8. Final disposition\n")
lines.append("Artifact status：`VALID`。Physical R10-A verdict：**`BACK_ACTION_OR_NONSELECTIVE_FAILURE`**。\n")
lines.append("当前 point 不满足 read1-only output activity、read0/control zero、retrap 或 canonical BVM source guard。停止该 local-bias single-point branch；下一设计边界按任务要求转向显式 `temporal rectification / hold` 的 BVM-specific QB redesign，不接 JTL/T1，也不做本点的追加 sweep。\n")

(RUN / "analysis/R10A_REPORT.md").write_text("".join(lines), encoding="utf-8")
print("wrote analysis/R10A_REPORT.md")
