# single-BVM 内部状态可视化补充

本次只补充可视化，不重新运行 JoSIM，也没有覆盖或修改任何历史 raw。

## 覆盖的 run

以下六个 run 均新增了
`plots/runs/<run>/BVM_INTERNAL_STATE.html`：

- `S0-R-CORRECTED`
- `S1-R-CORRECTED`
- `S0-J-CORRECTED`
- `S1-J-CORRECTED`
- `S0-J-CORRECTED-RERUN`
- `S1-J-CORRECTED-RERUN`

## 信号内容

每个页面选择 24 条可用的 BVM 状态/边界信号：

- BVM 内部四个 JJ：`B_JM1`、`B_JM2`、`B_JS1`、`B_JS2` 的 `P/V/I`，共 12 条；
- `V(SL1)`、`I(L_PSL|XBVM1)`、`I(L_SL|XBVM1)`，共 3 条；
- raw 中已经存在的 sensing-line 首尾 JJ `B_LD4_01`、`B_LD4_11` 的 `P/V/I`，共 6 条；
- `BVMOUT` 的 `P/V/I`，共 3 条。

这里的“全部 JJ”是指 BVM 内部四个 JJ，以及现有 raw 已打印的 SL 首尾 JJ。
实验 raw 并没有打印 SL 链中间的 `B_LD4_02..B_LD4_10`；本次不从缺失的 raw
中虚构这些信号，如需它们必须另做仅增加探针的重跑。

## 单位与完整性

- 使用 `scripts/josim-plot2.py` 的 `sep_comb`、`dark`、`-j 2pi` 经典方案；
- `P(...)` 在图中统一显示为 `rad/(2π)` turns，不将相位 turns 当作 SFQ 数量；
- 六个 raw 由 `bvmtools.raw.read_csv` 检查，均无重复列；
- 刷新前后 raw SHA-256 一致，脚本报告 `raw_unchanged=true`。

复现命令：

```bash
python3 test/exploration/bvmsim-single-corrected-baseline-v1-20260903/analysis/render_bvm_internal_state.py
```

逐页记录与哈希位于
`analysis/bvm_internal_state_plot_manifest_v1.json`；HTML 按仓库规则为生成文件，
保留在工作区的 `plots/runs/` 下。
