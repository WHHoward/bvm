# bvm-sfq-receiver-r14a-dcsfq-detector-20260823 topology

这是从实际 JoSIM netlist 展平并由 Graphviz 生成的结构图，不是 scientific verdict。
这是 analysis-only 目录；目录本身没有独立 simulation deck。主图继承已接受的 frozen fixture，仅用于说明分析所消费的拓扑。

## 主图来源

- source deck：`test/exploration/bvm-sfq-receiver-r12a-dcsfq-bvm-reaudit-20260823/inputs/phase-b-read1.cir`
- topology.svg：75 primitives，0 mutuals。
- 各输入 case 如果只改变 PWL、bias 数值或其他参数而未改变元件/连接结构，则共用此图。

## include / subcircuit provenance

- `.include ../../../../circuits/models/jjmit.cir`
- `.include ../../../../circuits/bvm/bvm_cell.cir`
- `.include ../../../../circuits/interface/DCSFQ_BVM.cir`
- `.include ../../../../circuits/standard/JTL.cir`

- subcircuit：`BVM`
- subcircuit：`THmitll_DCSFQ_BVM`
- subcircuit：`THmitll_JTL`

## 结构变体

- 本目录没有检测到结构不同的额外 netlist；参数/输入波形变体共用主图。

## 绘图边界

- 矩形为 netlist 中的 primitive，椭圆为展平后的精确 net，菱形为 mutual coupling。
- `.tran`、`.print`、PWL 时间点和分析脚本不是电路元件，因此不画成元件；其余已解析 primitive 与 K mutual 均保留。
- 图中分组只用于阅读：BVM/source、receiver/interface、QB/regenerator、standard JTL 和 top-level bias。
- 附件中的 BVM/BQ 图片仅用于配色/版式参考；本图的节点和元件必须回到 source deck 核对。
