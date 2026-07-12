---
name: skill-usage
description: 本项目安装了 ECC + Superpowers 技能套件，所有任务开始前必须检查并使用适用 skill
metadata: 
  node_type: memory
  type: project
  originSessionId: c5521155-33ba-4655-a787-c46e6bb6b2b1
---

JoSIM 项目安装了完整的 ECC + Superpowers 技能套件。

**核心规则**：每次响应前必须先检查是否有适用的 skill，即使只有 1% 可能也要调用 Skill 工具。不要凭惯性直接动手。

**高频使用的 skill**：
- `superpowers:systematic-debugging` — 测试失败、结果异常时
- `superpowers:verification-before-completion` — 声称完成前
- `dataviz` — 任何图表/可视化
- `josim-viz` — 本项目仿真结果可视化

**Why:** 之前多个任务中（XOR 真值表验证、可视化生成）Claude 没有调用 skill，直接裸写逻辑，效率和一致性不如用 skill。

**How to apply:** 每个任务开始时，先扫一遍 CLAUDE.md 中的触发规则表，确认是否有匹配的 skill，有则立即调用 Skill 工具。
