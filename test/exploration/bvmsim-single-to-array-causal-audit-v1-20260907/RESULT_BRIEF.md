# Single → 4×1 shared-SL causal audit

本报告是 bounded historical BVMSim simulation analysis，不是 Formal Gate。comparison HTML 是本任务验收项。

## Observed

- 现有 raw 与 G1/G2 raw 均解析通过；array/passive same-mask grid exact=True，single→array overlap exact=True，没有插值。
- single→one-hot 直接对照存在 protocol/history 与 sensing-load 混杂；因此它只作差异定位背景，不作唯一因果归因。主 timeline 的 representative one-hot 是 `1000`。
- bridge 的 G0→G1 是 sensing boundary 改变，G1→G2 是 history/protocol bundle 改变，G2→G3 是加入了完整历史但在最终 READ 时保持 quiet 的三个 connected BVM，G3→G4 是第二个 active BVM；comparison HTML 覆盖关键轨迹和 same-time pre-READ 对照。

## Bridge transition summary

| transition | LSL max | LS2 max | LM3 max | LS1 max | JM2 phase max | QB BJ2 phase max |
|---|---:|---:|---:|---:|---:|---:|
| G0_to_G1_boundary | 20.9642 uA | 79.3945 uA | 66.0395 uA | 83.6991 uA | 0.491096 rad | 0.084119 rad |
| G1_to_G2_protocol | 62.5969 uA | 159.728 uA | 202.553 uA | 214.555 uA | 1.25912 rad | 6.28037 rad |
| G2_to_G3_quiet_cells | 78.6014 uA | 241.954 uA | 210.459 uA | 261.656 uA | 1.58164 rad | 6.28622 rad |
| G3_to_G4_second_active | 92.9516 uA | 207.216 uA | 174.043 uA | 215.168 uA | 1.3972 rad | 6.2881 rad |

## Pre-READ state comparison

G0/G1 的 same-time pre-READ 窗口是 `[62,70) ps`；G2/G3/G4 的 same-time pre-READ 窗口是 `[101,110) ps`。这些窗口只使用实际存储时间点，不插值。G1→G2 的两个历史窗口不同，因此只报告 descriptive stage statistics，不做 pointwise subtraction。对应图见 [READ_BEFORE_STATE](plots/comparison/READ_BEFORE_STATE.html)、[ARRAY_PRE_READ_STATE](plots/comparison/ARRAY_PRE_READ_STATE.html) 和 [SINGLE_TO_ARRAY_BRIDGE_OVERVIEW](plots/comparison/SINGLE_TO_ARRAY_BRIDGE_OVERVIEW.html)。

| same-time transition | COMMON_SL max | LSL max | LS2 max | JM2 phase max | QB BJ2 phase max |
|---|---:|---:|---:|---:|---:|
| G0_to_G1_boundary | 0.0405375 mV | 1.26396 uA | 2.76055 uA | 0.0040844 rad | 0.004529 rad |
| G2_to_G3_quiet_cells | 0.153463 mV | 7.02553 uA | 7.96722 uA | 0.0104097 rad | 0.0263982 rad |
| G3_to_G4_second_active | 0 mV | 0 uA | 0 uA | 0 rad | 0 rad |

G1→G2 relative-window descriptive comparison (`G1 [62,70) ps` vs `G2 [101,110) ps`；右侧减左侧，仅比较窗口统计量)：

| signal | G1 mean | G2 mean | descriptive Δmean |
|---|---:|---:|---:|
| COMMON_SL | 0.0158791 mV | 0.00624843 mV | -0.00963069 mV |
| LSL | -0.910785 uA | -1.32047 uA | -0.409683 uA |
| LS2 | -19.222 uA | -20.7847 uA | -1.56266 uA |
| JM2 | 0.322804 rad | 0.310322 rad | -0.0124816 rad |
| BJ2 | 0.893434 rad | 0.893157 rad | -0.000277151 rad |

same-time 表中的数值是窗口内差值的最大绝对值；relative 表中的数值是不同历史窗口的统计量，不是逐点差值。它们都不是事件计数。phase 的 `P(...)` 原始单位是 rad，图中 turns 只表示 rad/(2π)。

## Q1–Q8 bounded answers

1. **Q1:** 在代表性 one-hot `1000` 的阈值扫描中，所有注册层都在 50.1 ps 首次越过各自阈值；因此不能从该结果声称 `COMMON_SL` 先于其它层发生了可归因分歧。[DIVERGENCE_TIMELINE](plots/comparison/DIVERGENCE_TIMELINE.html) 只作差异定位，不能单独排除 protocol/load 混杂。
2. **Q2:** direct Golden-vs-array 图在 READ 前已混入不同 WRITE/history；桥接的 G0→G1 same-time pre-READ 对照表明仅换 sensing boundary 就能留下差异，G1→G2 则只能作为不同历史窗口的 descriptive comparison。这里的“已存在”是 bounded waveform difference，不等于已定位唯一根因。
3. **Q3:** output/R-loop disturbance 在 bridge comparison 中可观测到 COMMON_SL、LSL、RSL、LS2/JS2、LM3、LS1/JS1，并进一步出现在 JM2/JM1；[SINGLE_TO_ARRAY_BRIDGE_OVERVIEW](plots/comparison/SINGLE_TO_ARRAY_BRIDGE_OVERVIEW.html) 包含这套完整 bridge probe schema。
4. **Q4:** [QUIET_VICTIM_CROSSTALK](plots/comparison/QUIET_VICTIM_CROSSTALK.html) 显示 `0001→0011` 时 BVM1（以及镜像 case 的 quiet victims）并非被静默视为零；这是 bounded shared-SL crosstalk observation，不能外推为 universal isolation failure。
5. **Q5:** [ACTIVE_VICTIM_CROSSTALK](plots/comparison/ACTIVE_VICTIM_CROSSTALK.html) 显示 `0001→0011` 时保持 active 的 BVM4 也发生可观测变化；同一页包含镜像 `1000→1100`。
6. **Q6:** passive boundary 下的同一 aggressor-victim difference 也存在，详见 [PASSIVE_VS_QB_CROSSTALK](plots/comparison/PASSIVE_VS_QB_CROSSTALK.html)。
7. **Q7:** QB-extra 是 `ΔQB−Δpassive` 的差分，不把 QB 影响与 intrinsic shared-SL coupling 混为一谈；本 fixture 的量化表和图同时给出二者，结论只保留为 bounded comparison。
8. **Q8:** G0→G4 的首次变化不能从 single-vs-array raw 直接唯一归因；桥接顺序中 G1 已由 sensing boundary 产生可见变化，G2/G3/G4 又各有增量，不能把后续差异误写成单一根因。

## Interpretation labels

- `SENSING_BOUNDARY_EFFECT_OBSERVED`：G0→G1 在本固定 fixture、same-time pre-READ 窗口和 observables 下留下了 bounded waveform difference；这不是唯一机制证明。
- `HISTORY_PROTOCOL_BUNDLE_EFFECT_OBSERVED`：G1→G2 的历史/协议 bundle 的 registered-window statistics 不同；不能把它拆成单一 PWL 或单一器件原因。
- `FULL_HISTORY_CELLS_ADDED_EFFECT_OBSERVED`：G2→G3 比较的是带完整历史、仅在最终 READ 时保持 quiet 的额外 connected cells；纯 quiet-loading effect remains `INCONCLUSIVE`。
- `SECOND_ACTIVE_SHARED_SL_EFFECT_OBSERVED`：G3→G4 在第二个 active cell 加入后的 READ-window difference 可观测；不单独等同于已隔离的 coupling mechanism。
- `RECEIVER_BOUNDARY_CONDITIONED_CROSSTALK_DIFFERENCE_OBSERVED`：QB 与 passive 的 difference-of-differences 是 bounded observation；不升级为 QB back-action 的唯一机制。
- `PRIMARY_CLASSIFICATION: INCONCLUSIVE`；`QUICK_LABEL: QUICK_AMBIGUOUS`，因为本轮没有把 boundary、history、connected-cell loading 和 receiver boundary 完全正交隔离。

## Unknown / not proved

- 没有证明 canonical BVM、论文机制、硬件行为、普适 isolation、工艺 margin 或唯一 QB operating mechanism。
- 没有把 phase displacement、voltage area、I>Ic 或 local phase activity 当作 SFQ count；本任务也没有建立 downstream event identity。
- G1/G2 是新 Quick raw；G3/G4 是 hash-bound reuse 的旧 4×1 raw。没有运行 G5、参数 sweep、timestep sweep 或优化。

## Visualization acceptance

所有关键结论对应的 comparison HTML 位于 `plots/comparison/`，由 `scripts/josim-plot2.py` 使用 `sep_comb + dark + -j 2pi` 生成；plot manifest 与 viz QA 记录输入 label、hash 和单位检查。

关键页面：
- [SINGLE_VS_ARRAY_OUTPUT](plots/comparison/SINGLE_VS_ARRAY_OUTPUT.html)：COMMON_SL、LSL/RSL/LPSL；
- [SINGLE_VS_ARRAY_RLOOP_LOWER](plots/comparison/SINGLE_VS_ARRAY_RLOOP_LOWER.html)：RS、LS3、LS2、JS2 的 I/P/V；
- [SINGLE_VS_ARRAY_RLOOP_UPPER](plots/comparison/SINGLE_VS_ARRAY_RLOOP_UPPER.html)：LM3、LS1、JS1、JM2；
- [SINGLE_VS_ARRAY_MEMORY](plots/comparison/SINGLE_VS_ARRAY_MEMORY.html)：JM1/JM2 memory branch；
- [READ_BEFORE_STATE](plots/comparison/READ_BEFORE_STATE.html)、[ARRAY_PRE_READ_STATE](plots/comparison/ARRAY_PRE_READ_STATE.html)、[DIVERGENCE_TIMELINE](plots/comparison/DIVERGENCE_TIMELINE.html)：same-time READ 前状态与分歧时序；
- [ACTIVE_VICTIM_CROSSTALK](plots/comparison/ACTIVE_VICTIM_CROSSTALK.html)、[QUIET_VICTIM_CROSSTALK](plots/comparison/QUIET_VICTIM_CROSSTALK.html)：forward+mirror aggressor/victim；
- [PASSIVE_VS_QB_CROSSTALK](plots/comparison/PASSIVE_VS_QB_CROSSTALK.html)：passive、QB 和 `ΔQB−Δpassive`；
- [SINGLE_TO_ARRAY_BRIDGE_OVERVIEW](plots/comparison/SINGLE_TO_ARRAY_BRIDGE_OVERVIEW.html)：G0→G4 轨迹总览。

## Gate

`AWAITING_USER_REVIEW`; `user_reviewed: false`; `next_step_authorized: false`; `automatic_next_experiment: false`; `next_action: STOP`。
