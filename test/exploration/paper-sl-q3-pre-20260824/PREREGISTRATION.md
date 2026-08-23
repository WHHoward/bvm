# PAPER-SL-Q3-PRE — BJs→BJL1 transfer analysis-only checkpoint

## Scope

这是一个 bounded、analysis-only Exploration。只读取三个已接受 raw：

1. QB-Q0 scaled ideal-current `68.4 µA` positive control；
2. PAPER-SL-Q1 paper-JSL logical1 READ，`IBIAS=35 µA`；
3. PAPER-SL-Q2 paper-JSL logical1 READ，`IBIAS=40 µA`。

本轮不运行 JoSIM，不改变任何 physical circuit，不连接 physical
BVM→12JSL→QB，也不接 JTL。Q0 的周期 raw 只作为已知 local-QB 正例和
transfer comparison；它不是 canonical BVM source evidence。

Registration time: `2026-08-24T04:22:08+08:00`
Parent HEAD: `1f6f3c90617c2c28adcb781a5fce747ad216f618`

## Single scientific question

为什么 Q0 68.4 µA replay 能产生约 `1.226 turn` 的完整 BJL1 segment，而
paper-JSL-derived replay 只有约 `0.8 turn`，尽管 BJs 仍有约 `14.09 turn`
的强 activity？

## Frozen analysis inputs

- `bq_cell.cir` scaled QB：BJs AREA=.50，BJL1=.36，BJL2=.54；
- `Lin=.8 pH`、`L0=1.323 pH`、`L1=L2=3.91 pH`；
- `RJ1=33 Ω`、`RJ2=22 Ω`、`RB=6 Ω`、output load=10 Ω；
- Q0/Q1/Q2 的 raw、netlist/model provenance 不变；
- Q0 实际时间步 `0.1 ps`，Q1/Q2 实际时间步 `0.0125 ps`；
- Q0 activity windows `[10,35) ... [260,285) ps`；
- Q1/Q2 activity window `[94,130) ps`；
- phase/area 使用 raw CSV 实际 time，不重采样、不插值；
- 同一 JJ、同一方向、同一 monotonic segment 的 direct `P/V` 才进行交叉校验。

## Registered calculations

对每个 case 直接计算：

- continuous unwrapped `P(BJs)`, `P(BJL1)`, `P(BJL2)`；
- largest monotonic segment 的 `ΔP_rad`、`ΔP_turns`、same-JJ voltage area；
- `I(BJL1)`, `I(L1)`, `I(RB)` 及 `I(RJ1)`, `I(L2)`, `I(BJL2)`, `I(RJ2)`, `I(L0)`；
- dominant BJs 与 paired BJL1 的 onset/end、相对时间、overlap/delay；
- node2/node3/node4 KCL residual；
- requested phase-transfer ratios；
- node2 local branch split：`I(BJL1)+I(RJ1)` 相对 `I(BJs)` 的 actual-time integrated fraction。

Q0 的 aligned comparison 选择包含其 global largest BJs segment 的 `210 ps`
pulse；requested ratios 仍使用各 JJ 全部注册窗口中的 global largest segment。

## Event boundary

本轮不以 total phase range、`I>Ic` 或 voltage peak 单独判定 event。若引用
local complete transition，只能写成同一 JJ、同一 monotonic segment 的 phase
与 voltage-area 一致，并保留“无 downstream JTL”的边界。

## Decision output

只允许输出以下之一：

- **A**：主要 threshold-limited，建议一个小的 BJL1-only ratio experiment；
- **B**：主要 waveform/routing/timing-limited，指出改变 threshold 前最高信息量的
  单一 internal routing variable；
- **C**：证据不足，并精确指出缺失 observable。

停止规则：完成分析报告与 provenance/hash checkpoint 后停止；不得降低
BJL2 AREA、连接 physical BVM→12JSL→QB、连接 JTL 或运行新的参数实验。
