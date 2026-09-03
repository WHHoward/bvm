# 独立步长可视化

这些页面分别对应本次实验矩阵中的一个 raw，均由仓库统一的
`scripts/josim-plot2.py` 生成，布局为 `sep_comb`、深色主题。绘图只选取
关键链路信号，不修改 raw CSV，也不把图作为 SFQ 事件计数或物理 Gate 的
判定依据。

| 页面 | 条件 |
|---|---|
| [RESULT_T100.html](RESULT_T100.html) | `dt=0.1 ps`，从 `45 ps` 开始输出，历史 print-start 重现 |
| [RESULT_T050.html](RESULT_T050.html) | `dt=0.05 ps`，从 `0 ps` 开始输出 |
| [RESULT_T025.html](RESULT_T025.html) | `dt=0.025 ps`，从 `0 ps` 开始输出 |
| [RESULT_T0125.html](RESULT_T0125.html) | `dt=0.0125 ps`，从 `0 ps` 开始输出 |
| [RESULT_T100_FULL.html](RESULT_T100_FULL.html) | `dt=0.1 ps`，从 `0 ps` 开始输出，print-start 控制 |

每页包含：`I(BVMOUT)`、QB `BJ2` 的相位/电压、JTL1 `B01` 的相位/电压，
以及 JTL6 `B02` 的相位/电压。相位原始量为 JoSIM 的 radians，图中通过
`-j 2pi` 显示为 `rad/(2*pi)` turns；这只是相位显示单位转换，不是 SFQ
事件计数。

可再生命令：

```bash
python3 test/exploration/bvmsim-stagea-timestep-event-count-v1-20260902/analysis/render_individual_plots.py
```
