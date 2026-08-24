# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 plots

## Registered comparison

- `9ps-vs-Wstar-qb-replay-comparison.html`：由仓库
  `.agents/skills/josim-exploration-visualization/scripts/plot_case_matrix.py`
  生成的 accepted PAPER-SL-Q1 9 ps replay 与本轮 W*=12 ps exact current
  replay 的 QB 对比。
- `../analysis/phase-c-matrix.json`：matrix plot 的唯一输入清单，声明了每个
  CSV、精确列名、case role、单位换算和线型。
- `9ps-vs-Wstar-qb-replay-comparison.metadata.json`：plot role、case provenance
  和 phase semantics。

图中 phase 统一表示：

> 连续相位 `φ/2π (turn)`，由原始 JoSIM `P(...)` 轨迹连续展开；未按脉冲
> 归零，也不等于 SFQ event count。

图仅用于查看 waveform/trajectory。正式 event 判据和 verdict 以
`analysis/PHASE_C_REPORT.md` 为准。
