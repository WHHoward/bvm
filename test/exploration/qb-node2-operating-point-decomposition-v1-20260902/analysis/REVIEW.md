# QB_NODE2_OPERATING_POINT_DECOMPOSITION_V1：Adversarial / Numerical Review

审查对象：本目录的 existing-raw-only 分析、派生指标、provenance、单张关键数据图和报告。结论保持 Exploration 级，不构成 Formal 或 accepted scientific Gate。

## 1. Artifact review：PASS

- G/I0/P0 raw 均有路径、SHA-256、sidecar/登记信息、CSV QA 和时间网格记录。
- G/I0/P0 各为 13,599 samples，时间严格递增，0–169.9875 ps；NaN/Inf QA 通过。非均匀时间网格被保留，积分使用实际时间坐标。
- Q45/Q68 raw 的 SHA-256 均登记为 true。审查中发现同名 paper/scaled raw 可能造成 basename 匹配歧义，分析脚本已改为要求 Q0 root 下的精确相对路径，并在最终 manifest checks 中对两项 raw registration fail-closed。
- Q45/Q68 的 deck semantics、35 µA bias、10 Ω load、periodic stimulus、0.1 ps timestep、300 ps stop time 和 scaled model hashes 均通过；authority 仍明确是 `HISTORICAL_SUPPORTING_REFERENCE`。
- 当前任务没有调用 `build/josim-cli`，没有生成新 solver raw，没有覆盖历史 raw；`NO_NEW_JOSIM=true`。
- 单张 HTML 使用 canonical `scripts/josim-plot2.py` 的 `CLASSIC_LOCKED`、`sep_comb`、dark profile，phase 显示采用 `-j 2pi`；图中只有本任务声明的关键 I0/P0 signal groups，不是 exhaustive dashboard。

## 2. Numerical review：PASS

- 所有 branch orientation 直接从实际 QB netlist 记录：BJs `1→2`、BJL1 `2→0`、L1 `2→3`、RB `IB→3`、L2 `3→4`、BJL2 `4→0`、L0 `4→OUT`。
- I0/P0 满足 QB input/node2/node3/node4 KCL，使用实际方向和 `0.001 µA` absolute tolerance；G 仅是 grounded-source reference，不作为 QB KCL case。I0/P0 最大 residual 约 `6×10^-5 µA`，远低于容差。
- signed area、positive/negative area、zero crossing 和 occupancy 均按窗口内实际时间坐标计算；没有把 derivative over-threshold samples 当作 event count。
- phase 仍被当作 raw JoSIM radians；turns 只由同一 signal 的连续 unwrap phase difference `/ (2π)` 得到。phase turn 未被等同为 SFQ count。
- I0/P0 的 W3 difference 是 same signal、same window、same run pair、exact common grid，`interpolation_mode=none`。
- I0 strict anchor 保持：`103.0375–110.175 ps`、phase `1.0160289228944646 turns`、area `1.0160368344325381 Φ0`、`CLEAN_ONE_SFQ_CANDIDATE`。P0 strict local 为 `SUBTHRESHOLD`。claim ceiling 仍是 same-JJ local phase/area compatibility。
- RJ1/RJ2 的 power 只标记为 resistor dissipation proxy，不冒充 QB total power。

## 3. Adversarial probes

| probe | 结果 | 防护 |
|---|---|---|
| source branch duplicate headers | G 中的 `I(B_LD1)`/`I(B_LD12)` 有 duplicate occurrence；分析显式记录 occurrences，replay closure 同时核对源 branch；未把重复列静默当作不同物理 branch | provenance 保留 duplicate QA |
| raw stale/mismatch | G/I0/P0 通过 SHA-256、sidecar 和 exact-grid/样本数检查 | 哈希与 QA fail-closed |
| Q45/Q68 basename collision | 发现并修正：不再接受 paper/scaled 同 basename 的模糊匹配 | 精确 Q0-relative path + final registration checks |
| plot column misclassification | 首版派生列名未以 `I(`/`P(` 开始，已修正为 `I(I0|...)`/`P(I0|...)` 等 canonical names | metadata 与 HTML 同步核对 |
| weak oracle | `CLEAN_ONE_SFQ_CANDIDATE` 只作为任务局部 anchor compatibility；不用于证明 event count 或 downstream delivery | 报告显式 claim ceiling |
| local phase as SFQ | 所有报告和图注都保留“phase turns are not SFQ counts”边界 | evidence contract |
| old audit authority leakage | 旧 audit 只记录为历史动机，未消费为当前 authority | provenance boundary |
| first-divergence overclaim | legacy result-dependent 10% 规则降为 sensitivity-only；primary 只用 W2 PRE p99 noise，矩阵覆盖 1/2 µA、0.05/0.10 turns、1/3 samples、time-aware persistence 及 0.0125/0.025 ps tie；报告为 descriptive，不记 causal | onset/KCL shared helpers + layer/tie metadata |
| Q45/Q68 threshold overclaim | Q45/Q68 不做 pointwise comparison、插值或通用阈值拟合 | supporting-only authority |

## 4. Corrective analysis disposition

旧分类 `NODE2_REDISTRIBUTION_SUPPORTED` 已被 corrective reanalysis 改为 `COUPLED_INPUT_BJS_NODE2`。robustness summary=`MIXED`：24 个 PRE-noise 配置中 12 个为 input/BJs+node2 tie 的 coupled ordering，12 个为 input/BJs earliest ordering。主配置的首组是 input/BJs 与 node2 的 `0.025 ps` tie，因此不支持 node2-only 的稳健 temporal order。

独立强观察 `NODE2_REDISTRIBUTION_DIFFERENCE_OBSERVED=true`：BJL1 current/phase、L1 separation、稳定 RB、L2 downstream separation 和 I0 clean/P0 subthreshold 的 BJL2 local contrast 均成立。该观察与 onset ordering 分开，不等于 causal proof。

特别注意：I0 的 clean local anchor 和 P0 的 subthreshold label 都不提供 JTL reception 证据；本任务没有 JTL downstream event counter，也没有 timestep convergence rerun。图形只描述数据，不能单独赋予 physical Gate authority。`causal_order=NOT_PROVEN`。

## 5. 审查 disposition

- Artifact validity：`PASS`。
- Numerical consistency：`PASS`。
- Physical mechanism claim：`EXPLORATORY / INCONCLUSIVE`，不是 Formal Gate。
- User review：`REQUIRED`。
- Final state：`AWAITING_USER_REVIEW / STOP`。
