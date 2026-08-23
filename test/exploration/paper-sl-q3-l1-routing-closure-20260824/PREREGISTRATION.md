# PAPER-SL-Q3 — L1 Routing Closure

状态：`PREREGISTERED_SINGLE_POINT`

记录时间：`2026-08-24T04:42:32+08:00`

## 唯一科学问题

在冻结的 PAPER-SL replay、`IBIAS=40 uA` 和 scaled QB 其余参数不变时，单点
`L1: 3.91 pH -> 4.50 pH` 是否能把 node2 的快速扰动更多地导入
`BJL1||RJ1`，从而提高 read1 的 BJL1 非线性响应，同时保持 logical0 和
READ=0 control 不触发，并保持 BVM/source guard。

## Stage-A 依据

`analysis/ANALYTIC_PRECHECK.md` 只使用已接受的 Q0 68.4-uA 正例、PAPER-SL-Q1
logical1/35-uA raw 和 PAPER-SL-Q2 logical1/40-uA raw。其结论是
`L1_DIRECTION_PRECHECK_PASS; NEXT_POINT_L1_4P50_PH`。

选择依据是 measured node2 KCL 和实际 CSV 时间上的 `dI(L1)/dt`：Q1/Q2 的
signed local-current fraction 约为 0.196/0.219，而 Q0 reference 约为 0.381；
对应的 complementary L1 fraction 约为 0.804/0.781 与 0.619。增大 L1 只作为
一个动态阻抗/分流假设，不把它表述成普遍的静态电流定律。

## 冻结参数与唯一改动

除下列一项外，完全继承 PAPER-SL-Q2 40-uA fixture：

| 参数 | 冻结值 |
|---|---:|
| `L1` | **4.50 pH**（唯一变更） |
| `L2` | 3.91 pH |
| `Lin` | 0.80 pH |
| `L0` | 1.323 pH |
| `BJs AREA` | 0.50 |
| `BJL1 AREA` | 0.36 |
| `BJL2 AREA` | 0.54 |
| `IBIAS` | 35 uA |
| `RJ1/RJ2` | 33/22 ohm |
| `RB` | 6 ohm |
| output load | 10 ohm |
| JJ model | accepted Q2 `jjmit.cir` snapshot |
| source replay | accepted Q2 40-uA paper-JSL waveforms, byte-identical decks |
| timestep / stop | Q2 fixture: 0.0125 ps / 170 ps |

注意：本任务中的“IBIAS=40-uA”指 PAPER-SL-Q2 的 `40u` source-replay fixture；
QB central bias 仍按该 fixture实际值 `IBIAS=35 uA` 冻结。不得将两者混写为同一个
电路参数。

## 拓扑和 KCL

采用 repository `bq_cell.cir` 的 native topology，只在 `L1 2 3` 的数值上改为
`4.50p`：

```text
Lin IN--1--BJs--2--L1(4.50pH)--3--L2(3.91pH)--4--L0--OUT
                 |                 |                 |
              BJL1||RJ1          RB to IBIAS       BJL2||RJ2
                 |                 |                 |
                GND              node 3             GND
```

在 node2 直接核对：

`I(BJs) = I(L1) + I(BJL1) + I(RJ1)`。

所有电流的方向沿 JoSIM 直接输出列定义，不用峰值或 `I>Ic` 代替 KCL 或事件
判据。

## Matched cases 与停止规则

四个 case 使用完全相同的 source PWL、模型、时间步长、停止时间、探针和分析窗口：

1. `logical1 + READ=0 control`（首跑）；
2. `logical0 + READ=0 control`；
3. `logical0 + canonical READ`；
4. `logical1 + canonical READ`。

首个 control 若出现 solver/artifact failure、startup/free-running、非选择性完整
transition 或明显 source instability，立即停止，不执行余下 case。

主分析窗口为 `[94,130) ps`；post window 为 `[140,170) ps`。若时间窗内有多个
候选 segment，逐段报告，不把全局 phase range 当事件数。

## 预注册测量与判据

每个 case 保存原始 CSV、JoSIM stdout/stderr、exit code、netlist/input snapshot
和 SHA-256。直接记录 BJs/BJL1/BJL2 的 `P/V/I`，L1/L2/Lin/RB/RJ1/RJ2 的电流，
并保留 source replay 的输入/输出信息。

报告必须包含：

- node2 KCL residual；
- `F_local = ∫[I(BJL1)+I(RJ1)]dt / ∫I(BJs)dt` 和 complementary L1 fraction；
- signed BJL1 current area；
- BJs/BJL1/BJL2 的 continuous unwrapped phase；
- 每个同一 JJ、同一 segment 的 voltage-time area `∫Vdt/Φ0`；
- onset/end、overlap/delay、post event count 和 retrap/free-running；
- logical0/control 的零事件检查；
- 如 raw 含 upstream guards，则与 accepted Q2/canonical 参考比较。

“完整 event”只在同一个 JJ 的 continuous monotonic phase segment 达到约一整圈，
并且同一时间 segment 的直接 JJ voltage area 与该 phase evolution 一致、随后有
bounded/retrap 时成立。`I>Ic`、voltage peak、总 phase range、旧
`fast_events` 均不能单独支持 event claim。

若 routing gain 出现但 BJL1 仍 subthreshold，则以 bounded routing conclusion
结束；不得追加 L1 sweep。若 read0/control 出现完整 event、multifire、free-running
或 source guard failure，按失败停止。不得改 BJL1/BJL2 AREA、central bias、L2、
RB/RJ1/RJ2、replay shape，也不得接 physical BVM->12JSL->QB 或 JTL。

## 预期 verdict 分类

- `ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED`
- `ROUTING_GAIN_WITH_BJL1_SUBTHRESHOLD`
- `L1_ROUTING_NO_GAIN`
- `NONSELECTIVE_OR_FREE_RUNNING_FAILURE`
- `SOURCE_BACK_ACTION_FAILURE`
- `INCONCLUSIVE`

本单点即使出现 BJL1/BJL2 local event，也不自动等于 downstream SFQ delivery。
