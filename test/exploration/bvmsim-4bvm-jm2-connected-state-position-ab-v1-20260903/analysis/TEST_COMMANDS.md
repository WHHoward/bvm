# 执行记录

本文件记录本轮 setup、运行、分析和可视化命令。原始 raw 未被重写。

| 阶段 | 命令 | 结果 |
|---|---|---:|
| Python 语法检查 | `python3 -m py_compile generate_decks.py analysis/*.py` | 0 |
| deck 生成静态检查 | `python3 generate_decks.py --check-only` | 0 |
| 运行前 static preflight | `python3 analysis/static_preflight.py --check-only` | 0 |
| 仓库空白检查 | `git diff --check` | 0 |
| 共享 bvmtools 测试（含 frozen strict anchors 与 synthetic event-list） | `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools` | 0（48 passed） |
| 预注册 setup 提交 | `git commit -m "experiment: preregister JM2-connected four-BVM six-state A-B"` | 0；`f5e0cddf` |
| 六状态物理运行 | `./run.sh` | 0；0000/1000/0100/0010/0001/1111 均为 solver exit 0 |
| 独立数值复算 | `python3 analysis/independent_check.py` | 0；`PASS` |
| 主分析 | `python3 analysis/analyze.py` | 0；`ARTIFACT_VALID`，independent check `PASS` |
| 可视化渲染 | `python3 analysis/render_plots.py` | 0；39 个图，raw hash unchanged |
| Sol XHigh 只读复核后的修订流水线 | `python3 analysis/render_plots.py && python3 analysis/independent_check.py && python3 analysis/analyze.py` | 0；39 个图、independent `PASS`、主分析 `ARTIFACT_VALID` |
| 全时窗 strict selectivity 补充 | `python3 -m py_compile generate_decks.py analysis/*.py && python3 analysis/independent_check.py && python3 analysis/analyze.py` | 0；BJ2/JTL B01/B02 均记录 PRE/WRITE0/READ0/WRITE1/READ1/TAIL |
| 最终 hash/link QA | 独立检查 checker/JSON/report/brief/review/gate/plot-manifest 哈希及 INDEX/overview 链接 | 0；所有绑定哈希一致，39/43 个本地链接均有效 |

实现阶段曾有两次在写出分析结果前被发现的脚本内部错误：独立复算中的记录数断言
误写为 8（已改为 12），主分析中的返回值解包错误（已修正）。修正后重新执行并
通过；两次均未修改 raw，也未重新运行 solver。Sol XHigh 复核提出的交付层修订
同样没有重新运行 solver。

可视化采用既有 `scripts/josim-plot2.py`、`sep_comb`、`dark` 和 `-j 2pi`。JoSIM
`P(...)` 原始单位为 rad，图中的 phase 仅显示为 rad/(2π) turns；它不是 SFQ 事件数。

图交付策略：39 个 standalone/focused Plotly HTML 和工作区 `plots/INDEX.html` 因
内嵌 Plotly 体积较大，按 `.gitignore` 作为可再生成文件保留在工作区，不纳入本次
Git 提交；本次提交纳入 `plots/RESULT_OVERVIEW.html`、derived CSV 和
`analysis/plot_manifest.json`。在 checkout 后运行
`python3 analysis/render_plots.py` 即可重建这些详细 HTML，索引链接相对于
`plots/` 目录。
