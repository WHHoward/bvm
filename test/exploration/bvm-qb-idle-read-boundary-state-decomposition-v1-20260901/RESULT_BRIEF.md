# BVM_QB_IDLE_AND_READ_BOUNDARY_STATE_DECOMPOSITION_V1

## 状态

`QUICK_AMBIGUOUS` / `INCONCLUSIVE` / `AWAITING_USER_REVIEW` / `STOP`

## 本轮改变、固定与目的

- **改变**：没有改变科学参数或拓扑；只对父矩阵中 13 ps / 12×320 /
  logical1_read 的三份既有 raw 做边界条件分解。
- **固定**：A 为 BVM→12×320 JSL→ground 的 grounded-JSL source reference；
  B 为 exact source waveform→ideal current replay→QB；C 为
  BVM→12×320 JSL→physical QB。窗口和信号登记见 `PREREGISTRATION.md`。
- **目的**：区分 QB 是否改变 BVM 的初始化/稳定存储状态，以及主要不兼容是否在
  READ 动态阶段出现。本轮没有运行 JoSIM、没有重采样、没有插值。

## 主要观察（仅保留关键数据）

1. **[OBSERVED] A↔C 的 settled idle 差异很小，初始化扰动较大但仍是有限窗观测。**
   W2 的四个 BVM phase 信号最大 exact-grid 差为
   `0.000423989 turns`，`I(B_LD1)` 最大差为 `0.0410959 uA`；
   W1 的 BVM phase 最大差为 `0.00863408 turns`。

2. **[OBSERVED] READ 时 BVM/JSL 电流轨迹明显改变。** W3 grounded reference 的
   `I(B_LD1)` 正峰为 `79.0668 uA`（104.237 ps），
   physical QB 为 `68.1454 uA`（103.762 ps）；
   正面积分别为 `713.088` 和 `471.94 uA*ps`，
   signed area 分别为 `713.088` 和
   `464.125 uA*ps`。W3 exact-grid 最大差为
   `84.5943 uA`。这些是电流波形诊断量，不是 SFQ 计数。

3. **[OBSERVED] B↔C 的 QB pre-READ preload 接近。** W2 `BJS` median 为
   `5.47791e-06` 与 `7.65076e-07 turns`，
   其 exact-grid 最大差为
   `0.00019889 turns`；
   `L1` mean 为 `-15.12` 与 `-15.1217 uA`，
   exact-grid 最大差为
   `0.04128 uA`。

4. **[OBSERVED] B↔C 的主要 QB 差异出现在 READ。** W3 `BJS` p2p 为
   `8.39437`（ideal replay）与 `2.77658 turns`（physical），
   `BJL1` p2p 为 `1.28725` 与 `0.278799 turns`；
   `LIN` mean 为 `47.5557` 与 `30.9447 uA`。

5. **[PHYSICS-BASED INFERENCE]** 在本固定工作点和固定窗口下，证据最符合
   “pre-READ 状态大体保留、主要不兼容在 READ 动态阶段显现”的有界描述，即 H-D
   较一致；H-A/H-B/H-C 不能被本轮数据单独确立。W4 中部分 JS phase 仍在活动，
   所以不能把它当作最终 retrapped state，也不能从 local phase turns 推出下游 SFQ。

## 不证明什么

- 不证明唯一的 backfeed、界面 preload 或 READ 机制；未观测的节点仍为 `UNKNOWN`。
- 不证明硬件测量、SFQ delivery、系统逻辑 Gate、步长收敛或普适不可行性。
- 父实验冻结的历史 `[94,130)` 核对值与本报告的 W3 `[95,110)` 不同，不能混用。

## 后续选项（本轮未执行）

1. 由用户审核本 QUICK 结果后，选择是否把某个边界差异提升为 Candidate 复核。
2. 若需要机制定位，另行预注册节点级 interface/preload 证据，不回写本轮 raw。
3. 若需要结论级主张，另行冻结 timestep/convergence 与独立证据审计。

父窗口历史核对：grounded signed/positive/negative area =
`863.198` /
`899.297` /
`-36.0987 uA*ps`；
physical = `344.775` /
`499.106` /
`-154.331 uA*ps`。
