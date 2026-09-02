---
name: skill-usage
description: JoSIM × BVM 仓库级 skills 的发现位置、触发边界与使用规范
metadata:
  node_type: memory
  type: project
  last_updated: 2026-09-02
---

# 项目 skill 使用规范

## 唯一规范源

- Codex/Agent Skills：`.agents/skills/<name>/SKILL.md`
- Claude Code 兼容：`.claude/skills/<name>` 目录链接到同一 canonical skill
- 仓库通用不变量：`AGENTS.md`

不得再维护 `.claude/skills/*.md` 平铺副本，也不得把仓库内 `.codex/skills` 当成项目级目录。技能由 description 按任务触发；只有跨多个工作流或不知道如何选择时才使用 router，不在每次工具调用前强制加载全部技能。

## 当前项目 skills

| Skill | 用途 |
|---|---|
| `josim-experiment` | 默认 Compact Quick；只有用户明确要求时进入 Formal |
| `josim-evidence-audit` | 审计 raw phase、同 JJ 电压面积、JTL 接收、收敛和物理结论 |
| `josim-viz` | 关键 waveform、拓扑图和 classic 结果索引；可视化不替代物理 Gate |
| `josim-handoff` | 仅显式 Codex–Claude 合同、ACK/receipt 或委派审计 |
| `reviewer-adversarial` | 仅显式深度/对抗性复核 |
| `reviewer-numerical` | 仅显式数值单位、积分、阈值和收敛复核 |

## 使用原则

Compact V2 普通路径为 QUESTION → MINIMUM QUICK → RESULT → USER REVIEW →
NEXT or ARCHIVE。check-in、router、task-manager 和 summary 不再是普通 Quick 的
前置技能；它们的少量耐久规则进入 workflow 文档或项目状态页。历史任务文本中
出现的旧 skill 名称保持原样，不因此重写历史。

1. 先按用户授权区分只读审查、诊断、实现和实验，不因 skill 触发扩大写入范围。
2. 只加载完成任务所需的最小 skill 和 reference，避免把整个项目知识库塞入上下文。
3. 项目状态从 `docs/HANDOVER.md` 和 `memory/project-todo.md` 动态读取；skill 不复制易过时结论。
4. 相位/SFQ/Gate 解释使用 `josim-evidence-audit`；`.cir` 运行使用 `josim-experiment`。
5. `scripts/sfq_metrics.py` 和 `scripts/run_exp.sh` 在 Phase −1 M4–M11 完成前不得作为物理结论流水线。
6. 使用 skill 后仍必须验证实际产物；skill 规范不能替代测试和原始证据。
7. 委派任务以签名 request 为授权边界；receipt 的“已完成”不等于 artifact 有效或物理 Gate 通过，只有接受的 audit 才能上推项目状态。
8. Codex 不可用时的 stand-in 动作（2026-08-09）：必须经用户明确授权，写入 `research/tasks/<id>/standin/<Sxx>/record.yaml`（PROVISIONAL），Codex review 确认前不生效；stand-in 不得审计自身执行。

## 显式调用示例

```text
$josim-handoff：为 M4 创建可由 Claude ACK 的实现任务包，完成后独立审计回执。
$josim-experiment：给 BQ v4 设计一次不可覆盖的单 PWL 对照实验。
$josim-evidence-audit：审计这个 CSV 能支持到哪一级证据。
$josim-viz：把相位以 raw rad 绘图并标出 pre/post 窗口。
$josim-handoff：只有明确存在 Codex–Claude 合同或 receipt 时才介入。
```

**Why（2026-09-02）**：Compact V2 将日常路径收敛为 QUESTION → MINIMUM QUICK →
RESULT → USER REVIEW → NEXT or ARCHIVE；实验执行、可视化和物理判定仍分离，
但不再用 router、check-in、summary 或 task-manager 作为普通 Quick 前置仪式。

**How to apply**：新增或修改 skill 时使用标准 `<name>/SKILL.md` 结构，运行 `skill-creator` 的 `quick_validate.py`，检查 `agents/openai.yaml`，再用独立任务做前向测试。

**Handoff 扩展（2026-08-09）**：新增 `josim-handoff` 与 `research/` 控制层，将 Codex 的计划/审计和 Claude Code 的实现/实验分开；完整协议见 `research/WORKFLOW.md`，Claude 的最小执行入口见 `research/CLAUDE_EXECUTOR.md`。
