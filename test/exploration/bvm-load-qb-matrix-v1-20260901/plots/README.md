# BVM_LOAD_QB_MATRIX_V1 classic 可视化

本目录严格复用项目既有 classic JoSIM viewer 方案：
`scripts/josim-plot2.py` 直接读取 raw CSV；所有页面使用 `sep_comb`、dark theme，含相位的页面使用 `-j 2pi`。

独立 physical case 页面直接使用原始 CSV；比较页面只在生成过程中使用临时 merged CSV，页面旁的 metadata 记录所有 raw 来源。没有重跑 JoSIM，也没有修改 raw。

## 建议先看

- [Physical BVM → JSL → scaled QB — four-point readout key data](comparisons/matrix-physical-readout-key.html)
- [Ideal source replay → scaled QB — four-point readout key data](comparisons/matrix-replay-readout-key.html)

## 独立 case 页面（48 个）

这些页面直接读取 raw CSV，保留四种 formal role；source、replay、physical 分别对应三类 fixture。

### Source 独立页面（16 个）

- [BVM → 12×JSL (320 µA) → GND source — 9 ps — logical1 READ](cases/source/9ps-12x320-logical1_read.html)
- [BVM → 12×JSL (320 µA) → GND source — 9 ps — logical0 READ](cases/source/9ps-12x320-logical0_read.html)
- [BVM → 12×JSL (320 µA) → GND source — 9 ps — logical1 READ=0](cases/source/9ps-12x320-logical1_no_read_control.html)
- [BVM → 12×JSL (320 µA) → GND source — 9 ps — logical0 READ=0](cases/source/9ps-12x320-logical0_no_read_control.html)
- [BVM → 8×JSL (500 µA) → GND source — 9 ps — logical1 READ](cases/source/9ps-8x500-logical1_read.html)
- [BVM → 8×JSL (500 µA) → GND source — 9 ps — logical0 READ](cases/source/9ps-8x500-logical0_read.html)
- [BVM → 8×JSL (500 µA) → GND source — 9 ps — logical1 READ=0](cases/source/9ps-8x500-logical1_no_read_control.html)
- [BVM → 8×JSL (500 µA) → GND source — 9 ps — logical0 READ=0](cases/source/9ps-8x500-logical0_no_read_control.html)
- [BVM → 12×JSL (320 µA) → GND source — 13 ps — logical1 READ](cases/source/13ps-12x320-logical1_read.html)
- [BVM → 12×JSL (320 µA) → GND source — 13 ps — logical0 READ](cases/source/13ps-12x320-logical0_read.html)
- [BVM → 12×JSL (320 µA) → GND source — 13 ps — logical1 READ=0](cases/source/13ps-12x320-logical1_no_read_control.html)
- [BVM → 12×JSL (320 µA) → GND source — 13 ps — logical0 READ=0](cases/source/13ps-12x320-logical0_no_read_control.html)
- [BVM → 8×JSL (500 µA) → GND source — 13 ps — logical1 READ](cases/source/13ps-8x500-logical1_read.html)
- [BVM → 8×JSL (500 µA) → GND source — 13 ps — logical0 READ](cases/source/13ps-8x500-logical0_read.html)
- [BVM → 8×JSL (500 µA) → GND source — 13 ps — logical1 READ=0](cases/source/13ps-8x500-logical1_no_read_control.html)
- [BVM → 8×JSL (500 µA) → GND source — 13 ps — logical0 READ=0](cases/source/13ps-8x500-logical0_no_read_control.html)

### Replay 独立页面（16 个）

- [Ideal source replay → scaled QB — 9 ps — 12x320 — logical1 READ](cases/replay/9ps-12x320-logical1_read.html)
- [Ideal source replay → scaled QB — 9 ps — 12x320 — logical0 READ](cases/replay/9ps-12x320-logical0_read.html)
- [Ideal source replay → scaled QB — 9 ps — 12x320 — logical1 READ=0](cases/replay/9ps-12x320-logical1_no_read_control.html)
- [Ideal source replay → scaled QB — 9 ps — 12x320 — logical0 READ=0](cases/replay/9ps-12x320-logical0_no_read_control.html)
- [Ideal source replay → scaled QB — 9 ps — 8x500 — logical1 READ](cases/replay/9ps-8x500-logical1_read.html)
- [Ideal source replay → scaled QB — 9 ps — 8x500 — logical0 READ](cases/replay/9ps-8x500-logical0_read.html)
- [Ideal source replay → scaled QB — 9 ps — 8x500 — logical1 READ=0](cases/replay/9ps-8x500-logical1_no_read_control.html)
- [Ideal source replay → scaled QB — 9 ps — 8x500 — logical0 READ=0](cases/replay/9ps-8x500-logical0_no_read_control.html)
- [Ideal source replay → scaled QB — 13 ps — 12x320 — logical1 READ](cases/replay/13ps-12x320-logical1_read.html)
- [Ideal source replay → scaled QB — 13 ps — 12x320 — logical0 READ](cases/replay/13ps-12x320-logical0_read.html)
- [Ideal source replay → scaled QB — 13 ps — 12x320 — logical1 READ=0](cases/replay/13ps-12x320-logical1_no_read_control.html)
- [Ideal source replay → scaled QB — 13 ps — 12x320 — logical0 READ=0](cases/replay/13ps-12x320-logical0_no_read_control.html)
- [Ideal source replay → scaled QB — 13 ps — 8x500 — logical1 READ](cases/replay/13ps-8x500-logical1_read.html)
- [Ideal source replay → scaled QB — 13 ps — 8x500 — logical0 READ](cases/replay/13ps-8x500-logical0_read.html)
- [Ideal source replay → scaled QB — 13 ps — 8x500 — logical1 READ=0](cases/replay/13ps-8x500-logical1_no_read_control.html)
- [Ideal source replay → scaled QB — 13 ps — 8x500 — logical0 READ=0](cases/replay/13ps-8x500-logical0_no_read_control.html)

### Physical 独立页面（16 个）

- [Physical BVM → 12×JSL (320 µA) → scaled QB — 9 ps — logical1 READ](cases/physical/9ps-12x320-logical1_read.html)
- [Physical BVM → 12×JSL (320 µA) → scaled QB — 9 ps — logical0 READ](cases/physical/9ps-12x320-logical0_read.html)
- [Physical BVM → 12×JSL (320 µA) → scaled QB — 9 ps — logical1 READ=0](cases/physical/9ps-12x320-logical1_no_read_control.html)
- [Physical BVM → 12×JSL (320 µA) → scaled QB — 9 ps — logical0 READ=0](cases/physical/9ps-12x320-logical0_no_read_control.html)
- [Physical BVM → 8×JSL (500 µA) → scaled QB — 9 ps — logical1 READ](cases/physical/9ps-8x500-logical1_read.html)
- [Physical BVM → 8×JSL (500 µA) → scaled QB — 9 ps — logical0 READ](cases/physical/9ps-8x500-logical0_read.html)
- [Physical BVM → 8×JSL (500 µA) → scaled QB — 9 ps — logical1 READ=0](cases/physical/9ps-8x500-logical1_no_read_control.html)
- [Physical BVM → 8×JSL (500 µA) → scaled QB — 9 ps — logical0 READ=0](cases/physical/9ps-8x500-logical0_no_read_control.html)
- [Physical BVM → 12×JSL (320 µA) → scaled QB — 13 ps — logical1 READ](cases/physical/13ps-12x320-logical1_read.html)
- [Physical BVM → 12×JSL (320 µA) → scaled QB — 13 ps — logical0 READ](cases/physical/13ps-12x320-logical0_read.html)
- [Physical BVM → 12×JSL (320 µA) → scaled QB — 13 ps — logical1 READ=0](cases/physical/13ps-12x320-logical1_no_read_control.html)
- [Physical BVM → 12×JSL (320 µA) → scaled QB — 13 ps — logical0 READ=0](cases/physical/13ps-12x320-logical0_no_read_control.html)
- [Physical BVM → 8×JSL (500 µA) → scaled QB — 13 ps — logical1 READ](cases/physical/13ps-8x500-logical1_read.html)
- [Physical BVM → 8×JSL (500 µA) → scaled QB — 13 ps — logical0 READ](cases/physical/13ps-8x500-logical0_read.html)
- [Physical BVM → 8×JSL (500 µA) → scaled QB — 13 ps — logical1 READ=0](cases/physical/13ps-8x500-logical1_no_read_control.html)
- [Physical BVM → 8×JSL (500 µA) → scaled QB — 13 ps — logical0 READ=0](cases/physical/13ps-8x500-logical0_no_read_control.html)


## 聚焦 comparison 页面

每个工作点的 source/replay/physical matched 页只显示回答问题所需的信号；physical-vs-replay 页用于观察负载后的 QB 轨迹与理想重放的差异。

- [BVM → 12×JSL source — 9 ps — matched cases](comparisons/9ps-12x320-source-matched.html)
- [Ideal source replay → scaled QB — 9 ps — matched cases](comparisons/9ps-12x320-replay-matched.html)
- [Physical BVM → 12×JSL → scaled QB — 9 ps / 12x320 — matched cases](comparisons/9ps-12x320-physical-matched.html)
- [Physical BVM → 12×JSL → scaled QB vs ideal replay — 9 ps / 12x320](comparisons/9ps-12x320-physical-vs-replay-qb.html)
- [BVM → 8×JSL source — 9 ps — matched cases](comparisons/9ps-8x500-source-matched.html)
- [Ideal source replay → scaled QB — 9 ps — matched cases](comparisons/9ps-8x500-replay-matched.html)
- [Physical BVM → 8×JSL → scaled QB — 9 ps / 8x500 — matched cases](comparisons/9ps-8x500-physical-matched.html)
- [Physical BVM → 8×JSL → scaled QB vs ideal replay — 9 ps / 8x500](comparisons/9ps-8x500-physical-vs-replay-qb.html)
- [BVM → 12×JSL source — 13 ps — matched cases](comparisons/13ps-12x320-source-matched.html)
- [Ideal source replay → scaled QB — 13 ps — matched cases](comparisons/13ps-12x320-replay-matched.html)
- [Physical BVM → 12×JSL → scaled QB — 13 ps / 12x320 — matched cases](comparisons/13ps-12x320-physical-matched.html)
- [Physical BVM → 12×JSL → scaled QB vs ideal replay — 13 ps / 12x320](comparisons/13ps-12x320-physical-vs-replay-qb.html)
- [BVM → 8×JSL source — 13 ps — matched cases](comparisons/13ps-8x500-source-matched.html)
- [Ideal source replay → scaled QB — 13 ps — matched cases](comparisons/13ps-8x500-replay-matched.html)
- [Physical BVM → 8×JSL → scaled QB — 13 ps / 8x500 — matched cases](comparisons/13ps-8x500-physical-matched.html)
- [Physical BVM → 8×JSL → scaled QB vs ideal replay — 13 ps / 8x500](comparisons/13ps-8x500-physical-vs-replay-qb.html)

## 读图边界

- 原始 `P(...)` 是 rad；`-j 2pi` 只显示连续相位 φ/2π（turns），不是 SFQ 计数。
- 图形只描述 raw/report 已有证据；事件、receiver 或 Gate 判定回到分析报告。
- source 是末级 JSL 接地；physical 是 `BVM → 12/8 JSL → QB`；replay 是 source 的 `I(B_LD1)(t)` 原样驱动 QB。
- QB 外部输出负载是 `R_LOAD OUT 0 10`，即 10 Ω 接地。
