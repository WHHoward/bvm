# BVM_QB_IDLE_AND_READ_BOUNDARY_STATE_DECOMPOSITION_V1 分析报告

## 结论边界

这是对父矩阵已有 raw 的 `EXISTING_RAW_ONLY` QUICK 分析，不运行 JoSIM，不改变
BVM/JSL/QB 参数或拓扑。结果是当前模型、当前单一请求步长和三个既有边界条件
下的 simulation evidence，不是硬件测量。raw `P(...)` 单位为 rad；报告中的
phase turns 是连续 unwrap 后除以 `2π` 的显示单位，不是 SFQ 计数。

## 输入与固定窗口

| Case | topology meaning | samples | time range (ps) | hash prefix |
|---|---|---:|---:|---|
| A_grounded_source_reference | A grounded-JSL source reference | 13599 | [0, 169.988] | b92056235a06 |
| B_ideal_replay_qb | B ideal current replay QB | 13599 | [0, 169.988] | be7e0403586b |
| C_physical_bvm_jsl_qb | C physical BVM/JSL/QB | 13599 | [0, 169.988] | 9aecc3f62614 |

| Window | interval (ps) | samples | meaning |
|---|---:|---:|---|
| W0_bias | [2, 9) | 560 | QB bias established, before BVM init |
| W1_initialization | [10, 21) | 880 | BVM initialization |
| W2_settled_idle | [80, 90) | 800 | settled idle / stored-state |
| W3_read | [95, 110) | 1200 | READ |
| W4_post_read | [110, 130) | 1600 | post-READ settling |

A/C 与 B/C 均使用 exact-grid、无插值比较；差值定义为 `right - left`。
A/C 的重复 `I(B_LD1)` 与 `I(B_LD12)` 选 occurrence 0；raw 中 occurrence 0/1
的 QA 相同结果记录在 `metrics.json`。

## Q1：physical QB 是否改变 BVM 状态

### Observed：初始化与 settled idle

| signal | W1 A→C max diff | W2 A→C max diff | W2 grounded median/mean | W2 physical median/mean | unit |
|---|---:|---:|---:|---:|---|
| `P(B_JM1|XBVM1)` | 0.00369637 | 3.43775e-05 | 0.940775 | 0.940776 | turns |
| `P(B_JM2|XBVM1)` | 0.000727497 | 5.8378e-05 | 0.0504919 | 0.0504915 | turns |
| `P(B_JS1|XBVM1)` | 0.00591327 | 0.000423989 | 0.042475 | 0.0424946 | turns |
| `P(B_JS2|XBVM1)` | 0.00863408 | 0.000392428 | -0.0424607 | -0.0424923 | turns |
| `I(B_LD1)` | n/a | 0.0410959 | 0.000928695 | -0.00064046 | uA mean |
| `I(B_LD12)` | n/a | 0.0410959 | 0.000928695 | -0.00064046 | uA mean |

W2 的 BVM core phase 差异很小，W1 的有限启动扰动较大；这支持把 persistent
idle-state backfeed 作为未被当前数据支持的主解释，而不是把它宣称为不可能。

### Observed：READ current and BVM phase trajectory

| signal | grounded W3 key statistic | physical W3 key statistic | exact-grid max diff | unit |
|---|---|---|---:|---|
| `I(B_LD1)` | peak=79.0668, rms=50.6141 | peak=68.1454, rms=36.8867 | 84.5943 | uA |
| `I(L_PSL|XBVM1)` | peak=79.0668, rms=50.6141 | peak=68.1454, rms=36.8867 | 84.5943 | uA |
| `I(L_SL|XBVM1)` | peak=79.0668, rms=50.6141 | peak=68.1454, rms=36.8867 | 84.5943 | uA |
| `P(B_JM1|XBVM1)` | end Δ=0.0330686 | end Δ=0.0699513 | 0.0514394 | turns |
| `P(B_JM2|XBVM1)` | end Δ=0.0526147 | end Δ=0.137179 | 0.18439 | turns |
| `P(B_JS1|XBVM1)` | end Δ=-4.04038 | end Δ=-5.26947 | 1.22906 | turns |
| `P(B_JS2|XBVM1)` | end Δ=-4.63765 | end Δ=-5.81751 | 1.1799 | turns |

### W3 `I(B_LD1)` required waveform diagnostics

| condition | positive peak (uA) | peak time (ps) | positive area (uA*ps) | negative area (uA*ps) | signed area (uA*ps) | RMS (uA) |
|---|---:|---:|---:|---:|---:|---:|
| A grounded-JSL source reference | 79.0668 | 104.237 | 713.088 | 0 | 713.088 | 50.6141 |
| C physical BVM/JSL/QB | 68.1454 | 103.762 | 471.94 | -7.81556 | 464.125 | 36.8867 |

这里的面积是电流对时间的 waveform diagnostic；不命名为 SFQ area，也不从它
单独推导 SFQ 接收。W4 的 JS1/JS2 仍有显著 phase activity，因此 W4 不能被当作
最终静止态；W4 统计仍完整保存在机器可读指标中。

## Q2：QB 是 preloaded 还是在 READ 才发生主要差异

### Observed：W2 pre-READ

| QB signal | ideal replay (median / p2p) | physical (median / p2p) | exact-grid max diff | unit/stat |
|---|---:|---:|---:|---|
| `P(BJS|XBQ)` | 5.47791e-06 / 0.00047548 | 7.65076e-07 / 0.000162021 | 0.00019889 | median / p2p turns |
| `P(BJL1|XBQ)` | 0.0690029 / 0.000245226 | 0.0689931 / 0.000111138 | 0.000152582 | median / p2p turns |
| `P(BJL2|XBQ)` | 0.059998 / 8.68986e-05 | 0.0599999 / 3.51414e-05 | 5.33806e-05 | median / p2p turns |
| `I(L1|XBQ)` | -15.12 / 0.06652 / 15.12 / 15.1532 | -15.1217 / 0.03018 / 15.1217 / 15.1361 | 0.04128 | mean / p2p / RMS / maxabs uA |
| `I(LIN|XBQ)` | 0.000928695 / 0.0656465 / 0.0175975 / 0.0343754 | -0.00064046 / 0.0277605 / 0.00712757 / 0.0144479 | 0.0410959 | mean / p2p / RMS / maxabs uA |
| `I(RB|XBQ)` | 35 / 0 / 35 / 35 | 35 / 0 / 35 / 35 | 0 | mean / p2p / RMS / maxabs uA |
| `I(L2|XBQ)` | 19.88 / 0.06652 / 19.88 / 19.9133 | 19.8783 / 0.03018 / 19.8783 / 19.8941 | 0.04128 | mean / p2p / RMS / maxabs uA |

W2 的 `RB` 两侧均为固定 35 uA；其它 QB current 的 exact-grid 最大差不超过
0.04128 uA。

### Observed：W3 READ

| QB signal | ideal replay W3 median / p2p | physical W3 median / p2p | exact-grid max diff | unit/stat |
|---|---:|---:|---:|---|
| `P(BJS|XBQ)` | 0.295023 / 8.39437 | 0.22447 / 2.77658 | 5.61775 | median / p2p turns |
| `P(BJL1|XBQ)` | 0.308401 / 1.28725 | 0.213024 / 0.278799 | 1.28644 | median / p2p turns |
| `P(BJL2|XBQ)` | 0.178995 / 1.13194 | 0.124762 / 0.133621 | 1.13305 | median / p2p turns |
| `I(L1|XBQ)` | 20.992 / 92.8369 / 29.8788 / 77.7074 | 1.60251 / 47.2152 / 12.9793 / 24.327 | 69.7879 | mean / p2p / RMS / maxabs uA |
| `I(LIN|XBQ)` | 47.5557 / 79.0645 / 50.6141 / 79.0668 | 30.9447 / 78.5275 / 36.8867 / 68.1454 | 84.5943 | mean / p2p / RMS / maxabs uA |
| `I(RB|XBQ)` | 35 / 0 / 35 / 35 | 35 / 0 / 35 / 35 | 0 | mean / p2p / RMS / maxabs uA |
| `I(L2|XBQ)` | 55.992 / 92.8369 / 59.8931 / 112.707 | 36.6025 / 47.2152 / 38.8025 / 59.327 | 69.7879 | mean / p2p / RMS / maxabs uA |

## Hypothesis disposition

| hypothesis | bounded disposition | evidence label |
|---|---|---|
| H-A persistent QB-bias backfeed changes BVM idle state | W2 BVM core差异小，主导解释未获支持；不能排除未观测节点的有限 backfeed | OBSERVED + UNKNOWN |
| H-B QB mainly changes initialization and leaves persistent stored-state difference | W1 有限扰动，但 W2 未见同量级 persistent core shift | OBSERVED / INCONCLUSIVE |
| H-C BVM stored state preserved but interface preload differs | W2 已测 QB internal preload 接近；未测界面节点仍未知 | OBSERVED + UNKNOWN |
| H-D pre-READ approximately preserved, dominant incompatibility during READ | 与 W2 接近、W3 分叉的 pattern 最一致；不是唯一机制证明 | PHYSICS-BASED INFERENCE |

## Frozen historical reference check

该表使用预注册的 `[94,130)` ps，而不是 W3 `[95,110)` ps：

| condition | positive area | negative area | signed area | peak time | max diff vs other | RMS diff vs other |
|---|---:|---:|---:|---:|---:|---:|
| A grounded-JSL source reference | 899.297 | -36.0987 | 863.198 | 104.237 | — | — |
| C physical BVM/JSL/QB | 499.106 | -154.331 | 344.775 | 103.762 | — | — |
| A→C exact-grid difference | — | — | — | — | 84.5943 uA | 23.1956 uA |

## Unknown / limitations

- 没有改变任何科学参数或运行新的 JoSIM；因此不提供 timestep convergence。
- 没有磁耦合、JTL、T1，也没有把 local JJ phase 或 current-time area 解释为下游 SFQ delivery。
- 本分析只覆盖 13 ps / 12×320 / logical1_read；不向其它负载、读宽或状态外推。
- plot 是描述性证据，不是科学 Gate；唯一结果页见 `plots/RESULT_OVERVIEW.html`。

## Artifacts

- `analysis/metrics.json`：固定窗统计、exact-grid 差值、重复列 QA 和历史核对。
- `analysis/provenance.json`：raw/hash、父 manifest、metric spec 与本次分析命令边界。
- `plots/RESULT_OVERVIEW.html`：classic `sep_comb` / dark / `-j 2pi` 的五组 paired key signals。

## Gate

`QUICK_AMBIGUOUS` / `INCONCLUSIVE` / `AWAITING_USER_REVIEW` / `STOP`
