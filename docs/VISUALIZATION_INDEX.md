# BVM→QB/JTL receiver 可视化索引

更新时间：2026-08-24；可视化 checkpoint parent HEAD：`960f3948f48017747b79d0a7c37a8b0dd302c913`。

本索引只导航已经存在的 raw 与正式报告，不新增科学结论。所有 HTML 都由仓库现有 `scripts/josim-plot2.py` 的经典 dark/`sep_comb` 约定生成，或使用同一 dark Plotly layout 生成 comparison；`P(...)` 显示为 `rad/2π` turns。phase turns、voltage peak 和 derivative activity 都不自动等于 SFQ event。正式 event/Gate verdict 以链接的 report 为准。

HTML 使用 Plotly 3.1.0 CDN；首次打开需要网络加载 Plotly runtime。

## P0：核心证据与 JTL/load boundary

| 重要问题 / 该看什么 | 已接受结论（不由图形重新判定） | 实验与入口 | 主要曲线 / 时间范围 |
|---|---|---|---|
| scaled QB 的输入窗口在哪里？看四个 ideal input level 的 BJs→BJL1→BJL2 和 OUT | 0 µA `ZERO_EVENT`；45 µA 无 complete event；68.4 µA standalone exactly-one reference；90 µA multi-event。 | [QB-Q0 scaled comparison](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-comparison.html)；[单点目录说明](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/README.md) | `P(BJS|XBQ)`, `P(BJL1|XBQ)`, `P(BJL2|XBQ)`, `V(OUT)`；完整 raw window / 原始 pulse |
| paper-original QB 与 scaled QB 有何差异？ | paper-original 68.4/90 µA 不建立 complete BJL2 event；它是 provenance comparison，不是 scaled Q0 threshold。 | [paper reference comparison](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/paper-reference-comparison.html) | BJL1/BJL2 phase、OUT；完整 raw window |
| 10 Ω、OPEN、JTL-only 怎样改变真实 Q0 event？ | load-boundary matrix 只支持 fixture-bounded local/load conclusions；不要把边界结果外推为 universal interface rule。 | [Q0 boundary comparison](../test/exploration/qb-load-boundary-matrix-20260824/plots/q0-boundary-comparison.html)；[Q5 OPEN/JTL-only](../test/exploration/qb-load-boundary-matrix-20260824/plots/q5-open-vs-jtl-read1.html) | BJL2 phase、OUT、L0；JTL fixtures另有四颗 JTL phase；完整 raw window |
| parallel QB→JTL 哪一级丢失？ | M1 `FIRST_STAGE_ONLY`；M3 local Q0 event preserved but JTL subthreshold；M2/M4/M5 boundary下 local event丢失。 | [M1](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M1-ideal-replay.html)、[M3](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M3-rseries10.html)、[matrix QB comparison](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-qb-phase-comparison.html)、[JTL comparison](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-jtl-phase-comparison.html) | QB BJs/BJL1/BJL2；四颗 JTL JJ；pulse-by-pulse |
| 原/反极性 replay 是否进入同一 transport chain？ | 原极性与反极性必须分开按 strict local 和 settled transport 阅读；不能以 phase range alone 判定。 | [original](../test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/original.html)、[reverse](../test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/reverse.html)、[对照](../test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/original-vs-reverse.html) | 四颗 JTL phase、input/mid/output voltage；pulse-5 full window |
| JTL methodology 的 strict local 与 settled well 是否一致？ | R11 positive control 在注册方法内为四-stage settled transport reference；M5 historical exactly-one interpretation 已 supersede，不能混用。 | [methodology sources](../test/exploration/jtl-transport-gate-v1-methodology-20260824/plots/README.md)；[R11](../test/exploration/jtl-transport-gate-v1-methodology-20260824/plots/R11-positive-control.html)；[M5-PC](../test/exploration/jtl-transport-gate-v1-methodology-20260824/plots/M5-positive-control.html) | 四颗 JTL phase/voltage；strict local 与 pre/post well 对应注册窗口 |
| 数值 timestep 是否闭合 Gate？ | 当前正式 disposition 保持 `JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE`；pulse5-original window robustness 未闭合。 | [R11 timestep](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/r11-timestep-comparison.html)、[original timestep](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-timestep-comparison.html)、[reverse timestep](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-reverse-timestep-comparison.html) | dt `0.025/0.0125/0.00625 ps`；注册 pre/post window robustness |
| JTL load 怎样改变 QB trajectory？ | accepted bounded mechanism classification：`MIXED_DYNAMIC_LOADING`。 | [back-action comparison](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/backaction_compare.html)；[README/window说明](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/README.md) | BJL2、L2、L0、OUT；重点 `208–210`、`210–217.1`、`217.1–259 ps` |

## P1：PAPER-SL / QB internal route

| 重要问题 / 该看什么 | 已接受结论 | 实验与入口 | 主要曲线 / 时间范围 |
|---|---|---|---|
| paper-JSL replay 对 frozen scaled QB 是否足够？ | `PAPER-SL_QB_SUBTHRESHOLD`，但 read1 near-threshold：BJL1/BJL2 接近 1 turn，read0/control 分离。 | [PAPER-SL-Q1 comparison](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/comparison.html) | BJs/BJL1/BJL2 phase、V/I、OUT；原始 replay full window |
| central bias 37.5/40 µA 能否闭合？ | Q2 bias bracket 仍未建立 selective complete output event；不要把 bias points 解释成连续 threshold。 | [37.5 µA](../test/exploration/paper-sl-q2-20260824/plots/37p5u/comparison.html)、[40 µA](../test/exploration/paper-sl-q2-20260824/plots/40u/comparison.html) | BJs/BJL1/BJL2、input/bias/loop currents；原始 replay window |
| Q3-PRE 的 BJs→BJL1 transfer 受什么限制？ | 这是 source-linked analysis-only checkpoint；正式 routing/timing 结论以 report 为准。 | [Q3-PRE comparison](../test/exploration/paper-sl-q3-pre-20260824/plots/comparison.html) | Q0/Q1/Q2 source-linked BJs/BJL1/BJL2；各自原始时间基准 |
| L1 proximal routing 有多大？ | Q3 是 weak causal routing gain，未闭合 local event。 | [Q3 comparison](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/l1-4p5/comparison.html) | BJs/BJL1/BJL2、OUT、loop currents；注册主 comparison window |
| L2 placement 是共同增益还是方向性 effect？ | Q4 `Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT`；BJL2 total range 不等于 event。 | [Q4 comparison](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/plots/q4-l1-3p91-l2-4p50/comparison.html) | BJL1/BJL2 phase、OUT、loop currents；Q4 registered window |
| L1×L2 是否产生 nonlinear interaction？ | Q5 `Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT`；未见正的 nonlinear BJL2 interaction。 | [Q5 comparison](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q5-l1-4p50-l2-4p50/comparison.html) | BJs/BJL1/BJL2、OUT、loop currents；Q2–Q5 registered comparison window |
| frozen Q5 输出能否直接驱动标准 JTL？ | `NO_JTL_TRIGGER`；不得把 coupled phase/voltage activity叫作 propagated event。 | [Q6 comparison](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q6-q5-to-two-cell-jtl/comparison.html) | QB BJL2 与四颗 JTL JJ；canonical matched full window |

## P2：路线变化的历史节点

这些图用于组会中快速理解路线如何从 receiver front-end 走向 QB/DCSFQ/JTL；它们不替代各自 analysis report，也不把被否定的 instance 升级为整个 architecture family 的 universal impossibility。

| 路线节点 / 该看什么 | 正式结论 | 可视化入口 | 主要曲线 / 关注窗口 |
|---|---|---|---|
| R0b：SL trigger discrimination | accepted R0b complete-trigger/discrimination baseline。 | [R0b comparison](../test/exploration/bvm-sfq-receiver-r0b-20260819/plots/comparison.html) | B_TRIG、SL/N6、JM/JS；完整 READ/control window |
| R1a：passive series pickup | passive state-dependent extraction established；不是 downstream SFQ。 | [R1a comparison](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/plots/comparison.html) | B_TRIG、L_TX/L_SEC、N_SEC、SL/N6；完整 matched window |
| R2a：secondary direct activation | 代表性 K=.80 fixture；正式 R2 evidence 仍在 R2 report。 | [R2a K=.80 comparison](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/k080-representative/comparison.html) | B_TRIG/B_OUT、secondary、damping；完整 matched window |
| R11a：canonical SL→standard JTL | `NO_JTL_TRIGGER`；positive control 与 BVM direct test分开。 | [R11a BVM comparison](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/comparison.html)、[positive control](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/positive-control.html) | 四颗 JTL JJ、SL/N6、JS；full read window |
| R12a：historical DCSFQ re-audit | 300 µA controlled point 可建立 local B3 reference；canonical cascade仍 subthreshold。 | [Phase A](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/phase-a-comparison.html)、[Phase B](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/phase-b-comparison.html) | DCSFQ B1/B2/B3、两-cell JTL；controlled/full matched windows |
| R13a：理想 rectification/hold requirements | `TEMPORAL_CONDITIONING_INSUFFICIENT`；ideal transformation 不是 physical implementation。 | [R13 raw replay](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-replay/comparison.html) | B1/B2/B3、replay voltage、loop currents；raw replay full window |
| R15b：AFQ-3 magnetic correction | `ACTIVE_STAGE_NO_TRIGGER`，并保留 bounded extra back-action disposition。 | [R15b comparison](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/plots/comparison.html) | B_DET/B_SET/B_Q/B_OUT、DCS branch、BVM guards；完整 matched window |

## P0 anchor：canonical BVM internal readout

canonical BVM 的既有交互图仍在：[logical1 canonical READ](../test/exploration/bvm-internal-readout-20260819/plots/logical1-canonical-read.html)、[logical0 canonical READ](../test/exploration/bvm-internal-readout-20260819/plots/logical0-canonical-read.html)、[rewrite 0101](../test/exploration/bvm-internal-readout-20260819/plots/rewrite-read-0101.html)、[rewrite 1010](../test/exploration/bvm-internal-readout-20260819/plots/rewrite-read-1010.html)。

这些图用于 source/storage anchor：JS1/JS2、N6、SL、SL branch currents 与 JM/JS guards。README 已明确 phase turns ≠ SFQ count；canonical BVM topology 与 frozen evidence 没有在本 checkpoint 中修改。

## 读图规则

1. 先看 matched control/read0，再看 read1；不要只看 voltage peak。
2. 对任何 event 讨论，回到对应 report 的 continuous monotonic same-JJ phase 与 same-segment direct voltage area；full-window settled well 是另一层证据。
3. `P(...)` 的 y 轴是 `rad/2π` turns；不是 event 数、不是 fluxoid count、也不是 downstream SFQ delivery。
4. P2 的代表性节点可能直接消费父实验 raw；README 与 report 会标明 provenance。图形 checkpoint 不改变 raw、formal verdict 或 frozen circuits。
