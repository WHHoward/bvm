# CIRCUIT SCHEMATIC INDEX

基线 HEAD：`e41d05fcf9aabd26890805bc4f2a12622b24eed7`。本页将论文级电路图、实验注释图和连接调试图分开。

## Canonical BVM：storage/readout cell

**Topology ID**：`BVM_CANONICAL`

**状态**：`PUBLICATION_SCHEMATIC_VALIDATED`；signature=`0527abb40428e8e4`…

- 【论文级电路图】 [schematic.svg](../test/exploration/bvm-internal-readout-20260819/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/bvm-internal-readout-20260819/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-internal-readout-20260819/topology/connectivity-debug.svg)
- representative deck：`test/exploration/bvm-internal-readout-20260819/inputs/pos-read-single.cir`

共享实验：
- `test/exploration/bvm-internal-readout-20260819`

---

## R13-A：temporal conditioning requirements

**Topology ID**：`DCSFQ_REPLAY_CONDITIONER`

**状态**：`DEBUG_ONLY`；signature=`1cae9275fd3e2fc7`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823/inputs/raw-replay/read1.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823`

---

## PAPER-SL-Q1：paper-JSL replay → frozen scaled QB

**Topology ID**：`PAPER_JSL_TO_FROZEN_QB`

**状态**：`DEBUG_ONLY`；signature=`cbe5a50d8d737fac`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q1-20260824/topology/topology.svg)
- representative deck：`test/exploration/paper-sl-q1-20260824/inputs/paper-j1-logical1-read.cir`

共享实验：
- `test/exploration/paper-sl-q1-20260824`
- `test/exploration/paper-sl-q2-20260824`
- `test/exploration/paper-sl-q3-l1-routing-closure-20260824`
- `test/exploration/paper-sl-q4-l1-l2-placement-20260824`
- `test/exploration/paper-sl-q5-l1-l2-factorial-20260824`

---

## PAPER-SL-Q6：Q5 → standard JTL compatibility

**Topology ID**：`Q5_TO_STANDARD_JTL`

**状态**：`DEBUG_ONLY`；signature=`997d6d8e61c47e3f`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/topology/topology.svg)
- representative deck：`test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824/inputs/q6-q5-to-two-cell-jtl/paper-j1-logical1-read.cir`

共享实验：
- `test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824`

---

## Q0 recorded V(OUT) ideal replay → standard JTL

**Topology ID**：`QB_M1_IDEAL_REPLAY_JTL`

**状态**：`DEBUG_ONLY`；signature=`762b19105f96c088`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main/topology.svg)
- representative deck：`test/exploration/parallel-qb-jtl-interface-mechanism-20260824/inputs/M1-ideal-replay/main.cir`

共享实验：
- `test/exploration/parallel-qb-jtl-interface-mechanism-20260824`

---

## 低 Ic QB → RISO=10Ω → standard JTL

**Topology ID**：`QB_M2_RISO10_JTL`

**状态**：`DEBUG_ONLY`；signature=`18bc023d1f93bb00`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-2/topology.svg)
- representative deck：`test/exploration/parallel-qb-jtl-interface-mechanism-20260824/inputs/M2-riso10/main.cir`

共享实验：
- `test/exploration/parallel-qb-jtl-interface-mechanism-20260824`

---

## M1–M5：QB→JTL interface mechanism matrix

**Topology ID**：`QB_M3_SERIES10_JTL`

**状态**：`DEBUG_ONLY`；signature=`b85efce84ad62238`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-3/topology.svg)
- representative deck：`test/exploration/parallel-qb-jtl-interface-mechanism-20260824/inputs/M3-rseries10/main.cir`

共享实验：
- `test/exploration/parallel-qb-jtl-interface-mechanism-20260824`
- `test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824`

---

## 低 Ic QB → LISO=10pH → standard JTL

**Topology ID**：`QB_M4_LISO10P_JTL`

**状态**：`DEBUG_ONLY`；signature=`ffeb4cda355de410`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-4/topology.svg)
- representative deck：`test/exploration/parallel-qb-jtl-interface-mechanism-20260824/inputs/M4-liso10p/main.cir`

共享实验：
- `test/exploration/parallel-qb-jtl-interface-mechanism-20260824`

---

## 低 Ic QB → scaled JTL

**Topology ID**：`QB_M5_SCALED_JTL`

**状态**：`DEBUG_ONLY`；signature=`e7516b9c2a62ed6c`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/parallel-qb-jtl-interface-mechanism-20260824/topology/variants/main-5/topology.svg)
- representative deck：`test/exploration/parallel-qb-jtl-interface-mechanism-20260824/inputs/M5-q0-scaled/main.cir`

共享实验：
- `test/exploration/parallel-qb-jtl-interface-mechanism-20260824`

---

## QB-Q0：低 Ic QB standalone 量化窗口

**Topology ID**：`QB_Q0_10OHM`

**状态**：`PUBLICATION_SCHEMATIC_VALIDATED`；signature=`103283576557852a`…

- 【论文级电路图】 [schematic.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic.svg)
- 【实验注释电路图】 [schematic-annotated.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/schematic-annotated.svg)
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q0-standalone-current-quantized-event-20260824/topology/connectivity-debug.svg)
- representative deck：`test/exploration/qb-q0-standalone-current-quantized-event-20260824/inputs/scaled-iin-68p4u.cir`

共享实验：
- `test/exploration/qb-q0-standalone-current-quantized-event-20260824`
- `test/exploration/qb-load-boundary-matrix-20260824`
- `test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824`

---

## 低 Ic QB + 10Ω || standard JTL

**Topology ID**：`QB_Q0_10OHM_PARALLEL_JTL`

**状态**：`DEBUG_ONLY`；signature=`b0e8c66a4fd29fe2`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/scaled-iin-68p4u-2/topology.svg)
- representative deck：`test/exploration/qb-load-boundary-matrix-20260824/inputs-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.cir`

共享实验：
- `test/exploration/qb-load-boundary-matrix-20260824`
- `test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824`

---

## 低 Ic QB → standard JTL direct

**Topology ID**：`QB_Q0_JTL_ONLY`

**状态**：`DEBUG_ONLY`；signature=`c4a9a1a578c1742f`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/variants/scaled-iin-68p4u/topology.svg)
- representative deck：`test/exploration/qb-load-boundary-matrix-20260824/inputs-v2/B-q0-jtl-only/scaled-iin-68p4u.cir`

共享实验：
- `test/exploration/qb-load-boundary-matrix-20260824`
- `test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824`

---

## 低 Ic QB → OPEN output boundary

**Topology ID**：`QB_Q0_OPEN`

**状态**：`DEBUG_ONLY`；signature=`1a217f47dac80ec8`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-load-boundary-matrix-20260824/topology/topology.svg)
- representative deck：`test/exploration/qb-load-boundary-matrix-20260824/inputs-v2/A-q0-open/scaled-iin-68p4u.cir`

共享实验：
- `test/exploration/qb-load-boundary-matrix-20260824`
- `test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824`

---

## QB-Q1：physical BVM → frozen scaled QB

**Topology ID**：`SCALED_QB_REPLAY`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/topology/topology.svg)
- representative deck：`test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/inputs/bq_cell.cir`

共享实验：
- `test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824`
- `test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824`
- `test/exploration/qb-q2b-central-bias-bracketing-20260824`

---

## JTL transport methodology

**Topology ID**：`STANDARD_JTL_2CELL`

**状态**：`DEBUG_ONLY`；signature=`194cd42df9988272`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-v1-methodology-20260824/topology/topology.svg)
- representative deck：`test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/inputs/r11/0p0125/main.cir`

共享实验：
- `test/exploration/jtl-transport-gate-v1-methodology-20260824`

---

## bvm-sfq-receiver-r6a-native-qb-isolation-20260822

**Topology ID**：`TOPOLOGY_076c3ccc98`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822/inputs/bq_cell_paper.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822`

---

## bvm-sfq-receiver-r6b-native-qb-ratio-20260822

**Topology ID**：`TOPOLOGY_0bba1f61c1`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822/inputs/bq_cell_paper.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822`

---

## bvm-sfq-receiver-r2c-directdrive-20260821

**Topology ID**：`TOPOLOGY_0da30ee288`

**状态**：`DEBUG_ONLY`；signature=`ea1a9c827ff301b5`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821/inputs/amp20u0-receiver.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821`

---

## jtl-transport-gate-polarity-replay-20260824

**Topology ID**：`TOPOLOGY_0fca67e829`

**状态**：`DEBUG_ONLY`；signature=`MISSING`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-polarity-replay-20260824/topology/topology.svg)
- representative deck：`未记录`

共享实验：
- `test/exploration/jtl-transport-gate-polarity-replay-20260824`

---

## bvm-sfq-receiver-r5a-biased-quantizer-20260822

**Topology ID**：`TOPOLOGY_16ea7d821b`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822`

---

## bvm-sfq-receiver-r0b-20260819

**Topology ID**：`TOPOLOGY_2600b475f4`

**状态**：`DEBUG_ONLY`；signature=`cefd9f9e156ea6a3`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r0b-20260819/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r0b-20260819/inputs/a050-b15-read1.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r0b-20260819`

---

## paper-sl-l0-20260824

**Topology ID**：`TOPOLOGY_345d48a6be`

**状态**：`DEBUG_ONLY`；signature=`e3b0c44298fc1c14`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-l0-20260824/topology/topology.svg)
- representative deck：`test/exploration/paper-sl-l0-20260824/inputs/jjmit.cir`

共享实验：
- `test/exploration/paper-sl-l0-20260824`

---

## bvm-sfq-receiver-r5b-loadline-20260822

**Topology ID**：`TOPOLOGY_36fb1f63c9`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r5b-loadline-20260822/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r5b-loadline-20260822`

---

## jtl-transport-gate-v1-numerical-freeze-20260824

**Topology ID**：`TOPOLOGY_3a1af7987d`

**状态**：`DEBUG_ONLY`；signature=`MISSING`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824/topology/topology.svg)
- representative deck：`未记录`

共享实验：
- `test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824`

---

## bvm-sfq-receiver-r5c-saddle-selectivity-20260822

**Topology ID**：`TOPOLOGY_4e1d8a8345`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822`

---

## bvm-sfq-receiver-r1b-output-jj-20260819

**Topology ID**：`TOPOLOGY_5233bbad6e`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/inputs/bq_cell_paper-reference.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819`

---

## bvm-sfq-receiver-native-qb-20260822

**Topology ID**：`TOPOLOGY_599236eda7`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-native-qb-20260822/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-native-qb-20260822/inputs/bq_cell_paper.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-native-qb-20260822`

---

## bvm-sfq-receiver-r15c-jset-causal-20260823

**Topology ID**：`TOPOLOGY_6161c7c30f`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823`

---

## bvm-sfq-receiver-r1-oneshot-20260819

**Topology ID**：`TOPOLOGY_658acd44d8`

**状态**：`DEBUG_ONLY`；signature=`cefd9f9e156ea6a3`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r1-oneshot-20260819/inputs/a050-b15-lq10-read1.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r1-oneshot-20260819`

---

## bvm-sfq-receiver-r10a-local-bjl2-bias-20260823

**Topology ID**：`TOPOLOGY_6776d3562e`

**状态**：`DEBUG_ONLY`；signature=`3ee72bfb04746e3a`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823/inputs/bq_cell_paper_r10a_local_bias.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823`

---

## bvm-sfq-receiver-r2f-dwell-20260821

**Topology ID**：`TOPOLOGY_7278e859dc`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r2f-dwell-20260821/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r2f-dwell-20260821`

---

## bvm-sfq-receiver-r1a-transfer-20260819

**Topology ID**：`TOPOLOGY_73d3c8d7f4`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r1a-transfer-20260819/inputs/bq_cell_paper-reference.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r1a-transfer-20260819`

---

## bvm-sfq-receiver-r0-20260819

**Topology ID**：`TOPOLOGY_75d201da61`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r0-20260819/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r0-20260819/inputs/bq_cell_paper-reference.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r0-20260819`

---

## bvm-sfq-receiver-r1b-area008-20260821

**Topology ID**：`TOPOLOGY_7dca5b0bd5`

**状态**：`DEBUG_ONLY`；signature=`185660d47eaffad0`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1b-area008-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r1b-area008-20260821/inputs/area010_receiver_reference.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r1b-area008-20260821`

---

## jtl-transport-gate-v1-numerical-freeze-20260824-rerun

**Topology ID**：`TOPOLOGY_8403837f5b`

**状态**：`DEBUG_ONLY`；signature=`MISSING`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun/topology/topology.svg)
- representative deck：`未记录`

共享实验：
- `test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun`

---

## bvm-sfq-receiver-r2e-ampthreshold-20260821

**Topology ID**：`TOPOLOGY_879c0c5b61`

**状态**：`DEBUG_ONLY`；signature=`ea1a9c827ff301b5`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821/inputs/a40u0-receiver.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821`

---

## bvm-sfq-receiver-r15d-jq-compressor-20260823

**Topology ID**：`TOPOLOGY_9334bd7f21`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823`

---

## bvm-sfq-receiver-r15a-afq3-20260823

**Topology ID**：`TOPOLOGY_9a2c21177c`

**状态**：`DEBUG_ONLY`；signature=`051d117392ff4cee`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r15a-afq3-20260823/inputs/DCSFQ_BVM.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r15a-afq3-20260823`

---

## bvm-sfq-receiver-r3a-onset-extraction-20260822

**Topology ID**：`TOPOLOGY_a4ff2838c2`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822`

---

## bvm-sfq-receiver-r2a-coupling-20260821

**Topology ID**：`TOPOLOGY_a5649ee5af`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r2a-coupling-20260821/inputs/bq_cell_paper-reference.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r2a-coupling-20260821`

---

## bvm-sfq-receiver-r2d-duration-20260821

**Topology ID**：`TOPOLOGY_a61a44b0c0`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2d-duration-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r2d-duration-20260821/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r2d-duration-20260821`

---

## bvm-sfq-receiver-r1b-differential-output-20260821

**Topology ID**：`TOPOLOGY_a8dab02d1d`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821/inputs/bq_cell_paper-reference.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821`

---

## bvm-sfq-receiver-r1c-bias-margin-20260821

**Topology ID**：`TOPOLOGY_ac497f8640`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821/inputs/bq_cell_paper-reference.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821`

---

## bvm-sfq-receiver-r2g-twopulse-20260821

**Topology ID**：`TOPOLOGY_ad32926098`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821`

---

## bvm-sfq-receiver-r2b-damping-20260821

**Topology ID**：`TOPOLOGY_b01953770c`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r2b-damping-20260821/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r2b-damping-20260821/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r2b-damping-20260821`

---

## bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823

**Topology ID**：`TOPOLOGY_b2733b8e3c`

**状态**：`DEBUG_ONLY`；signature=`d1a7855abab4a553`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/inputs/phase-a-bump-300u.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823`

---

## bvm-sfq-receiver-r7a-l1-routing-20260823

**Topology ID**：`TOPOLOGY_b2e3690473`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823/inputs/bq_cell_paper.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823`

---

## paper-sl-q3-pre-20260824

**Topology ID**：`TOPOLOGY_ba0fe9d75d`

**状态**：`DEBUG_ONLY`；signature=`MISSING`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/paper-sl-q3-pre-20260824/topology/topology.svg)
- representative deck：`未记录`

共享实验：
- `test/exploration/paper-sl-q3-pre-20260824`

---

## qb-q2c-uniform-junction-scale-20260824

**Topology ID**：`TOPOLOGY_bb821ba72c`

**状态**：`DEBUG_ONLY`；signature=`e3b0c44298fc1c14`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/qb-q2c-uniform-junction-scale-20260824/topology/topology.svg)
- representative deck：`test/exploration/qb-q2c-uniform-junction-scale-20260824/inputs/jjmit.cir`

共享实验：
- `test/exploration/qb-q2c-uniform-junction-scale-20260824`

---

## bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823

**Topology ID**：`TOPOLOGY_c69c14b0ad`

**状态**：`DEBUG_ONLY`；signature=`194cd42df9988272`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/inputs/positive-control.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823`

---

## bvm-sfq-receiver-r4a-weak-mutual-capture-20260822

**Topology ID**：`TOPOLOGY_cb0a106fd7`

**状态**：`DEBUG_ONLY`；signature=`1a8fdb9f2b649c71`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822/inputs/bvm_cell.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822`

---

## bvm-sfq-receiver-r14a-dcsfq-detector-20260823

**Topology ID**：`TOPOLOGY_d1f5096eb9`

**状态**：`DEBUG_ONLY`；signature=`MISSING`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823/topology/topology.svg)
- representative deck：`未记录`

共享实验：
- `test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823`

---

## bvm-sfq-receiver-r15b-magnetic-correction-20260823

**Topology ID**：`TOPOLOGY_e9d593f012`

**状态**：`DEBUG_ONLY`；signature=`051d117392ff4cee`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823/inputs/DCSFQ_BVM.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823`

---

## bvm-sfq-receiver-r8-bjl2-area070-20260823

**Topology ID**：`TOPOLOGY_e9e3fdb426`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823/inputs/bq_cell_paper.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823`

---

## bvm-sfq-receiver-r9a-l2-routing-20260823

**Topology ID**：`TOPOLOGY_f2413fa505`

**状态**：`DEBUG_ONLY`；signature=`043c29a9dfbfe094`…

- 【论文级电路图】 `schematic.svg（未生成）`
- 【实验注释电路图】 `schematic-annotated.svg（未生成）`
- 【网表连接调试图】 [connectivity-debug.svg](../test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/topology/topology.svg)
- representative deck：`test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823/inputs/bq_cell_paper.cir`

共享实验：
- `test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823`

---

## 结构图边界

只有存在 semantic + geometric validation 的 `schematic.svg` 才列为论文级电路图；Graphviz `topology.svg` 只作 debug/provenance，不作为默认结构图入口。
