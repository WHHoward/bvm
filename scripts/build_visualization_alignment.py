#!/usr/bin/env python3
"""Build the V2 visualization/topology manifests and human indexes.

The manifests are the source for both indexes.  This script only reads
existing reports, raw CSV paths, plots, and schematic artifacts; it never
invokes JoSIM and never edits a scientific circuit or raw output.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

import yaml

from render_alignment_ui import render_index as render_rich_index
from render_alignment_ui import render_topology_index


ROOT = Path(__file__).resolve().parents[1]
# The documentation-only alignment rebuild is anchored to the repository HEAD
# that was present when this task started.  It is deliberately not replaced by
# the post-generation commit hash.
HEAD = "576ca9d32b15c99f8c35c4271336ffa079664b64"
MANIFEST_PATH = ROOT / "docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml"
TOPOLOGY_PATH = ROOT / "docs/TOPOLOGY_ALIGNMENT_MANIFEST.yaml"

PHASE_SEMANTICS = {
    "continuous_absolute": "原始 JoSIM P(t)/(2π) 连续相位轨迹；未基线相减、未按脉冲归零；不等于 SFQ 计数。",
    "relative_to_baseline": "相对登记 baseline 的 [P(t)-P_pre]/(2π)。",
    "event_delta": "登记同一 JJ、同一 monotonic segment 的 ΔP/(2π)。",
    "settled_well": "pre/post 稳定势阱变化 Δn；不能由连续轨迹本身替代。",
}


# The indexes are a research narrative, not a lexical directory listing.
# Keep the sequence explicit so a newly added directory cannot silently move
# an old result to a different place in the story.
EXPERIMENT_ORDER = [
    "bvm-internal-readout-20260819",
    "bvm-sfq-receiver-r0-20260819",
    "bvm-sfq-receiver-r0b-20260819",
    "bvm-sfq-receiver-r1-oneshot-20260819",
    "bvm-sfq-receiver-r1a-transfer-20260819",
    "bvm-sfq-receiver-r1b-output-jj-20260819",
    "bvm-sfq-receiver-r1b-area008-20260821",
    "bvm-sfq-receiver-r1b-differential-output-20260821",
    "bvm-sfq-receiver-r1c-bias-margin-20260821",
    "bvm-sfq-receiver-r2a-coupling-20260821",
    "bvm-sfq-receiver-r2b-damping-20260821",
    "bvm-sfq-receiver-r2c-directdrive-20260821",
    "bvm-sfq-receiver-r2d-duration-20260821",
    "bvm-sfq-receiver-r2e-ampthreshold-20260821",
    "bvm-sfq-receiver-r2f-dwell-20260821",
    "bvm-sfq-receiver-r2g-twopulse-20260821",
    "bvm-sfq-receiver-r3a-onset-extraction-20260822",
    "bvm-sfq-receiver-r4a-weak-mutual-capture-20260822",
    "bvm-sfq-receiver-r5a-biased-quantizer-20260822",
    "bvm-sfq-receiver-r5b-loadline-20260822",
    "bvm-sfq-receiver-r5c-saddle-selectivity-20260822",
    "bvm-sfq-receiver-native-qb-20260822",
    "bvm-sfq-receiver-r6a-native-qb-isolation-20260822",
    "bvm-sfq-receiver-r6b-native-qb-ratio-20260822",
    "bvm-sfq-receiver-r7a-l1-routing-20260823",
    "bvm-sfq-receiver-r8-bjl2-area070-20260823",
    "bvm-sfq-receiver-r9a-l2-routing-20260823",
    "bvm-sfq-receiver-r10a-local-bjl2-bias-20260823",
    "bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823",
    "bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823",
    "bvm-sfq-receiver-r13a-temporal-conditioning-20260823",
    "bvm-sfq-receiver-r14a-dcsfq-detector-20260823",
    "bvm-sfq-receiver-r15a-afq3-20260823",
    "bvm-sfq-receiver-r15b-magnetic-correction-20260823",
    "bvm-sfq-receiver-r15c-jset-causal-20260823",
    "bvm-sfq-receiver-r15d-jq-compressor-20260823",
    "qb-q0-standalone-current-quantized-event-20260824",
    "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824",
    "qb-q2a-source-decoupled-waveform-replay-20260824",
    "qb-q2b-central-bias-bracketing-20260824",
    "qb-q2c-uniform-junction-scale-20260824",
    "bvm-jsl-read-width-to-qb-sfq-v1-20260824",
    "paper-sl-l0-20260824",
    "paper-sl-q1-20260824",
    "paper-sl-q2-20260824",
    "paper-sl-q3-pre-20260824",
    "q3-l1-routing-closure-20260824",
    "paper-sl-q3-l1-routing-closure-20260824",
    "paper-sl-q4-l1-l2-placement-20260824",
    "paper-sl-q5-l1-l2-factorial-20260824",
    "paper-sl-q6-qb-jtl-compatibility-20260824",
    "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824",
    "physical-bvm-jsl12-qb-sfq-closure-v1-20260824",
    "qb-load-boundary-matrix-20260824",
    "parallel-qb-jtl-interface-mechanism-20260824",
    "jtl-transport-gate-polarity-replay-20260824",
    "jtl-transport-gate-v1-methodology-20260824",
    "jtl-transport-gate-v1-numerical-freeze-20260824",
    "jtl-transport-gate-v1-numerical-freeze-20260824-rerun",
    "qb-to-jtl-load-backaction-causal-audit-v1-20260824",
]

STAGE_DEFINITIONS = [
    ("stage-00", "基础 source：canonical BVM readout", range(1, 2)),
    ("stage-01", "R0–R1：trigger / passive transfer", range(2, 10)),
    ("stage-02", "R2：direct receiver feasibility", range(10, 17)),
    ("stage-03", "R3–R5：capture / quantizer closure", range(17, 22)),
    ("stage-04", "R6–R10：native QB isolation / routing", range(22, 29)),
    ("stage-05", "R11–R15：direct JTL / active-stage route", range(29, 37)),
    ("stage-06", "QB-Q0–Q2：standalone scaled QB", range(37, 42)),
    ("stage-07", "PAPER-SL：JSL waveform → QB + READ semantics", range(42, 53)),
    ("stage-08", "physical BVM→JSL12→QB closure", range(53, 54)),
    ("stage-09", "QB output boundary / JTL transport", range(54, 61)),
]


# Human-facing experiment narratives.  These are deliberately kept separate
# from the machine-derived raw/plot discovery below: the report remains the
# scientific authority, while this catalog supplies the short answer to
# “what was tested / what was learned / what is the boundary?” for both
# generated indexes.  Keys are Exploration directory basenames.
EXPERIMENT_NARRATIVES: dict[str, dict[str, str]] = {
    "bvm-internal-readout-20260819": {
        "title_cn": "Canonical BVM：storage/readout source baseline",
        "what_done": "对 canonical BVM 做 write/read 与 READ=0 对照，检查 JM1/JM2、JS1/JS2、SL、N6 及 read timing。",
        "result_summary": "read1/read0 的 storage sign 与 SL/N6 输出保持稳定区分；read1 有强 R-loop/JS activity，read0 主要是 READ-edge response，因此该结果被用作 source baseline。",
        "conclusion_boundary": "这是 BVM source/read baseline，不是 receiver switching 或 SFQ-delivery 结果。",
    },
    "bvm-sfq-receiver-r0-20260819": {
        "title_cn": "R0：SL-route trigger discrimination",
        "what_done": "在 canonical SL 后接最小外部 JJ trigger，比较 logical1/read1、logical0/read0 和两个 READ=0 controls。",
        "result_summary": "R0 PARTIAL：R0-A threshold discrimination PASS；read1 与 read0/controls 分离且 source/storage guard 保持，但 read1 B_TRIG excursion 未满足完整 2π transition。",
        "conclusion_boundary": "不能称 complete trigger switching、exactly-one、self-quench 或 SFQ delivery。",
    },
    "bvm-sfq-receiver-r0b-20260819": {
        "title_cn": "R0b：complete trigger closure",
        "what_done": "保持 SL route，使用 B_TRIG AREA=.50、bias=+15 µA，执行 read1/read0/两个 READ=0 matched cases。",
        "result_summary": "R0b PASS：read1 出现约 4.997-turn continuous complete segment；read0 最大约 0.185 turn，controls 无完整 transition，source/storage guard 保持。",
        "conclusion_boundary": "这是 multi-turn local trigger closure，不是 exactly-one SFQ、self-quench 或 downstream delivery。",
    },
    "bvm-sfq-receiver-r1-oneshot-20260819": {
        "title_cn": "R1：parallel feedback one-shot attempt",
        "what_done": "在 B_TRIG 后加入 parallel LQ–RQ feedback/transfer branch，尝试把 trigger running 压缩为 one-shot output。",
        "result_summary": "R1 FAIL：强 feedback branch 明显加载并压制 B_TRIG，弱 branch 虽保留 trigger 却不能提供足够 transfer；该拓扑没有建立 read1 output event。",
        "conclusion_boundary": "只否定当前 parallel LQ–RQ instance，不否定所有 one-shot 或 transfer family。",
    },
    "bvm-sfq-receiver-r1a-transfer-20260819": {
        "title_cn": "R1a：series pickup passive transfer",
        "what_done": "用 SL→R_IN→L_TX→B_TRIG 的 series pickup，并以 L_TX–L_SEC mutual coupling 接 passive secondary/load。",
        "result_summary": "R1a PASS：read1 B_TRIG 约 3.944-turn complete，read0 约 0.185-turn；secondary read1 约 66.77 µV/5.56 µA，约为 read0 的 4.9 倍，controls inactive。",
        "conclusion_boundary": "建立的是 passive state-dependent extraction，不是 output-JJ switching、one-shot 或 SFQ delivery。",
    },
    "bvm-sfq-receiver-r1b-output-jj-20260819": {
        "title_cn": "R1b：common-mode secondary → B_OUT",
        "what_done": "把 R1a secondary 接到最小 output JJ，并检查 secondary 是否在 B_OUT 两端形成有效 differential drive。",
        "result_summary": "FAIL 的根因是 common-mode：V(N_OUT) 跟随 V(N_SEC)，V(B_OUT) 近 numerical zero，I(B_OUT) 与 phase 基本恒定；没有实际 differential activation。",
        "conclusion_boundary": "这是接口/KCL 失配，不是通过调 AREA、bias 或 damping 可以诊断的 output-margin 结果。",
    },
    "bvm-sfq-receiver-r1b-area008-20260821": {
        "title_cn": "R1b-area=.08：output-JJ barrier diagnostic",
        "what_done": "保持 R1b differential topology，只将 B_OUT AREA 从 .10 改为 .08，比较 read1/read0/controls。",
        "result_summary": "AREA=.08 未提高 activation：read1 最大 B_OUT segment 约 0.020 turn，read0/controls 无完整 event；read1 signal 仍存在但远离 switching。",
        "conclusion_boundary": "AREA 同时改变 Ic、C、RN、R0，因此只能说明该 output-class point 不足，不能归因于纯 Ic reduction。",
    },
    "bvm-sfq-receiver-r1b-differential-output-20260821": {
        "title_cn": "R1b：differential secondary-driven output",
        "what_done": "修正 secondary→B_OUT 的 differential KCL，使 induced current 直接进入 B_OUT 对地支路，并保留 R1a secondary/load。",
        "result_summary": "因果 transfer 成立：read1 B_OUT 有 state-dependent transient，但最大连续段仅约 0.022 turn；read0/controls 无 event，B_TRIG/source guards 保持。",
        "conclusion_boundary": "证明 signal existence，不证明 output-JJ activation；随后 AREA/bias 诊断均仍是 bounded sub-turn。",
    },
    "bvm-sfq-receiver-r1c-bias-margin-20260821": {
        "title_cn": "R1c：B_OUT bias-margin diagnostic",
        "what_done": "冻结 AREA=.10、transformer、secondary、damping，只测试 B_OUT bias 6/7/8/9/10 µA。",
        "result_summary": "所有 bias 点都有 state-dependent read1 transient，但没有完整 B_OUT transition；read0/controls 无 event，因此 bias operating point 不是该 fixture 的主要解法。",
        "conclusion_boundary": "这是局部 bias bracket，未测试其他 topology，也没有 downstream SFQ/JTL 结论。",
    },
    "bvm-sfq-receiver-r2a-coupling-20260821": {
        "title_cn": "R2-A：mutual-coupling transfer diagnostic",
        "what_done": "冻结 R1b differential receiver，只比较 K=.6/.7/.8/.9/.95 对 secondary 与 B_OUT activation 的影响。",
        "result_summary": "增大 K 会增强 secondary，但 read1 B_OUT 仍停留在约 10^-2-turn 级，未形成 complete event；read0/controls 与 source guards 保持。",
        "conclusion_boundary": "否定当前 coupling matrix 的 activation closure，不否定全部 transformer/mutual family；动态 dwell/receiver load 仍未解决。",
    },
    "bvm-sfq-receiver-r2b-damping-20260821": {
        "title_cn": "R2-B：receiver damping diagnostic",
        "what_done": "冻结其他条件，只改变 output damping，观察 underdamped/overdamped 变化是否能释放 B_OUT phase slip。",
        "result_summary": "减弱 damping 只使 read1 最大段约 0.0261→0.0290 turn（约 10.9%），没有 complete event；read0/controls 和 BVM guards 保持。",
        "conclusion_boundary": "只说明当前 damping sweep 不是主瓶颈，不代表所有拓扑中的 damping 都无关。",
    },
    "bvm-sfq-receiver-r2c-directdrive-20260821": {
        "title_cn": "R2-C：fast direct-drive threshold",
        "what_done": "将实测 read1 narrow forward lobe 以 ideal direct current 注入 secondary，固定快脉冲形状，测试有限 amplitude matrix。",
        "result_summary": "没有 amplitude 点产生完整 B_OUT event；约 78% 快注入电流被 N_SEC 的 reactive/resistive shunts 分流，junction drive transfer 约 22.4%。",
        "conclusion_boundary": "这是 fast-transient fixture 的 duration/load limitation，不是静态 Ic threshold 的普适结论。",
    },
    "bvm-sfq-receiver-r2d-duration-20260821": {
        "title_cn": "R2-D：direct-drive duration bracket",
        "what_done": "固定 3.5 µA direct-drive amplitude，只增加 pulse FWHM/有效持续时间。",
        "result_summary": "响应随 duration 非线性增大（最大段约 .0096→.0835 turn），但矩阵内仍无完整 event；20 ps 点已接近 96% Ic 的 quasi-static ceiling。",
        "conclusion_boundary": "在该 amplitude 下 duration alone 不够；下一限制转向 amplitude，不能推出所有更长脉冲都无效。",
    },
    "bvm-sfq-receiver-r2e-ampthreshold-20260821": {
        "title_cn": "R2-E：quasi-static amplitude threshold",
        "what_done": "固定 20 ps pulse width/shape，测试 4.0/4.5/5.0 µA direct-drive amplitude。",
        "result_summary": "所有点都接近 Ic 但没有完整 B_OUT segment，正式结论为 bounded matrix 内 NO_THRESHOLD；没有建立 switching threshold。",
        "conclusion_boundary": "不能把 I≈Ic 或 voltage peak 当 event，也不涉及 retrap、JTL 或 physical transformer。",
    },
    "bvm-sfq-receiver-r2f-dwell-20260821": {
        "title_cn": "R2-F：near-critical dwell closure",
        "what_done": "固定 4.5 µA direct-drive，增加 0/5/10/20 ps flat-top hold，检查 near-critical creep 是否完成 phase slip。",
        "result_summary": "20 ps hold 首次产生一个约 1.0039-turn、phase/area 一致且 retrap 的 local B_OUT event；0–10 ps 为 near-miss。",
        "conclusion_boundary": "这是理想 direct-drive output-stage requirement，不是 BVM→receiver 或 downstream SFQ delivery。",
    },
    "bvm-sfq-receiver-r2g-twopulse-20260821": {
        "title_cn": "R2-G：two-pulse retrigger/rearm",
        "what_done": "在 R2-F h20 点输入两个间隔约 60 ps 的相同 4.5 µA/20 ps-hold pulse，直接检查两次 local slip 和中间 retrap。",
        "result_summary": "两个 pulse 各产生 exactly one local complete slip，间隔期间 retrap/rearm 清晰，无 multifire/free-running；建立了 direct-drive 的 2-pulse single-slip primitive。",
        "conclusion_boundary": "只证明理想 direct-drive output stage 的局部可重复性，不证明真实 transformer、BVM、JTL 或 T1。",
    },
    "bvm-sfq-receiver-r3a-onset-extraction-20260822": {
        "title_cn": "R3-A：B_TRIG onset extractor",
        "what_done": "用 1 fF C_ON 将 B_TRIG onset 变成 fast differentiated spike，再驱动 B_OUT/hold branch。",
        "result_summary": "read1 的 C_ON current 可达约 2.24 µA，但 B_OUT causal-window peak 仅约 8.06 µA、相对 bias 只有约 1.06 µA；四 cases 均无 complete event。",
        "conclusion_boundary": "只否定该 fast capacitive extractor instance；失败位于 transient→sustained drive，不否定所有 B_TRIG extraction。",
    },
    "bvm-sfq-receiver-r4a-weak-mutual-capture-20260822": {
        "title_cn": "R4-A：weak-mutual passive flux capture",
        "what_done": "用 B_TRIG→weak mutual→100 pH capture loop/J_SET，测试 read1 是否留下 persistent fluxoid state。",
        "result_summary": "read1 loop 最大 circulating current 约 4.874 µA，仅约 half-quantum boundary 的一小部分，最终回到 n=0；read0/controls 更小，J_SET 无 complete slip。",
        "conclusion_boundary": "降级的是该 passive weak-mutual single point，不是整个 mutual-coupling family；capture 需要更强 transfer 或 bias-assisted quantization。",
    },
    "bvm-sfq-receiver-r5a-biased-quantizer-20260822": {
        "title_cn": "R5-A：reduced biased quantizer",
        "what_done": "给单 JJ quantizer 加独立 bias，在实际 B_TRIG mutual drive 下检查 read1 是否跨过 nonlinear saddle 并 escape。",
        "result_summary": "read1 产生 large bounded plasma oscillation并跨过 analytic reverse-critical displacement，但没有 complete phase slip；read0/controls clean。",
        "conclusion_boundary": "说明 amplitude 已足以产生强 nonlinear activity，但缺少不可逆性/不对称 escape；不能称 quantization。",
    },
    "bvm-sfq-receiver-r5b-loadline-20260822": {
        "title_cn": "R5-B：minimal SET shunt/load-line test",
        "what_done": "先保留并诊断 wiring correction，再把最小 shunt 放到 functionally active 的 SET boundary，测试其是否促成 escape。",
        "result_summary": "active shunt 实际只是额外 damping/current diversion，使 R5-A oscillation 收缩、没有 complete event；结论是 paper-QB 的 bias placement 不能用 SET 并联 shunt 替代。",
        "conclusion_boundary": "否定该 minimal direct-shunt hypothesis，不等于完整 paper QB 已被实验闭合。",
    },
    "bvm-sfq-receiver-r5c-saddle-selectivity-20260822": {
        "title_cn": "R5-C：correct-saddle selectivity",
        "what_done": "使用完整 nonlinear loop equation 选 bias，使 read1 预计跨真实 saddle，再用四 matched cases 检查 local phase escape。",
        "result_summary": "read1 确实跨过正确 static saddle，但仍为 bounded multi-lobe oscillation、没有 complete event；同时产生明显 read1 back-action 和约 −4-turn JS1/JS2 post shift。",
        "conclusion_boundary": "关闭 reduced quantizer 的 bias/K/L point tuning；不能把 saddle crossing 当作 event。",
    },
    "bvm-sfq-receiver-native-qb-20260822": {
        "title_cn": "Native paper-QB：direct SL compatibility",
        "what_done": "用 canonical SL galvanic 直接驱动 frozen native paper-QB，记录 BJs/BJL1/BJL2 与 BVM source/storage guards。",
        "result_summary": "read1 在 QB core 中有明显 state-selective nonlinear activity，但 JS1/JS2 post-state 各约 −3 turns，source/storage guard 失败；BJL2 无 complete event。",
        "conclusion_boundary": "direct SL native-QB point 是 back-action failure；不能因 activity 强就称 local pass。",
    },
    "bvm-sfq-receiver-r6a-native-qb-isolation-20260822": {
        "title_cn": "R6-A：isolated native-QB transfer",
        "what_done": "将 canonical SL 改接 weak mutual transformer isolation，再进入冻结 native paper-QB，保持 QB 内部 topology/参数。",
        "result_summary": "相对 direct SL，canonical source/storage guard 恢复，read1 QB activity 仍明显高于 read0/control，说明 isolation feasibility PASS；BJL2 仍仅约 0.0016 turn，无 local pass。",
        "conclusion_boundary": "这是 isolation-preserved state-selective activity，不是 BJL2 quantization。",
    },
    "bvm-sfq-receiver-r6b-native-qb-ratio-20260822": {
        "title_cn": "R6-B：secondary winding-ratio transfer",
        "what_done": "冻结 native QB，只把 R6-A 的 secondary 改为 L_PRI=.20 pH、L_SEC=1.0 pH、K=.707 单点，检查 drive gain 与 reflected loading。",
        "result_summary": "read1 secondary/Lin current 和 BJs/BJL1 activity 增强，source isolation 保持；但 BJL2 最大段几乎不变（约 .0015846→.0015880 turn），没有 output quantization。",
        "conclusion_boundary": "关闭 transformer 参数优化；瓶颈更像 front-stage absorption/loop load-line，而非单纯 secondary amplitude。",
    },
    "bvm-sfq-receiver-r7a-l1-routing-20260823": {
        "title_cn": "R7-A：native-QB L1 routing",
        "what_done": "回到 R6-B baseline，只将 native QB L1 从 3.91 pH 降到 2.50 pH，比较 front-stage→L2/BJL2 routing。",
        "result_summary": "G_L2 约提升 25.9%、G_BJL2 约提升 26.2%，read0 selectivity/source guard 保持；但 BJL2 最大段仍约 .001886 turn，且 settled BJL2 current 反而下降。",
        "conclusion_boundary": "建立 routing gain，不是 threshold gain、complete event 或 SFQ delivery。",
    },
    "bvm-sfq-receiver-r8-bjl2-area070-20260823": {
        "title_cn": "R8：BJL2 output-class adjustment",
        "what_done": "保持 R7-A，只将 BJL2 AREA 1.89→.70，实际同时改变 Ic/C/RN/R0 与 damping/load-line。",
        "result_summary": "read1 phase/area activity 约增加 36%，但仍在 10^-3-turn 区间；BJL2 current excursion下降，read0 相对增幅更大，没有 threshold-like jump 或 complete event。",
        "conclusion_boundary": "停止 BJL2 AREA sweep；不能把该点解释成纯 Ic reduction failure。",
    },
    "bvm-sfq-receiver-r9a-l2-routing-20260823": {
        "title_cn": "R9-A：native-QB L2 routing",
        "what_done": "恢复 R7-A output class，将 L2 3.91→2.50 pH，测 node3→node4/BJL2 routing 与 static bias redistribution。",
        "result_summary": "L2/BJL2 control-subtracted routing 再次提高（read0 也近似 co-amplify），source guard 保持；BJL2 仍约 2×10^-3 turn，未进入 quantization。",
        "conclusion_boundary": "关闭 passive L1/L2 tuning 分支，不能由 routing gain 推断 nonlinear amplification。",
    },
    "bvm-sfq-receiver-r10a-local-bjl2-bias-20260823": {
        "title_cn": "R10-A：local BJL2 bias routing",
        "what_done": "在 node4 加有限阻抗、独立 bias feed，不把它直接作为 BJL2 parallel damping shunt。",
        "result_summary": "local bias 造成四 case 级别的 8–14-turn activity、free-running 和 source disturbance，未形成 bounded one-shot；主 verdict 为 BACK_ACTION_OR_NONSELECTIVE_FAILURE。",
        "conclusion_boundary": "只关闭当前 local-feed point，不否定所有 bias-routing，但不再继续该 sweep。",
    },
    "bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823": {
        "title_cn": "R11-A：canonical BVM → standard JTL direct",
        "what_done": "先用标准 SFQ positive control 验证两-cell JTL，再将 canonical BVM SL galvanic 接到同一冻结 JTL chain。",
        "result_summary": "positive control 通过；canonical read1 对第一颗 JTL JJ 最大单调 excursion 仅约 .151 turn，未触发第一 stage，主 verdict NO_JTL_TRIGGER；read0/controls 无 event。",
        "conclusion_boundary": "仅否定当前 direct-galvanic BVM→standard JTL point，不否定有 conditioner 的 JTL route。",
    },
    "bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823": {
        "title_cn": "R12-A：historical DCSFQ_BVM re-audit",
        "what_done": "先用 0/68.4/300 µA controlled bump 重审 frozen DCSFQ_BVM，再以 canonical BVM SL 接 converter 与两-cell JTL。",
        "result_summary": "Phase A 证明 300 µA controlled point 可使 B3 产生约 1.03-turn bounded local event，而 68.4 µA 无 event；canonical read1 B3 仅约 .0365 turn，未量化也未驱动 JTL。",
        "conclusion_boundary": "converter mechanism 本身成立，但 canonical source 到 backend 的 amplitude/time-scale 不匹配；不恢复旧参数 sweep。",
    },
    "bvm-sfq-receiver-r13a-temporal-conditioning-20260823": {
        "title_cn": "R13-A：temporal conditioning requirements",
        "what_done": "把 R12 actual input 做 raw replay，并分别测试原始、单极性整流、20 ps hold、整流+hold 四种 ideal transform。",
        "result_summary": "四种 replay 都未产生 selective DCSFQ B3 exactly-one；最终 verdict TEMPORAL_CONDITIONING_INSUFFICIENT，说明无 amplitude gain 的理想 conditioning 仍不够。",
        "conclusion_boundary": "这是 requirements/counterfactual 结果，不是 physical conditioner implementation，也不支持参数 sweep。",
    },
    "bvm-sfq-receiver-r14a-dcsfq-detector-20260823": {
        "title_cn": "R14-A：passive interstage scale precheck",
        "what_done": "只读比较 R1a passive secondary 的 5.56 µA 量级与 frozen DCSFQ 的 68.4/110/300 µA reference，并审计 R_SEC_LOAD termination。",
        "result_summary": "PRECHECK_NO_GO：optimistic loaded DCSFQ input 约 9.77 µA，3 ps sanity 也约 19.1 µA，远低于已知 68.4 µA no-event 与 300 µA positive point；缺失功能是 active/regenerative interstage energy transfer。",
        "conclusion_boundary": "没有运行 JoSIM；不把 passive transformer/termination scale 解释成 active gain。",
    },
    "bvm-sfq-receiver-r15a-afq3-20260823": {
        "title_cn": "R15-A：AFQ-3 active interstage precheck",
        "what_done": "对 AFQ-3 nominal three-winding mutual topology 做 netlist closure、jjmit 参数、稳定性、discrimination 与 output-scale precheck。",
        "result_summary": "PRECHECK_NO_GO：L_Q/L_F/L_CTL mutual matrix determinant 为 −.62、最小 eigenvalue 为负，拓扑 constitutive matrix 无效；没有运行可解释的 physics point。",
        "conclusion_boundary": "只否定该 invalid magnetic formulation，不是 active-stage physics failure，也没有 DCSFQ/JTL 结果。",
    },
    "bvm-sfq-receiver-r15b-magnetic-correction-20260823": {
        "title_cn": "R15-B：split-winding active interstage",
        "what_done": "用 two-core/split-winding 修正 mutual matrix，保留 B_DET 并加入 J_SET/J_Q/J_OUT active-state-compression path。",
        "result_summary": "B_DET read1 仍约 3.9-turn 强 activity，但 J_SET/J_Q/J_OUT 四 cases 几乎相同，DCSFQ I(L1) 仅约 .511 µA；主 verdict ACTIVE_STAGE_NO_TRIGGER，另有 bounded extra back-action。",
        "conclusion_boundary": "问题定位到 detector state 未进入 J_SET 判别变量；不说明 active gain family 普遍失败。",
    },
    "bvm-sfq-receiver-r15c-jset-causal-20260823": {
        "title_cn": "R15-C：finite-impedance J_SET causal fixture",
        "what_done": "移除 ideal 5.6 µA current clamp，使用有限阻抗 bias return，让 B_DET mutual waveform 可改变 J_SET branch current。",
        "result_summary": "CAUSAL_NEAR_THRESHOLD：read1 I(B_SET) 约 2.10–9.13 µA、read0 约 4.89–6.28 µA，read1 最大 J_SET segment 约 .2244 turn；因果 modulation 成立但未完成 event。",
        "conclusion_boundary": "建立 detector→J_SET causal transfer，不建立 one-shot；没有接 J_Q/J_OUT/DCSFQ。",
    },
    "bvm-sfq-receiver-r15d-jq-compressor-20260823": {
        "title_cn": "R15-D：J_SET → J_Q refractory compressor",
        "what_done": "保留 R15-C J_SET，增加 split node、独立 J_Q bias、L_Q 和 R_Q refractory branch，检查 state compression。",
        "result_summary": "JQ_CAUSAL_NEAR_THRESHOLD：read1 selective J_SET/J_Q activity 与 L_Q transient depletion/recovery 可见，但 J_Q 没有完整 one-shot event；source guard 仍是 bounded extra back-action。",
        "conclusion_boundary": "不能把 depletion/recovery 单独称 refractory one-shot；暂停 R15-E 设计。",
    },
    "qb-q0-standalone-current-quantized-event-20260824": {
        "title_cn": "QB-Q0：scaled QB standalone 量化窗口",
        "what_done": "用理想 current pulse 0/45/68.4/90 µA 驱动 frozen scaled QB，并以 paper-original QB 做历史参数对照。",
        "result_summary": "scaled：0=ZERO_EVENT，45=NO_COMPLETE_EVENT，68.4=EXACTLY_ONE（每 pulse 约 1.096 turn），90=MULTI_EVENT（约 2.006 turn）；paper 68.4/90 均无完整 BJL2 event。",
        "conclusion_boundary": "68.4 µA 只是 ideal standalone reference，不是 canonical BVM threshold 或 physical receiver requirement。",
    },
    "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824": {
        "title_cn": "QB-Q1：physical BVM → frozen scaled QB",
        "what_done": "把 canonical BVM 直接接入 Q0 frozen scaled QB，运行 logical1/read、logical0/read 和两个 READ=0 controls。",
        "result_summary": "read1 QB activity 强于 read0/control，但 direct coupling 造成 JS1/JS2 约 −3-turn post drift，主 verdict QB_SOURCE_BACKACTION_FAILURE；BJL2 仍 subthreshold。",
        "conclusion_boundary": "直接 physical coupling 失败，不能用 source-isolated replay 替代真实 BVM back-action。",
    },
    "qb-q2a-source-decoupled-waveform-replay-20260824": {
        "title_cn": "QB-Q2A：source-decoupled waveform replay",
        "what_done": "冻结 scaled QB，用 Q0 positive control、Q1 loaded waveform 和 canonical no-receiver read1/read0 waveform 做 ideal replay。",
        "result_summary": "Q0 68.4 µA replay exactly-one；canonical no-receiver read1 BJL2 约 .178 turn、read0 约 .031 turn，仍未量化，结论 QB_DYNAMIC_WINDOW_MISMATCH。",
        "conclusion_boundary": "完美 source isolation alone 也不够；不是 source impedance 唯一瓶颈。",
    },
    "qb-q2b-central-bias-bracketing-20260824": {
        "title_cn": "QB-Q2B：central-bias bracket",
        "what_done": "冻结 canonical source-isolated replay，只测试 central IBIAS=30/35/40 µA 对 BJs→BJL1/BJL2 的影响。",
        "result_summary": "read1 BJL1 约 +.321/.339/−.415 turn，logical0 约 .059 turn；所有点无 complete BJL1/BJL2 event，controls bounded，BIAS_BRACKET_NO_BJL1_EVENT。",
        "conclusion_boundary": "停止 central-bias branch；不把 phase range 或 I/Ic 当作 event。",
    },
    "qb-q2c-uniform-junction-scale-20260824": {
        "title_cn": "QB-Q2C：uniform junction-scale bracket",
        "what_done": "在 canonical source-isolated replay 下统一缩放 BJs/BJL1/BJL2 AREA 与 IBIAS，测试 s=.85/.70/.55。",
        "result_summary": "三个 scale 都没有建立 selective BJL1/BJL2 event，最终 UNIFORM_SCALE_NO_OUTPUT_EVENT；停止整体缩放，转向 paper-JSL load waveform。",
        "conclusion_boundary": "不能从 uniform scaling 推断某一颗 JJ ratio 是唯一原因。",
    },
    "paper-sl-l0-20260824": {
        "title_cn": "PAPER-SL-L0：12×320 µA JSL external load",
        "what_done": "在 canonical SL path 加入 paper Figure 4/section 2.5 语义下的 12 个 AREA=3.2 non-switching JSL series external load。",
        "result_summary": "12 个 JSL 全部 non-switching；logical1 current/area/duration waveform 明显改变，logical0 仍很小，判定 PAPER_JSL_LOAD_VALID（external-series-load realization）。",
        "conclusion_boundary": "只验证 paper-shaped SL load waveform，不接 QB，也不说明 JSL load 一定改善量化。",
    },
    "bvm-jsl-read-width-to-qb-sfq-v1-20260824": {
        "title_cn": "历史 JSL width bracket：12 ps W* baseline",
        "what_done": "在旧 lineage 中比较 canonical BVM/12×JSL 的 READ plateau，并把 12 ps source waveform replay 到 frozen scaled QB。",
        "result_summary": "旧报告支持 12 ps source-side margin improvement，但 Phase C 仍为 subthreshold；其 logical0 source provenance 不是当前 canonical WL+SE logical0，因此仅作历史/同-read1 reference。",
        "conclusion_boundary": "不得用该旧 logical0 lineage 支撑新的 canonical logical0 discrimination claim；本轮新的 READ semantics audit 已提供修正 12 ps logical0 与 13/14/15 ps bracket。",
    },
    "paper-sl-q1-20260824": {
        "title_cn": "PAPER-SL-Q1：paper-JSL waveform → frozen scaled QB",
        "what_done": "将 PAPER-SL-L0 logical1/logical0/controls 的实际 JSL current trajectory 原样 ideal replay 到 frozen scaled QB。",
        "result_summary": "read1 BJL1 约 .830、BJL2 约 .893 turn，read0 约 .019/.0066，controls≈0；read1 明显 near-threshold 但无 complete event，PAPER_JSL_QB_SUBTHRESHOLD。",
        "conclusion_boundary": "不能改写为 one-shot；Q0 68.4 µA 只作 positive control。",
    },
    "paper-sl-q2-20260824": {
        "title_cn": "PAPER-SL-Q2：paper-JSL local bias bracket",
        "what_done": "保持 PAPER-SL-Q1 waveform byte-identical，只比较 37.5/40 µA central QB bias。",
        "result_summary": "两点均保持 read1>read0、bounded 且无 complete BJL1/BJL2 event；40 µA 将 BJL2 推到约 .944 turn，但仍未闭合。",
        "conclusion_boundary": "停止 bias-only bracket；不把 .944 turn 当 event，也不连接 physical BVM。",
    },
    "paper-sl-q3-pre-20260824": {
        "title_cn": "PAPER-SL-Q3-PRE：BJs→BJL1 routing audit",
        "what_done": "只读对齐 Q0 68.4 µA、PAPER-SL-Q1 35 µA、Q2 40 µA 的 BJs/BJL1/BJL2 phase、current/KCL 和 timing。",
        "result_summary": "BJs→BJL1 更像 waveform/routing/timing-limited：Q0 的 local branch signed transfer 比 Q1/Q2 更有利；phase/area 与 KCL 均闭合。",
        "conclusion_boundary": "这是 mechanism inference，不是 BJL1 threshold 已被排除；未运行新 circuit。",
    },
    "q3-l1-routing-closure-20260824": {
        "title_cn": "PAPER-SL-Q3-PRE：L1 routing point selection",
        "what_done": "基于 Q3-PRE routing audit 选择唯一 L1=4.50 pH point，并登记其与 Q2/Q4/Q5 的 factorial 关系。",
        "result_summary": "这是 analysis-only provenance checkpoint；结论是 L1 routing knob 值得 single-point execution，独立目录不产生新 waveform。",
        "conclusion_boundary": "正式物理结果归属于下一条 paper-sl-q3-l1-routing-closure execution。",
    },
    "paper-sl-q3-l1-routing-closure-20260824": {
        "title_cn": "PAPER-SL-Q3：L1=4.50 pH routing closure",
        "what_done": "以 Q2 accepted 40 µA replay 为 baseline，只把 native QB L1 3.91→4.50 pH，测 node2 routing 与 BJL1/BJL2。",
        "result_summary": "F_local .218660→.224945、G_local .515185→.526585；BJL1 .815414→.821070，BJL2 .944323→.950537，read0/control zero-event，结论为 routing gain 但仍 subthreshold。",
        "conclusion_boundary": "L1 是 causal routing knob，不是 complete-event 或 nonlinear-gain closure；不连接 physical BVM/JSL/QB。",
    },
    "paper-sl-q4-l1-l2-placement-20260824": {
        "title_cn": "PAPER-SL-Q4：L2=4.50 pH placement comparator",
        "what_done": "从 Q2 直接改 L2 3.91→4.50 pH，与 Q3 保持相同 L1+L2 总电感，区分 proximal 与 downstream placement effect。",
        "result_summary": "Q4 的 BJL2 response 可增强，但 BJL1 forward phase 与 node2 local routing 明显退化；BJL2 最大连续段约 .9654 turn，仍无 event，判定方向性 placement effect。",
        "conclusion_boundary": "不能要求 BJL1 complete slip 才解释 BJL2 activity；仍无 isolated QB event。",
    },
    "paper-sl-q5-l1-l2-factorial-20260824": {
        "title_cn": "PAPER-SL-Q5：L1×L2 factorial completion",
        "what_done": "完成 Q2/Q3/Q4/Q5=(3.91,3.91)/(4.50,3.91)/(3.91,4.50)/(4.50,4.50) 的 2×2 factorial comparison。",
        "result_summary": "Q5 保留 Q4 downstream BJL2 gain并部分恢复 Q3 L1 routing，但 BJL2 最大段约 .9682 turn；interaction≈−.00344，无 complete event。",
        "conclusion_boundary": "停止 passive L1/L2 tuning；未建立正向 nonlinear BJL2 interaction。",
    },
    "paper-sl-q6-qb-jtl-compatibility-20260824": {
        "title_cn": "PAPER-SL-Q6：Q5 → standard JTL",
        "what_done": "将 frozen Q5 near-event output 接入已验证的 two-cell standard JTL，和 Q5 standalone 做 matched comparison。",
        "result_summary": "JTL loading 使 Q5 trajectory collapse，四颗 JTL JJ 均无完整 propagated event，主 verdict NO_JTL_TRIGGER。",
        "conclusion_boundary": "不能把 coupled failure 归因于 isolated QB 本身，也不能称 JTL voltage peak 为 event。",
    },
    "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824": {
        "title_cn": "BVM READ semantics audit + JSL width bracket",
        "what_done": "审计 logical1/logical0/READ=0 的正式语义，修正 canonical logical0，并把 12/13/14/15 ps 的实际 12-JSL source current 原样 replay 到 frozen scaled QB。",
        "result_summary": "READ audit PASS；修正后的 12 ps logical0 为 zero-event；ideal replay 首个 1/0/0 candidate 在 13 ps（BJL2≈1.016 turn），14/15 ps为已执行的 post-candidate observations。",
        "conclusion_boundary": "这只是 source waveform→frozen QB 的 ideal replay candidate，不是 physical BVM→12JSL→QB，也不是 JTL/T1 delivery；旧 PAPER-SL logical0 lineage 的 canonical read0 claims 被降级。",
    },
    "qb-load-boundary-matrix-20260824": {
        "title_cn": "QB load-boundary matrix：Q0 output boundary",
        "what_done": "保持同一 Q0 true-event source，比较 OPEN、10Ω、JTL-only、10Ω||JTL 四种 output boundary。",
        "result_summary": "OPEN≈3 events；10Ω exactly-one；JTL-only 与 10Ω||JTL 无 event；矩阵支持 MIXED_DYNAMIC_LOADING，load 在 crossing 前/中/后都改变 current partition。",
        "conclusion_boundary": "不冻结普适等效阻抗；Q5 boundary 仅作 secondary comparator。",
    },
    "parallel-qb-jtl-interface-mechanism-20260824": {
        "title_cn": "M1–M5：QB→JTL interface mechanism matrix",
        "what_done": "并列比较 ideal replay、series R/L、standard/scaled JTL 和 Q0/Q5 source boundary 对 QB local event 与 JTL transport 的影响。",
        "result_summary": "Q0+10Ω 保留 exactly-one，M3 series-10Ω 保留 local event但 JTL subthreshold；M1/Q0 replay 与 M5 transport 需按 strict/local 与 settled-well 分层，M5 历史 exactly-one 解释废止。",
        "conclusion_boundary": "这是 interface mechanism matrix，不是一个可直接实现的 receiver，也不授权参数优化。",
    },
    "jtl-transport-gate-polarity-replay-20260824": {
        "title_cn": "JTL polarity replay：original vs reverse",
        "what_done": "从 accepted Q0 pulse-5 提取完整 V(OUT,t)，原极性/反极性 ideal replay 到同一 standard two-cell JTL。",
        "result_summary": "原极性在 strict local vector 上只保证第一颗 JJ，但 full-window/pre-post 呈四级约一井响应；反极性无 strict local event、无 one-well transport。",
        "conclusion_boundary": "ideal replay 不是 physical QB→JTL 证据；strict local event 与 settled-well transport 必须分开。",
    },
    "jtl-transport-gate-v1-methodology-20260824": {
        "title_cn": "JTL transport methodology：strict vs settled-well",
        "what_done": "统一 R11 positive、M1 ideal replay、M5-PC、pulse5 original/reverse 的 phase/area、pre/post well、onset 和 transport vector 口径。",
        "result_summary": "建立 fixture-level 方法学 reconciliation：R11/M1/pulse5 original 呈 provisional +1-well transport signature，M5 是 two-well，reverse 非 transport。",
        "conclusion_boundary": "这是方法学整理，不是 global metric freeze，也不改变 physical BVM/JTL compatibility。",
    },
    "jtl-transport-gate-v1-numerical-freeze-20260824": {
        "title_cn": "JTL transport Gate V1：timestep ladder",
        "what_done": "对 R11、pulse5 original、pulse5 reverse 做 0.025/0.0125/0.00625 ps ladder 与预注册 window robustness。",
        "result_summary": "三组 timestep classification 稳定；R11/reverse window checks 通过，但 pulse5 original post-window robustness 未完全通过，最终 STRICT_REPLAY_INCONCLUSIVE。",
        "conclusion_boundary": "不是 timestep 数值不稳定，而是 registered robustness Gate 未闭合；不改变 JTL 参数。",
    },
    "jtl-transport-gate-v1-numerical-freeze-20260824-rerun": {
        "title_cn": "JTL transport Gate V1：rerun evidence package",
        "what_done": "对同一 numerical-freeze raw 做 successor/rerun 复核，保留完整 timestep、phase/area、pre/post 和 window-grid evidence。",
        "result_summary": "R11 与 pulse5 original 的 +1-well settled behavior 跨 timestep 保持，reverse 保持 non-transport；original robustness 条件仍未全通过，结论仍 INCONCLUSIVE。",
        "conclusion_boundary": "rerun 只加强 provenance/数值稳定性，不升级 Gate 为 PASS。",
    },
    "qb-to-jtl-load-backaction-causal-audit-v1-20260824": {
        "title_cn": "QB→JTL load back-action causal audit",
        "what_done": "用 Q0+10Ω、OPEN、JTL-only、10Ω||JTL、M3 series-10Ω→JTL 的既有 raw，按 pre-crossing/crossing/retrap 三个时间窗审计 node4 KCL 与 current partition。",
        "result_summary": "判定 MIXED_DYNAMIC_LOADING：direct/parallel JTL 在 barrier crossing 前已改 settled load-line，crossing 中继续分流；M3 保留 local BJL2 event但仍不能驱动 JTL。",
        "conclusion_boundary": "不能把负载作用压缩成单一静态阻抗，也不能把 M3 local event 称 downstream SFQ delivery。",
    },
    "physical-bvm-jsl12-qb-sfq-closure-v1-20260824": {
        "title_cn": "Physical BVM→12×JSL→scaled QB：SFQ closure",
        "what_done": "把 canonical BVM SL 通过 12 个 AREA=3.2 的串联 JSL 直接接到 frozen scaled QB，运行 13/14 ps 与 logical1/logical0/两个 READ=0 controls，并与已有 ideal replay 对比。",
        "result_summary": "PHYSICAL_BACKACTION_PREVENTS_CLOSURE：13/14 ps physical read1 的 BJL2 最大连续段仅约 −0.122 turn，read0/control 为零 complete event；I(L_SL) 未数量级塌缩，但 physical load-line 改变了 source voltage/current partition，ideal replay 的 1/0/0 candidate 未保留。",
        "conclusion_boundary": "不能称 physical BVM→QB selective one-SFQ closure，也没有 T1/JTL evidence；该结果把下一问题限定为 physical QB source matching/load-line，而不是继续 width sweep。",
    },
}


EXPERIMENT_STATUS_OVERRIDES = {
    "bvm-internal-readout-20260819": "ACCEPTED_CANONICAL_SOURCE",
    "bvm-sfq-receiver-r0-20260819": "R0_PARTIAL",
    "bvm-sfq-receiver-r0b-20260819": "R0B_PASS",
    "bvm-sfq-receiver-r1-oneshot-20260819": "R1_FAIL",
    "bvm-sfq-receiver-r1a-transfer-20260819": "R1A_PASS",
    "bvm-sfq-receiver-r1b-output-jj-20260819": "R1B_FAIL",
    "bvm-sfq-receiver-r1b-area008-20260821": "R1B_AREA008_FAIL",
    "bvm-sfq-receiver-r1b-differential-output-20260821": "R1B_FAIL",
    "bvm-sfq-receiver-r1c-bias-margin-20260821": "R1C_FAIL",
    "bvm-sfq-receiver-r2a-coupling-20260821": "R2A_FAIL_NO_COMPLETE_BOUT",
    "bvm-sfq-receiver-r2b-damping-20260821": "R2B_NO_COMPLETE_EVENT",
    "bvm-sfq-receiver-r2c-directdrive-20260821": "NO_THRESHOLD_BOUNDED_FAST_MATRIX",
    "bvm-sfq-receiver-r2d-duration-20260821": "NO_THRESHOLD_BOUNDED_DURATION_MATRIX",
    "bvm-sfq-receiver-r2e-ampthreshold-20260821": "NO_THRESHOLD_BOUNDED_MATRIX",
    "bvm-sfq-receiver-r2f-dwell-20260821": "DWELL_THRESHOLD_FOUND",
    "bvm-sfq-receiver-r2g-twopulse-20260821": "REPEATABLE_TWO_PULSE_SINGLE_SLIP",
    "bvm-sfq-receiver-r3a-onset-extraction-20260822": "NO_OUTPUT_EVENT",
    "bvm-sfq-receiver-r4a-weak-mutual-capture-20260822": "R4A_NO_PERSISTENT_READ1_STATE",
    "bvm-sfq-receiver-r5a-biased-quantizer-20260822": "R5A_NO_SET_EVENT",
    "bvm-sfq-receiver-r5b-loadline-20260822": "R5B_STILL_BOUNDED_OSCILLATION",
    "bvm-sfq-receiver-r5c-saddle-selectivity-20260822": "R5C_SADDLE_CROSSED_NO_COMPLETE_EVENT",
    "bvm-sfq-receiver-native-qb-20260822": "BACK_ACTION_FAILURE",
    "bvm-sfq-receiver-r6a-native-qb-isolation-20260822": "ISOLATION_PRESERVED_STATE_SELECTIVE_QB_ACTIVITY",
    "bvm-sfq-receiver-r6b-native-qb-ratio-20260822": "DRIVE_GAIN_WITH_ISOLATION_PRESERVED",
    "bvm-sfq-receiver-r7a-l1-routing-20260823": "ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED",
    "bvm-sfq-receiver-r8-bjl2-area070-20260823": "OUTPUT_CLASS_CHANGE_WITHOUT_MEANINGFUL_BJL2_GAIN",
    "bvm-sfq-receiver-r9a-l2-routing-20260823": "ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED",
    "bvm-sfq-receiver-r10a-local-bjl2-bias-20260823": "BACK_ACTION_OR_NONSELECTIVE_FAILURE",
    "bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823": "NO_JTL_TRIGGER",
    "bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823": "DCSFQ_BVM_NO_TRIGGER",
    "bvm-sfq-receiver-r13a-temporal-conditioning-20260823": "TEMPORAL_CONDITIONING_INSUFFICIENT",
    "bvm-sfq-receiver-r14a-dcsfq-detector-20260823": "PRECHECK_NO_GO",
    "bvm-sfq-receiver-r15a-afq3-20260823": "PRECHECK_NO_GO",
    "bvm-sfq-receiver-r15b-magnetic-correction-20260823": "ACTIVE_STAGE_NO_TRIGGER",
    "bvm-sfq-receiver-r15c-jset-causal-20260823": "CAUSAL_NEAR_THRESHOLD",
    "bvm-sfq-receiver-r15d-jq-compressor-20260823": "JQ_CAUSAL_NEAR_THRESHOLD",
    "qb-q0-standalone-current-quantized-event-20260824": "ACCEPTED_STANDALONE_REFERENCE",
    "qb-q1-canonical-bvm-scaled-qb-compatibility-20260824": "QB_SOURCE_BACKACTION_FAILURE",
    "qb-q2a-source-decoupled-waveform-replay-20260824": "QB_DYNAMIC_WINDOW_MISMATCH",
    "qb-q2b-central-bias-bracketing-20260824": "BIAS_BRACKET_NO_BJL1_EVENT",
    "qb-q2c-uniform-junction-scale-20260824": "UNIFORM_SCALE_NO_OUTPUT_EVENT",
    "paper-sl-l0-20260824": "PAPER_JSL_LOAD_VALID",
    "bvm-jsl-read-width-to-qb-sfq-v1-20260824": "WIDTH_IMPROVES_QB_MARGIN_BUT_SUBTHRESHOLD",
    "paper-sl-q1-20260824": "PAPER_JSL_QB_SUBTHRESHOLD",
    "paper-sl-q2-20260824": "BIAS_BRANCH_SUBTHRESHOLD",
    "paper-sl-q3-pre-20260824": "Q3_PRE_ROUTING_MECHANISM_INFERENCE",
    "q3-l1-routing-closure-20260824": "Q3_PRE_SINGLE_POINT_SELECTED",
    "paper-sl-q3-l1-routing-closure-20260824": "ROUTING_GAIN_WITH_BJL1_SUBTHRESHOLD",
    "paper-sl-q4-l1-l2-placement-20260824": "Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT",
    "paper-sl-q5-l1-l2-factorial-20260824": "Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT",
    "paper-sl-q6-qb-jtl-compatibility-20260824": "NO_JTL_TRIGGER",
    "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824": "IDEAL_REPLAY_SELECTIVE_ONE_SFQ_CANDIDATE",
    "qb-load-boundary-matrix-20260824": "MIXED_DYNAMIC_LOADING",
    "parallel-qb-jtl-interface-mechanism-20260824": "BOUNDED_INTERFACE_MATRIX",
    "jtl-transport-gate-polarity-replay-20260824": "POLARITY_REPLAY_RECONCILED",
    "jtl-transport-gate-v1-methodology-20260824": "JTL_TRANSPORT_GATE_V1_RECONCILED",
    "jtl-transport-gate-v1-numerical-freeze-20260824": "JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE",
    "jtl-transport-gate-v1-numerical-freeze-20260824-rerun": "JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE",
    "qb-to-jtl-load-backaction-causal-audit-v1-20260824": "MIXED_DYNAMIC_LOADING",
    "physical-bvm-jsl12-qb-sfq-closure-v1-20260824": "PHYSICAL_BACKACTION_PREVENTS_CLOSURE",
}


def order_metadata(name: str) -> tuple[int, str, str]:
    """Return one-based execution order and stage metadata."""
    try:
        number = EXPERIMENT_ORDER.index(name) + 1
    except ValueError:
        number = len(EXPERIMENT_ORDER) + 1
    for stage_id, title, positions in STAGE_DEFINITIONS:
        if number in positions:
            return number, stage_id, title
    return number, "stage-99", "其它 / 后续补充"


def ordered_entries(entries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    for name, entry in entries.items():
        sequence, stage_id, stage_title = order_metadata(Path(name).name)
        entry.setdefault("sequence", sequence)
        entry.setdefault("stage_id", stage_id)
        entry.setdefault("stage_title", stage_title)
    return sorted(entries.values(), key=lambda e: (int(e.get("sequence", 10**9)), e.get("experiment_id", "")))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def exists(path: str | None) -> bool:
    return bool(path) and (ROOT / path).exists()


def report_for(exploration: Path) -> str | None:
    preferred = [
        exploration / "analysis/REPORT.md",
        exploration / "analysis/QB_Q0_REPORT.md",
        exploration / "analysis/R13A_REPORT.md",
        exploration / "REPORT.md",
        exploration / "analysis-v2/REPORT.md",
        exploration / "SUMMARY.md",
        exploration / "summary.md",
        exploration / "analysis/summary.md",
    ]
    for path in preferred:
        if path.exists():
            return rel(path)
    candidates = sorted(exploration.glob("**/*REPORT*.md")) + sorted(exploration.glob("**/*report*.md"))
    return rel(candidates[0]) if candidates else None


KNOWN_VERDICTS = [
    "JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE",
    "MIXED_DYNAMIC_LOADING",
    "TEMPORAL_CONDITIONING_INSUFFICIENT",
    "PAPER_JSL_QB_SUBTHRESHOLD",
    "PAPER_JSL_LOAD_VALID",
    "QB_SOURCE_BACKACTION_FAILURE",
    "QB_BVM_SUBTHRESHOLD",
    "NO_JTL_TRIGGER",
    "DCSFQ_BVM_NO_TRIGGER",
    "ACTIVE_STAGE_NO_TRIGGER",
    "CAUSAL_NEAR_THRESHOLD",
    "BACK_ACTION_FAILURE",
    "ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED",
    "Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT",
    "Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT",
    "UNIFORM_SCALE_NO_OUTPUT_EVENT",
    "BIAS_BRACKET_NO_BJL1_EVENT",
    "PAPER_JSL_WAVEFORM_MATCHES_QB_ONE_SHOT",
    "IDEAL_REPLAY_SELECTIVE_ONE_SFQ_CANDIDATE",
    "PHYSICAL_BACKACTION_PREVENTS_CLOSURE",
]


def infer_verdict(exploration: Path) -> str:
    paths = [p for p in [exploration / "SUMMARY.md", exploration / "summary.md", exploration / "REPORT.md", exploration / "analysis/REPORT.md"] if p.exists()]
    discovered = report_for(exploration)
    if discovered:
        discovered_path = ROOT / discovered
        if discovered_path not in paths:
            paths.append(discovered_path)
    text = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in paths)
    for verdict in KNOWN_VERDICTS:
        if verdict in text:
            return verdict
    return "REPORT_PRESENT" if paths else "NO_FORMAL_REPORT_FOUND"


def case_role(case_id: str) -> str:
    low = case_id.lower()
    if "read0-control" in low or "read=0" in low or "control" in low or "zero" in low:
        return "ZERO_CONTROL"
    if "positive-control" in low or "positive" in low:
        return "POSITIVE_CONTROL"
    if "reverse" in low:
        return "NEGATIVE_CONTROL"
    if "paper" in low and ("reference" in low or "original" in low):
        return "HISTORICAL_REFERENCE"
    if "logical0" in low or "read0" in low:
        return "NEGATIVE_CONTROL"
    return "RESULT"


def raw_cases(exploration: Path) -> list[dict[str, Any]]:
    roots = [exploration / "raw"]
    if not roots[0].exists():
        roots = [exploration / "raw-v2"] if (exploration / "raw-v2").exists() else [exploration / "raw-v3"]
    out = []
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.csv")):
            if "reference" in path.parts or "invalid" in path.parts:
                continue
            case_id = path.relative_to(root).as_posix()
            if case_id.endswith("/run-01.csv"):
                case_id = case_id[:-len("/run-01.csv")]
            elif case_id.endswith(".csv"):
                case_id = case_id[:-4]
            out.append({
                "id": case_id,
                "role": case_role(case_id),
                "fixture": exploration.name,
                "condition": case_id,
                "expected_classification": "REPORT_DEFINED",
                "raw": rel(path),
            })
    return out


def signals_from_cases(cases: list[dict[str, Any]]) -> list[str]:
    signals: set[str] = set()
    for case in cases[:8]:
        raw = case.get("raw")
        if not raw or not (ROOT / raw).is_file():
            continue
        try:
            with (ROOT / raw).open("r", encoding="utf-8", errors="replace") as handle:
                header = next((line for line in handle if line.startswith("time,")), None)
            if header:
                columns = next(csv.reader([header]))
                signals.update(c for c in columns if c.startswith(("P(", "V(", "I(")))
        except (OSError, StopIteration, csv.Error):
            continue
    return sorted(signals)


def read_plot_meta(path: Path) -> dict[str, Any]:
    meta_path = path.with_suffix(".metadata.json")
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def plot_record(path: str, *, role: str, cases: list[str], source_classification: str,
                phase: str | None = "continuous_absolute", source_experiments: list[str] | None = None) -> dict[str, Any]:
    record = {
        "path": path,
        "role": role,
        "cases": cases,
        "source_classification": source_classification,
        "phase_semantics": phase,
    }
    if phase is None:
        record["phase_plot"] = False
    if source_experiments:
        record["source_experiments"] = source_experiments
    meta = read_plot_meta(ROOT / path)
    if meta.get("source_paths"):
        record["source_paths"] = meta["source_paths"]
    return record


def common_plot(exploration: Path, cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    path = exploration / "plots/alignment-overview.html"
    if not path.exists():
        path = exploration / "plots/overview.html"
    if not path.exists():
        return []
    return [plot_record(rel(path), role="RESULT", cases=[c["id"] for c in cases], source_classification="CURRENT_RESULT")]


def key_entry(name: str, *, title: str, question: str, result: str, status: str,
              report: str | None, claim_type: str, topology_id: str,
              notes: str = "", cases: list[dict[str, Any]] | None = None,
              plots: list[dict[str, Any]] | None = None,
              reading: str = "", topology_variants: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    entry = {
        "experiment_id": name,
        "title_cn": title,
        "scientific_question": question,
        "formal_result": result,
        "what_done": question,
        "result_summary": result,
        "conclusion_boundary": notes or "正式结论以 report 为准；可视化不改变 scientific verdict。",
        "scientific_status": status,
        "current_status": ("NO_WAVEFORM_VISUALIZATION_REQUIRED" if not (cases or []) else ("ALIGNED" if plots else "VISUALIZATION_INCOMPLETE")),
        "report": report,
        "claim_type": claim_type,
        "required_cases": cases or [],
        "required_signals": ["phase P(...)", "same-JJ voltage V(...)", "current I(...)"],
        "plots": plots or [],
        "topology_id": topology_id,
        "phase_semantics": PHASE_SEMANTICS,
        "notes": notes,
        "reading_guide": reading,
    }
    if topology_variants:
        entry["topology_variants"] = topology_variants
    return entry


def apply_experiment_narratives(entries: dict[str, dict[str, Any]]) -> None:
    """Attach explicit human-readable purpose/result/boundary to every entry."""
    missing: list[str] = []
    for entry in entries.values():
        name = Path(entry["experiment_id"]).name
        narrative = EXPERIMENT_NARRATIVES.get(name)
        if narrative is None:
            missing.append(name)
            continue
        entry.update(narrative)
        # Keep the legacy manifest keys populated for existing consumers while
        # making the new three fields the UI-facing source of wording.
        entry["scientific_question"] = narrative["what_done"]
        entry["formal_result"] = narrative["result_summary"]
        entry["notes"] = narrative["conclusion_boundary"]
        entry["scientific_status"] = EXPERIMENT_STATUS_OVERRIDES.get(name, entry.get("scientific_status", "UNKNOWN"))
    if missing:
        raise RuntimeError("Missing experiment narrative metadata: " + ", ".join(sorted(missing)))


def explicit_cases(items: list[tuple[str, str, str, str, str, str]]) -> list[dict[str, Any]]:
    return [{"id": i, "role": role, "fixture": fixture, "condition": cond,
             "expected_classification": expected, "raw": raw} for i, role, fixture, cond, expected, raw in items]


def curated_entries() -> dict[str, dict[str, Any]]:
    e: dict[str, dict[str, Any]] = {}
    q0 = "test/exploration/qb-q0-standalone-current-quantized-event-20260824"
    scaled_cases = explicit_cases([
        ("scaled/iin-0", "ZERO_CONTROL", q0, "scaled 0 µA", "ZERO_EVENT", f"{q0}/raw/scaled/iin-0.csv"),
        ("scaled/iin-45u", "RESULT", q0, "scaled 45 µA", "NO_COMPLETE_EVENT", f"{q0}/raw/scaled/iin-45u.csv"),
        ("scaled/iin-68p4u", "RESULT", q0, "scaled 68.4 µA", "EXACTLY_ONE", f"{q0}/raw/scaled/iin-68p4u.csv"),
        ("scaled/iin-90u", "RESULT", q0, "scaled 90 µA", "MULTI_EVENT", f"{q0}/raw/scaled/iin-90u.csv"),
        ("paper/iin-0", "HISTORICAL_REFERENCE", q0, "paper 0 µA", "ZERO_EVENT", f"{q0}/raw/paper/iin-0.csv"),
        ("paper/iin-68p4u", "HISTORICAL_REFERENCE", q0, "paper 68.4 µA", "NO_COMPLETE_EVENT", f"{q0}/raw/paper/iin-68p4u.csv"),
        ("paper/iin-90u", "HISTORICAL_REFERENCE", q0, "paper 90 µA", "NO_COMPLETE_EVENT", f"{q0}/raw/paper/iin-90u.csv"),
    ])
    e[q0] = key_entry(
        q0, title="QB-Q0：低 Ic QB standalone 量化窗口",
        question="低 Ic scaled QB 在理想输入下的 zero / subthreshold / exactly-one / multi-event 窗口是什么？",
        result="scaled 0=ZERO_EVENT；45=NO_COMPLETE_EVENT；68.4=EXACTLY_ONE；90=MULTI_EVENT。paper-original 68.4/90 均无完整 BJL2 event。",
        status="ACCEPTED_STANDALONE_REFERENCE", report=f"{q0}/analysis/QB_Q0_REPORT.md", claim_type="input_window",
        topology_id="QB_Q0_10OHM", cases=scaled_cases, plots=[
            plot_record(f"{q0}/plots/scaled-comparison.html", role="COMPARISON", cases=[c["id"] for c in scaled_cases[:4]], source_classification="CURRENT_RESULT"),
            plot_record(f"{q0}/plots/scaled-68p4uA.html", role="RESULT", cases=["scaled/iin-68p4u"], source_classification="CURRENT_RESULT"),
            plot_record(f"{q0}/plots/scaled-90uA.html", role="RESULT", cases=["scaled/iin-90u"], source_classification="CURRENT_RESULT"),
            plot_record(f"{q0}/plots/scaled-45uA.html", role="RESULT", cases=["scaled/iin-45u"], source_classification="CURRENT_RESULT"),
            plot_record(f"{q0}/plots/scaled-0uA.html", role="ZERO_CONTROL", cases=["scaled/iin-0"], source_classification="CURRENT_ZERO_CONTROL"),
            plot_record(f"{q0}/plots/paper-reference-comparison.html", role="HISTORICAL_REFERENCE", cases=[c["id"] for c in scaled_cases[4:]], source_classification="PAPER_REFERENCE"),
            plot_record(f"{q0}/plots/68p4-paper-reference.html", role="HISTORICAL_REFERENCE", cases=["paper/iin-68p4u"], source_classification="PAPER_REFERENCE"),
            plot_record(f"{q0}/plots/90-paper-reference.html", role="HISTORICAL_REFERENCE", cases=["paper/iin-90u"], source_classification="PAPER_REFERENCE"),
        ], notes="论文参数 QB 对照不得成为 scaled-Q0 exactly-one 的 primary evidence。",
        reading="先看 scaled-comparison；再看 68.4 exactly-one 和 90 multi-event；最后看 paper reference 对照。",
    )

    q1 = "test/exploration/paper-sl-q1-20260824"
    q1_cases = explicit_cases([
        ("q0-68p4u-positive-control", "POSITIVE_CONTROL", q1, "Q0 scaled 68.4 µA", "EXACTLY_ONE", "test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv"),
        ("paper-j1-logical1-read", "RESULT", q1, "paper-JSL logical1 READ", "PAPER_JSL_QB_SUBTHRESHOLD", f"{q1}/raw/paper-j1-logical1-read.csv"),
        ("paper-j0-logical0-read", "NEGATIVE_CONTROL", q1, "paper-JSL logical0 READ", "NO_COMPLETE_EVENT", f"{q1}/raw/paper-j0-logical0-read.csv"),
        ("paper-j1-logical1-read0-control", "ZERO_CONTROL", q1, "logical1 READ=0", "ZERO_EVENT", f"{q1}/raw/paper-j1-logical1-read0-control.csv"),
        ("paper-j0-logical0-read0-control", "ZERO_CONTROL", q1, "logical0 READ=0", "ZERO_EVENT", f"{q1}/raw/paper-j0-logical0-read0-control.csv"),
    ])
    e[q1] = key_entry(q1, title="PAPER-SL-Q1：paper-JSL replay → frozen scaled QB",
        question="paper-JSL waveform replay 是否足以驱动 frozen scaled QB？", result="read1 > read0 >> controls，但 BJL2 未达到 exactly-one；Q0 68.4 µA 仅作为 positive control。",
        status="PAPER_JSL_QB_SUBTHRESHOLD", report=f"{q1}/analysis/REPORT.md", claim_type="source_to_receiver",
        topology_id="PAPER_JSL_TO_FROZEN_QB", cases=q1_cases, plots=[
            plot_record(f"{q1}/plots/qb-replay/comparison.html", role="COMPARISON", cases=[c["id"] for c in q1_cases], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/paper-j1-logical1-read.html", role="RESULT", cases=["paper-j1-logical1-read"], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/paper-j0-logical0-read.html", role="NEGATIVE_CONTROL", cases=["paper-j0-logical0-read"], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/paper-j1-logical1-read0-control.html", role="ZERO_CONTROL", cases=["paper-j1-logical1-read0-control"], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/paper-j0-logical0-read0-control.html", role="ZERO_CONTROL", cases=["paper-j0-logical0-read0-control"], source_classification="QB_RESPONSE"),
            plot_record(f"{q1}/plots/qb-replay/q0-68p4u-positive-control.html", role="POSITIVE_CONTROL", cases=["q0-68p4u-positive-control"], source_classification="Q0_REFERENCE"),
            plot_record(f"{q1}/plots/paper-sl-l0-classic/logical1-read.html", role="SOURCE_REFERENCE", cases=["paper-JSL/logical1-read"], source_classification="PAPER_JSL_SOURCE"),
        ], notes="source waveform 只能是 SOURCE_REFERENCE；核心图必须展示 QB response。")

    q2 = "test/exploration/paper-sl-q2-20260824"
    q2cases = raw_cases(ROOT / q2)
    e[q2] = key_entry(q2, title="PAPER-SL-Q2：central-bias bracket",
        question="37.5 与 40 µA central bias 是否关闭 frozen paper-JSL replay 的 BJL1/BJL2 event？",
        result="BIAS_BRANCH_SUBTHRESHOLD；两点均保持 bounded，未建立 complete BJL1/BJL2 event。",
        status="BIAS_BRANCH_SUBTHRESHOLD", report=f"{q2}/analysis/REPORT.md", claim_type="bias_comparison",
        topology_id="PAPER_JSL_TO_FROZEN_QB", cases=q2cases, plots=[
            plot_record(f"{q2}/plots/bias-37p5-vs-40-comparison.html", role="COMPARISON", cases=[c["id"] for c in q2cases], source_classification="CURRENT_RESULT"),
            plot_record(f"{q2}/plots/37p5u/comparison.html", role="RESULT", cases=[c["id"] for c in q2cases if c["id"].startswith("37p5u/")], source_classification="CURRENT_RESULT"),
            plot_record(f"{q2}/plots/40u/comparison.html", role="RESULT", cases=[c["id"] for c in q2cases if c["id"].startswith("40u/")], source_classification="CURRENT_RESULT"),
        ], notes="comparison 必须同时覆盖 37.5 和 40 µA。")

    physical = "test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824"
    physical_cases = explicit_cases([
        ("13/logical1_read", "RESULT", physical, "13 ps logical1 + canonical READ", "SUBTHRESHOLD", f"{physical}/raw/13/logical1_read/run-01.csv"),
        ("13/logical0_read", "NEGATIVE_CONTROL", physical, "13 ps logical0 + canonical READ", "NO_COMPLETE_EVENT", f"{physical}/raw/13/logical0_read/run-01.csv"),
        ("13/logical1_no_read_control", "ZERO_CONTROL", physical, "13 ps logical1 + READ=0", "ZERO_EVENT", f"{physical}/raw/13/logical1_no_read_control/run-01.csv"),
        ("13/logical0_no_read_control", "ZERO_CONTROL", physical, "13 ps logical0 + READ=0", "ZERO_EVENT", f"{physical}/raw/13/logical0_no_read_control/run-01.csv"),
        ("14/logical1_read", "RESULT", physical, "14 ps logical1 + canonical READ", "SUBTHRESHOLD", f"{physical}/raw/14/logical1_read/run-01.csv"),
        ("14/logical0_read", "NEGATIVE_CONTROL", physical, "14 ps logical0 + canonical READ", "NO_COMPLETE_EVENT", f"{physical}/raw/14/logical0_read/run-01.csv"),
        ("14/logical1_no_read_control", "ZERO_CONTROL", physical, "14 ps logical1 + READ=0", "ZERO_EVENT", f"{physical}/raw/14/logical1_no_read_control/run-01.csv"),
        ("14/logical0_no_read_control", "ZERO_CONTROL", physical, "14 ps logical0 + READ=0", "ZERO_EVENT", f"{physical}/raw/14/logical0_no_read_control/run-01.csv"),
    ])
    e[physical] = key_entry(
        physical,
        title="Physical BVM→12×JSL→scaled QB：SFQ closure",
        question="真实 canonical BVM→12×320 µA JSL→frozen scaled QB 连接后，ideal replay 的 read1=1/read0=0 candidate 是否仍保持？",
        result="PHYSICAL_BACKACTION_PREVENTS_CLOSURE；13/14 ps read1 BJL2 均约 −0.12 turn，read0/controls 无完整 event；I(L_SL) 未数量级塌缩，但 physical source/load-line 与 QB current partition 改变。",
        status="PHYSICAL_BACKACTION_PREVENTS_CLOSURE",
        report=f"{physical}/REPORT.md",
        claim_type="physical_bvm_to_qb_closure",
        topology_id="BVM_JSL12_SCALED_QB_PHYSICAL",
        cases=physical_cases,
        plots=[
            # Rebuilt physical-closure views: the first five are the intended
            # navigation entry points.  They expose SL current, BVM guards,
            # all JSL currents, QB routing/KCL, and the four matched cases;
            # the per-case pages below ensure every required raw case has a
            # direct result view rather than only appearing inside a matrix.
            plot_record(f"{physical}/plots/physical-width-comparison.html", role="COMPARISON", cases=[f"{w}/{r}" for w in (13, 14) for r in ["logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control"]], source_classification="PHYSICAL_RESULT"),
            plot_record(f"{physical}/plots/13ps-matched-cases.html", role="COMPARISON", cases=[f"13/{r}" for r in ["logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control"]], source_classification="PHYSICAL_RESULT"),
            plot_record(f"{physical}/plots/14ps-matched-cases.html", role="COMPARISON", cases=[f"14/{r}" for r in ["logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control"]], source_classification="PHYSICAL_RESULT"),
            plot_record(f"{physical}/plots/physical-source-and-storage-guards.html", role="COMPARISON", cases=[f"{w}/{r}" for w in (13, 14) for r in ["logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control"]], source_classification="SOURCE_STORAGE_GUARD"),
            plot_record(f"{physical}/plots/physical-jsl12-current-consistency.html", role="RESULT", cases=[f"{w}/{r}" for w in (13, 14) for r in ["logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control"]], source_classification="JSL_SERIES_CONSISTENCY", phase=None),
            plot_record(f"{physical}/plots/physical-qb-routing-and-kcl.html", role="COMPARISON", cases=["13/logical1_read", "13/logical0_read", "14/logical1_read", "14/logical0_read"], source_classification="QB_ROUTING_KCL", phase=None),
            *[
                plot_record(f"{physical}/plots/cases/{w}ps-{r}.html", role=("ZERO_CONTROL" if "no_read_control" in r else ("NEGATIVE_CONTROL" if r == "logical0_read" else "RESULT")), cases=[f"{w}/{r}"], source_classification="PHYSICAL_CASE_RESULT")
                for w in (13, 14)
                for r in ["logical1_read", "logical0_read", "logical1_no_read_control", "logical0_no_read_control"]
            ],
            plot_record(f"{physical}/plots/13ps-ideal-vs-physical-qb.html", role="COMPARISON", cases=["13/logical1_read", "13/logical0_read", "13/logical1_no_read_control", "13/logical0_no_read_control"], source_classification="PHYSICAL_PRIMARY_VS_IDEAL_REFERENCE", source_experiments=[physical, "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824"]),
            plot_record(f"{physical}/plots/14ps-ideal-vs-physical-qb.html", role="COMPARISON", cases=["14/logical1_read", "14/logical0_read", "14/logical1_no_read_control", "14/logical0_no_read_control"], source_classification="PHYSICAL_PRIMARY_VS_IDEAL_REFERENCE", source_experiments=[physical, "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824"]),
            plot_record(f"{physical}/plots/physical-logical1-vs-logical0.html", role="COMPARISON", cases=["13/logical1_read", "13/logical0_read", "14/logical1_read", "14/logical0_read"], source_classification="PHYSICAL_RESULT", source_experiments=[physical]),
            plot_record(f"{physical}/plots/13ps-source-before-vs-after-qb-loading.html", role="COMPARISON", cases=["13 source-only logical1", "13 physical logical1", "13 source-only logical0", "13 physical logical0"], source_classification="SOURCE_LOADLINE_COMPARISON", source_experiments=[physical, "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824"]),
            plot_record(f"{physical}/plots/14ps-source-before-vs-after-qb-loading.html", role="COMPARISON", cases=["14 source-only logical1", "14 physical logical1", "14 source-only logical0", "14 physical logical0"], source_classification="SOURCE_LOADLINE_COMPARISON", source_experiments=[physical, "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824"]),
            plot_record(f"{physical}/plots/bjl2-phase-area-evidence.html", role="RESULT", cases=["13/logical1_read", "14/logical1_read", "13/logical0_read", "14/logical0_read"], source_classification="PHYSICAL_EVENT_EVIDENCE"),
        ],
        notes="ideal replay 只作后验 reference，不能替代 physical primary。13/14 均未形成 physical BJL2 clean one-SFQ；本轮不进入 timestep/rewrite confirmation、JTL 或 T1。新入口先看 width/matched-cases，再看 SL current/source guards、JSL12 consistency、QB routing/KCL，最后看 strict phase/area evidence。",
        reading="先看 physical-width-comparison 或 13/14 matched-cases；再看 physical-source-and-storage-guards 与 physical-jsl12-current-consistency；然后看 physical-qb-routing-and-kcl；最后看 bjl2-phase-area-evidence 与正式 REPORT。",
    )

    legacy_width = "test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824"
    legacy_width_path = ROOT / legacy_width
    e[legacy_width] = key_entry(
        legacy_width,
        title="历史 JSL width bracket：12 ps W* baseline",
        question="旧 JSL width baseline 对 frozen scaled QB 的 source-side margin 做了什么？",
        result="WIDTH_IMPROVES_QB_MARGIN_BUT_SUBTHRESHOLD；该 lineage 的 logical0 语义已被新的 READ audit 标为 noncanonical。",
        status="SUPERSEDED_ONLY",
        report=f"{legacy_width}/REPORT.md",
        claim_type="historical_width_reference",
        topology_id="PAPER_JSL_TO_FROZEN_QB",
        cases=[],
        plots=[
            plot_record(f"{legacy_width}/plots/9ps-vs-Wstar-qb-replay-comparison.html", role="HISTORICAL_REFERENCE", cases=["historical/QB replay"], source_classification="HISTORICAL_REFERENCE"),
            plot_record(f"{legacy_width}/plots/9ps-vs-Wstar-qb-current-comparison.html", role="HISTORICAL_REFERENCE", cases=["historical/current"], source_classification="HISTORICAL_REFERENCE", phase=None),
            plot_record(f"{legacy_width}/plots/sl-readout-current-comparison.html", role="HISTORICAL_REFERENCE", cases=["historical/SL current"], source_classification="HISTORICAL_REFERENCE", phase=None),
        ],
        notes="保留旧 raw/plots 供 provenance 追溯；不得用其非canonical logical0 作为当前 read1/read0 claim 的 primary evidence。",
        reading="作为旧 12 ps baseline 参考；canonical READ 语义和 corrected 12/13/14/15 ps bracket 以本阶段新 Exploration 为准。",
    )

    factor_info = {
        "paper-sl-q3-l1-routing-closure-20260824": ("Q3", "L1=4.50,L2=3.91", "ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED"),
        "paper-sl-q4-l1-l2-placement-20260824": ("Q4", "L1=3.91,L2=4.50", "Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT"),
        "paper-sl-q5-l1-l2-factorial-20260824": ("Q5", "L1=4.50,L2=4.50", "Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT"),
    }
    for exp, (label, point, verdict) in factor_info.items():
        path = ROOT / "test/exploration" / exp
        cases = raw_cases(path)
        plots = [plot_record(f"test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html", role="COMPARISON", cases=["Q2", "Q3", "Q4", "Q5"], source_classification="FACTORIAL_RESULT", source_experiments=["paper-sl-q2-20260824", *factor_info.keys()])]
        plots.append(plot_record(f"test/exploration/{exp}/plots/alignment-overview.html", role="RESULT", cases=[c["id"] for c in cases], source_classification="CURRENT_RESULT"))
        e[str(path.relative_to(ROOT))] = key_entry(str(path.relative_to(ROOT)), title=f"{label}：{point}",
            question="L1/L2 placement 如何影响 QB routing 与 BJL2 response？",
            result=verdict, status=verdict, report=report_for(path), claim_type="factorial_point",
            topology_id="PAPER_JSL_TO_FROZEN_QB", cases=cases, plots=plots,
            notes="Q2/Q3/Q4/Q5 factorial comparison 是正式 comparison claim 的核心入口。")

    load = "test/exploration/qb-load-boundary-matrix-20260824"
    load_cases = raw_cases(ROOT / load)
    e[load] = key_entry(load, title="QB load-boundary matrix：Q0 output boundary",
        question="同一 Q0 source 在 OPEN、10Ω、JTL-only、10Ω||JTL 下如何改变 local quantization 与 transport？",
        result="Q0+10Ω exactly-one；OPEN multi-event；JTL-only 与 10Ω||JTL event lost；机制报告为 MIXED_DYNAMIC_LOADING。",
        status="MIXED_DYNAMIC_LOADING", report=f"{load}/analysis/REPORT.md", claim_type="load_matrix",
        topology_id="QB_Q0_10OHM", cases=load_cases, plots=[
            plot_record(f"{load}/plots/q0-complete-boundary-comparison.html", role="COMPARISON", cases=["Q0 + 10Ω (accepted)", "Q0 OPEN", "Q0 JTL-only", "Q0 10Ω || JTL"], source_classification="Q0_BOUNDARY_RESULT"),
            plot_record(f"{load}/plots/q5-open-vs-jtl-read1.html", role="COMPARISON", cases=[c["id"] for c in load_cases if c["id"].startswith(("D-", "E-"))], source_classification="Q5_BOUNDARY_RESULT"),
            plot_record(f"{load}/plots/alignment-overview.html", role="RESULT", cases=[c["id"] for c in load_cases], source_classification="CURRENT_RESULT"),
        ], notes="Q5 OPEN/JTL 为独立 secondary comparison，不替代 Q0 four-boundary core。每个 output boundary 都保留独立 topology provenance。",
        topology_variants=[
            {"topology_id": "QB_Q0_OPEN", "title_cn": "低 Ic QB → OPEN output boundary",
             "representative_deck": f"{load}/inputs-v2/A-q0-open/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/topology.svg"},
            {"topology_id": "QB_Q0_JTL_ONLY", "title_cn": "低 Ic QB → standard JTL direct",
             "representative_deck": f"{load}/inputs-v2/B-q0-jtl-only/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/variants/scaled-iin-68p4u/topology.svg"},
            {"topology_id": "QB_Q0_10OHM_PARALLEL_JTL", "title_cn": "低 Ic QB + 10Ω || standard JTL",
             "representative_deck": f"{load}/inputs-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/variants/scaled-iin-68p4u-2/topology.svg"},
        ])

    par = "test/exploration/parallel-qb-jtl-interface-mechanism-20260824"
    par_path = ROOT / par
    e[par] = key_entry(par, title="M1–M5：QB→JTL interface mechanism matrix",
        question="不同输出接口如何影响 QB local event 与 JTL transport？", result="M5 positive-control 的历史 exactly-one 解释已废止；保留 full matrix 与 strict local/transport distinction。",
        status="BOUNDED_INTERFACE_MATRIX", report=f"{par}/analysis-v2/REPORT.md", claim_type="interface_matrix",
        topology_id="QB_M3_SERIES10_JTL", cases=raw_cases(par_path), plots=[
            plot_record(f"{par}/plots/interface-qb-phase-comparison.html", role="COMPARISON", cases=["M1", "M2", "M3", "M4", "M5"], source_classification="QB_INTERFACE_RESULT"),
            plot_record(f"{par}/plots/interface-jtl-phase-comparison.html", role="COMPARISON", cases=["M1", "M2", "M3", "M4", "M5"], source_classification="JTL_INTERFACE_RESULT"),
            plot_record(f"{par}/plots/M1-ideal-replay.html", role="RESULT", cases=["M1"], source_classification="CURRENT_RESULT"),
            plot_record(f"{par}/plots/M3-rseries10.html", role="RESULT", cases=["M3"], source_classification="CURRENT_RESULT"),
            plot_record(f"{par}/plots/M5-positive-control.html", role="HISTORICAL_REFERENCE", cases=["M5"], source_classification="SUPERSEDED_M5_INTERPRETATION"),
            plot_record(f"{par}/plots/alignment-overview.html", role="RESULT", cases=[c["id"] for c in raw_cases(par_path)], source_classification="CURRENT_RESULT"),
        ], notes="M5-PC 标记 MULTI_WELL_TRANSPORT_NOT_ONE_TURN；历史 exactly-one interpretation 不作为 current claim。每个接口变体均绑定自己的 representative deck。",
        topology_variants=[
            {"topology_id": "QB_M1_IDEAL_REPLAY_JTL", "title_cn": "Q0 recorded V(OUT) ideal replay → standard JTL",
             "representative_deck": f"{par}/inputs/M1-ideal-replay/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main/topology.svg"},
            {"topology_id": "QB_M2_RISO10_JTL", "title_cn": "低 Ic QB → RISO=10Ω → standard JTL",
             "representative_deck": f"{par}/inputs/M2-riso10/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main-2/topology.svg"},
            {"topology_id": "QB_M4_LISO10P_JTL", "title_cn": "低 Ic QB → LISO=10pH → standard JTL",
             "representative_deck": f"{par}/inputs/M4-liso10p/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main-4/topology.svg"},
            {"topology_id": "QB_M5_SCALED_JTL", "title_cn": "低 Ic QB → scaled JTL",
             "representative_deck": f"{par}/inputs/M5-q0-scaled/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main-5/topology.svg"},
        ])

    jm = "test/exploration/jtl-transport-gate-v1-methodology-20260824"
    jn = "test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun"
    jcases = [{"id": x, "role": "POSITIVE_CONTROL" if x == "r11" else ("NEGATIVE_CONTROL" if "reverse" in x else "RESULT"), "fixture": jm, "condition": x, "expected_classification": "REGISTERED_REPLAY", "raw": f"{jn}/raw/{x}"} for x in ["r11", "pulse5-original", "pulse5-reverse"]]
    e[jm] = key_entry(jm, title="JTL transport methodology",
        question="标准正控、Q0 pulse5 原极性与反极性的 transport evidence 是否一致？",
        result="保留 strict replay distinction；numerical freeze 当前为 JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE。",
        status="JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE", report=f"{jn}/analysis/REPORT.md", claim_type="polarity_convergence",
        topology_id="STANDARD_JTL_2CELL", cases=jcases, plots=[
            plot_record(f"{jn}/plots/r11-timestep-comparison.html", role="POSITIVE_CONTROL", cases=["r11"], source_classification="STANDARD_JTL_POSITIVE_CONTROL"),
            plot_record(f"{jn}/plots/pulse5-original-timestep-comparison.html", role="RESULT", cases=["pulse5-original"], source_classification="Q0_ORIGINAL_REPLAY"),
            plot_record(f"{jn}/plots/pulse5-reverse-timestep-comparison.html", role="NEGATIVE_CONTROL", cases=["pulse5-reverse"], source_classification="Q0_REVERSE_REPLAY"),
        ], notes="不把 post-window robustness 未完全通过误写成 timestep classification 不稳定。")

    back = "test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824"
    back_cases = explicit_cases([
        ("Q0+10Ω", "RESULT", back, "Q0 + 10Ω", "ACCEPTED_Q0_REFERENCE", "test/exploration/qb-q0-standalone-current-quantized-event-20260824/raw/scaled/iin-68p4u.csv"),
        ("Q0 OPEN", "RESULT", back, "Q0 OPEN", "Q0_OPEN", "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/A-q0-open/scaled-iin-68p4u.csv"),
        ("Q0 JTL-only", "RESULT", back, "Q0 JTL-only", "Q0_JTL_ONLY", "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/B-q0-jtl-only/scaled-iin-68p4u.csv"),
        ("Q0 10Ω||JTL", "RESULT", back, "Q0 10Ω||JTL", "Q0_PARALLEL_JTL", "test/exploration/qb-load-boundary-matrix-20260824/raw-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.csv"),
        ("M3 series10Ω→JTL", "RESULT", back, "M3 series10Ω→JTL", "M3_SERIES_R", "test/exploration/parallel-qb-jtl-interface-mechanism-20260824/raw-v2/M3-rseries10/run.csv"),
    ])
    e[back] = key_entry(back, title="QB→JTL load back-action causal audit",
        question="负载改变 Q0 BJL2 trajectory 的主要阶段是 barrier crossing 前、crossing 中还是 retrap？",
        result="MIXED_DYNAMIC_LOADING；核心时间窗 208–210、210–217.1、217.1–259 ps。",
        status="MIXED_DYNAMIC_LOADING", report=f"{back}/analysis/REPORT.md", claim_type="load_backaction_audit",
        topology_id="QB_Q0_10OHM", cases=back_cases, plots=[
            plot_record(f"{back}/plots/backaction_compare.html", role="COMPARISON", cases=["Q0+10Ω", "Q0 OPEN", "Q0 JTL-only", "Q0 10Ω||JTL", "M3 series10Ω→JTL"], source_classification="BACKACTION_AUDIT"),
        ], notes="不能把非线性接口压缩为单一 scalar impedance，除非 report 证据支持；比较图并列引用以下真实 interface topology。",
        topology_variants=[
            {"topology_id": "QB_Q0_OPEN", "title_cn": "低 Ic QB → OPEN output boundary",
             "representative_deck": f"{load}/inputs-v2/A-q0-open/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/topology.svg"},
            {"topology_id": "QB_Q0_JTL_ONLY", "title_cn": "低 Ic QB → standard JTL direct",
             "representative_deck": f"{load}/inputs-v2/B-q0-jtl-only/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/variants/scaled-iin-68p4u/topology.svg"},
            {"topology_id": "QB_Q0_10OHM_PARALLEL_JTL", "title_cn": "低 Ic QB + 10Ω || standard JTL",
             "representative_deck": f"{load}/inputs-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.cir",
             "connectivity_debug": f"{load}/topology/variants/scaled-iin-68p4u-2/topology.svg"},
            {"topology_id": "QB_M3_SERIES10_JTL", "title_cn": "低 Ic QB → series 10Ω → standard JTL",
             "representative_deck": f"{par}/inputs/M3-rseries10/main.cir",
             "connectivity_debug": f"{par}/topology/variants/main-3/topology.svg"},
        ])

    r13 = "test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823"
    r13path = ROOT / r13
    e[r13] = key_entry(r13, title="R13-A：temporal conditioning requirements",
        question="极性整流、20 ps hold 或两者是否足以触发 frozen DCSFQ？", result="TEMPORAL_CONDITIONING_INSUFFICIENT。raw/C1/C2/C3 均未完成 selective DCSFQ event。",
        status="TEMPORAL_CONDITIONING_INSUFFICIENT", report=f"{r13}/analysis/R13A_REPORT.md", claim_type="conditioning_matrix",
        topology_id="DCSFQ_REPLAY_CONDITIONER", cases=raw_cases(r13path), plots=[
            plot_record(f"{r13}/plots/raw-vs-c1-vs-c2-vs-c3.html", role="COMPARISON", cases=["raw-replay", "c1-rectify", "c2-hold20", "c3-rectify-hold20"], source_classification="CONDITIONING_RESULT"),
            *[plot_record(f"{r13}/plots/{c}/comparison.html", role="RESULT", cases=[f"{c}/{x}" for x in ["read1", "read0", "logical1-read0-control", "logical0-read0-control"]], source_classification="CONDITIONING_RESULT") for c in ["raw-replay", "c1-rectify", "c2-hold20", "c3-rectify-hold20"]],
        ], notes="理想 waveform transformation 的结果只建立 requirements boundary，不是 physical receiver implementation。")

    q6 = "test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824"
    e[q6] = key_entry(q6, title="PAPER-SL-Q6：Q5 → standard JTL compatibility",
        question="Q5 near-threshold QB output 接入 standard JTL 后是否产生 selective regenerative event？", result="NO_JTL_TRIGGER；Q5 standalone 对照必须与 Q6 coupled 并列。",
        status="NO_JTL_TRIGGER", report=f"{q6}/REPORT.md", claim_type="qb_to_jtl", topology_id="Q5_TO_STANDARD_JTL", cases=raw_cases(ROOT / q6), plots=[
            plot_record(f"{q6}/plots/q5-standalone-vs-q6-coupled.html", role="COMPARISON", cases=["Q5 standalone", "Q6 coupled"], source_classification="Q5_Q6_RESULT"),
            plot_record(f"{q6}/plots/q6-q5-to-two-cell-jtl/comparison.html", role="RESULT", cases=[c["id"] for c in raw_cases(ROOT / q6)], source_classification="Q6_COUPLED_RESULT"),
            plot_record(f"{q6}/plots/alignment-overview.html", role="RESULT", cases=[c["id"] for c in raw_cases(ROOT / q6)], source_classification="CURRENT_RESULT"),
        ])

    read_width = "test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824"
    read_width_cases = []
    for width in (12, 13, 14, 15):
        for role, expected in [
            ("logical1_read", "EXACTLY_ONE" if width >= 13 else "NO_COMPLETE_EVENT"),
            ("logical0_read", "NO_COMPLETE_EVENT"),
            ("logical1_no_read_control", "ZERO_EVENT"),
            ("logical0_no_read_control", "ZERO_EVENT"),
        ]:
            read_width_cases.append({
                "id": f"{width}ps/{role}",
                "role": "ZERO_CONTROL" if "no_read_control" in role else "RESULT",
                "fixture": read_width,
                "condition": f"{width} ps {role}",
                "expected_classification": expected,
                "raw": f"{read_width}/raw/replay/{width}ps/{role}/run-01.csv",
            })
    source_case_ids = [f"{width}ps/{role}" for width in (12, 13, 14, 15) for role in ("logical1_read", "logical0_read")]
    e[read_width] = key_entry(
        read_width,
        title="BVM READ semantics audit + canonical JSL width bracket",
        question="修正 READ 语义后，canonical 12-JSL source current 的 12/13/14/15 ps plateau replay 是否在 frozen scaled QB 中形成 selective 1/0/0 event？",
        result="IDEAL_REPLAY_SELECTIVE_ONE_SFQ_CANDIDATE；首个 1/0/0 replay candidate 为 13 ps。",
        status="IDEAL_REPLAY_SELECTIVE_ONE_SFQ_CANDIDATE",
        report=f"{read_width}/REPORT.md",
        claim_type="read_semantics_width_bracket",
        topology_id="PAPER_JSL_TO_FROZEN_QB",
        cases=read_width_cases,
        plots=[
            plot_record(f"{read_width}/plots/qb-replay-width-comparison.html", role="COMPARISON", cases=[c["id"] for c in read_width_cases], source_classification="QB_WIDTH_REPLAY"),
            plot_record(f"{read_width}/plots/source-width-comparison.html", role="SOURCE_REFERENCE", cases=source_case_ids, source_classification="CANONICAL_JSL_SOURCE", phase=None),
            plot_record(f"{read_width}/plots/bjl2-margin-vs-width.html", role="COMPARISON", cases=[f"{w}ps/logical1_read" for w in (12, 13, 14, 15)] + [f"{w}ps/logical0_read" for w in (12, 13, 14, 15)], source_classification="QB_WIDTH_MARGIN"),
            plot_record(f"{read_width}/plots/read-semantics-audit.html", role="COMPARISON", cases=["READ_SEMANTICS_AUDIT"], source_classification="READ_PROTOCOL_AUDIT", phase=None),
        ],
        notes="canonical logical0 必须是负存储态 + 与 logical1 完全相同的正 WL+SE READ；旧 PAPER-SL logical0 为 WL-only/noncanonical lineage。13 ps 是 ideal replay candidate，不是 physical cascade。",
        reading="先看 READ semantics audit，再看 source-width-comparison 的 SL/JSL 电流，最后看 frozen QB replay 与 BJL2 margin。",
    )

    for name, title, question, result, status, claim, topology_id in [
        ("test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824", "QB-Q1：physical BVM → frozen scaled QB", "canonical BVM 直接驱动 frozen scaled QB 是否保持 source guard 并量化？", "QB_SOURCE_BACKACTION_FAILURE；次级 QB_BVM_SUBTHRESHOLD。", "QB_SOURCE_BACKACTION_FAILURE", "source_backaction", "BVM_TO_SCALED_QB"),
        ("test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824", "QB-Q2A：source-decoupled waveform replay", "source isolation alone 是否足以让 frozen QB 量化？", "QB_DYNAMIC_WINDOW_MISMATCH。", "QB_DYNAMIC_WINDOW_MISMATCH", "source_isolation", "SCALED_QB_REPLAY"),
        ("test/exploration/qb-q2b-central-bias-bracketing-20260824", "QB-Q2B：central-bias bracket", "central bias bracket 是否建立 read1-only BJL1 event？", "BIAS_BRACKET_NO_BJL1_EVENT。", "BIAS_BRACKET_NO_BJL1_EVENT", "bias_bracket", "SCALED_QB_REPLAY"),
        ("test/exploration/qb-q2c-uniform-junction-scale-20260824", "QB-Q2C：uniform junction-scale bracketing", "uniform junction scaling 是否建立 selective BJL1/BJL2 event？", "UNIFORM_SCALE_NO_OUTPUT_EVENT。", "UNIFORM_SCALE_NO_OUTPUT_EVENT", "uniform_scale", "SCALED_QB_REPLAY"),
    ]:
        path = ROOT / name
        e[name] = key_entry(name, title=title, question=question, result=result, status=status,
            report=report_for(path), claim_type=claim, topology_id=topology_id, cases=raw_cases(path),
            plots=common_plot(path, raw_cases(path)), notes="重要因果节点；overview 只用于导航，正式结论以 report 为准。")

    # Q3 routing closure is an analysis-only provenance checkpoint.  It has no
    # independent waveform/report package; the accepted Q3 execution fixture
    # is the paper-sl-q3-l1-routing-closure entry below.  Keep this checkpoint
    # visible in execution order without inventing a result plot or report.
    q3_pre = "test/exploration/q3-l1-routing-closure-20260824"
    e[q3_pre] = key_entry(
        q3_pre, title="PAPER-SL-Q3-PRE：L1 routing closure precheck",
        question="Q3 的 L1 routing hypothesis 是否值得进入单点 execution？",
        result="分析-only provenance checkpoint；不单独产生 waveform verdict。",
        status="NO_WAVEFORM_VISUALIZATION_REQUIRED", report=None, claim_type="analysis_only",
        topology_id="PAPER_JSL_TO_FROZEN_QB", cases=[], plots=[],
        notes="该目录只保存分析/拓扑来源；正式 raw、report 和 result plot 归属于 paper-sl-q3-l1-routing-closure-20260824。",
    )

    bvm = "test/exploration/bvm-internal-readout-20260819"
    e[bvm] = key_entry(
        bvm, title="Canonical BVM：storage/readout cell",
        question="canonical BVM 的 S-Loop、R-Loop、read timing 与 SL output 的真实结构和 waveform 是什么？",
        result="canonical BVM source/read behavior frozen；本页只做结构与已有 read evidence 导航。",
        status="ACCEPTED_CANONICAL_SOURCE", report=f"{bvm}/summary.md", claim_type="canonical_source",
        topology_id="BVM_CANONICAL", cases=raw_cases(ROOT / bvm),
        plots=common_plot(ROOT / bvm, raw_cases(ROOT / bvm)),
        notes="publication schematic 已通过 semantic + geometric validation；不把 schematic 当作 receiver verdict。",
    )
    return e


def topology_signature(deck: Path) -> str:
    """Create a structural, parameter-insensitive signature for an input deck."""
    if not deck.exists():
        return "MISSING"
    rows: list[str] = []
    for raw in deck.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.startswith(";"):
            continue
        low = line.lower()
        if low.startswith((".include", ".print", ".plot", ".tran", ".option", ".end", ".param", ".model")):
            continue
        tokens = line.replace("\t", " ").split()
        if not tokens:
            continue
        name = tokens[0]
        if name.startswith("K") and len(tokens) >= 3:
            rows.append("K " + " ".join(tokens[:3]))
        elif name[0].upper() == "X" and len(tokens) >= 4:
            # Preserve subcircuit instance identity and its endpoint list;
            # otherwise standard versus scaled JTL (and physical versus
            # replay fixtures) could collapse to the same false signature.
            rows.append("X " + " ".join(tokens))
        elif len(tokens) >= 3 and name[0].upper() in "BICJLRV":
            rows.append(f"{name[0].upper()} {name} {tokens[1]} {tokens[2]}")
    return hashlib.sha256("\n".join(sorted(rows)).encode()).hexdigest()


def include_refs(deck: Path | None) -> list[str]:
    if not deck or not deck.exists():
        return []
    refs = []
    for line in deck.read_text(encoding="utf-8", errors="replace").splitlines():
        tokens = line.strip().split()
        if tokens and tokens[0].lower() == ".include" and len(tokens) > 1:
            refs.append(tokens[1])
    return refs


LIBRARY_ONLY_NAMES = {
    "jjmit.cir", "bvm_cell.cir", "bq_cell.cir", "bq_cell_paper.cir",
    "JTL.cir", "JTL_SCALED.cir", "DCSFQ_BVM.cir", "receiver.cir",
}


def has_top_level_circuit_elements(path: Path) -> bool:
    """Reject copied include libraries when resolving a representative deck."""
    if not path.exists() or path.name in LIBRARY_ONLY_NAMES:
        return False
    inside_subckt = False
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith(("*", ";")):
            continue
        low = line.lower()
        if low.startswith(".subckt"):
            inside_subckt = True
            continue
        if low.startswith(".ends"):
            inside_subckt = False
            continue
        if inside_subckt or low.startswith((".include", ".print", ".plot", ".tran", ".option", ".end", ".param", ".model", ".ic", ".nodeset")):
            continue
        tokens = line.replace("\t", " ").split()
        if tokens and len(tokens) >= 3 and tokens[0][0].upper() in "BICJLRV":
            return True
        if tokens and len(tokens) >= 4 and tokens[0].upper().startswith("X"):
            return True
    return False


def inherited_source_deck(experiment: Path) -> Path | None:
    """Read an analysis-only fixture's explicit source-deck provenance."""
    notes = sorted(experiment.glob("**/README*.md")) + sorted(experiment.glob("**/*REPORT*.md"))
    for note in notes:
        text = note.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"source deck[^`]*`([^`]+)`", text, re.IGNORECASE)
        if match:
            candidate = ROOT / match.group(1).strip()
            if candidate.exists():
                return candidate
    return None


def representative_deck(experiment: Path, topo_id: str, explicit: str | None = None) -> Path | None:
    """Resolve the top-level simulation deck, never a copied library include."""
    if explicit:
        candidate = ROOT / explicit
        if candidate.exists():
            return candidate
    special = {
        "QB_Q0_10OHM": experiment / "inputs/scaled-iin-68p4u.cir",
        "BVM_CANONICAL": experiment / "inputs/pos-read-single.cir",
        "PAPER_JSL_TO_FROZEN_QB": experiment / "inputs/paper-j1-logical1-read.cir",
        "BVM_TO_SCALED_QB": experiment / "inputs/logical1-read.cir",
        "QB_M3_SERIES10_JTL": experiment / "inputs/M3-rseries10/main.cir",
        "STANDARD_JTL_2CELL": ROOT / "test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/inputs/r11/0p0125/main.cir",
        "Q5_TO_STANDARD_JTL": experiment / "inputs/q6-q5-to-two-cell-jtl/paper-j1-logical1-read.cir",
        "DCSFQ_REPLAY_CONDITIONER": experiment / "inputs/raw-replay/read1.cir",
        "SCALED_QB_REPLAY": ROOT / "test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/inputs/C-canonical-logical1-vsl.cir",
        "BVM_JSL12_SCALED_QB_PHYSICAL": experiment / "inputs/13/logical1_read.cir",
    }
    if topo_id in special and special[topo_id].exists():
        return special[topo_id]
    inherited = inherited_source_deck(experiment)
    if inherited:
        return inherited
    inputs = experiment / "inputs"
    if not inputs.exists():
        return None
    candidates = [p for p in sorted(inputs.rglob("*.cir")) if has_top_level_circuit_elements(p)]
    if not candidates:
        return None
    preferred_tokens = ("logical1", "read1", "positive", "main", "paper-j1", "scaled-iin-68")
    candidates.sort(key=lambda p: (0 if any(token in p.name.lower() for token in preferred_tokens) else 1, len(p.parts), p.as_posix()))
    return candidates[0]


def schematic_package(experiment: Path, topo_id: str) -> Path | None:
    """Find an existing or generated publication-schematic package."""
    root_package = experiment / "topology"
    root_json = root_package / "schematic.json"
    if (root_package / "schematic.svg").exists():
        if not root_json.exists():
            return root_package
        try:
            if json.loads(root_json.read_text(encoding="utf-8")).get("topology_id", topo_id) == topo_id:
                return root_package
        except (OSError, json.JSONDecodeError):
            pass
    for manifest in sorted(experiment.glob("topology/**/schematic.json")):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if data.get("topology_id") == topo_id and (manifest.parent / "schematic.svg").exists():
            return manifest.parent
    return None


def build_topology_manifest(entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    topologies: dict[str, dict[str, Any]] = {}
    for exp_id, entry in entries.items():
        topo_id = entry.get("topology_id") or f"TOPOLOGY_{hashlib.sha1(exp_id.encode()).hexdigest()[:10]}"
        shared_experiment = entry.get("_shared_experiment", exp_id)
        exp = ROOT / entry.get("_topology_experiment", shared_experiment)
        source = representative_deck(exp, topo_id, entry.get("_representative_deck"))
        topo = topologies.setdefault(topo_id, {
            "topology_id": topo_id,
            "title_cn": entry["title_cn"],
            "representative_experiment": exp_id,
            "sequence": int(entry.get("sequence") or order_metadata(Path(shared_experiment).name)[0]),
            "stage_id": entry.get("stage_id") or order_metadata(Path(shared_experiment).name)[1],
            "stage_title": entry.get("stage_title") or order_metadata(Path(shared_experiment).name)[2],
            "representative_deck": rel(source) if source and source.exists() else None,
            "includes": include_refs(source), "subcircuits": [],
            "topology_signature": topology_signature(source) if source else "MISSING",
            "core_blocks": [topo_id], "external_boundary": [],
            "publication_schematic": None, "annotated_schematic": None, "connectivity_debug": None,
            "semantic_validation": None, "geometric_validation": None,
            "shared_by_experiments": [], "status": "DEBUG_ONLY",
        })
        if shared_experiment not in topo["shared_by_experiments"]:
            topo["shared_by_experiments"].append(shared_experiment)
        tdir = exp / "topology"
        debug_override = entry.get("_connectivity_debug")
        if topo_id == "QB_M3_SERIES10_JTL" and not debug_override:
            # The matrix root graph is the M5-PC graph; use the actual M3
            # variant graph for the primary topology instead.
            debug_override = "test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-3/topology.svg"
        if debug_override and not topo["connectivity_debug"]:
            topo["connectivity_debug"] = debug_override
        package = schematic_package(exp, topo_id)
        if package and not topo["publication_schematic"]:
            topo["publication_schematic"] = rel(package / "schematic.svg")
            topo["annotated_schematic"] = rel(package / "schematic-annotated.svg") if (package / "schematic-annotated.svg").exists() else None
            topo["connectivity_debug"] = rel(package / "connectivity-debug.svg") if (package / "connectivity-debug.svg").exists() else topo["connectivity_debug"]
            topo["semantic_validation"] = rel(package / "schematic-validation.json") if (package / "schematic-validation.json").exists() else None
            topo["geometric_validation"] = rel(package / "geometric-connectivity-validation.json") if (package / "geometric-connectivity-validation.json").exists() else None
            topo["status"] = "PUBLICATION_SCHEMATIC_VALIDATED" if topo["semantic_validation"] and topo["geometric_validation"] else "PUBLICATION_SCHEMATIC_UNVALIDATED"
        elif (tdir / "topology.svg").exists() and not topo["connectivity_debug"] and not debug_override:
            topo["connectivity_debug"] = rel(tdir / "topology.svg")
    values = list(topologies.values())
    values.sort(key=lambda x: (int(x.get("sequence", 10**9)), x["topology_id"]))
    for topo in values:
        seq = int(topo.get("sequence", 10**9))
        if seq < 10**9 and seq <= len(EXPERIMENT_ORDER):
            _, sid, title = order_metadata(EXPERIMENT_ORDER[seq - 1])
            topo["stage_id"] = topo.get("stage_id") or sid
            topo["stage_title"] = topo.get("stage_title") or title
    return {"schema_version": "2.0", "parent_head": HEAD, "topologies": values}


def markdown_link(path: str | None, label: str) -> str:
    return f"[{label}](../{path})" if path and exists(path) else f"`{label}（未生成）`"


def plot_links(entry: dict[str, Any]) -> list[str]:
    labels = {
        "COMPARISON": "【关键对比图】", "RESULT": "【单工况/结果图】",
        "POSITIVE_CONTROL": "【正向对照】", "NEGATIVE_CONTROL": "【负向对照】",
        "ZERO_CONTROL": "【零输入对照】", "SOURCE_REFERENCE": "【源波形参考】",
        "HISTORICAL_REFERENCE": "【历史参考】",
    }
    return [f"- {labels.get(p['role'], '[' + p['role'] + ']')} {markdown_link(p['path'], p['path'])}" for p in entry.get("plots", [])]


def render_index(entries: dict[str, dict[str, Any]], *, flow: bool, head: str = HEAD) -> str:
    order = list(entries)
    if flow:
        title = "# EXPLORATION FLOW INDEX V2"
        intro = (f"生成基线 HEAD：`{head}`。\n\n"
                 "本页由 `docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml` 生成，展示科研路线；结果图、controls、source/reference 和电路入口均保持角色区分。")
    else:
        title = "# VISUALIZATION INDEX V2"
        intro = (f"生成基线 HEAD：`{head}`。\n\n"
                 "本页由统一 alignment manifest 生成，按科学语义列出核心结果、对比、controls 和 source/reference。")
    lines = [title, "", intro, "", "## 阅读约定", "",
             "- `continuous_absolute`：原始 JoSIM P(...) 连续轨迹的 φ/2π（turn），不等于 SFQ 计数。",
             "- source/reference/historical 图不能作为 current result 的核心证据。",
             "- 论文级 schematic、annotated schematic、connectivity debug graph 分开列出。", ""]
    for exp_id in order:
        entry = entries[exp_id]
        lines += [f"## {entry['title_cn']}", "", f"**实验 ID**：`{exp_id}`", "",
                  f"**做了什么**：{entry.get('what_done', entry['scientific_question'])}", "",
                  f"**关键结果**：{entry.get('result_summary', entry['formal_result'])}", "",
                  f"**当前状态**：`{entry['scientific_status']}` / alignment=`{entry['current_status']}`", "",
                  f"**结论边界**：{entry.get('conclusion_boundary', entry.get('notes') or '正式结论以 report 为准；可视化不改变 scientific verdict。')}", "",
                  "**推荐先看**：", *plot_links(entry), ""]
        topo = next((t for t in yaml.safe_load(TOPOLOGY_PATH.read_text(encoding="utf-8")).get("topologies", []) if t["topology_id"] == entry.get("topology_id")), None) if TOPOLOGY_PATH.exists() else None
        if topo:
            lines += ["**电路**：",
                      f"- 【论文级电路图】 {markdown_link(topo.get('publication_schematic'), 'schematic.svg')}",
                      f"- 【实验注释电路图】 {markdown_link(topo.get('annotated_schematic'), 'schematic-annotated.svg')}",
                      f"- 【网表连接调试图】 {markdown_link(topo.get('connectivity_debug'), 'connectivity-debug.svg')}", ""]
            variants = entry.get("topology_variants", [])
            if variants:
                lines += ["**真实 topology 变体**："]
                for variant in variants:
                    label = variant.get("title_cn", variant.get("topology_id", "variant"))
                    lines += [f"- `{label}`：",
                              f"  - 【论文级电路图】 {markdown_link(variant.get('publication_schematic'), 'schematic.svg')}",
                              f"  - 【实验注释电路图】 {markdown_link(variant.get('annotated_schematic'), 'schematic-annotated.svg')}",
                              f"  - 【网表连接调试图】 {markdown_link(variant.get('connectivity_debug'), 'connectivity-debug.svg')}"]
                lines.append("")
        if entry.get("report"):
            lines += [f"**正式报告**：{markdown_link(entry['report'], entry['report'])}", ""]
        lines += ["---", ""]
    return "\n".join(lines)


def html_index(markdown: str, title: str, entries: dict[str, dict[str, Any]], topology: dict[str, Any] | None = None) -> str:
    # Keep the HTML index generated from the same entry set; the simple
    # renderer intentionally avoids a second link mapping.
    body = []
    topology_map = {t.get("topology_id"): t for t in (topology or {}).get("topologies", [])}
    for entry in entries.values():
        body.append(f"<section data-experiment-id='{html.escape(entry['experiment_id'])}'><h2>{html.escape(entry['title_cn'])}</h2>")
        body.append(f"<p><b>做了什么：</b>{html.escape(entry.get('what_done', entry['scientific_question']))}</p>")
        body.append(f"<p><b>关键结果：</b>{html.escape(entry.get('result_summary', entry['formal_result']))}</p>")
        body.append(f"<p><b>结论边界：</b>{html.escape(entry.get('conclusion_boundary', entry.get('notes', '正式结论以 report 为准。')))}</p>")
        body.append(f"<p><b>状态：</b><code>{html.escape(entry['scientific_status'])}</code> / <code>{html.escape(entry['current_status'])}</code></p><ul>")
        for p in entry.get("plots", []):
            if exists(p["path"]):
                body.append(f"<li data-plot-role='{html.escape(p['role'])}'><a href='../{html.escape(p['path'])}'>{html.escape(p['role'])} · {html.escape(p['path'])}</a></li>")
        body.append("</ul>")
        topo = topology_map.get(entry.get("topology_id"))
        if topo:
            body.append("<p><b>电路：</b>")
            for label, key in (("论文级电路图", "publication_schematic"), ("实验注释电路图", "annotated_schematic"), ("网表连接调试图", "connectivity_debug")):
                target = topo.get(key)
                if target and exists(target):
                    body.append(f" <a href='../{html.escape(target)}'>{label}</a>")
                else:
                    body.append(f" <span>{label}（未生成）</span>")
            body.append("</p>")
            variants = entry.get("topology_variants", [])
            if variants:
                body.append("<p><b>真实 topology 变体：</b></p><ul>")
                for variant in variants:
                    body.append(f"<li><b>{html.escape(variant.get('title_cn', variant.get('topology_id', 'variant')))}</b>")
                    for label, key in (("论文级电路图", "publication_schematic"), ("实验注释电路图", "annotated_schematic"), ("网表连接调试图", "connectivity_debug")):
                        target = variant.get(key)
                        if target and exists(target):
                            body.append(f" <a href='../{html.escape(target)}'>{label}</a>")
                        else:
                            body.append(f" <span>{label}（未生成）</span>")
                    body.append("</li>")
                body.append("</ul>")
        if entry.get("report") and exists(entry["report"]):
            body.append(f"<p><a href='../{html.escape(entry['report'])}'>正式报告</a></p>")
        body.append("</section>")
    return ("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<title>{html.escape(title)}</title><style>body{{font-family:system-ui;max-width:1200px;margin:2rem auto;line-height:1.55}}section{{border-bottom:1px solid #ddd;padding:1rem 0}}a{{color:#0758a8}}code{{background:#f2f2f2;padding:.1rem .25rem}}</style></head>"
            f"<body><h1>{html.escape(title)}</h1><p>由统一 alignment manifest 生成。基线 HEAD <code>{HEAD}</code>。</p>{''.join(body)}</body></html>\n")


def html_topology_index(topology: dict[str, Any]) -> str:
    body: list[str] = []
    for topo in topology.get("topologies", []):
        body.append(f"<section><h2>{html.escape(topo['title_cn'])}</h2><p><code>{html.escape(topo['topology_id'])}</code> · <code>{html.escape(topo['status'])}</code></p><ul>")
        for label, key in (("论文级电路图", "publication_schematic"), ("实验注释电路图", "annotated_schematic"), ("网表连接调试图", "connectivity_debug")):
            target = topo.get(key)
            if target and exists(target):
                body.append(f"<li><a href='../{html.escape(target)}'>{label}</a></li>")
            else:
                body.append(f"<li>{label}（未生成）</li>")
        body.append(f"</ul><p>representative deck: <code>{html.escape(topo.get('representative_deck') or '未记录')}</code></p></section>")
    return ("<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<title>CIRCUIT SCHEMATIC INDEX</title><style>body{{font-family:system-ui;max-width:1200px;margin:2rem auto;line-height:1.55}}section{{border-bottom:1px solid #ddd;padding:1rem 0}}a{{color:#0758a8}}code{{background:#f2f2f2;padding:.1rem .25rem}}</style></head>"
            f"<body><h1>CIRCUIT SCHEMATIC INDEX</h1><p>由 topology manifest 生成。基线 HEAD <code>{HEAD}</code>。</p>{''.join(body)}</body></html>\n")


def build_alignment_audit(manifest: dict[str, Any], topology: dict[str, Any]) -> str:
    topo_map = {t.get("topology_id"): t for t in topology.get("topologies", [])}
    lines = [
        "# Visualization Alignment Audit V2", "",
        f"基线 HEAD：`{manifest.get('parent_head')}`", "",
        "本审计只检查 raw/report/plot/index/topology 的 provenance 对齐，不改变任何 scientific verdict。", "",
        "| 实验 | 科学状态 | required cases | plots | core/comparison | report | topology | status |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    for entry in manifest.get("experiments", []):
        topo = topo_map.get(entry.get("topology_id"), {})
        core = any(p.get("role") in {"RESULT", "COMPARISON"} for p in entry.get("plots", []))
        lines.append("| {} | `{}` | {} | {} | {} | {} | `{}` | `{}` |".format(
            entry.get("experiment_id"), entry.get("scientific_status"), len(entry.get("required_cases", [])),
            len(entry.get("plots", [])), "YES" if core else "NO", "YES" if entry.get("report") else "NO",
            topo.get("status", "MISSING"), entry.get("current_status")))
    lines += ["", "## 状态定义", "", "- `ALIGNED`：manifest 已明确 raw case、result/comparison plot、report，并通过角色约束；",
              "- `VISUALIZATION_INCOMPLETE`：required case 没有足够 plot coverage；",
              "- `TOPOLOGY_MISMATCH`：结构图 signature 或 publication/debug 角色不一致；",
              "- `NO_WAVEFORM_VISUALIZATION_REQUIRED`：该条目只有 analysis/documentation，没有可登记 raw waveform；",
              "- `SUPERSEDED_ONLY`：仅保留历史 provenance，不作为 current core。", "",
              "## 关键人工 spot-check 集合", "",
              "QB-Q0、PAPER-SL-Q1/Q2、Q2–Q5 factorial、QB load-boundary、M1–M5、JTL methodology/numerical freeze、back-action、R13、Q6 均由 manifest 显式登记；其 core link 不从文件名排序推断。", ""]
    return "\n".join(lines)


def build_reading_guide(entries: dict[str, dict[str, Any]], *, head: str = HEAD) -> str:
    rows = [
        ("我想确认 scaled QB 的输入窗口", "QB-Q0", "qb-q0-standalone-current-quantized-event-20260824/plots/scaled-comparison.html", "看 scaled 0/45/68.4/90 的 BJL2 连续轨迹；paper 只作历史对照。", "不推出 canonical BVM compatibility。"),
        ("我想看 paper-JSL 是否驱动 QB", "PAPER-SL-Q1", "paper-sl-q1-20260824/plots/qb-replay/comparison.html", "看 BJs/BJL1/BJL2 的 read1/read0/control 分离。", "不要把 paper-JSL source 图当 QB response。"),
        ("我想比较 37.5 与 40 µA", "PAPER-SL-Q2", "paper-sl-q2-20260824/plots/bias-37p5-vs-40-comparison.html", "看 BJL1/BJL2 phase 与 current。", "不能只看 37.5 单点。"),
        ("我想看 L1/L2 factorial", "Q2–Q5", "paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html", "看四点的 BJL1/BJL2 与 routing current。", "phase range 不自动等于 event。"),
        ("我想看 output boundary", "QB load-boundary", "qb-load-boundary-matrix-20260824/plots/q0-complete-boundary-comparison.html", "看同一 Q0 的 10Ω/OPEN/JTL/parallel。", "Q5 boundary 是 secondary comparison。"),
        ("我想看 JTL polarity/convergence", "JTL methodology", "jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-timestep-comparison.html", "同时打开 R11 与 reverse。", "严格 Gate 仍 INCONCLUSIVE。"),
        ("我想看 R13 conditioning", "R13-A", "bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-vs-c1-vs-c2-vs-c3.html", "逐条件查看 raw/C1/C2/C3 的 B3。", "理想 replay 不是 physical implementation。"),
        ("我想看 Q5 接 JTL 的变化", "PAPER-SL-Q6", "paper-sl-q6-qb-jtl-compatibility-20260824/plots/q5-standalone-vs-q6-coupled.html", "直接比较 BJL1/BJL2/V(OUT)。", "不把耦合系统成功等同 isolated QB event。"),
        ("我想确认 READ 语义和首个 width candidate", "BVM READ audit + JSL width", "bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824/plots/read-semantics-audit.html", "先确认 canonical logical0 是负存储态 + 同一正 WL/SE READ，再看 13 ps 的 QB replay。", "不能把 ideal replay candidate 当作 physical BVM→12JSL→QB closure。"),
        ("我想看真实 BVM→12×JSL→QB 的完整电流链", "Physical BVM→12×JSL→QB", "physical-bvm-jsl12-qb-sfq-closure-v1-20260824/plots/physical-width-comparison.html", "先看 SL 读出电流，再看 BJs→BJL1→BJL2 phase/current、JSL12 电流一致性和 node2/3/4 KCL。", "不能把 phase activity 或电流峰值单独称为 SFQ event；正式判定看同段 phase/voltage area。"),
    ]
    lines = ["# Visualization Reading Guide", "", f"本指南由 alignment manifest 生成，基线 HEAD：`{head}`。", "", "| 想确认什么 | 实验 | 先打开 | 看什么 | 不能据此推出什么 |", "|---|---|---|---|---|"]
    lines += ["|" + "|".join(row) + "|" for row in rows]
    lines += ["", "## Phase semantics", "", *[f"- `{k}`：{v}" for k, v in PHASE_SEMANTICS.items()], ""]
    return "\n".join(lines)


def build_schematic_index(topology: dict[str, Any], entries: dict[str, dict[str, Any]], *, head: str = HEAD) -> str:
    lines = ["# CIRCUIT SCHEMATIC INDEX", "", f"基线 HEAD：`{head}`。本页将论文级电路图、实验注释图和连接调试图分开。", ""]
    for topo in topology["topologies"]:
        lines += [f"## {topo['title_cn']}", "", f"**Topology ID**：`{topo['topology_id']}`", "",
                  f"**状态**：`{topo['status']}`；signature=`{topo['topology_signature'][:16]}`…", "",
                  f"- 【论文级电路图】 {markdown_link(topo.get('publication_schematic'), 'schematic.svg')}",
                  f"- 【实验注释电路图】 {markdown_link(topo.get('annotated_schematic'), 'schematic-annotated.svg')}",
                  f"- 【网表连接调试图】 {markdown_link(topo.get('connectivity_debug'), 'connectivity-debug.svg')}",
                  f"- representative deck：`{topo.get('representative_deck') or '未记录'}`", "",
                  "共享实验：", *[f"- `{x}`" for x in topo.get("shared_by_experiments", [])], "", "---", ""]
    lines += ["## 结构图边界", "", "只有存在 semantic + geometric validation 的 `schematic.svg` 才列为论文级电路图；Graphviz `topology.svg` 只作 debug/provenance，不作为默认结构图入口。"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--head", default=HEAD, help="recorded parent HEAD; default is the task baseline")
    args = ap.parse_args()
    recorded_head = args.head
    entries = curated_entries()
    # Add every remaining Exploration as an explicit manifest entry.  Its
    # alignment status is conservative: the generated alignment overview is a
    # complete case view, while a missing report/topology remains visible.
    for path in sorted((ROOT / "test/exploration").iterdir()):
        exp_key = path.relative_to(ROOT).as_posix()
        if not path.is_dir() or exp_key in entries:
            continue
        cases = raw_cases(path)
        report = report_for(path)
        if not cases and not report:
            continue
        plots = common_plot(path, cases)
        entries[exp_key] = key_entry(
            exp_key, title=path.name,
            question="见该 Exploration 的 preregistration / report。",
            result="正式结论见 report；索引不新增科学解释。",
            status=("NO_WAVEFORM_VISUALIZATION_REQUIRED" if not cases else infer_verdict(path)), report=report, claim_type="generic_exploration",
            topology_id=f"TOPOLOGY_{hashlib.sha1(path.name.encode()).hexdigest()[:10]}", cases=cases,
            plots=plots, notes="自动审计条目；未在本轮改写 scientific verdict。")
    apply_experiment_narratives(entries)
    # Reinsert the mapping in explicit scientific execution order.  This order
    # drives both Markdown and HTML; directory enumeration is never a route
    # authority.
    entries = {entry["experiment_id"]: entry for entry in ordered_entries(entries)}
    # Use the recorded baseline supplied by the caller, not the current
    # post-generation HEAD, so provenance stays explicit.
    # A comparison experiment may contain several real electrical boundaries.
    # Materialize each declared variant for the topology manifest without
    # pretending that one representative deck describes the whole matrix.
    topology_entries = dict(entries)
    for exp_id, entry in entries.items():
        for variant in entry.get("topology_variants", []):
            variant_entry = dict(entry)
            variant_entry.update({
                "topology_id": variant["topology_id"],
                "title_cn": variant.get("title_cn", variant["topology_id"]),
                "_shared_experiment": exp_id,
                "_topology_experiment": exp_id,
                "_representative_deck": variant.get("representative_deck"),
                "_connectivity_debug": variant.get("connectivity_debug"),
            })
            topology_entries[f"{exp_id}::{variant['topology_id']}"] = variant_entry
    topology = build_topology_manifest(topology_entries)
    topology["parent_head"] = recorded_head
    topology_map = {t["topology_id"]: t for t in topology["topologies"]}
    for entry in entries.values():
        topo = topology_map.get(entry.get("topology_id"))
        if topo:
            entry["topology_signature"] = topo.get("topology_signature")
            entry["topology_status"] = topo.get("status")
            entry["topology"] = {
                "topology_id": topo.get("topology_id"),
                "topology_signature": topo.get("topology_signature"),
                "publication_schematic": topo.get("publication_schematic"),
                "annotated_schematic": topo.get("annotated_schematic"),
                "connectivity_debug": topo.get("connectivity_debug"),
            }
        if entry.get("topology_variants"):
            resolved_variants = []
            for variant in entry["topology_variants"]:
                vt = topology_map.get(variant["topology_id"])
                resolved = dict(variant)
                if vt:
                    resolved.update({
                        "topology_signature": vt.get("topology_signature"),
                        "publication_schematic": vt.get("publication_schematic"),
                        "annotated_schematic": vt.get("annotated_schematic"),
                        "connectivity_debug": vt.get("connectivity_debug"),
                        "status": vt.get("status"),
                    })
                resolved_variants.append(resolved)
            entry["topology_variants"] = resolved_variants
        entry["required_signals"] = signals_from_cases(entry.get("required_cases", [])) or entry.get("required_signals", [])
        groups = {"core_result": [], "key_comparison": [], "case_plots": [], "controls": [], "source_references": []}
        for plot in entry.get("plots", []):
            role = plot.get("role")
            if role == "COMPARISON":
                groups["key_comparison"].append(plot.get("path"))
            elif role in {"SOURCE_REFERENCE", "HISTORICAL_REFERENCE", "SUPERSEDED_REFERENCE"}:
                groups["source_references"].append(plot.get("path"))
            elif role in {"POSITIVE_CONTROL", "NEGATIVE_CONTROL", "ZERO_CONTROL"}:
                groups["controls"].append(plot.get("path"))
            else:
                groups["case_plots"].append(plot.get("path"))
        groups["core_result"] = [p.get("path") for p in entry.get("plots", []) if p.get("role") in {"RESULT", "COMPARISON"}]
        entry["plot_groups"] = groups
    manifest = {
        "schema_version": "2.0",
        "manifest_id": "PROJECT_VISUALIZATION_INDEX_ALIGNMENT_V2",
        "parent_head": recorded_head,
        "authority_order": ["raw", "accepted_analysis_report", "visualization", "index"],
        "phase_semantics": PHASE_SEMANTICS,
        "experiments": ordered_entries(entries),
    }
    MANIFEST_PATH.write_text(yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False), encoding="utf-8")
    TOPOLOGY_PATH.write_text(yaml.safe_dump(topology, allow_unicode=True, sort_keys=False), encoding="utf-8")
    flow_md = render_index(entries, flow=True, head=recorded_head)
    viz_md = render_index(entries, flow=False, head=recorded_head)
    (ROOT / "docs/EXPLORATION_FLOW_INDEX.md").write_text(flow_md, encoding="utf-8")
    (ROOT / "docs/VISUALIZATION_INDEX.md").write_text(viz_md, encoding="utf-8")
    entry_list = ordered_entries(entries)
    (ROOT / "docs/EXPLORATION_FLOW_INDEX.html").write_text(render_rich_index(entry_list, topology, title="BVM→QB/JTL receiver Exploration 流程总索引", flow=True, head=recorded_head), encoding="utf-8")
    (ROOT / "docs/VISUALIZATION_INDEX.html").write_text(render_rich_index(entry_list, topology, title="BVM→QB/JTL receiver 可视化结果索引", flow=False, head=recorded_head), encoding="utf-8")
    (ROOT / "docs/VISUALIZATION_READING_GUIDE.md").write_text(build_reading_guide(entries, head=recorded_head), encoding="utf-8")
    (ROOT / "docs/CIRCUIT_SCHEMATIC_INDEX.md").write_text(build_schematic_index(topology, entries, head=recorded_head), encoding="utf-8")
    (ROOT / "docs/CIRCUIT_SCHEMATIC_INDEX.html").write_text(render_topology_index(topology, title="BVM→QB/JTL 电路结构导航", head=recorded_head), encoding="utf-8")
    (ROOT / "docs/VISUALIZATION_ALIGNMENT_AUDIT.md").write_text(build_alignment_audit(manifest, topology), encoding="utf-8")
    print(f"experiments={len(entries)} topologies={len(topology['topologies'])}")


if __name__ == "__main__":
    main()
