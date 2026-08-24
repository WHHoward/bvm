# QB load-boundary matrix：Q0/Q5 output compatibility

日期：2026-08-24
实验级别：Exploration / bounded causal load matrix
parent HEAD：`30590c9d9d4831f98c2a3f1db28ee7f6813eee59`

## 唯一科学问题

下游 load boundary 如何控制 QB 的 local quantization，以及它与已验证 standard two-cell JTL 的兼容性？

这不是参数 sweep。矩阵只改变离散 output boundary；QB JJ、bias、L/R、model、input waveform 和 JTL parameters 均不调节。

## Frozen source fixtures

### Q0 true-event source

直接以 accepted `qb-q0-standalone-current-quantized-event-20260824` 的 scaled `iin-68p4u.cir` 为 parent：

- `IIN=68.4 µA`、`IBIAS=35 µA`；
- BJs/BJL1/BJL2 AREA=`0.50/0.36/0.54`；
- `Lin/L0/L1/L2=0.80/1.323/3.91/3.91 pH`；
- `RJ1/RJ2=33/22 Ω`、`RB=6 Ω`；
- 原始 periodic `pulse(0 IIN 10p 1p 1p 5p 50p)`、六个 pulse start 和 `.tran 0.1p 300p` 不变；
- accepted comparator `Q0 + 10Ω`：每个 pulse 一个 BJL2 local phase/area event。

### Q5 near-event source

直接以 accepted Q5 `inputs/q5-l1-4p50-l2-4p50` 四个 deck 为 parent：

- `IBIAS=40 µA`、`L1=L2=4.50 pH`；
- 所有其他 QB AREA/L/R/model、replay source、`.tran 0.0125p 170p` 不变；
- accepted comparator `Q5 + 10Ω`：read1 BJL2 最大约 `0.968179 turn`，无 complete event；
- accepted Q6 comparator `Q5 + (10Ω || JTL)`：`NO_JTL_TRIGGER`。

## Five independent fixtures

每个 fixture 都从自己的 accepted parent 独立构建，拥有独立 `inputs/`、`raw/`、`logs/`；不从另一个已修改 fixture 再派生。

| fixture | source | output boundary | JTL |
|---|---|---|---|
| A — `q0-open` | accepted Q0 | 删除 `R_LOAD OUT 0 10`，无 downstream load | 无 |
| B — `q0-jtl-only` | accepted Q0 | 删除 10Ω，`OUT → XJTL1.a` | 两个 frozen standard cells |
| C — `q0-10ohm-parallel-jtl` | accepted Q0 | 保留 10Ω，并接 JTL | 两个 frozen standard cells |
| D — `q5-open` | accepted Q5 四 cases | 删除 10Ω，无遮载 | 无 |
| E — `q5-jtl-only` | accepted Q5 四 cases | 删除 10Ω，`OUT → XJTL1.a` | 两个 frozen standard cells |

JTL 原样使用 `circuits/standard/JTL.cir` / `THmitll_JTL`，保留其内部 bias、JJ AREA、L1–L4、bias tee、阻尼和 `R_TERM JTL_OUT 0 1`。Q0/Q5 fixtures 均不加入 `R_IN/L_IN`、transformer、conditioner 或其他 matching 元件。R11-A positive-control provenance 已接受，不在本矩阵重复运行。

## Cases and execution

Q0 A/B/C 各运行一个六 pulse deck；Q5 D/E 各运行四个 byte-identical matched cases：

- logical1 + READ；
- logical0 + READ；
- logical1 + READ=0；
- logical0 + READ=0。

五个 fixture 可并行执行，但每个 fixture 的 raw/log 输出目录完全独立。每个 fixture 必须先独立分析并给出 local verdict，再进行矩阵比较。

## Event evidence

所有 JJ 使用 continuous unwrapped phase、largest monotonic segment、同一 JJ/同一 segment 的 direct voltage area `∫Vdt/Φ0`、segment onset/end 和 post retrap/ringing。`I>Ic`、voltage peak、total phase range 和 legacy `fast_events` 不构成 event evidence。

Q0 逐 pulse 报告 BJs/BJL1/BJL2 phase/area/event count；Q5 四 matched cases 报告同样指标。JTL fixtures 额外报告四颗 JTL JJ 的 phase/area/event count、onset order、post behavior、JTL input branch current 和 final output。

## Matrix interpretation, not optimization

矩阵完成后只回答：

1. 10Ω 是否是 Q0 quantization/retrap 的必要边界；
2. true Q0 event 是否 survive JTL-only 和 parallel-JTL loading；
3. true Q0 event 是否传播通过 JTL；
4. Q6 failure 是否特异地来自 `10Ω || JTL` over-loading；
5. Q5 near-event 是否比 Q0 true-event 更 load-sensitive；
6. JTL loading 是否同时破坏 Q0 与 Q5，指向 interface mismatch。

本轮完成后停止，不调 QB/JTL 参数，不加 conditioner，不接 T1，不连接 physical BVM。
