# Historical BVMSim operational baseline V1 — preflight

本文件是实验 setup commit 的 preflight 记录；运行后的精确 run、raw、分析
和图表哈希写入同目录的 provenance/manifest 文件。历史 BVMSim 树保持只读。

```yaml
experiment: bvmsim-bvm-qb-jtl-operational-baseline-v1-20260903
study_phase: EXPLORATION
source_class: HISTORICAL_BVMSIM
head_before_task: 2a2159a5d012011b44186600987f09ba46eed9b2
working_tree_before_setup: CLEAN
authorized_axes: [qb_bias_IB, qb_RJ1, physical_input_alpha]
nominal_RJ1_ohm: 12
nominal_RJ2_ohm: 4
nominal_QB_bias_uA: 250
operational_timestep_ps: 0.1
stop_time_ps: 200
automatic_next_experiment: false
```

## 只读 historical source

本轮不编辑、清理、重命名、删除或覆盖以下文件：

- `BVMSim/BQ.cir`
- `BVMSim/bvm_cell.cir`
- `BVMSim/test_bvm_mixed_0.cir`
- `BVMSim/data_tran.csv`
- `BVMSim/library_josim/jtl2.cir`
- `BVMSim/run.sh`
- `BVMSim/josim-plot.py`

`BVMSim/bvm_cell.cir` 是 historical/exploratory source，不是 canonical BVM
authority；其 `R_JM1=8 ohm`，canonical `circuits/bvm/bvm_cell.cir` 为
`6 ohm`。本实验不切换 canonical BVM。

## 预注册验收边界

- single-BVM：`S0-R`、`S1-R`、`S0-J`、`S1-J`，terminal sensing segment
  固定为 11 个 load JJ 加 1 个 `BVMout` JJ，共 12 个。
- 4-BVM：完整的 16 个状态；`READ1` 预期 count=`popcount(state)`。
- hard functional checks：expected count、0-count false trigger、JTL6
  end-to-end count、polarity、no-extra/no-loss、same-JJ phase/area
  consistency。dense burst 不要求固定 0.25 ps quiet gap。
- 对每个 weight 记录 weakest/strongest state、输入 spread、timing spread；
  不预先指定位置强弱。
- individual visualization 必须先于 comparison visualization；使用
  `scripts/josim-plot2.py`、`sep_comb`、dark、`-j 2pi`，只保留关键 probe。

## 停止规则

如果 nominal 16-state 不能支持 0→0、1→1、2→2、3→3、4→4 的功能映射，
记录 `BASELINE_FUNCTIONAL_FAIL`，不开始 margin sweep，等待用户审阅。
即使 baseline 功能通过，本轮结论也只适用于 historical BVMSim、固定
0.1-ps operational profile；不证明 canonical compatibility、timestep
convergence、process margin、T1 或论文机制。

