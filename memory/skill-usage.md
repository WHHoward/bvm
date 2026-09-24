---
name: skill-usage
description: JoSIM × BVM 仓库级 skills 的发现位置、触发边界与使用规范
metadata:
  node_type: memory
  type: project
  last_updated: 2026-09-24
---

# 项目 skill 使用规范

## 唯一规范源

- Codex/Agent Skills：`.agents/skills/<name>/SKILL.md`
- Claude Code 兼容：`.claude/skills/<name>` 目录链接到同一 canonical skill
- 仓库通用不变量：`AGENTS.md`

不得再维护 `.claude/skills/*.md` 平铺副本，也不得把仓库内 `.codex/skills` 当成项目级目录。技能由 description 按任务触发；只有跨多个工作流或不知道如何选择时才使用 router，不在每次工具调用前强制加载全部技能。

## 当前项目 skills

### Executor default

| Skill | 用途 |
|---|---|
| `josim-experiment` | 普通 Compact Quick / 用户明确要求的 Formal execution |
| `josim-viz` | 仅在请求或工作要求可视化时，用指定图集处理现有 raw |
| `josim-submit` | 仅在用户请求或 active contract 要求 submit/package 时处理已完成 evidence |

普通 user→Codex BVM experiment path 加载最小集合：通常先
`josim-experiment`，需要/被要求出图时再加载 `josim-viz`，仅在被要求提交/打包时
才加载 `josim-submit`（若 active experiment contract 明确要求交付，也遵循该要求）。

### Specialized / not default

| Skill | 路由 |
|---|---|
| `josim-handoff` | 真实 Codex↔Claude contract、ACK/receipt 或委派审计 |
| `josim-evidence-audit` | 用户明确要求 phase/SFQ/physics scientific interpretation |
| `reviewer-adversarial` | 独立对抗性复核 |
| `reviewer-numerical` | 独立数值复核 |

### Retired compatibility

`josim-exploration-visualization` 不是 active skill。保留其 README、references
与历史 compatibility scripts，不恢复 skill routing，也不删除旧 launcher。

## 使用原则

普通路径是一个有界的用户任务：执行请求内容、保留证据、按请求可视化/提交，
再停在 user review。不得把“user review”自动扩展成 NEXT experiment。

1. 先按用户授权区分只读审查、诊断、实现和实验，不因 skill 触发扩大写入范围。
2. 只加载完成任务所需的最小 skill 和 reference，避免把整个项目知识库塞入上下文。
3. 普通 BVM executor 先读取 `memory/LUNA_EXECUTOR_MEMORY.md`、
   `memory/BVM_CURRENT_CONTEXT.md` 和 active experiment config；仅当任务需要
   historical scientific context、route/status reconciliation 或 physical claims 时读 `docs/HANDOVER.md`。
4. 显式 scientific interpretation 使用 `josim-evidence-audit`；`.cir` 运行使用 `josim-experiment`。
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

**Executor memory（2026-09-24）**：普通 BVM 执行先复用成熟平台与配置入口，
不将 scientific/reviewer/handoff skills 全量预加载；提交/打包使用独立
`josim-submit` 路由。

**How to apply**：新增或修改 skill 时使用标准 `<name>/SKILL.md` 结构，运行 `skill-creator` 的 `quick_validate.py`，检查 `agents/openai.yaml`，再用独立任务做前向测试。

**Handoff 扩展（2026-08-09）**：新增 `josim-handoff` 与 `research/` 控制层，将 Codex 的计划/审计和 Claude Code 的实现/实验分开；完整协议见 `research/WORKFLOW.md`，Claude 的最小执行入口见 `research/CLAUDE_EXECUTOR.md`。
