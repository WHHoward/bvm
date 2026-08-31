# BVM/QB 实验与数据分享包

创建时间：2026-08-31（Asia/Shanghai）  
对应仓库 HEAD：`c8cdf07794d40f3376a1c542603c836b76535f99`

这个文件夹是给老师和论文作者查看的集中副本，包含相关 JoSIM 网表、原始 CSV、运行日志、分析结果、实验报告和少量关键可视化。原始实验目录没有被修改；本包只做复制和整理。

建议先看 [`EXPERIMENT_MAP.md`](EXPERIMENT_MAP.md)，再按编号进入 `experiments/`。每个实验目录里的 `REPORT.md`、`SUMMARY.md` 和 `manifest.yaml` 保留了原实验的判据、来源和限制。

## 一个必须说明的参数差异

当前仓库中与这组 BVM/JSL 测试对应的 12-JJ 网表实例是：

- 12 个串联 `jjmit area=3.2`，在本模型中约为 `IC=320 µA`；
- 没有找到这组实验中 12 个 `area=3.5`（约 `IC=350 µA`）的有效实例；检索到的 `area=3.5` 只出现在其他电路的单个 JJ 示例/说明中。

因此本包没有把 12×320 µA 改名为 12×350 µA。若“IC=350”是必须的实验条件，需要另开并重新记录一个 `area=3.5` 的实验，不能从现有数据倒推。

## 证据边界

- 这里的结果全部是 JoSIM 仿真，不是硬件测量。
- `raw/` 中的 CSV 是原始输出；没有为了展示而平滑、重采样或改变极性。
- logical 1、logical 0 和 READ=0 controls 尽量成组保留。
- phase turn、局部 JJ activity 和 SFQ delivery 不是同一个量；具体结论以各实验报告为准。
- 可视化只保留关键对比图，完整实验目录仍在仓库的 `test/exploration/` 下。

## 文件结构

```text
experiments/
  01_9ps_bvm_12jj_source             9 ps，BVM + 12-JJ external JSL
  02_13ps_bvm_12jj_source             13 ps，BVM + 12-JJ external JSL
  03_13ps_bvm_8jj_physical            13 ps，BVM + 8×500-µA JSL + QB
  04_9ps_12jj_ideal_replay_to_qb      9 ps，12-JJ 输出理想重放到 QB
  05_13ps_12jj_ideal_replay_to_qb     13 ps，12-JJ 输出理想重放到 QB
  06_9ps_bvm_to_qb_direct             9 ps，BVM SL1 直接 galvanic 接 QB
  07_13ps_bvm_to_qb_direct_physical   13 ps，BVM→12-JSL→QB 物理级联
supplementary/
  13ps_ideal_physical_trajectory_audit 相关 13 ps 轨迹审计
sources/                                canonical BVM/QB/JJ model 和 metric spec
SHA256SUMS.txt                          本分享包内文件校验值（不含自身）
```

`03` 的“8 个 JJ”实际是 `area=5`，即本模型约 `IC=500 µA`，不是 350 µA；`07` 的 13 ps 物理连接按仓库已有实现是 `BVM → 12×area=3.2 JSL → QB`。这些拓扑差异已在 `EXPERIMENT_MAP.md` 中单独标明。

分享包只抽取了用户点名的 9 ps/13 ps 数据和关键图；原始实验目录中未点名的 12/14/15 ps 以及完整 dashboard 没有重复复制。各目录保留的原始 `manifest.yaml` 可能因此引用仓库中的完整实验路径；包内的 `EXPERIMENT_MAP.md` 是本次抽取范围说明。
