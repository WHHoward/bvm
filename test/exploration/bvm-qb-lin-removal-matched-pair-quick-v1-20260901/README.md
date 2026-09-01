# BVM→QB Lin removal matched-pair Quick

本目录记录 `BVM_QB_LIN_REMOVAL_MATCHED_PAIR_QUICK_V1`。它只改变 QB 输入电感：
baseline 为 `Lin=0.8 pH`，candidate 删除 `Lin`；只新增 P1 physical 和 I1 ideal replay
两次运行。P0/I0/G 均复用父矩阵已有 raw。

## 结果入口

- [实验预注册](PREREGISTRATION.md)
- [实验前预检](PREFLIGHT.md)
- [Result brief](RESULT_BRIEF.md)
- [固定窗 matched-pair 报告](analysis/REPORT.md)
- [机器可读指标](analysis/metrics.json)
- [provenance](analysis/provenance.json)
- [唯一关键可视化](plots/RESULT_OVERVIEW.html)
- [可复现的关键可视化输入](analysis/plot_input.csv)
- [运行目录（P1/I1 raw、日志和输入快照）](run)
- [运行器汇总](run/manifest.json)
- [运行器 provenance](run/provenance.json)
- [运行器分析](run/analysis.json)

## 语义

I0→I1 是理想输入边界下 QB 内部对 Lin 的响应；P0→P1 是真实 BVM/JSL/QB 耦合系统
响应；D0→D1 是 physical-to-matched-ideal gap。图只展示回答这些问题所需的关键
waveforms，继续使用 `josim-plot2.py` 的 `sep_comb / dark / -j 2pi` classic profile。
`run/` 下的文件是运行器在两次候选仿真结束时产生的原始汇总；最终 matched-pair
判据和人工审阅闸门以本目录根部的 `RESULT_BRIEF.md`、`analysis/REPORT.md` 与
`analysis/human-gate.yaml` 为准。

该目录只表示当前模型、单一 13 ps 条件和单一 Lin intervention 下的 exploratory
simulation evidence，不是硬件测量或 Formal interface Gate。完成运行后状态固定为
`AWAITING_USER_REVIEW / STOP`，不自动开始下一个实验。
