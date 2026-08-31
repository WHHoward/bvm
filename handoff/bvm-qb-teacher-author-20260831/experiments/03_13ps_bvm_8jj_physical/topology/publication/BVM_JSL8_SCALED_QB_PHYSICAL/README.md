# Paper-like BVM→8×500 JSL→scaled QB：13 ps recheck publication schematic

这是一张由实际 representative deck 生成的论文级语义原理图，不是 Graphviz connectivity graph。

- topology_id：`BVM_JSL8_SCALED_QB_PHYSICAL`
- representative deck：`test/exploration/bvm-jsl8-500-physical-qb-recheck-v1-20260824/inputs/13/logical1_read.cir`
- topology signature：`fe9c11a4258d5c75cf24c21b4098b140149c2a536d5cc86017058f6c236e5508`
- clean：`schematic.svg/png/pdf`
- annotated：`schematic-annotated.svg/png/pdf`
- debug/provenance：`connectivity-debug.svg`（若源目录已有）

- JSL interface：`8` junctions；I_c≈500 µA（与 matched layout 对照）

## Display boundary

内部 flattened node name、probe-only directive、完整 jjmit model 字段未塞入主图；它们没有从 simulation deck 删除。所有 top-level 电气元件都在 `schematic.json` 中登记并映射到功能区域或外部符号，semantic 与 geometric validation 必须为 PASS。
