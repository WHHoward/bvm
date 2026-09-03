# PHASE B command and exit record

工作目录：`/home/howard/JoSIM`

| Command | Exit | Result |
|---|---:|---|
| `python3 test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/generate_decks.py --check-only` | 0 | 6 个 deck 生成检查通过；不写文件 |
| `./test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/run.sh` | 0 | 6/6 solver runs 成功；每个 raw 1549 行 |
| `python3 test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/analysis/analyze.py --output test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/analysis/metrics_v4.json` | 0 | 修正后的六状态分析完成；随后保留旧分析痕迹并将 v4 作为 `metrics.json` |
| `python3 test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/analysis/render_plots.py` | 0 | 36 个 run 图 + 4 个 comparison 图；plot2 QA 全部通过 |
| 独立 stdlib CSV raw recheck（网格、phase/area、input、state level、KCL） | 0 | 30 个断言通过；不调用 task-local analyzer |

渲染参数固定为 `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`。
`plots/INDEX.html` 汇总各 run 和 comparison 链接；phase 轴检查为
`Phase (turns)` 与 `2pi`，不含 axis-level `Unknown`。
