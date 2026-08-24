# bvm-internal-readout-20260819 canonical BVM schematic

本目录现在提供 canonical BVM 的第二阶段 publication-schematic prototype：

- [`schematic.svg`](schematic.svg) / [`schematic.png`](schematic.png) / [`schematic.pdf`](schematic.pdf)：
  clean 论文级结构图；
- [`schematic-annotated.svg`](schematic-annotated.svg) / [`schematic-annotated.png`](schematic-annotated.png) / [`schematic-annotated.pdf`](schematic-annotated.pdf)：
  annotated 版本，保留代表性 `+100 µA` init/read PWL、参数和 `R_LD=12 Ω` load boundary；
- [`connectivity-debug.svg`](connectivity-debug.svg) / [`connectivity-debug.dot`](connectivity-debug.dot)：
  历史 Graphviz connectivity graph，仅用于 debug/provenance，不是 canonical schematic。

## Source and provenance

- representative source deck：`test/exploration/bvm-internal-readout-20260819/inputs/pos-read-single.cir`；
- canonical BVM subcircuit：`circuits/bvm/bvm_cell.cir`；
- Exploration copy：`inputs/bvm_cell.cir`，SHA-256 与 canonical 文件一致：
  `ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4`；
- include：`jjmit.cir`、`bvm_cell.cir`；subcircuit：`BVM(WL, BL, SE, SL)`；
- representative case：positive stored state + canonical positive READ；其它只改变 PWL/bias/initialization 的 case 共用此结构图；
- `R_LD=12 Ω` 是所选 representative top-level deck 的外部 SL load，使用浅灰色显示。

## Schematic boundary

- 图中展开真实 BVM subcircuit，并按真实 connectivity 绘出 `R_WL/L_PWL`、`R_BL/L_PBL`、S-Loop、R-Loop、输出 `L_PSL/R_SL/L_SL` 及真实 JJ/resistor/inductor；没有从参考论文图中添加网表不存在的元件。
- `S-Loop` 使用克制蓝色区域，`R-Loop` 使用克制红色区域；内部 flattened node names 默认隐藏，只保留功能结构阅读所需的 junction dots 和端口。
- `WL`、`BL`、`SE` 是外部 control buses；`SL / Data Out` 是右侧输出路径。
- 图中右侧 `SL` 是 `XBVM1` 的 `SL1` 顶层端口别名；代表性 deck 的 `R_LD` 仍按真实网表连接在该顶层端口与 ground 之间。
- `I_WL1`、`I_BL1`、`I_SE1` 是 simulation-only ideal PWL sources，以外部 bus 和 annotated deck note 表示：WL+BL 初始化为 `+100 µA`，WL+SE canonical READ 为 `+100 µA`，时间窗口来自代表性 deck。
- 这些 omitted source elements 是 `OMITTED FROM DISPLAY, PRESENT IN SIMULATION`；它们不是从 simulation 中删除。
- `XBVM1` 没有作为黑盒框显示，而是展开为 BVM 结构；参考图只提供布局/符号/分区语言，不是 connectivity authority。

## Validation and renderer

- semantic layout：[`schematic.json`](schematic.json)；
- semantic netlist validation：[`schematic-validation.json`](schematic-validation.json)，以 [`schematic.json`](schematic.json) 为输入，必须为 `PASS`；
- geometric ledger：[`geometric-connectivity.json`](geometric-connectivity.json)；
- geometric validation：[`geometric-connectivity-validation.json`](geometric-connectivity-validation.json)，必须为 `PASS`；
- renderer：`scripts/schematic/render_bvm.py`；共用 Q0 V2 的 `scripts/schematic/symbols.py`、`geometric.py` 和两个 validator。

本图是 netlist-validated structural description，不是 BVM logical/SFQ/receiver scientific verdict。BVM prototype 在人工视觉审阅前不扩展到其它 Exploration。
