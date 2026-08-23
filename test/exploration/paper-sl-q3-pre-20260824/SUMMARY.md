# PAPER-SL-Q3-PRE summary

## Verdict

**B — `BJS_TO_BJL1_WAVEFORM_ROUTING_TIMING_LIMITED`**

在当前三个已接受 fixture 中，BJs→BJL1 更像 waveform/routing/timing
限制，而不是可以主要归因于 BJL1 Ic。Q1/Q2 的 BJL1 current peak 并不低于
Q0，但其 BJL1 signed current transfer 和 node2 local-branch split 明显不同。

## Core comparison

| case | BJs largest | BJL1 largest | BJL2 largest | BJL1/BJs | BJL2/BJL1 | BJL2/BJs |
|---|---:|---:|---:|---:|---:|---:|
| Q0 68.4 µA | 16.4233 | 1.22553 | 1.09601 | 0.07462 | 0.89432 | 0.06674 |
| paper-JSL Q1 35 µA | 14.0921 | 0.829846 | 0.892527 | 0.05889 | 1.07553 | 0.06334 |
| paper-JSL Q2 40 µA | 14.0921 | 0.815414 | 0.944323 | 0.05786 | 1.15809 | 0.06701 |

Q1/Q2 的 BJL1 phase segment 分别只有 Q0 的约 67.7% / 66.5%。Q2 的
BJL2/BJL1 ratio 反而上升，因此当前主要差异集中在 BJs→BJL1。

## Most informative routing observable

在 paired BJL1 segment 上，
`F_local = integral(I(BJL1)+I(RJ1) dt) / integral(I(BJs) dt)`：

| case | `F_local` | `L1/BJs` | `BJL1` signed area (µA·ps) |
|---|---:|---:|---:|
| Q0 68.4 µA | 0.3798 | 0.6202 | +75.74 |
| paper-JSL Q1 35 µA | 0.1959 | 0.8041 | −7.25 |
| paper-JSL Q2 40 µA | 0.2187 | 0.7813 | −2.89 |

因此改变 BJL1 threshold 前，最高信息量的单一 internal routing variable
是 node2 的 `I(L1)` / local `(BJL1+RJ1)` KCL split waveform。

## Evidence boundary

Observed/Derived/Inferred/Unknown 详见
[REPORT.md](analysis/REPORT.md)。本结论只适用于三个既有 raw fixture；没有
新的 JoSIM、physical BVM connection、JTL 或 threshold experiment。
