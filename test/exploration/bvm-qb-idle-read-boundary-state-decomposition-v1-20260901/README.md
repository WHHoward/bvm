# BVM→QB idle/read boundary state decomposition

本目录记录 `BVM_QB_IDLE_AND_READ_BOUNDARY_STATE_DECOMPOSITION_V1` 的现有 raw
QUICK 分析。它针对父矩阵的 `13 ps / 12×320 / logical1_read` 工作点，比较：

- `A`：BVM→12×320 JSL→ground 的 grounded-JSL source reference；
- `B`：同一 source 波形的 ideal current replay→QB；
- `C`：BVM→12×320 JSL→physical QB。

分析使用固定窗口 W0–W4 和额外的历史核对窗口 `[94,130)` ps，采用共享
`scripts/bvmtools` 的 raw reader、phase unwrap、exact-grid compare 与 waveform
metrics。没有运行 JoSIM，也没有修改父目录的原始数据或电路模型。

## Results

- [简要结果](RESULT_BRIEF.md)
- [固定窗口报告](analysis/REPORT.md)
- [机器可读指标](analysis/metrics.json)
- [可复算 provenance](analysis/provenance.json)
- [关键可视化](plots/RESULT_OVERVIEW.html)
- [预注册分析边界](PREREGISTRATION.md)

## Boundary

结果是当前模型、当前 raw 和当前请求步长下的描述性 simulation evidence，
不是硬件测量。`P(...)` 原始单位为 rad；图中的 turns 是连续相位除以 `2π`，
不等于 SFQ 计数。current-time area 只是波形诊断量。状态为
`QUICK_AMBIGUOUS` / `AWAITING_USER_REVIEW`，本目录不自动升级物理 Gate 或论文级结论。
