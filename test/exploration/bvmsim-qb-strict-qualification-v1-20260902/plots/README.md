# Stage A 可视化索引

所有图都来自同一份既有 S1 raw：

`../raw/s1/run-01.csv`

绘图后端固定为 `scripts/josim-plot2.py`，配置为 `sep_comb`、`dark`、
`-j 2pi`。图只用于展示 raw，不改变 Stage A 的事件分类或 human gate。

## 图页

- `RESULT_OVERVIEW.html`：原有 BVMout 电流和 QB/JTL 相位链，补充
  `V(QBIN)`、`V(QBOUT)` 和 `V(O6)` 作为输入、QB 输出、末级 JTL 节点电压。
- `RESULT_VOLTAGE_NODES.html`：对应
  `BVMSim/test_bvm_mixed_0.cir` 第 276–278 行的
  `V(QBIN)`、`V(QBOUT)`、`V(O1)`–`V(O6)`，用于观察 QB→JTL 节点电压传播。
- `RESULT_VOLTAGE_JUNCTIONS.html`：S1 raw 中 QB 三个 JJ 和六级 JTL 的
  `B01` 结电压，用于与同一结的 phase trace 对照；这些是诊断观测量，不是
  单独的 SFQ 计数。

电压单位为 V；`P(...)` 在主图中显示为 `rad/(2π)` turns。重复标签问题按
`bvmtools.raw` 规则处理；本次 S1 raw 的选定电压标签无重复列。
