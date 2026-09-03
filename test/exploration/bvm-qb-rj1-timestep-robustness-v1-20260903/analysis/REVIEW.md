# REVIEW

分析产物已生成；最终科学审阅待 Sol XHigh reviewer。

本文件不把 solver exit 0、图形或 net turns 升级为 SFQ/Gate 结论。

## 执行与产物复核

复核时间：`2026-09-03T11:39:34+08:00`

- 24/24 个 effective runs 的 raw、deck、per-run metrics 均存在，global artifact status 为 `VALID`。
- 四-BVM 初始 root raw 保留不动；由于初始模板漏印 `P/V(BVMOUT)`，四-BVM 的结论级 effective raw 使用保留的 `attempt-03` 重跑。`attempt-02` 的路径错误、deck 和日志也保留，未伪装成成功运行。
- 四-BVM `attempt-03` 只补齐 `P/V(BVMOUT)` 并修正相对 include 路径；single-BVM 使用初始有效 raw。各次 solver exit code 均为 `0`，实际时间网格由分析脚本检查。
- 原始 BVMSim 源文件、历史 raw、共享 `jjmit`、共享 renderer 的 SHA256 与 `PREFLIGHT.md` / `provenance.json` 一致；本轮没有改写 BVMSim source evidence。
- 24 个 run 各有 5 张独立 HTML，QA 为 `PASS`；7 张 comparison HTML 的 QA 为 `PASS`。comparison 只使用共同时间网格，不插值。

## 验证命令

- `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools/test_bvmtools.py test/tools/test_strict_event_list.py test/plot/test_josim_plot2.py`：`34 passed`。
- `python3 -m py_compile analysis/analyze.py analysis/render_plots.py analysis/render_comparison.py analysis/make_summaries.py inputs/generate_decks.py inputs/make_four_probe_complete_attempt2.py inputs/make_four_probe_complete_attempt3.py`：exit `0`。
- `bash -n run.sh`：exit `0`。
- raw/hash、run 数量、独立图数量和 comparison 数量的最终机械复核：`PASS`。

## 待审查问题

请 Sol XHigh reviewer 独立判断：

1. coarse→fine 的约 `4→5` net trajectory 是否有足够证据被归因于 timestep-induced branch change，还是只能报告为未归因的 branch difference；
2. fine BJ2 的 continuous multi-turn 主段和 late sub-unit candidate 是否支持 separated SFQ，及其与 JTL B02 局部活动的关系；
3. 三种 RJ1 的 single-BVM S0/S1 protection、11 Ω 的过阻尼/margin-loss 可能性，以及是否有理由推荐 11.5 Ω 进入下一 candidate。

在 reviewer 返回前，当前 classification 保持 `INCONCLUSIVE_PENDING_SOL_XHIGH_REVIEW`，不执行任何后续实验。
