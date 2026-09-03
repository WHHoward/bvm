# PHASE B detailed report — four-BVM six-state position closure

## Artifact and protocol layer

六个独立 run 的 JoSIM exit code 都为 `0`，日志没有 `Missing model` 或
`Using default model`。每个 raw 有 `1549` 个样本，时间范围为
`45.0--199.9 ps`；六个 raw 的时间 token 完全相同，因此跨状态比较使用
原始共同网格，没有插值。`dt_min≈0.1 ps`、`dt_max≈0.2 ps` 反映历史 raw
中保留的实际存储网格，不能把它重新描述成严格均匀网格。

完整探针包含四个 BVM 的 JM1/JM2/JS1/JS2 P/V/I、L_M1/L_M2/L_M3/L_PM/L_PSL、
SL 电压/电流，BVMout，QB 内部 P/V/I 与电感/偏置电流，以及六级 JTL 两个
结的 P/V。六个 deck 的静态 QA 均为 `ARTIFACT_VALID`，重复列为零。

WRITE1 使用各状态指定的 BL 极性；READ1 使用共同的 WL+SE。共享 stimulus
API 对每个 run 返回 `PROTOCOL_VALID`，WL/SE 在不同状态间的共同控制波形
比较为零差异；这是刺激一致性证据，不是功能 Gate。

## State closure observation

状态关联使用预注册的 task-local basis：`PRE_READ1` 中连续展开的
`P(B_JM1|XBVMn)/(2*pi)` 电平符号，配合该窗口的 p2p 稳定性。观测值约为：

| commanded | observed basis | status |
|---|---|---|
| `0000` | `0000` | `OBSERVED_STATE_MATCH_AND_CLOSED` |
| `1000` | `1000` | `OBSERVED_STATE_MATCH_AND_CLOSED` |
| `0100` | `0100` | `OBSERVED_STATE_MATCH_AND_CLOSED` |
| `0010` | `0010` | `OBSERVED_STATE_MATCH_AND_CLOSED` |
| `0001` | `0001` | `OBSERVED_STATE_MATCH_AND_CLOSED` |
| `1111` | `1111` | `OBSERVED_STATE_MATCH_AND_CLOSED` |

零位约为 `−0.938 turn`，一位约为 `+0.937 turn`；最大预读 p2p 约
`0.0062 turn`。这里的“observed basis”依赖本历史 fixture 的相位参考，
不等于普适存储机制证明。

## Position-dependent source evidence

weight-1 的 READ1 输入峰值如下。`I(LIN|XBQ1)` 与 `I(BVMOUT)` 在该拓扑中
呈相同的 branch-current 数值，故两者都列入 raw/plot，但不把它们当作两个
独立物理源。

| state / active BVM | `I(LIN)` peak abs (µA) | peak time (ps) | `V(QBIN)` peak abs (mV) |
|---|---:|---:|---:|
| `1000` / BVM1 | 149.1224 | 122.3 | 0.8674488 |
| `0100` / BVM2 | 55.5952 | 120.0 | 0.3849220 |
| `0010` / BVM3 | 120.9974 | 123.8 | 0.7843221 |
| `0001` / BVM4 | 215.2944 | 121.6 | 1.0953740 |

峰值范围为 `159.6992 µA`，高于预注册的 `0.1 µA` 描述性差异阈值。因此，
“相同 weight-1 只由一个理想 bit 决定、与位置无关”在这个 fixture 中没有
得到支持；这里仅报告实际输入波形差异。

## QB and JTL strict event evidence

所有 phase 数值的原始量是 JoSIM radians；显示 turns 使用
`continuous_unwrap(rad)/(2*pi)`。严格事件列表使用同一 junction 的 P/V、
实际存储网格、`complete_min=1.0 turn`、`clean_upper=1.15 turn` 和 bounded
retrap p2p `0.25 turn`。累计 phase/area 只作为 burst-total 描述，不作为事件
数 authority。

| state | expected popcount | BJ2 cumulative phase / area (turns) | BJ2 complete / clean | BJ2 continuous running | JTL6 B02 complete / clean |
|---|---:|---:|---:|---|---:|
| `0000` | 0 | 0.000092 / 0.000088 | 0 / 0 | no | 0 / 0 |
| `1000` | 1 | 2.001186 / 2.001181 | 1 / 0 | yes, ~1.996-turn segment | 2 / 2 |
| `0100` | 1 | 1.000304 / 1.000298 | 0 / 0 | no; largest ~0.9762 | 1 / 1 |
| `0010` | 1 | 2.000577 / 2.000570 | 1 / 0 | yes, ~1.9999-turn segment | 2 / 2 |
| `0001` | 1 | 3.000601 / 3.000591 | 1 / 0 | yes, ~3.0038-turn segment | 3 / 3 |
| `1111` | 4 | 3.999517 / 3.999502 | 1 / 0 | yes, ~3.9854-turn segment | 4 / 4 |

JTL B02 clean counts across `JTL1..JTL6` are：

| state | JTL1 | JTL2 | JTL3 | JTL4 | JTL5 | JTL6 |
|---|---:|---:|---:|---:|---:|---:|
| `0000` | 0 | 0 | 0 | 0 | 0 | 0 |
| `1000` | 0 | 0 | 0 | 0 | 1 | 2 |
| `0100` | 0 | 0 | 0 | 0 | 0 | 1 |
| `0010` | 0 | 0 | 0 | 0 | 0 | 2 |
| `0001` | 0 | 0 | 0 | 0 | 2 | 3 |
| `1111` | 0 | 0 | 0 | 0 | 1 | 4 |

BJ2 在所有状态的 complete segments 都只出现在 READ1；因此在本次严格
窗口检查中没有发现 READ1 之外的 QB BJ2 complete event。JTL 以及 QB 其他
junction 的完整逐窗口计数保存在 `analysis/metrics.json`。

## KCL and limits

共享 `bvmtools.kcl` 对 QB 三个内部方程进行了数值评估。READ1 最大残差
约为 `0.000035--0.000100 µA`（BJs/BJ1/RJ1/L1）、
`0.000050 µA`（L1+IB−L2）和 `0.000099--0.000140 µA`
（L2/BJ2/RJ2/L3，随状态变化）。本报告记录这些 residual，不把它们
擅自升级成新的容差 PASS。

这仍不证明 canonical BVM、single-BVM、timestep convergence、process margin、
机制身份或论文结论。它也不证明 JTL1→JTL6 具有完整的离散事件 identity
transport；JTL6 的局部 clean events 与上游计数不一致，正是需要保留的
负面证据。

## Bounded conclusion

`STATE_CLOSED_POSITION_DEPENDENT_INPUT_WITH_COUNT_MISMATCH`：在历史
BVMSim fixture 和本轮固定参数下，六个状态的 task-local phase-level basis
闭合，但位置依赖的 source/QB 输入和严格计数不匹配同时存在。该标签是
exploratory classification，不是 Gate 或 paper-level verdict。
