# qb-q0-standalone-current-quantized-event-20260824 topology

本目录现在区分两个层级：

- [`schematic.svg`](schematic.svg) / [`schematic.png`](schematic.png) / [`schematic.pdf`](schematic.pdf)：
  publication-quality electrical schematic，供论文、组会和人工阅读使用。
- [`connectivity-debug.svg`](connectivity-debug.svg) / [`connectivity-debug.dot`](connectivity-debug.dot)：
  旧 Graphviz netlist connectivity graph，仅用于 debug/provenance，不是 canonical schematic。

publication schematic 使用固定的语义坐标和真实电路符号；它不是 Graphviz connectivity graph，
也不是 scientific verdict。

## 主图来源

- schematic source：`schematic.json`。
- source deck：`test/exploration/qb-q0-standalone-current-quantized-event-20260824/inputs/scaled-iin-68p4u.cir`。
- semantic connectivity validation：[`schematic-validation.json`](schematic-validation.json)，必须为 `PASS`。
- 各输入 case 如果只改变 PWL、bias 数值或其他参数而未改变元件/连接结构，则共用此图。

## include / subcircuit provenance

- `.include jjmit.cir`
- `.include bq_cell.cir`

- subcircuit：`BQ`

## 结构变体

- `test-bvm-paper-bq`：[`topology.svg`](variants/test-bvm-paper-bq/topology.svg)，source `test/exploration/qb-q0-standalone-current-quantized-event-20260824/inputs/test_bvm_paper_bq.cir`；15 primitives / 0 mutuals。
- `test-qb-final`：[`topology.svg`](variants/test-qb-final/topology.svg)，source `test/exploration/qb-q0-standalone-current-quantized-event-20260824/inputs/test_qb_final.cir`；4 primitives / 0 mutuals。

## publication schematic 绘图边界

- 主干按真实 `BQ` subcircuit 排列为 `In → Lin → Js → L1 → L2 → L0 → Out`。
- `JL1/RJ1` 和 `JL2/RJ2` 是 Q0 netlist 中真实存在的并联支路，因此在图中明确显示。
- `I_Bias` 是 top-level `I_IBIAS` 的语义显示，`RB` 连接到真实 bias node。
- `R_LOAD=10 Ω` 是当前 Q0 fixture 的真实输出负载，用浅灰虚线支路显示以保留 load boundary。
- `I_IN` 以 `In` 端口表示；`.tran`、`.print` 和 measurement helpers 不是 schematic 元件，详见 `schematic.json` 的 omitted list。
- 参考 BQ 图片只提供符号、留白和布局语法；所有元件和端点必须回到 source deck 核对。

## renderer / validation

本机没有 CircuitikZ、pdflatex 或 schemdraw，因此使用项目内 deterministic Matplotlib/SVG fallback：
`scripts/schematic/render_qb_q0.py` 与 `scripts/schematic/symbols.py`。
`scripts/schematic/validate_schematic.py` 会将 semantic endpoint 与 `bq_cell.cir` 和 top-level deck
逐项比较；validation 通过后才接受 schematic。
