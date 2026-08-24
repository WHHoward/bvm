# bvm-sfq-receiver-r1b-output-jj-20260819 topology

这是从实际 JoSIM netlist 展平并由 Graphviz 生成的结构图，不是 scientific verdict。
主图来自本 Exploration 内的代表性 simulation deck。

## 主图来源

- source deck：`test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/inputs/l010-b07-rd100-read1.cir`
- topology.svg：34 primitives，1 mutuals。
- 各输入 case 如果只改变 PWL、bias 数值或其他参数而未改变元件/连接结构，则共用此图。

## include / subcircuit provenance

- `.include jjmit.cir`
- `.include bvm_cell.cir`
- `.include r1b_output_jj_l010_b07_rd100.cir`

- subcircuit：`BVM`
- subcircuit：`SERIES_PICKUP_OUTPUT`

## 结构变体

- `l010-b07-rd100-loop-read1`：[`topology.svg`](variants/l010-b07-rd100-loop-read1/topology.svg)，source `test/exploration/bvm-sfq-receiver-r1b-output-jj-20260819/inputs/l010-b07-rd100-loop-read1.cir`；34 primitives / 1 mutuals。

## 绘图边界

- 矩形为 netlist 中的 primitive，椭圆为展平后的精确 net，菱形为 mutual coupling。
- `.tran`、`.print`、PWL 时间点和分析脚本不是电路元件，因此不画成元件；其余已解析 primitive 与 K mutual 均保留。
- 图中分组只用于阅读：BVM/source、receiver/interface、QB/regenerator、standard JTL 和 top-level bias。
- 附件中的 BVM/BQ 图片仅用于配色/版式参考；本图的节点和元件必须回到 source deck 核对。
