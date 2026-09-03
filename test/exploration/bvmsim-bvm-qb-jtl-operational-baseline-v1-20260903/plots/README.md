# Baseline visualization index

所有图均由 `scripts/josim-plot2.py` 生成，参数固定为 `sep_comb`、`dark`、
`-j 2pi`。图中 phase 轴是 `rad/2pi` turns，不是 SFQ count。

## Primary / compact overviews

- [RESULT_OVERVIEW.html](RESULT_OVERVIEW.html)：代表性的 4-BVM 状态和最终 JTL6。
- [SINGLE_2X2_OVERVIEW.html](SINGLE_2X2_OVERVIEW.html)：single-BVM 2×2 的关键 phase。

## Independent 4-BVM run plots

每个 4-BVM 独立图除核心 BVM/QB/JTL 信号外，还包含四个 BVM 的
`I(I_WL1..4)`、`I(I_BL1..4)`、`I(I_SE1..4)` 输入电流轨迹；这些轨迹用于
核对每个 state run 的 WL、BL、SE 激励时序和极性。

- [0000](runs/F4_0000_R12_T100/RUN_OVERVIEW.html)
- [0001](runs/F4_0001_R12_T100/RUN_OVERVIEW.html)
- [0010](runs/F4_0010_R12_T100/RUN_OVERVIEW.html)
- [0011](runs/F4_0011_R12_T100/RUN_OVERVIEW.html)
- [0100](runs/F4_0100_R12_T100/RUN_OVERVIEW.html)
- [0101](runs/F4_0101_R12_T100/RUN_OVERVIEW.html)
- [0110](runs/F4_0110_R12_T100/RUN_OVERVIEW.html)
- [0111](runs/F4_0111_R12_T100/RUN_OVERVIEW.html)
- [1000](runs/F4_1000_R12_T100/RUN_OVERVIEW.html)
- [1001](runs/F4_1001_R12_T100/RUN_OVERVIEW.html)
- [1010](runs/F4_1010_R12_T100/RUN_OVERVIEW.html)
- [1011](runs/F4_1011_R12_T100/RUN_OVERVIEW.html)
- [1100](runs/F4_1100_R12_T100/RUN_OVERVIEW.html)
- [1101](runs/F4_1101_R12_T100/RUN_OVERVIEW.html)
- [1110](runs/F4_1110_R12_T100/RUN_OVERVIEW.html)
- [1111](runs/F4_1111_R12_T100/RUN_OVERVIEW.html)

## Independent single-BVM run plots

- [S0-R](runs/S0-R/RUN_OVERVIEW.html)
- [S1-R](runs/S1-R/RUN_OVERVIEW.html)
- [S0-J](runs/S0-J/RUN_OVERVIEW.html)
- [S1-J](runs/S1-J/RUN_OVERVIEW.html)

每个图的精确 input/raw/output/hash/QA 记录在
`analysis/visualization_manifest.json`；图只用于查看，不作为 raw 或 Gate 的替代。
