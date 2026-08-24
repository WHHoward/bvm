# QB-Q1：physical BVM → frozen scaled QB publication schematic

这是一张由实际 representative deck 生成的论文级语义原理图，不是 Graphviz connectivity graph。

- topology_id：`BVM_TO_SCALED_QB`
- representative deck：`test/exploration/qb-q1-canonical-bvm-scaled-qb-compatibility-20260824/inputs/logical1-read.cir`
- topology signature：`bd76882122473b615a6082d4e1ff0c93c15d31d6e6c48752b1ff696a2c94db1c`
- clean：`schematic.svg/png/pdf`
- annotated：`schematic-annotated.svg/png/pdf`
- debug/provenance：`connectivity-debug.svg`（若源目录已有）

## Display boundary

内部 flattened node name、probe-only directive、完整 jjmit model 字段未塞入主图；它们没有从 simulation deck 删除。所有 top-level 电气元件都在 `schematic.json` 中登记并映射到功能区域或外部符号，semantic 与 geometric validation 必须为 PASS。
