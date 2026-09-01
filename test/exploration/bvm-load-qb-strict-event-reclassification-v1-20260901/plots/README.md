# Strict BJL2 event plots

三张图均由 `scripts/josim-plot2.py` 生成，使用 `sep_comb`、dark theme、`-j 2pi`；相位轴是连续相位 turns，不是 SFQ 计数。

- [9 ps / 12x320 ideal replay BJL2 strict event](9ps-12x320-replay-bjl2-strict-event.html)
- [13 ps / 12x320 ideal replay BJL2 strict event](13ps-12x320-replay-bjl2-strict-event.html)
- [Strict-event matrix: four ideal replay + four physical logical1 READ](strict-event-matrix.html)

前两张直接读取对应 raw CSV，并在 metadata 中记录 window displacement、最大单调段的 start/end、同段面积和分类。矩阵图只显示八个 logical1 READ case 的 BJL2 phase/voltage 与 VOUT 关键轨迹；四种 role 的完整 strict 数值仍以 `analysis/strict-event-summary.csv` 为准。

图是描述性证据，不替代同段 phase/area、控制和 post boundedness 审计。
