# Stage A 可视化索引

绘图后端固定为 `scripts/josim-plot2.py`，配置为 `sep_comb`、`dark`、
`-j 2pi`。图只用于展示 raw，不改变 Stage A 的事件分类或 human gate。

## 原有 S1 图页

这些页面来自既有 raw：

`../raw/s1/run-01.csv`

- `RESULT_OVERVIEW.html`：原有 BVMout 电流和 QB/JTL 相位链，补充
  `V(QBIN)`、`V(QBOUT)` 和 `V(O6)` 作为输入、QB 输出、末级 JTL 节点电压。
- `RESULT_VOLTAGE_NODES.html`：对应
  `BVMSim/test_bvm_mixed_0.cir` 第 276–278 行的
  `V(QBIN)`、`V(QBOUT)`、`V(O1)`–`V(O6)`，用于观察 QB→JTL 节点电压传播。
- `RESULT_VOLTAGE_JUNCTIONS.html`：S1 raw 中 QB 三个 JJ 和六级 JTL 的
  `B01` 结电压，用于与同一结的 phase trace 对照；这些是诊断观测量，不是
  单独的 SFQ 计数。

## BVM 负载支路与 BVMout 图页

这些页面来自本次 print-only 诊断 raw：

`../raw/s1_bld_probes/run-01.csv`

对应 deck 为：

`../migrated/s1_bvmsim_qb_bld_probes.cir`

该 deck 只在原 S1 deck 末尾增加了 `B_LD12`、`B_LD2_12`、`B_LD3_12` 和
`BVMOUT` 的 `P/V/I` 观测，没有改变 `.tran`、拓扑、参数、激励或停止时间。

- `RESULT_B_LD12.html`：`P(B_LD12)`、`V(B_LD12)`、`I(B_LD12)`。
- `RESULT_B_LD2_12.html`：`P(B_LD2_12)`、`V(B_LD2_12)`、`I(B_LD2_12)`。
- `RESULT_B_LD3_12.html`：`P(B_LD3_12)`、`V(B_LD3_12)`、`I(B_LD3_12)`。
- `RESULT_BVMOUT.html`：`P(BVMOUT)`、`V(BVMOUT)`、`I(BVMOUT)`。
- `RESULT_BLD_BVMOUT_MERGED.html`：上面四个支路的全部 12 条曲线，按相位、
  电压、电流分成对应面板，共用同一时间轴，适合逐段放大查看。

原始 CSV 中 `I(BVMOUT)` 同时来自基准 deck 原有的 print 和新增 print，因而
出现两次。两次数值逐点相同；生成这些图时用 `bvmtools.raw` 明确选择了第 0
次出现，未让 pandas 对重复列做隐式科学选择。

本次 raw 有 7999 个样本，时间从 0 到 199.975 ps；名义输出步长为 0.025 ps，
未将数据降采样到 1 ps，因此合并图保留了更细的时间分辨率（原始输出中只有
一个 0.05 ps 间隔）。

电压单位为 V，电流保持 JoSIM 原始单位 A；`P(...)` 原始值为 rad，图中用
`-j 2pi` 显示为 `rad/(2π)` turns。相位转数只是相位显示，不单独等同于 SFQ
事件计数。
