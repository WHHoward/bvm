---
name: josim-viz
description: Render or inspect JoSIM waveform and netlist-derived topology evidence with correct units and compact classic defaults. Use for CSV/DAT plots, focused comparisons, schematics, or visualization indexes; visualization never certifies SFQ events or Gates.
---

# JoSIM 波形与拓扑可视化

这是项目唯一的可视化技能，统一负责 waveform、comparison、netlist-derived
topology 和相关索引。普通 Quick 默认只展示回答问题所需的关键数据：
CLASSIC_LOCKED、sep_comb、dark、phase rad/(2π) turns。

默认调用 scripts/josim-plot2.py，只选择输入、被审计结、输出或加载后 JTL
中的 2–5 条精确标签。full 或其他视觉风格必须由用户明确要求。绘图前
读取 CSV 表头；重复标签必须显式选择 occurrence，classic CLI 无法安全选择时
拒绝隐式取第一列。

## 波形边界

- JoSIM P(...) 原始值是 radians；-j 2pi 是数值除以 2π，标签应写
  phase turns (rad/2π)，不能写成 SFQ count。
- 图只描述 raw 中直接存在的信号；不能用图形峰值或相位阶跃替代
  josim-evidence-audit 的同 JJ phase/area、控制和传播证据。
- plot 不运行 JoSIM、不改变 raw、不改变分类；只生成可再生的
  plots/RESULT_OVERVIEW.html 或明确的 comparison 页面。

## 拓扑图边界

拓扑来源必须是所选 .cir 及其 resolved includes：
netlist/include → semantic schematic → deterministic layout →
renderer → endpoint validation → geometric validation。

出版级图使用电阻、电感、JJ、互感、接地、端口和电流箭头等真实元件符号；
必须保留连接端点、外部边界和有意省略项。Graphviz connectivity graph 只作
debug/provenance，不得作为 publication schematic 的默认入口，也不得从论文
图反推网表中不存在的元件。详细 artifact contract 见
references/topology-format.md。

维护的矩阵/拓扑辅助脚本位于 .agents/skills/josim-viz/scripts/。旧的
josim-exploration-visualization/scripts/ 仅是历史兼容 launcher，不是第二套
skill 或默认 renderer。批量刷新索引必须由用户明确授权，并保留每个 result、
control、source/reference 和 topology 的直接 provenance link。

## BVM 角色标签

成对 BVM 图使用明确角色：logical1_read、logical0_read、
logical1_no_read_control、logical0_no_read_control。同一 canonical READ
协议的极性、幅值、起点、宽度和负载不一致时标记 READ_PROTOCOL_MISMATCH；
WL-only 或反极性诊断不能伪装成 logical0。历史或 superseded 图保持可访问，
但不能成为当前结果的主证据。
