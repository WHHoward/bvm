# REVIEW

分析产物已生成，Sol XHigh reviewer 已完成独立只读审阅；修正后的结果已重新生成并记录在 `analysis/SOL_XHIGH_REVIEW.md`。

本文件不把 solver exit 0、图形或 net turns 升级为 SFQ/Gate 结论。

## 执行与产物复核

复核时间：`2026-09-03T11:39:34+08:00`

- 24/24 个 effective runs 的 raw、deck、per-run metrics 均存在，global artifact status 为 `VALID`。
- 四-BVM 初始 root raw 保留不动；由于初始模板漏印 `P/V(BVMOUT)`，四-BVM 的结论级 effective raw 使用保留的 `attempt-03` 重跑。`attempt-02` 的路径错误、deck 和日志也保留，未伪装成成功运行。
- 四-BVM `attempt-03` 只补齐 `P/V(BVMOUT)` 并修正相对 include 路径；single-BVM 使用初始有效 raw。各 effective valid run 的 solver exit code 均为 `0`；attempt-02 的路径失败 exit code 为 `255`，实际时间网格由分析脚本检查。
- 原始 BVMSim 源文件、历史 raw、共享 `jjmit`、共享 renderer 的 SHA256 与 `PREFLIGHT.md` / `provenance.json` 一致；本轮没有改写 BVMSim source evidence。
- 24 个 run 各有 5 张独立 HTML，QA 为 `PASS`；7 张 comparison HTML 的 QA 为 `PASS`。comparison 只使用共同时间网格，不插值。

## 验证命令

- `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools/test_bvmtools.py test/tools/test_strict_event_list.py test/plot/test_josim_plot2.py`：`34 passed`。
- `python3 -m py_compile analysis/analyze.py analysis/render_plots.py analysis/render_comparison.py analysis/make_summaries.py inputs/generate_decks.py inputs/make_four_probe_complete_attempt2.py inputs/make_four_probe_complete_attempt3.py`：exit `0`。
- `bash -n run.sh`：exit `0`。
- raw/hash、run 数量、独立图数量和 comparison 数量的最终机械复核：`PASS`。

## Sol XHigh 审阅结论

- 四-BVM primary classification：`TIMESTEP_SENSITIVE`。
- RJ1=12 Ω 仅为 `BASELINE` 参考；RJ1=11.5/11 Ω 均为 `INCONCLUSIVE`，没有 winner。
- single-BVM protection：`INCONCLUSIVE`。
- coarse→fine 的约 `4→5` 是观察到的 timestep-conditioned trajectory selection，但不足以证明已识别的 dynamical branch switch，也不是 convergence proof。
- fine BJ2 是连续 multi-turn 主段加 late sub-unit activity，不是四个 separated SFQ；JTL B02 序列没有建立逐级 source-event identity。
- S0 是有限 fixture/read+post 窗口内的 bounded no-strict-trigger observation；S1 仅支持 source-level 约 1 Φ0 local observation，不能升级为完整六级 protection。
- 需要的 analysis/report 修正已完成；没有修改 raw/deck，也没有重跑仿真。

完整审阅意见见 [`SOL_XHIGH_REVIEW.md`](SOL_XHIGH_REVIEW.md)。

当前 classification 保持 reviewer 给出的受限结论；不执行任何后续实验，等待用户 review。
