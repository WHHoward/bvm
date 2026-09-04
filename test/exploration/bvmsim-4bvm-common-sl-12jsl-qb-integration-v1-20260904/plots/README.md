# Visualization outputs

本目录使用 `scripts/josim-plot2.py` 的固定参数：
`-t sep_comb -c dark -j 2pi`。

- `RESULT_OVERVIEW.html` 是版本库保留的主图。
- `runs/<mask>/` 中是每个 run 的独立 BVM、COMMON_SL/JSL、QB 和 JTL 关键图。
- `comparison/` 中是少量 source-back-action、population、additivity、BJ2/JTL6 比较图；`comparison/data/` 是它们的派生 CSV 输入。
- 全部页面可由 `analysis/render_plots.py --write` 从不可变 raw 重新生成；raw 中 `P(...)` 仍为 radians，绘图脚本只做一次 `rad/(2*pi)`。

补充 HTML 页面按仓库规则不全部纳入 Git；它们在本地实验目录中保留，主图、数据输入、脚本和 manifest 可审计。
