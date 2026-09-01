# BVM → JSL source fixture publication schematic

这是一张由实际 representative deck 生成的论文级语义原理图，不是 Graphviz connectivity graph。

- topology_id：`BVM_JSL_SOURCE`
- representative deck：`test/exploration/bvm-load-qb-matrix-v1-20260901/inputs/source/13ps/12x320/logical1_read.cir`
- topology signature：`source-boundary-bvm-jsl-ground`
- clean：`schematic.svg/png/pdf`
- annotated：`schematic-annotated.svg/png/pdf`
- debug/provenance：`connectivity-debug.svg`（若源目录已有）

- JSL interface：`12` junctions；I_c≈320 µA（与 matched layout 对照）

## Display boundary

内部 flattened node name、probe-only directive、完整 jjmit model 字段未塞入主图；它们没有从 simulation deck 删除。所有 top-level 电气元件都在 `schematic.json` 中登记并映射到功能区域或外部符号，semantic 与 geometric validation 必须为 PASS。
