# Physical BVM→12×JSL→scaled QB：SFQ closure publication schematic

这是一张由实际 representative deck 生成的论文级语义原理图，不是 Graphviz connectivity graph。

- topology_id：`BVM_JSL12_SCALED_QB_PHYSICAL`
- representative deck：`test/exploration/physical-bvm-jsl12-qb-sfq-closure-v1-20260824/inputs/13/logical1_read.cir`
- topology signature：`6bb970abed466863acc621b91ddd772282b97949ccd6243570632b6b8f203f82`
- clean：`schematic.svg/png/pdf`
- annotated：`schematic-annotated.svg/png/pdf`
- debug/provenance：`connectivity-debug.svg`（若源目录已有）

## Display boundary

内部 flattened node name、probe-only directive、完整 jjmit model 字段未塞入主图；它们没有从 simulation deck 删除。所有 top-level 电气元件都在 `schematic.json` 中登记并映射到功能区域或外部符号，semantic 与 geometric validation 必须为 PASS。
