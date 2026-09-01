# BVM_LOAD_QB_MATRIX_V1

本 Exploration 完成了用户确认的物理级联矩阵：

`BVM → 12/8 个 JSL → scaled QB`

并配套运行了对应的 `source`（JSL 末端接地）和 `ideal replay`（把 source
的 `I(B_LD1)(t)` 原样接到 QB `IN`）对照。矩阵覆盖 9 ps/13 ps、12×320 µA
和 8×500 µA，以及 logical1/read、logical0/read、两个 no-read controls，
共 48 个 run。

## 先看这些

- [分析报告](analysis/REPORT.md)
- [独立数值/反例复核](analysis/REVIEW.md)
- [关键可视化入口](plots/README.md)
- [关键数据摘要](analysis/summary.csv)
- [逐 case metrics](analysis/metrics.json)
- [拓扑包](topology/README.md)

## 原始证据

- `raw/`：48 组 JoSIM CSV 与逐文件 SHA-256。
- `inputs/`：模型快照和每组完整网表。
- `logs/`：source、physical、replay 三类运行命令、stdout/stderr 和返回码。
- `manifest.yaml`：solver、模型、QB 负载、窗口、拓扑和 case 登记。

## 结论边界

这是当前模型和单一请求步长下的 exploratory simulation，不是硬件测量，
不包含磁耦合、JTL 或 T1。`P(...)` 原始单位为 rad；图中 turns 是除以
2π 后的连续相位显示，不是 SFQ 计数。输出负载是 QB `OUT` 到地的 10 Ω。
