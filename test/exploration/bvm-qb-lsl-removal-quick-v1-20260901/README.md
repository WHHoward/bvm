# BVM→QB L_SL removal Quick probe

本目录记录 `BVM_QB_LSL_REMOVAL_QUICK_V1`。它只运行一个新 candidate：在
13 ps、12×320、logical1/read、scaled QB 条件下删除 BVM 输出链的 `L_SL=0.4 pH`，
并把 `R_SL` 输出直接接到 `SL`。canonical BVM 与父矩阵 raw 不改写。

## 结果入口

- [RESULT_BRIEF.md](RESULT_BRIEF.md)
- [固定窗报告](analysis/REPORT.md)
- [机器可读指标](analysis/metrics.json)
- [candidate provenance](analysis/provenance.json)
- [唯一关键可视化](plots/RESULT_OVERVIEW.html)
- [候选 run 目录](quick/BVM_QB_LSL_REMOVAL_QUICK_V1)
- [保留的首次后处理失败说明](quick/BVM_QB_LSL_REMOVAL_QUICK_V1/POSTPROCESSING_FAILURE.md)

## 对照

- BASELINE physical：父矩阵已有 `BVM → 12×320 JSL → QB` raw；不重跑。
- GROUNDED reference：父矩阵已有 `BVM → 12×320 JSL → ground` raw。
- IDEAL replay：父矩阵已有 exact source waveform → ideal current replay → QB raw。
- CANDIDATE：本目录 experiment-local BVM variant，只删除 `L_SL`。

结果是当前模型、单一 Quick 条件和单一请求步长下的 exploratory simulation
evidence，不是硬件测量；局部 phase/area compatibility 不是 SFQ delivery 或
system Gate。用户复核后状态固定为 `USER_REVIEWED` / `STOP`，不授权下一物理实验。
