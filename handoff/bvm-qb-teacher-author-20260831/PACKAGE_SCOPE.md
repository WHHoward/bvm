# 本次抽取范围

本包是面向阅读和复核的实验副本，不是对原实验目录的改写。下列文件在复制时保持字节不变：输入 `.cir`、原始 `.csv`、实验报告、分析结果、运行日志、原始 manifest 和已经生成的关键图。

## 13 ps 12-JJ source 的 controls

13 ps 12-JJ source 实验原始记录只新跑了 `logical1-read` 和 `logical0-read`；它的两个 no-read controls 是沿用 `paper-sl-l0-20260824` 的 exact external-12-JSL no-read controls。本包将这两个文件显式放在：

- `experiments/02_13ps_bvm_12jj_source/inputs/reused_no_read_controls/`
- `experiments/02_13ps_bvm_12jj_source/raw/reused_no_read_controls/`

这样保留了原报告所说的 control provenance，也不把 9 ps no-read control 误写成新的 13 ps 仿真。

## 原始目录与分享包抽取目录

`01`、`04`、`06` 保留了对应实验的完整 matched-case raw/inputs/analysis/logs；`02`、`03`、`05`、`07` 只保留用户点名的 13 ps 分支，以及支撑它的原始报告、manifest、分析脚本和关键图。需要查看未复制的其他宽度或完整 dashboard 时，按 `EXPERIMENT_MAP.md` 的仓库原始目录回到 `test/exploration/`。

