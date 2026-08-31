# Topology provenance

本 Exploration 没有引入新的电气连接拓扑，因此不复制一张新的 publication
schematic。QB replay 使用已验证的 `PAPER_JSL_TO_FROZEN_QB` shared topology；
其 canonical publication/annotated/debug 图位于：

- `test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic.svg`
- `test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/schematic-annotated.svg`
- `test/exploration/paper-sl-q1-20260824/topology/publication/PAPER_JSL_TO_FROZEN_QB/connectivity-debug.svg`

本轮的变化是 READ protocol correction、12 个 external-series JSL 的
plateau width 以及 source waveform provenance，不是 QB 电路连接变化。12/13/14/15
ps 的物理 source decks 与 frozen QB replay deck 分别保存在本目录的
`inputs/` 下；physical BVM→JSL→QB 尚未连接，因此不能把 shared replay
schematic 解读为 physical cascade schematic。

## Display boundary

`PAPER_JSL_TO_FROZEN_QB` 的 schematic 显示实际 replay receiver topology；
source-waveform extraction、CSV probe 和 analysis-only helpers 是
`OMITTED FROM DISPLAY, PRESENT IN SIMULATION/ANALYSIS`。新的 READ semantic
audit 也不改变 electrical connectivity。

## Validation

本目录复用 Q1 已通过的 semantic/geometric validation；topology signature 和
shared-by provenance 由 `docs/TOPOLOGY_ALIGNMENT_MANIFEST.yaml` 维护。
