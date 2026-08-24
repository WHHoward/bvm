# Parallel QB→JTL interface mechanism batch

日期：2026-08-24  
实验级别：Exploration / bounded causal mechanism matrix  
parent HEAD：`d05d96ab3eb13dc19af9dbaa0b7a5d3ac92ac63d`

## 唯一科学问题

在已接受的 Q0 true-event operating point 下，Q0 输出事件与标准两级
JTL 之间的失败，主要来自 waveform/interface incompatibility，还是来自
downstream load boundary；一个小的串联隔离元件是否可以缓解该边界问题；
以及把标准 JTL 按 QB current class coherent scaling 后，是否仍能形成可用
的 JTL propagation interface。

本批次是离散的 causal mechanism matrix，不是参数 sweep。除 M2/M4/M5
预注册的单点外，不改变 QB、标准 JTL 或 source waveform 参数。

## Frozen Q0 source

所有 Q0 fixtures 均从 accepted source 独立生成：

- `IIN=68.4 µA`，原始六脉冲 `pulse(0 68.4u 10p 1p 1p 5p 50p)`；
- `IBIAS=35 µA`；
- BJs/BJL1/BJL2 AREA=`0.50/0.36/0.54`；
- `Lin/L0/L1/L2=0.80/1.323/3.91/3.91 pH`；
- `RJ1/RJ2=33/22 Ω`、`RB=6 Ω`、原始 `R_LOAD=10 Ω`；
- `dt=0.1 ps`、`stop=300 ps`；
- jjmit 与 `circuits/qb/bq_cell.cir` 使用 accepted repository copies。

Q0 + 10 Ω 是 accepted true-event comparator：六个输入 pulse 各有一个
BJL2 local phase/area-consistent event。该 local event 不自动等同于
downstream SFQ delivery。

## Frozen JTL

M1–M4 原样使用 `circuits/standard/JTL.cir` 的
`THmitll_JTL`，两个 cell 串联，所有内部 JJ、inductance、bias、阻尼和
`R_TERM=1 Ω` 不变。已接受的 R11-A standard-JTL positive-control 作为
provenance reference，不在 M1–M4 重跑。

## Fixtures

| fixture | source / boundary | single change or purpose |
|---|---|---|
| M1 | Q0 `V(OUT,t)` ideal voltage replay → JTL input `a` | no QB; waveform compatibility counterfactual |
| M2 | Q0 + original `10 Ω`; `OUT → R_ISO=10 Ω → JTL a` | finite series isolation with original Q0 boundary retained |
| M3 | Q0; remove original `10 Ω`; `OUT → R_SER=10 Ω → JTL a` | series-vs-shunt topology control; original boundary intentionally not retained |
| M4 | Q0 + original `10 Ω`; `OUT → L_ISO=10 pH → JTL a` | inductive series isolation |
| M5-PC | independent positive control → coherent scaled JTL | validates scaled JTL before coupling |
| M5-Q0 | Q0 + original `10 Ω`; direct Q0 `OUT →` scaled JTL | one current-class scaling point only |

M5 的 coherent scale is fixed at `s=54/250=0.216`, chosen to place the
standard JTL junctions near the Q0 BJL2 `54 µA` class. It is not a tuned
optimum and is not interpreted as a new universal JTL design.

## Cases and stop rules

M1–M4 each use the single Q0 six-pulse deck. M5-PC runs first. Only if M5-PC
passes its independent positive-control gate is M5-Q0 executed. All input,
raw, log and output paths are fixture-private.

Every event claim requires the same JJ and same monotonic segment to have:

1. continuous unwrapped phase segment of at least one turn;
2. same-segment direct voltage area with the same direction and numerical
   consistency;
3. bounded post behavior/retrap and no additional event.

For the already validated standard-JTL positive-control calibration, the
registered R11-A full activity window/net phase-area result is retained as the
fixture-validity reference; its largest monotonic segment is still reported
separately. This calibration exception is not used to upgrade a new Q0/JTL
trace into an event without the same-JJ phase/area evidence.

No voltage peak, current peak, `I>Ic`, total phase range, or legacy
`fast_events` count is an event criterion.

The batch stops after M1–M4 and, if gated, M5-Q0. It does not tune QB/JTL
parameters, add a conditioner, connect T1, or connect physical BVM/12-JSL.
