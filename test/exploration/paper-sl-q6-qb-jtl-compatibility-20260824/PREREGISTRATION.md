# PAPER-SL-Q6：冻结 Q5 QB → 标准两-cell JTL regenerative compatibility probe

日期：2026-08-24  
实验级别：Exploration / bounded coupling experiment  
parent HEAD：`b92fdb7a37b17cadaa2e9bc96f1689bf45178ceb`

## 唯一研究问题

在不改变 Q5 QB 参数、且不调节标准 JTL 的条件下，Q5 的近阈值 QB 输出能否选择性触发并传播一个完整的 regenerative event？logical1 + canonical READ 应最多产生一个贯穿两-cell chain 的 event；logical0 与两个 READ=0 controls 应为零。

这是耦合系统 compatibility screening，不把耦合成功倒推为 isolated-QB SFQ generation。

## 冻结对象

- Q5 QB：`L1=L2=4.50 pH`、`IBIAS=40 µA`；BJs/BJL1/BJL2 AREA=`0.50/0.36/0.54`；`Lin=0.80 pH`、`L0=1.323 pH`；`RJ1/RJ2=33/22 Ω`；`RB=6 Ω`。
- Q5 的 `bq_cell.cir`、`jjmit.cir`、四个 replay source decks 从 accepted Q5 `inputs/q5-l1-4p50-l2-4p50` 逐字复制；只在 deck 末端增加标准 JTL include、实例和 probes。
- JTL 原样使用 `circuits/standard/JTL.cir` 的 `THmitll_JTL`，两 cell、所有 JJ AREA、L1–L4、bias tee、内部 `IB1`、阻尼和端口均冻结。该 chain 的 positive-control validation 来自已接受的 R11-A；Q6 不重调、不重跑 JTL positive control。
- timestep=`0.0125 ps`、stop=`170 ps`；replay waveform、极性和四 case source byte-identical 于 Q5。

## QB-OUT → JTL 输入与 load boundary

Q5 的 `OUT` 直接连接标准第一 cell 的 input port `a`：

```text
XBQ   IN       OUT       IBIAS   BQ
R_LOAD OUT     0         10Ω              # Q5 load retained
XJTL1 OUT      JTL_MID   THmitll_JTL
XJTL2 JTL_MID  JTL_OUT   THmitll_JTL
R_TERM JTL_OUT 0         1Ω               # R11-A standard termination
```

`R_LOAD=10 Ω` 被保留为与 Q5 相同的并联 external load；没有将它替换成 JTL，也没有把它隐藏地并入 JTL。于是 Q6 的 `OUT` 节点同时看到原 Q5 10 Ω load 与标准 JTL input network，这是本次唯一 coupling-induced load change，必须在报告中直接报告 `I(R_LOAD)`、`I(L0|XBQ)` 和 `I(L1|XJTL1)`。

不增加 `R_IN/L_IN`、transformer、series resistor、conditioner 或 matching 元件。JTL 的 input port `a` 按 `JTL.cir` 原始内部网络直接接入 `OUT`；其 DC/transient path 及标准 bias tee 因此成为真实 reflected load。`R_TERM` 保持 R11-A 的标准输出端 termination。

## 四个 matched cases（control-first）

1. `logical1 + READ=0` control（首跑；若 control complete event、free-running、nonselective activity、solver/artifact failure，立即停止）；
2. `logical1 + canonical READ`；
3. `logical0 + canonical READ`；
4. `logical0 + READ=0` control。

## Registered measurements

### QB

直接记录 `P/V/I(BJs|XBQ)`、`P/V/I(BJL1|XBQ)`、`P/V/I(BJL2|XBQ)`；`P/V/I` 只在同一 JJ、同一方向、同一 monotonic segment 上配对。记录 `V(OUT)`、`V(JTL_MID)`、`V(JTL_OUT)`、`I(L0|XBQ)`、`I(R_LOAD)`。

### 两个 JTL cells

对 `XJTL1`、`XJTL2` 的 B1/B2 四颗 JJ 记录 `P/V/I`；记录每个 cell 的 L1–L4、IB1、RB1/RB2、input/mid/output node voltage 与 `I(R_TERM)`。

## Event 判据

每颗 JJ 的 event 只在以下证据同时满足时计数：

- continuous unwrapped phase；
- 一个连续 monotonic phase segment 达到至少 `1 turn`；
- 同一 JJ、同一 segment 的直接 voltage integral `∫Vdt/Φ0` 与 phase evolution 一致；
- event 后 bounded/retrap，且没有第二个完整 segment。

不使用 voltage peak、`I>Ic`、总 phase range、旧 `fast_events` 或单独的 output waveform peak 作为 event 证据。

## Verdict classes / stop rules

- `JTL_REGENERATIVE_PASS`：read1 贯穿两-cell 四颗 JTL JJ 各 exactly one；read0/control zero；Q5 BJL2 可保持 sub-turn；
- `COUPLED_QB_JTL_CLOSURE`：JTL loading 后 BJL2 自身也 exactly one，并通过两-cell exactly once；
- `NO_JTL_TRIGGER`：read1 的 JTL 第一颗 JJ 没有 complete event，或 QB 保持 near-threshold 且无完整 JTL propagation；
- `NONSELECTIVE_OR_MULTIFIRE_FAILURE`：logical0/control complete event，或 read1 出现多于一个 propagated event；
- `INCONCLUSIVE`：artifact、solver、phase/area、onset order 或 post evidence 不完整。

首个命中停止条件后停止；无论结果如何不调 JTL bias/AREA/L/R，不改 QB/Ic/AREA/L/R，不接 T1，不再连接其他 receiver。

