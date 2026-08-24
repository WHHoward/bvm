# 低 Ic QB → RISO=10Ω → standard JTL publication schematic

这是一张由实际 representative deck 生成的论文级语义原理图，不是 Graphviz connectivity graph。

- topology_id：`QB_M2_RISO10_JTL`
- representative deck：`test/exploration/parallel-qb-jtl-interface-mechanism-20260824/inputs/M2-riso10/main.cir`
- topology signature：`18bc023d1f93bb00cfe9af608d6952a86310092caa7ecfff8f63d2bb4fad1be0`
- clean：`schematic.svg/png/pdf`
- annotated：`schematic-annotated.svg/png/pdf`
- debug/provenance：`connectivity-debug.svg`（若源目录已有）

## Display boundary

内部 flattened node name、probe-only directive、完整 jjmit model 字段未塞入主图；它们没有从 simulation deck 删除。所有 top-level 电气元件都在 `schematic.json` 中登记并映射到功能区域或外部符号，semantic 与 geometric validation 必须为 PASS。
