# PHASE B result brief — six-state position closure

## 1. What changed

在 PHASE A `INFRA_REGRESSION_PASS` 之后，新实验使用了简化目录和共享
`bvmtools` API，运行了六个预注册状态：`0000`、`1000`、`0100`、`0010`、
`0001`、`1111`。每个状态都有独立 deck、raw、run.log 和 metadata。

## 2. What was held fixed

仍使用历史 `BVMSim/test_bvm_mixed_0.cir`、历史 BVM/QB/JTL、RJ1=12 Ω、
RJ2=4 Ω、QB bias=250 µA、六级 JTL、10 Ω 终端和
`.tran 0.1p 200p 45p`。没有使用 canonical BVM，没有改拓扑或器件参数。

## 3. Why it was tested

目标是把“状态是否确实写入并在 READ1 前闭合”和“不同 BVM 位置是否产生相同
的输入/输出行为”分开观察，同时严格区分累计 phase turns 与离散 SFQ event。

## 4. Important observations

- 六个 run 均执行成功、无模型告警、控制协议均为 `PROTOCOL_VALID`；用
  `PRE_READ1` 的 JM1 phase 电平符号判定时，观测状态分别为命令的
  `0000/1000/0100/0010/0001/1111`，最大预读 p2p 约 `0.0062 turn`。
- 四个 weight-1 状态的 `I(LIN|XBQ1)` READ1 绝对峰值分别为：
  `1000:149.1224 µA`、`0100:55.5952 µA`、`0010:120.9974 µA`、
  `0001:215.2944 µA`；因此相同权重的输入明显依赖 BVM 位置。
- BJ2 的累计 READ1 phase/area 为约 `0/2/1/2/3/4 turns`（按状态顺序），
  但 `1000/0010/0001/1111` 是单个连续 multi-turn running segment，
  不是对应数量的 clean separated events；`0100` 的最大严格段约
  `0.9762 turn`，也没有达到 1-turn complete-segment 门槛。
- JTL6 的 B02 clean event 数为 `0/2/1/2/3/4`；JTL1–JTL5 的计数也不
  保持统一的端到端传播模式。因此不能把这些局部/末级事件当作完整的
  六状态 transport closure。

## 5. Physical meaning

在这个历史 fixture 中，状态电平可以被 task-local 判据观察到，但相同
weight-1 的 BVM 位置会改变送入 QB 的波形及后续事件结构；累计 phase turns
不能替代严格的事件分段和 retrap 证据。

## 6. What this does not prove

不证明 canonical BVM 兼容性、论文机制身份、单 BVM 行为、timestep 收敛、
工艺裕度、参数最优性或任何 Gate/paper-level claim。

## 7. Current status

`STATE_CLOSED_POSITION_DEPENDENT_INPUT_WITH_COUNT_MISMATCH`（bounded
exploratory classification）。当前状态：`AWAITING_USER_REVIEW`。

## 8. Possible next options

1. 用户先复核六个 raw、`plots/INDEX.html` 和 `analysis/REPORT.md`。
2. 若需要，另行授权对位置依赖的 source/load-line 与严格事件对应关系做
   独立诊断。
3. 若需要，另行授权 canonical BVM 对照；本轮没有创建或运行该实验。
