# EXPLORATION FLOW INDEX V2

生成基线 HEAD：`e41d05fcf9aabd26890805bc4f2a12622b24eed7`。

本页由 `docs/VISUALIZATION_ALIGNMENT_MANIFEST.yaml` 生成，展示科研路线；结果图、controls、source/reference 和电路入口均保持角色区分。

## 阅读约定

- `continuous_absolute`：原始 JoSIM P(...) 连续轨迹的 φ/2π（turn），不等于 SFQ 计数。
- source/reference/historical 图不能作为 current result 的核心证据。
- 论文级 schematic、annotated schematic、connectivity debug graph 分开列出。

## QB-Q0：低 Ic QB standalone 量化窗口

**实验 ID**：`test/exploration/qb-q0-standalone-current-quantized-event-20260824`

**做了什么**：低 Ic scaled QB 在理想输入下的 zero / subthreshold / exactly-one / multi-event 窗口是什么？

**关键结果**：scaled 0=ZERO_EVENT；45=NO_COMPLETE_EVENT；68.4=EXACTLY_ONE；90=MULTI_EVENT。paper-original 68.4/90 均无完整 BJL2 event。

**当前状态**：`ACCEPTED_STANDALONE_REFERENCE` / alignment=`ALIGNED`

**结论边界**：论文参数 QB 对照不得成为 scaled-Q0 exactly-one 的 primary evidence。

**推荐先看**：
- 【关键对比图】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-comparison.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-comparison.html)
- 【单工况/结果图】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-68p4uA.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-68p4uA.html)
- 【单工况/结果图】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-90uA.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-90uA.html)
- 【单工况/结果图】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-45uA.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-45uA.html)
- 【零输入对照】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-0uA.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/scaled-0uA.html)
- 【历史参考】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/paper-reference-comparison.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/paper-reference-comparison.html)
- 【历史参考】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/68p4-paper-reference.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/68p4-paper-reference.html)
- 【历史参考】 [test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/90-paper-reference.html](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/plots/90-paper-reference.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/connectivity-debug.svg)

**正式报告**：[test/exploration/qb-q0-standalone-current-quantized-event-20260824/analysis/QB_Q0_REPORT.md](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/analysis/QB_Q0_REPORT.md)

---

## PAPER-SL-Q1：paper-JSL replay → frozen scaled QB

**实验 ID**：`test/exploration/paper-sl-q1-20260824`

**做了什么**：paper-JSL waveform replay 是否足以驱动 frozen scaled QB？

**关键结果**：read1 > read0 >> controls，但 BJL2 未达到 exactly-one；Q0 68.4 µA 仅作为 positive control。

**当前状态**：`PAPER_JSL_QB_SUBTHRESHOLD` / alignment=`ALIGNED`

**结论边界**：source waveform 只能是 SOURCE_REFERENCE；核心图必须展示 QB response。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/comparison.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j1-logical1-read.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j1-logical1-read.html)
- 【负向对照】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j0-logical0-read.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j0-logical0-read.html)
- 【零输入对照】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j1-logical1-read0-control.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j1-logical1-read0-control.html)
- 【零输入对照】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j0-logical0-read0-control.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/paper-j0-logical0-read0-control.html)
- 【正向对照】 [test/exploration/paper-sl-q1-20260824/plots/qb-replay/q0-68p4u-positive-control.html](../test/exploration/paper-sl-q1-20260824/plots/qb-replay/q0-68p4u-positive-control.html)
- 【源波形参考】 [test/exploration/paper-sl-q1-20260824/plots/paper-sl-l0-classic/logical1-read.html](../test/exploration/paper-sl-q1-20260824/plots/paper-sl-l0-classic/logical1-read.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/topology.svg)

**正式报告**：[test/exploration/paper-sl-q1-20260824/analysis/REPORT.md](../test/exploration/paper-sl-q1-20260824/analysis/REPORT.md)

---

## PAPER-SL-Q2：central-bias bracket

**实验 ID**：`test/exploration/paper-sl-q2-20260824`

**做了什么**：37.5 与 40 µA central bias 是否关闭 frozen paper-JSL replay 的 BJL1/BJL2 event？

**关键结果**：BIAS_BRANCH_SUBTHRESHOLD；两点均保持 bounded，未建立 complete BJL1/BJL2 event。

**当前状态**：`BIAS_BRANCH_SUBTHRESHOLD` / alignment=`ALIGNED`

**结论边界**：comparison 必须同时覆盖 37.5 和 40 µA。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q2-20260824/plots/bias-37p5-vs-40-comparison.html](../test/exploration/paper-sl-q2-20260824/plots/bias-37p5-vs-40-comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q2-20260824/plots/37p5u/comparison.html](../test/exploration/paper-sl-q2-20260824/plots/37p5u/comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q2-20260824/plots/40u/comparison.html](../test/exploration/paper-sl-q2-20260824/plots/40u/comparison.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/topology.svg)

**正式报告**：[test/exploration/paper-sl-q2-20260824/analysis/REPORT.md](../test/exploration/paper-sl-q2-20260824/analysis/REPORT.md)

---

## Q3：L1=4.50,L2=3.91

**实验 ID**：`test/exploration/paper-sl-q3-l1-routing-closure-20260824`

**做了什么**：L1/L2 placement 如何影响 QB routing 与 BJL2 response？

**关键结果**：ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED

**当前状态**：`ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED` / alignment=`ALIGNED`

**结论边界**：Q2/Q3/Q4/Q5 factorial comparison 是正式 comparison claim 的核心入口。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/topology.svg)

**正式报告**：[test/exploration/paper-sl-q3-l1-routing-closure-20260824/analysis/REPORT.md](../test/exploration/paper-sl-q3-l1-routing-closure-20260824/analysis/REPORT.md)

---

## Q4：L1=3.91,L2=4.50

**实验 ID**：`test/exploration/paper-sl-q4-l1-l2-placement-20260824`

**做了什么**：L1/L2 placement 如何影响 QB routing 与 BJL2 response？

**关键结果**：Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT

**当前状态**：`Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT` / alignment=`ALIGNED`

**结论边界**：Q2/Q3/Q4/Q5 factorial comparison 是正式 comparison claim 的核心入口。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q4-l1-l2-placement-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/topology.svg)

**正式报告**：[test/exploration/paper-sl-q4-l1-l2-placement-20260824/REPORT.md](../test/exploration/paper-sl-q4-l1-l2-placement-20260824/REPORT.md)

---

## Q5：L1=4.50,L2=4.50

**实验 ID**：`test/exploration/paper-sl-q5-l1-l2-factorial-20260824`

**做了什么**：L1/L2 placement 如何影响 QB routing 与 BJL2 response？

**关键结果**：Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT

**当前状态**：`Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT` / alignment=`ALIGNED`

**结论边界**：Q2/Q3/Q4/Q5 factorial comparison 是正式 comparison claim 的核心入口。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/q2-q3-q4-q5-factorial-comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/topology.svg)

**正式报告**：[test/exploration/paper-sl-q5-l1-l2-factorial-20260824/REPORT.md](../test/exploration/paper-sl-q5-l1-l2-factorial-20260824/REPORT.md)

---

## QB load-boundary matrix：Q0 output boundary

**实验 ID**：`test/exploration/qb-load-boundary-matrix-20260824`

**做了什么**：同一 Q0 source 在 OPEN、10Ω、JTL-only、10Ω||JTL 下如何改变 local quantization 与 transport？

**关键结果**：Q0+10Ω exactly-one；OPEN multi-event；JTL-only 与 10Ω||JTL event lost；机制报告为 MIXED_DYNAMIC_LOADING。

**当前状态**：`MIXED_DYNAMIC_LOADING` / alignment=`ALIGNED`

**结论边界**：Q5 OPEN/JTL 为独立 secondary comparison，不替代 Q0 four-boundary core。每个 output boundary 都保留独立 topology provenance。

**推荐先看**：
- 【关键对比图】 [test/exploration/qb-load-boundary-matrix-20260824/plots/q0-complete-boundary-comparison.html](../test/exploration/qb-load-boundary-matrix-20260824/plots/q0-complete-boundary-comparison.html)
- 【关键对比图】 [test/exploration/qb-load-boundary-matrix-20260824/plots/q5-open-vs-jtl-read1.html](../test/exploration/qb-load-boundary-matrix-20260824/plots/q5-open-vs-jtl-read1.html)
- 【单工况/结果图】 [test/exploration/qb-load-boundary-matrix-20260824/plots/alignment-overview.html](../test/exploration/qb-load-boundary-matrix-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/connectivity-debug.svg)

**真实 topology 变体**：
- `低 Ic QB → OPEN output boundary`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/topology.svg)
- `低 Ic QB → standard JTL direct`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/scaled-iin-68p4u/topology.svg)
- `低 Ic QB + 10Ω || standard JTL`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/scaled-iin-68p4u-2/topology.svg)

**正式报告**：[test/exploration/qb-load-boundary-matrix-20260824/analysis/REPORT.md](../test/exploration/qb-load-boundary-matrix-20260824/analysis/REPORT.md)

---

## M1–M5：QB→JTL interface mechanism matrix

**实验 ID**：`test/exploration/parallel-qb-jtl-interface-mechanism-20260824`

**做了什么**：不同输出接口如何影响 QB local event 与 JTL transport？

**关键结果**：M5 positive-control 的历史 exactly-one 解释已废止；保留 full matrix 与 strict local/transport distinction。

**当前状态**：`BOUNDED_INTERFACE_MATRIX` / alignment=`ALIGNED`

**结论边界**：M5-PC 标记 MULTI_WELL_TRANSPORT_NOT_ONE_TURN；历史 exactly-one interpretation 不作为 current claim。每个接口变体均绑定自己的 representative deck。

**推荐先看**：
- 【关键对比图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-qb-phase-comparison.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-qb-phase-comparison.html)
- 【关键对比图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-jtl-phase-comparison.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/interface-jtl-phase-comparison.html)
- 【单工况/结果图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M1-ideal-replay.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M1-ideal-replay.html)
- 【单工况/结果图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M3-rseries10.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M3-rseries10.html)
- 【历史参考】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M5-positive-control.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/M5-positive-control.html)
- 【单工况/结果图】 [test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/alignment-overview.html](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-3/topology.svg)

**真实 topology 变体**：
- `Q0 recorded V(OUT) ideal replay → standard JTL`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main/topology.svg)
- `低 Ic QB → RISO=10Ω → standard JTL`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-2/topology.svg)
- `低 Ic QB → LISO=10pH → standard JTL`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-4/topology.svg)
- `低 Ic QB → scaled JTL`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-5/topology.svg)

**正式报告**：[test/exploration/parallel-qb-jtl-interface-mechanism-20260824/analysis-v2/REPORT.md](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/analysis-v2/REPORT.md)

---

## JTL transport methodology

**实验 ID**：`test/exploration/jtl-transport-gate-v1-methodology-20260824`

**做了什么**：标准正控、Q0 pulse5 原极性与反极性的 transport evidence 是否一致？

**关键结果**：保留 strict replay distinction；numerical freeze 当前为 JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE。

**当前状态**：`JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE` / alignment=`ALIGNED`

**结论边界**：不把 post-window robustness 未完全通过误写成 timestep classification 不稳定。

**推荐先看**：
- 【正向对照】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/r11-timestep-comparison.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/r11-timestep-comparison.html)
- 【单工况/结果图】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-timestep-comparison.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-original-timestep-comparison.html)
- 【负向对照】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-reverse-timestep-comparison.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/pulse5-reverse-timestep-comparison.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-v1-methodology-20260824/topology/topology.svg)

**正式报告**：[test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/analysis/REPORT.md](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/analysis/REPORT.md)

---

## QB→JTL load back-action causal audit

**实验 ID**：`test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824`

**做了什么**：负载改变 Q0 BJL2 trajectory 的主要阶段是 barrier crossing 前、crossing 中还是 retrap？

**关键结果**：MIXED_DYNAMIC_LOADING；核心时间窗 208–210、210–217.1、217.1–259 ps。

**当前状态**：`MIXED_DYNAMIC_LOADING` / alignment=`ALIGNED`

**结论边界**：不能把非线性接口压缩为单一 scalar impedance，除非 report 证据支持；比较图并列引用以下真实 interface topology。

**推荐先看**：
- 【关键对比图】 [test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/backaction_compare.html](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/plots/backaction_compare.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/connectivity-debug.svg)

**真实 topology 变体**：
- `低 Ic QB → OPEN output boundary`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/topology.svg)
- `低 Ic QB → standard JTL direct`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/scaled-iin-68p4u/topology.svg)
- `低 Ic QB + 10Ω || standard JTL`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/scaled-iin-68p4u-2/topology.svg)
- `低 Ic QB → series 10Ω → standard JTL`：
  - 【论文级电路图】 `schematic.svg（未生成）`
  - 【实验注释电路图】 `schematic-annotated.svg（未生成）`
  - 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-3/topology.svg)

**正式报告**：[test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/analysis/REPORT.md](../test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824/analysis/REPORT.md)

---

## R13-A：temporal conditioning requirements

**实验 ID**：`test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823`

**做了什么**：极性整流、20 ps hold 或两者是否足以触发 frozen DCSFQ？

**关键结果**：TEMPORAL_CONDITIONING_INSUFFICIENT。raw/C1/C2/C3 均未完成 selective DCSFQ event。

**当前状态**：`TEMPORAL_CONDITIONING_INSUFFICIENT` / alignment=`ALIGNED`

**结论边界**：理想 waveform transformation 的结果只建立 requirements boundary，不是 physical receiver implementation。

**推荐先看**：
- 【关键对比图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-vs-c1-vs-c2-vs-c3.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-vs-c1-vs-c2-vs-c3.html)
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-replay/comparison.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/raw-replay/comparison.html)
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c1-rectify/comparison.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c1-rectify/comparison.html)
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c2-hold20/comparison.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c2-hold20/comparison.html)
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c3-rectify-hold20/comparison.html](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/plots/c3-rectify-hold20/comparison.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/analysis/R13A_REPORT.md](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/analysis/R13A_REPORT.md)

---

## PAPER-SL-Q6：Q5 → standard JTL compatibility

**实验 ID**：`test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824`

**做了什么**：Q5 near-threshold QB output 接入 standard JTL 后是否产生 selective regenerative event？

**关键结果**：NO_JTL_TRIGGER；Q5 standalone 对照必须与 Q6 coupled 并列。

**当前状态**：`NO_JTL_TRIGGER` / alignment=`ALIGNED`

**结论边界**：正式结论以 report 为准；可视化不改变 scientific verdict。

**推荐先看**：
- 【关键对比图】 [test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q5-standalone-vs-q6-coupled.html](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q5-standalone-vs-q6-coupled.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q6-q5-to-two-cell-jtl/comparison.html](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/q6-q5-to-two-cell-jtl/comparison.html)
- 【单工况/结果图】 [test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/topology/topology.svg)

**正式报告**：[test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/REPORT.md](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/REPORT.md)

---

## QB-Q1：physical BVM → frozen scaled QB

**实验 ID**：`test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824`

**做了什么**：canonical BVM 直接驱动 frozen scaled QB 是否保持 source guard 并量化？

**关键结果**：QB_SOURCE_BACKACTION_FAILURE；次级 QB_BVM_SUBTHRESHOLD。

**当前状态**：`QB_SOURCE_BACKACTION_FAILURE` / alignment=`ALIGNED`

**结论边界**：重要因果节点；overview 只用于导航，正式结论以 report 为准。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/plots/alignment-overview.html](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/topology/topology.svg)

**正式报告**：[test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/SUMMARY.md](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/SUMMARY.md)

---

## QB-Q2A：source-decoupled waveform replay

**实验 ID**：`test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824`

**做了什么**：source isolation alone 是否足以让 frozen QB 量化？

**关键结果**：QB_DYNAMIC_WINDOW_MISMATCH。

**当前状态**：`QB_DYNAMIC_WINDOW_MISMATCH` / alignment=`ALIGNED`

**结论边界**：重要因果节点；overview 只用于导航，正式结论以 report 为准。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/plots/alignment-overview.html](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/topology/topology.svg)

**正式报告**：[test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/SUMMARY.md](../test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824/SUMMARY.md)

---

## QB-Q2B：central-bias bracket

**实验 ID**：`test/exploration/qb-q2b-central-bias-bracketing-20260824`

**做了什么**：central bias bracket 是否建立 read1-only BJL1 event？

**关键结果**：BIAS_BRACKET_NO_BJL1_EVENT。

**当前状态**：`BIAS_BRACKET_NO_BJL1_EVENT` / alignment=`ALIGNED`

**结论边界**：重要因果节点；overview 只用于导航，正式结论以 report 为准。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/qb-q2b-central-bias-bracketing-20260824/plots/alignment-overview.html](../test/exploration/qb-q2b-central-bias-bracketing-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/topology/topology.svg)

**正式报告**：[test/exploration/qb-q2b-central-bias-bracketing-20260824/SUMMARY.md](../test/exploration/qb-q2b-central-bias-bracketing-20260824/SUMMARY.md)

---

## Canonical BVM：storage/readout cell

**实验 ID**：`test/exploration/bvm-internal-readout-20260819`

**做了什么**：canonical BVM 的 S-Loop、R-Loop、read timing 与 SL output 的真实结构和 waveform 是什么？

**关键结果**：canonical BVM source/read behavior frozen；本页只做结构与已有 read evidence 导航。

**当前状态**：`ACCEPTED_CANONICAL_SOURCE` / alignment=`ALIGNED`

**结论边界**：publication schematic 已通过 semantic + geometric validation；不把 schematic 当作 receiver verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-internal-readout-20260819/plots/alignment-overview.html](../test/exploration/bvm-internal-readout-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-internal-readout-20260819/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-internal-readout-20260819/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-internal-readout-20260819/topology/connectivity-debug.svg)

**正式报告**：[test/exploration/bvm-internal-readout-20260819/summary.md](../test/exploration/bvm-internal-readout-20260819/summary.md)

---

## bvm-sfq-receiver-native-qb-20260822

**实验 ID**：`test/exploration/bvm-sfq-receiver-native-qb-20260822`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`BACK_ACTION_FAILURE` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-native-qb-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-native-qb-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-native-qb-20260822/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-native-qb-20260822/analysis/NATIVE_QB_REPORT.md](../test/exploration/bvm-sfq-receiver-native-qb-20260822/analysis/NATIVE_QB_REPORT.md)

---

## bvm-sfq-receiver-r0-20260819

**实验 ID**：`test/exploration/bvm-sfq-receiver-r0-20260819`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r0-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r0-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r0-20260819/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r0-20260819/analysis/R0_REPORT.md](../test/exploration/bvm-sfq-receiver-r0-20260819/analysis/R0_REPORT.md)

---

## bvm-sfq-receiver-r0b-20260819

**实验 ID**：`test/exploration/bvm-sfq-receiver-r0b-20260819`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r0b-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r0b-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r0b-20260819/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r0b-20260819/analysis/R0B_REPORT.md](../test/exploration/bvm-sfq-receiver-r0b-20260819/analysis/R0B_REPORT.md)

---

## bvm-sfq-receiver-r1-oneshot-20260819

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1-oneshot-20260819`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/analysis/R1_REPORT.md](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/analysis/R1_REPORT.md)

---

## bvm-sfq-receiver-r10a-local-bjl2-bias-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/analysis/R10A_REPORT.md](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/analysis/R10A_REPORT.md)

---

## bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`NO_JTL_TRIGGER` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/analysis/R11A_REPORT.md](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/analysis/R11A_REPORT.md)

---

## bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`DCSFQ_BVM_NO_TRIGGER` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/analysis/R12A_REPORT.md](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/analysis/R12A_REPORT.md)

---

## bvm-sfq-receiver-r14a-dcsfq-detector-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`NO_WAVEFORM_VISUALIZATION_REQUIRED` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/SUMMARY.md)

---

## bvm-sfq-receiver-r15a-afq3-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r15a-afq3-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`NO_WAVEFORM_VISUALIZATION_REQUIRED` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/SUMMARY.md)

---

## bvm-sfq-receiver-r15b-magnetic-correction-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`ACTIVE_STAGE_NO_TRIGGER` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/SUMMARY.md)

---

## bvm-sfq-receiver-r15c-jset-causal-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`CAUSAL_NEAR_THRESHOLD` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/SUMMARY.md)

---

## bvm-sfq-receiver-r15d-jq-compressor-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`CAUSAL_NEAR_THRESHOLD` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/SUMMARY.md](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/SUMMARY.md)

---

## bvm-sfq-receiver-r1a-transfer-20260819

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1a-transfer-20260819`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/analysis/R1A_REPORT.md](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/analysis/R1A_REPORT.md)

---

## bvm-sfq-receiver-r1b-area008-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1b-area008-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1b-area008-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1b-area008-20260821/analysis/R1B_AREA008_REPORT.md](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/analysis/R1B_AREA008_REPORT.md)

---

## bvm-sfq-receiver-r1b-differential-output-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/analysis/R1B_DIFF_REPORT.md](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/analysis/R1B_DIFF_REPORT.md)

---

## bvm-sfq-receiver-r1b-output-jj-20260819

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/analysis/R1B_REPORT.md](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/analysis/R1B_REPORT.md)

---

## bvm-sfq-receiver-r1c-bias-margin-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/analysis/R1C_BIAS_REPORT.md](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/analysis/R1C_BIAS_REPORT.md)

---

## bvm-sfq-receiver-r2a-coupling-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2a-coupling-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/analysis/R2A_COUPLING_REPORT.md](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/analysis/R2A_COUPLING_REPORT.md)

---

## bvm-sfq-receiver-r2b-damping-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2b-damping-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2b-damping-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2b-damping-20260821/analysis/R2B_DAMPING_REPORT.md](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/analysis/R2B_DAMPING_REPORT.md)

---

## bvm-sfq-receiver-r2c-directdrive-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/analysis/R2C_DIRECTDRIVE_REPORT.md](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/analysis/R2C_DIRECTDRIVE_REPORT.md)

---

## bvm-sfq-receiver-r2d-duration-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2d-duration-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2d-duration-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2d-duration-20260821/analysis/R2D_DURATION_REPORT.md](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/analysis/R2D_DURATION_REPORT.md)

---

## bvm-sfq-receiver-r2e-ampthreshold-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/analysis/R2E_AMPTHRESHOLD_REPORT.md](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/analysis/R2E_AMPTHRESHOLD_REPORT.md)

---

## bvm-sfq-receiver-r2f-dwell-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2f-dwell-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/analysis/R2F_DWELL_REPORT.md](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/analysis/R2F_DWELL_REPORT.md)

---

## bvm-sfq-receiver-r2g-twopulse-20260821

**实验 ID**：`test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/analysis/R2G_TWOPULSE_REPORT.md](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/analysis/R2G_TWOPULSE_REPORT.md)

---

## bvm-sfq-receiver-r3a-onset-extraction-20260822

**实验 ID**：`test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/analysis/R3A_ONSET_REPORT.md](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/analysis/R3A_ONSET_REPORT.md)

---

## bvm-sfq-receiver-r4a-weak-mutual-capture-20260822

**实验 ID**：`test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`NO_WAVEFORM_VISUALIZATION_REQUIRED` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/analysis/R4A_AMENDED_REPORT.md](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/analysis/R4A_AMENDED_REPORT.md)

---

## bvm-sfq-receiver-r5a-biased-quantizer-20260822

**实验 ID**：`test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/analysis/R5A_REPORT.md](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/analysis/R5A_REPORT.md)

---

## bvm-sfq-receiver-r5b-loadline-20260822

**实验 ID**：`test/exploration/bvm-sfq-receiver-r5b-loadline-20260822`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/analysis/R5B_REPORT.md](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/analysis/R5B_REPORT.md)

---

## bvm-sfq-receiver-r5c-saddle-selectivity-20260822

**实验 ID**：`test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/analysis/R5C_REPORT.md](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/analysis/R5C_REPORT.md)

---

## bvm-sfq-receiver-r6a-native-qb-isolation-20260822

**实验 ID**：`test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`BACK_ACTION_FAILURE` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/analysis/R6A_REPORT.md](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/analysis/R6A_REPORT.md)

---

## bvm-sfq-receiver-r6b-native-qb-ratio-20260822

**实验 ID**：`test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/analysis/R6B_REPORT.md](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/analysis/R6B_REPORT.md)

---

## bvm-sfq-receiver-r7a-l1-routing-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/analysis/R7A_REPORT.md](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/analysis/R7A_REPORT.md)

---

## bvm-sfq-receiver-r8-bjl2-area070-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/analysis/R8_REPORT.md](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/analysis/R8_REPORT.md)

---

## bvm-sfq-receiver-r9a-l2-routing-20260823

**实验 ID**：`test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/plots/alignment-overview.html](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/topology/topology.svg)

**正式报告**：[test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/analysis/R9A_REPORT.md](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/analysis/R9A_REPORT.md)

---

## jtl-transport-gate-polarity-replay-20260824

**实验 ID**：`test/exploration/jtl-transport-gate-polarity-replay-20260824`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/alignment-overview.html](../test/exploration/jtl-transport-gate-polarity-replay-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-polarity-replay-20260824/topology/topology.svg)

**正式报告**：[test/exploration/jtl-transport-gate-polarity-replay-20260824/analysis/REPORT.md](../test/exploration/jtl-transport-gate-polarity-replay-20260824/analysis/REPORT.md)

---

## jtl-transport-gate-v1-numerical-freeze-20260824

**实验 ID**：`test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`REPORT_PRESENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/plots/alignment-overview.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/topology/topology.svg)

**正式报告**：[test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/analysis/REPORT.md](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/analysis/REPORT.md)

---

## jtl-transport-gate-v1-numerical-freeze-20260824-rerun

**实验 ID**：`test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/alignment-overview.html](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/topology/topology.svg)

**正式报告**：[test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/analysis/REPORT.md](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/analysis/REPORT.md)

---

## paper-sl-l0-20260824

**实验 ID**：`test/exploration/paper-sl-l0-20260824`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`PAPER_JSL_LOAD_VALID` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/paper-sl-l0-20260824/plots/alignment-overview.html](../test/exploration/paper-sl-l0-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-l0-20260824/topology/topology.svg)

**正式报告**：[test/exploration/paper-sl-l0-20260824/REPORT.md](../test/exploration/paper-sl-l0-20260824/REPORT.md)

---

## paper-sl-q3-pre-20260824

**实验 ID**：`test/exploration/paper-sl-q3-pre-20260824`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`NO_WAVEFORM_VISUALIZATION_REQUIRED` / alignment=`NO_WAVEFORM_VISUALIZATION_REQUIRED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q3-pre-20260824/topology/topology.svg)

**正式报告**：[test/exploration/paper-sl-q3-pre-20260824/analysis/REPORT.md](../test/exploration/paper-sl-q3-pre-20260824/analysis/REPORT.md)

---

## qb-q2c-uniform-junction-scale-20260824

**实验 ID**：`test/exploration/qb-q2c-uniform-junction-scale-20260824`

**做了什么**：见该 Exploration 的 preregistration / report。

**关键结果**：正式结论见 report；索引不新增科学解释。

**当前状态**：`UNIFORM_SCALE_NO_OUTPUT_EVENT` / alignment=`ALIGNED`

**结论边界**：自动审计条目；未在本轮改写 scientific verdict。

**推荐先看**：
- 【单工况/结果图】 [test/exploration/qb-q2c-uniform-junction-scale-20260824/plots/alignment-overview.html](../test/exploration/qb-q2c-uniform-junction-scale-20260824/plots/alignment-overview.html)

**电路**：
- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q2c-uniform-junction-scale-20260824/topology/topology.svg)

**正式报告**：[test/exploration/qb-q2c-uniform-junction-scale-20260824/SUMMARY.md](../test/exploration/qb-q2c-uniform-junction-scale-20260824/SUMMARY.md)

---
