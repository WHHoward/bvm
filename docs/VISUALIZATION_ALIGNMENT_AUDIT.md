# Visualization Alignment Audit V2

基线 HEAD：`576ca9d32b15c99f8c35c4271336ffa079664b64`

本审计只检查 raw/report/plot/index/topology 的 provenance 对齐，不改变任何 scientific verdict。

| 实验 | 科学状态 | required cases | plots | core/comparison | report | topology | status |
|---|---|---:|---:|---|---|---|---|
| test/exploration/bvm-internal-readout-20260819 | `ACCEPTED_CANONICAL_SOURCE` | 15 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r0-20260819 | `R0_PARTIAL` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r0b-20260819 | `R0B_PASS` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r1-oneshot-20260819 | `R1_FAIL` | 16 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r1a-transfer-20260819 | `R1A_PASS` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819 | `R1B_FAIL` | 8 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r1b-area008-20260821 | `R1B_AREA008_FAIL` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r1b-differential-output-20260821 | `R1B_FAIL` | 8 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r1c-bias-margin-20260821 | `R1C_FAIL` | 20 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r2a-coupling-20260821 | `R2A_FAIL_NO_COMPLETE_BOUT` | 20 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r2b-damping-20260821 | `R2B_NO_COMPLETE_EVENT` | 16 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r2c-directdrive-20260821 | `NO_THRESHOLD_BOUNDED_FAST_MATRIX` | 5 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r2d-duration-20260821 | `NO_THRESHOLD_BOUNDED_DURATION_MATRIX` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r2e-ampthreshold-20260821 | `NO_THRESHOLD_BOUNDED_MATRIX` | 3 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r2f-dwell-20260821 | `DWELL_THRESHOLD_FOUND` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r2g-twopulse-20260821 | `REPEATABLE_TWO_PULSE_SINGLE_SLIP` | 1 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r3a-onset-extraction-20260822 | `NO_OUTPUT_EVENT` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r4a-weak-mutual-capture-20260822 | `R4A_NO_PERSISTENT_READ1_STATE` | 0 | 0 | NO | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `NO_WAVEFORM_VISUALIZATION_REQUIRED` |
| test/exploration/bvm-sfq-receiver-r5a-biased-quantizer-20260822 | `R5A_NO_SET_EVENT` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r5b-loadline-20260822 | `R5B_STILL_BOUNDED_OSCILLATION` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r5c-saddle-selectivity-20260822 | `R5C_SADDLE_CROSSED_NO_COMPLETE_EVENT` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-native-qb-20260822 | `BACK_ACTION_FAILURE` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r6a-native-qb-isolation-20260822 | `ISOLATION_PRESERVED_STATE_SELECTIVE_QB_ACTIVITY` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r6b-native-qb-ratio-20260822 | `DRIVE_GAIN_WITH_ISOLATION_PRESERVED` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r7a-l1-routing-20260823 | `ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r8-bjl2-area070-20260823 | `OUTPUT_CLASS_CHANGE_WITHOUT_MEANINGFUL_BJL2_GAIN` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r9a-l2-routing-20260823 | `ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r10a-local-bjl2-bias-20260823 | `BACK_ACTION_OR_NONSELECTIVE_FAILURE` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823 | `NO_JTL_TRIGGER` | 5 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823 | `DCSFQ_BVM_NO_TRIGGER` | 7 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r13a-temporal-conditioning-20260823 | `TEMPORAL_CONDITIONING_INSUFFICIENT` | 16 | 5 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r14a-dcsfq-detector-20260823 | `PRECHECK_NO_GO` | 0 | 0 | NO | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `NO_WAVEFORM_VISUALIZATION_REQUIRED` |
| test/exploration/bvm-sfq-receiver-r15a-afq3-20260823 | `PRECHECK_NO_GO` | 0 | 0 | NO | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `NO_WAVEFORM_VISUALIZATION_REQUIRED` |
| test/exploration/bvm-sfq-receiver-r15b-magnetic-correction-20260823 | `ACTIVE_STAGE_NO_TRIGGER` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r15c-jset-causal-20260823 | `CAUSAL_NEAR_THRESHOLD` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-sfq-receiver-r15d-jq-compressor-20260823 | `JQ_CAUSAL_NEAR_THRESHOLD` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/qb-q0-standalone-current-quantized-event-20260824 | `ACCEPTED_STANDALONE_REFERENCE` | 7 | 8 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824 | `QB_SOURCE_BACKACTION_FAILURE` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/qb-q2a-source-decoupled-waveform-replay-20260824 | `QB_DYNAMIC_WINDOW_MISMATCH` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/qb-q2b-central-bias-bracketing-20260824 | `BIAS_BRACKET_NO_BJL1_EVENT` | 8 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/qb-q2c-uniform-junction-scale-20260824 | `UNIFORM_SCALE_NO_OUTPUT_EVENT` | 12 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-jsl-read-width-to-qb-sfq-v1-20260824 | `WIDTH_IMPROVES_QB_MARGIN_BUT_SUBTHRESHOLD` | 0 | 3 | NO | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `NO_WAVEFORM_VISUALIZATION_REQUIRED` |
| test/exploration/paper-sl-l0-20260824 | `PAPER_JSL_LOAD_VALID` | 4 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/paper-sl-q1-20260824 | `PAPER_JSL_QB_SUBTHRESHOLD` | 5 | 7 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/paper-sl-q2-20260824 | `BIAS_BRANCH_SUBTHRESHOLD` | 8 | 3 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/paper-sl-q3-pre-20260824 | `Q3_PRE_ROUTING_MECHANISM_INFERENCE` | 0 | 0 | NO | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `NO_WAVEFORM_VISUALIZATION_REQUIRED` |
| test/exploration/q3-l1-routing-closure-20260824 | `Q3_PRE_SINGLE_POINT_SELECTED` | 0 | 0 | NO | NO | `PUBLICATION_SCHEMATIC_VALIDATED` | `NO_WAVEFORM_VISUALIZATION_REQUIRED` |
| test/exploration/paper-sl-q3-l1-routing-closure-20260824 | `ROUTING_GAIN_WITH_BJL1_SUBTHRESHOLD` | 4 | 2 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/paper-sl-q4-l1-l2-placement-20260824 | `Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT` | 4 | 2 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/paper-sl-q5-l1-l2-factorial-20260824 | `Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT` | 4 | 2 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/paper-sl-q6-qb-jtl-compatibility-20260824 | `NO_JTL_TRIGGER` | 4 | 3 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/bvm-read-semantics-audit-and-jsl-width-bracket-v1-20260824 | `IDEAL_REPLAY_SELECTIVE_ONE_SFQ_CANDIDATE` | 16 | 4 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824 | `PHYSICAL_BACKACTION_PREVENTS_CLOSURE` | 8 | 20 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/qb-load-boundary-matrix-20260824 | `MIXED_DYNAMIC_LOADING` | 11 | 3 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/parallel-qb-jtl-interface-mechanism-20260824 | `BOUNDED_INTERFACE_MATRIX` | 6 | 6 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/jtl-transport-gate-polarity-replay-20260824 | `POLARITY_REPLAY_RECONCILED` | 2 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/jtl-transport-gate-v1-methodology-20260824 | `JTL_TRANSPORT_GATE_V1_RECONCILED` | 3 | 3 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824 | `JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE` | 9 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/jtl-transport-gate-v1-numerical-freeze-20260824-rerun | `JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE` | 9 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |
| test/exploration/qb-to-jtl-load-backaction-causal-audit-v1-20260824 | `MIXED_DYNAMIC_LOADING` | 5 | 1 | YES | YES | `PUBLICATION_SCHEMATIC_VALIDATED` | `ALIGNED` |

## 状态定义

- `ALIGNED`：manifest 已明确 raw case、result/comparison plot、report，并通过角色约束；
- `VISUALIZATION_INCOMPLETE`：required case 没有足够 plot coverage；
- `TOPOLOGY_MISMATCH`：结构图 signature 或 publication/debug 角色不一致；
- `NO_WAVEFORM_VISUALIZATION_REQUIRED`：该条目只有 analysis/documentation，没有可登记 raw waveform；
- `SUPERSEDED_ONLY`：仅保留历史 provenance，不作为 current core。

## 关键人工 spot-check 集合

QB-Q0、PAPER-SL-Q1/Q2、Q2–Q5 factorial、QB load-boundary、M1–M5、JTL methodology/numerical freeze、back-action、R13、Q6 均由 manifest 显式登记；其 core link 不从文件名排序推断。
