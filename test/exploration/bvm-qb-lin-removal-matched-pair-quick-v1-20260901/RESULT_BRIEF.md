# BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1

## 状态

`QUICK_NO_EFFECT` / `INCONCLUSIVE`（物理结论层）/ `AWAITING_USER_REVIEW` / `STOP`

本次只新增两次 JoSIM science run：P1 physical 和 I1 ideal replay。唯一干预是删除
QB 的 `Lin=0.8 pH`；没有继续 Lin sweep，也没有修改 BVM、12×320 JSL、QB bias/load、
timestep 或 magnetic coupling。

## 关键结果

- frozen I0 replay source 在 I1 中保持 exact PWL block；`I(I_REPLAY)` raw waveform
  也保持 exact-grid identity。
- W3 `[95,110)` ps 的 5 个 primary matched QB gap 均在预注册 ±20% 范围内：
  `D0=P0↔I0` 到 `D1=P1↔I1` 没有形成有意义的整体收窄。
- source-side G↔P0 与 G↔P1 的 4 个登记信号也没有达到 20% 的一致改善。
- 因此当前 Quick 标签为 `QUICK_NO_EFFECT`，不是“Lin 在所有条件下无效”的普遍结论。

## D0 → D1（W3 RMS）

| signal | D0 | D1 | gap reduction |
|---|---:|---:|---:|
| `P(BJS|XBQ)` | 2.2452 turns | 2.20492 turns | 0.0179419 |
| `I(L1|XBQ)` | 28.3754 uA | 29.0629 uA | -0.0242281 |
| `P(BJL1|XBQ)` | 0.519117 turns | 0.523841 turns | -0.00909924 |
| `I(L2|XBQ)` | 28.3754 uA | 29.0629 uA | -0.0242281 |
| `P(BJL2|XBQ)` | 0.43001 turns | 0.433204 turns | -0.00742804 |

## source-side W3 reduction

| signal | G↔P0 RMS | G↔P1 RMS | reduction |
|---|---:|---:|---:|
| `I(B_LD1)` | 28.4735 uA | 28.6732 uA | -0.00701641 |
| `I(B_LD12)` | 28.4735 uA | 28.6732 uA | -0.00701641 |
| `I(L_PSL|XBVM1)` | 28.4735 uA | 28.6732 uA | -0.00701641 |
| `V(SL1)` | 0.895583 mV | 0.891404 mV | 0.00466626 |

## BJL2 local diagnostic

- P0：SUBTHRESHOLD；largest Δphase=-0.122128 turns，area=-0.122131 Φ0，residual=3.23871e-06 turns
- P1：SUBTHRESHOLD；largest Δphase=-0.121121 turns，area=-0.121126 Φ0，residual=4.62602e-06 turns
- I0：CLEAN_ONE_SFQ_CANDIDATE；largest Δphase=1.01603 turns，area=1.01604 Φ0，residual=-7.91154e-06 turns
- I1：CLEAN_ONE_SFQ_CANDIDATE；largest Δphase=1.01603 turns，area=1.01604 Φ0，residual=-7.91154e-06 turns

这些是同一 BJL2 的局部 phase/voltage-area compatibility arithmetic；不等价于 SFQ
计数、下游接收或系统 Gate。I0 的历史锚点回归检查通过。

下一步必须等待用户审阅；本任务不自动启动新的实验。
