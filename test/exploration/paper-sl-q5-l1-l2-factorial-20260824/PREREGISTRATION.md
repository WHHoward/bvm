# PAPER-SL-Q5 — 2×2 L1/L2 factorial-completion point

状态：`PREREGISTERED_SINGLE_POINT`

记录时间：`2026-08-24T08:01:00+08:00`

Parent HEAD 必须为：

`67a7c9e3335343a09e90ec7ddfe5a4d7c38ea52c`

## 唯一科学问题

完成离散的 2×2 L1/L2 design，测试 proximal L1 effect 与 downstream L2
effect 是否近似独立、互补，或产生 nonlinear L1×L2 interaction：

| point | L1 | L2 | role |
|---|---:|---:|---|
| Q2 | 3.91 pH | 3.91 pH | accepted reference |
| Q3 | 4.50 pH | 3.91 pH | proximal-L1 sibling |
| Q4 | 3.91 pH | 4.50 pH | downstream-L2 sibling |
| **Q5** | **4.50 pH** | **4.50 pH** | **factorial completion** |

当前工作解释保持为：Q4 已显示 BJL2 可以增强，同时 BJL1 forward phase 和 node2
local routing 明显下降；因此完整 BJL1 slip 不是 BJL2 strengthening 的必要前提，
node3/L2/node4/BJL2 可能构成部分独立的 downstream mechanism。Q5 测试该解释在
恢复 L1 routing 后是否仍成立。

## Fixture construction

Q5 必须直接从 accepted PAPER-SL-Q2 `inputs/40u` 复制构建，不能从 Q3 或 Q4
派生。唯一 circuit text changes 是：

```text
L1 2 3 3.91p  ->  L1 2 3 4.50p
L2 3 4 3.91p  ->  L2 3 4 4.50p
```

所有 replay deck、`jjmit.cir`、输入波形、极性和 Q2 模型保持逐字一致。

## Frozen parameters

| parameter | value |
|---|---:|
| IBIAS | 40 µA |
| L1 / L2 | 4.50 / 4.50 pH |
| Lin / L0 | 0.80 / 1.323 pH |
| BJs/BJL1/BJL2 AREA | 0.50 / 0.36 / 0.54 |
| RJ1 / RJ2 | 33 / 22 Ω |
| RB | 6 Ω |
| output load | 10 Ω |
| configured timestep / stop | 0.0125 ps / 170 ps |
| main / post window | `[94,130)` / `[140,170)` ps |

## Matched cases and stop gate

执行顺序固定：

1. `logical1 + READ=0 control`；
2. `logical0 + READ=0 control`；
3. `logical0 + canonical READ`；
4. `logical1 + canonical READ`。

首个 control 若出现 solver/artifact failure、startup/free-running、完整
phase/area-consistent output transition 或其他 preregistered stop condition，
立即停止。control bounded 后继续其余三个 case。四 case 完成后无条件停止。

## Evidence contract

对 BJs/BJL1/BJL2 使用 continuous unwrapped phase、同一 JJ/同一 monotonic
segment 的直接 `∫Vdt/Φ0` 和 post bounded/retrap。`I>Ic`、voltage peak、总
phase range 和旧 fast-event 指标不能单独定义 event。

完整 BJL2 event 必须满足：

- 至少一个连续 monotonic BJL2 segment `≥1 turn`；
- 同 segment voltage area 与 phase evolution 一致；
- event 后 bounded/retrap、无第二完整 event；
- logical0 与两个 READ=0 controls 为零 complete event。

read1 BJs 的 multi-turn source activity不计作 downstream output event。

## Required metrics

每个 Q5 case 报告：

- BJs/BJL1/BJL2 phase、V、I、largest monotonic segments、same-segment area、event count；
- BJL1 positive/negative/signed current area与 cancellation diagnostic；
- BJL1 forward/backward phase segments；
- BJs→BJL1、BJL1→BJL2 onset/delay/overlap；
- `F_local`、`F_L1`、control-subtracted `G_local`；
- `BJL2/BJL1` phase-transfer ratio；
- settled post-window branch operating points；
- node2/node3/node4 KCL residuals；
- post retrap/free-running。

KCL 定义：

```text
node2: I(BJs) = I(L1) + I(BJL1) + I(RJ1)
node3: I(L1) + I(RB) = I(L2)
node4: I(L2) = I(L0) + I(BJL2) + I(RJ2)
```

Q5/Q2/Q3/Q4 read1 至少比较：

- `F_local`；
- BJL1 forward phase；
- BJL2 largest forward phase；
- `BJL2/BJL1` ratio；
- BJL1 positive/negative/signed area；
- BJs→BJL1 与 BJL1→BJL2 timing/overlap；
- 三条 KCL residual。

## Discrete interaction

对下列 read1 major metrics计算：

```text
interaction = Q5 - Q3 - Q4 + Q2
```

至少覆盖 `F_local`、BJL1 forward phase、BJL2 largest forward phase、
`BJL2/BJL1` ratio 和 relevant timing/overlap。interaction 是离散设计派生量，
不是新的 physical universal parameter。

解释规则：

- Q5 接近 additive prediction：L1/L2 effects largely independent；
- Q5 substantially exceeds additive prediction：positive nonlinear interaction；
- Q5 restores BJL1 but not BJL2：proximal routing recoverable, downstream gain does not combine；
- Q5 preserves Q4 BJL2 gain while restoring Q3 BJL1 behavior：complementary placement mechanisms；
- 只有完整连续 BJL2 segment + area consistency + retrap + zero controls 才能报告 local exactly-one event。

## Hard boundary

本轮只运行 Q5 一个 point。禁止追加 L point、bias、Ic/AREA、RJ、waveform reshape、
physical BVM integration 或 JTL。完成报告后停止，不提出 Q6。
