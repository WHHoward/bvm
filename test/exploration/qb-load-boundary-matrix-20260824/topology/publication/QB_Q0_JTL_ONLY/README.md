# 低 Ic QB → standard JTL direct publication schematic

这是一张由实际 representative deck 生成的论文级语义原理图，不是 Graphviz connectivity graph。

- topology_id：`QB_Q0_JTL_ONLY`
- representative deck：`test/exploration/qb-load-boundary-matrix-20260824/inputs-v2/B-q0-jtl-only/scaled-iin-68p4u.cir`
- topology signature：`c4a9a1a578c1742f10c90f464bd112a3a24b700cdaf8c32561daf57cd6a34963`
- clean：`schematic.svg/png/pdf`
- annotated：`schematic-annotated.svg/png/pdf`
- debug/provenance：`connectivity-debug.svg`（若源目录已有）

## Display boundary

内部 flattened node name、probe-only directive、完整 jjmit model 字段未塞入主图；它们没有从 simulation deck 删除。所有 top-level 电气元件都在 `schematic.json` 中登记并映射到功能区域或外部符号，semantic 与 geometric validation 必须为 PASS。
