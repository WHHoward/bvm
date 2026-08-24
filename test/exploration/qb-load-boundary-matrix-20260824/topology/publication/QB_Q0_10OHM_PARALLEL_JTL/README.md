# 低 Ic QB + 10Ω || standard JTL publication schematic

这是一张由实际 representative deck 生成的论文级语义原理图，不是 Graphviz connectivity graph。

- topology_id：`QB_Q0_10OHM_PARALLEL_JTL`
- representative deck：`test/exploration/qb-load-boundary-matrix-20260824/inputs-v2/C-q0-10ohm-parallel-jtl/scaled-iin-68p4u.cir`
- topology signature：`b0e8c66a4fd29fe2ad80ac7a7bf33af122605b58d6c9df861faa2e8b6deecc52`
- clean：`schematic.svg/png/pdf`
- annotated：`schematic-annotated.svg/png/pdf`
- debug/provenance：`connectivity-debug.svg`（若源目录已有）

## Display boundary

内部 flattened node name、probe-only directive、完整 jjmit model 字段未塞入主图；它们没有从 simulation deck 删除。所有 top-level 电气元件都在 `schematic.json` 中登记并映射到功能区域或外部符号，semantic 与 geometric validation 必须为 PASS。
