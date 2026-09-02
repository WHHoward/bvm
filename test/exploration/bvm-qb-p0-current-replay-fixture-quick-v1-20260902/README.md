# BVM_QB_P0_CURRENT_REPLAY_FIXTURE_QUICK_V1

这是一次单运行 Exploration Quick Probe：把已有 P0 physical
`BVM → 12×320 JSL → scaled QB` 的完整 `I(LIN|XBQ)` 电流序列，以原始时间戳
literal replay 到相同 QB。P0 和 I0 都是已有 raw，本目录只新增一次 RP JoSIM
运行；不重跑 P0/I0，也不做偏置、Ic、扫描、磁耦合或 Formal Gate。

判定先检查输入 replay fidelity 和 W2 PRE 等价，再在 exact time grid 上计算
W3/W4 的 P0↔RP 与 I0↔P0 轨迹 RMS closure。BJL2 使用与既有 9/13 ps 锚点相同的
`StrictLocalEventSpec`/`strict_event_summary`，结论上限是同一 BJL2 的 local
phase/area compatibility，不是 SFQ 计数或下游接收证明。

## 入口

- [实验预注册](experiment.yaml)
- [PREFLIGHT](PREFLIGHT.md)
- [结果简报](RESULT_BRIEF.md)
- [分析报告](analysis/REPORT.md)
- [机器可读指标](analysis/metrics.json)
- [独立复核](analysis/REVIEW.md)
- [唯一关键图](plots/RESULT_OVERVIEW.html)
- [关键图输入](analysis/plot_input.csv)
- [最终人工审阅闸门](analysis/human-gate.yaml)

## 证据边界

`P()` 是 JoSIM 原始 phase radians；报告中的 turns 是完整轨迹 continuous unwrap
后除以 `2π`。local phase turn 不自动等于 downstream SFQ。raw、netlist、模型、
solver、时间网格、命令和 hash 都保留在本目录的 provenance 中；raw 不覆盖。
