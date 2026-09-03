# 4-BVM BVM_STATE 可视化补充

本次只更新可视化，不重新运行 JoSIM，也没有修改任何 `runs/*/raw.csv`。

## 补充内容

六个状态 run 的原有 `plots/runs/<state>/BVM_STATE.html` 已原位刷新，现包含：

- BVM1–BVM4 的全部四个内部 JJ：`B_JM1`、`B_JM2`、`B_JS1`、`B_JS2`；
- 每个内部 JJ 的 `P`、`V`、`I` 三类探针，共 `4 × 4 × 3 = 48` 条；
- 原有的 `V(SL1..SL4)` 和 `I(L_SL|XBVM1..4)` 八条 sensing-line 遥测。

因此每个 `BVM_STATE.html` 当前选择 56 条信号。同步将六个
`BVM_INTERNAL_PVI.html` 补全为 48 条内部 JJ P/V/I 信号，避免该辅助视图继续
只显示 JM1/JS1。

## 单位与完整性

- 渲染器固定为 `scripts/josim-plot2.py`，参数为 `sep_comb`、`dark`、`-j 2pi`；
- `P(...)` 原始数据是 radians，图中显示为 `rad/(2π)` turns；turns 不是 SFQ 计数；
- 六个 raw 均由 `bvmtools.raw.read_csv` 检查，表头无重复列；
- 刷新前后 raw SHA-256 一致，脚本报告 `raw_unchanged=true`；
- 旧的 SL 端点补充仍由既有 `BVMOUT_QB_INPUT.html` 页面承载，本次不改写 raw。

复现命令：

```bash
python3 test/exploration/bvmsim-4bvm-state-position-closure-v1-20260903/analysis/update_complete_bvm_state_plots.py
```

逐页记录与哈希位于
`analysis/plot_manifest_bvm_state_complete_v1.json`；HTML 按仓库规则为生成文件，
保留在工作区的 `plots/runs/` 下。
