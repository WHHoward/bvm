# Crossover visualization index

本目录按四个条件统一展示：`O+ / O- / N- / N+`。

- `RESULT_OVERVIEW.html`：入口页，包含四条件的关键 crossover 图和分析报告链接。
- `runs/<condition>/`：每个条件的 7 张 standalone 图，先分别检查 BVM、LSL、QB 和 JTL，再看合并结果。
- `comparison/`：12 张四条件 crossover 图，重点覆盖 history control、109.9 ps state、四条 LSL、LIN/QBIN 和 BJ2 trajectory。

渲染统一使用 `scripts/josim-plot2.py` 的 `sep_comb + dark + 2pi`。JoSIM 的 `P(...)` 原始单位是 rad；图中只有经过 continuous unwrap 后转换的 phase 才标为 turns。图是描述性证据，不能单独证明 clean SFQ event count。

详细 HTML 因文件较大按仓库既有约定不强制纳入 Git；可用 `analysis/render_plots.py` 从保留的 raw CSV 和 plot inputs 重新生成。
