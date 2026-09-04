# History audit plots

本目录的详细 HTML 均由 `scripts/josim-plot2.py` 生成，统一使用：

- `sep_comb`
- `dark`
- `-j 2pi`

`P(...)` 在 plot input 中保存为连续展开的 raw radians，由 plot2 显示为 `rad/(2*pi)` turns；这些图只描述轨迹，不把 crossing 当作 SFQ 事件计数。

重建全部页面：

```bash
cd /home/howard/JoSIM
python3 test/exploration/bvmsim-old-new-1111-history-causal-audit-v1-20260904/analysis/analyze_history.py
python3 test/exploration/bvmsim-old-new-1111-history-causal-audit-v1-20260904/analysis/render_plots.py
```

`RESULT_OVERVIEW.html` 是版本化的导航页；其余详细 HTML 属于可再生的本地 visualization output。
