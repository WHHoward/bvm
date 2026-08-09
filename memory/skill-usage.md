---
name: skill-usage
description: JoSIM × BVM 仓库级 skills 的发现位置、触发边界与使用规范
metadata:
  node_type: memory
  type: project
  last_updated: 2026-08-09
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
| `josim-experiment` | 设计、运行、扫描和记录不可覆盖的 JoSIM 实验 |
| `josim-evidence-audit` | 审计 raw phase、同 JJ 电压面积、JTL 接收、收敛和物理结论 |
| `josim-viz` | 安全绘图；可视化不替代物理 Gate |
| `josim-todo-manager` | 只读查询或按完成证据更新主任务表 |
| `josim-project-summary` | 生成/持久化项目总结、交接和变更历史；普通总结不删除文件 |
| `josim-skill-router` | 为跨工作流任务选择最小 skill 组合 |

## 使用原则

1. 先按用户授权区分只读审查、诊断、实现和实验，不因 skill 触发扩大写入范围。
2. 只加载完成任务所需的最小 skill 和 reference，避免把整个项目知识库塞入上下文。
3. 项目状态从 `docs/HANDOVER.md` 和 `memory/project-todo.md` 动态读取；skill 不复制易过时结论。
4. 相位/SFQ/Gate 解释使用 `josim-evidence-audit`；`.cir` 运行使用 `josim-experiment`。
5. `scripts/sfq_metrics.py` 和 `scripts/run_exp.sh` 在 Phase −1 M4–M11 完成前不得作为物理结论流水线。
6. 使用 skill 后仍必须验证实际产物；skill 规范不能替代测试和原始证据。

## 显式调用示例

```text
$josim-experiment：给 BQ v4 设计一次不可覆盖的单 PWL 对照实验。
$josim-evidence-audit：审计这个 CSV 能支持到哪一级证据。
$josim-viz：把相位以 raw rad 绘图并标出 pre/post 窗口。
$josim-todo-manager：只读告诉我当前下一项未阻塞任务。
```

**Why（2026-08-09）**：旧平铺技能引用了失效的 v1 指标、过时 Phase 1 优先级和自动删除规则；新版结构将实验执行、可视化和物理判定分离，并以单一 canonical source 防止 Claude/Codex 两套说明漂移。

**How to apply**：新增或修改 skill 时使用标准 `<name>/SKILL.md` 结构，运行 `skill-creator` 的 `quick_validate.py`，检查 `agents/openai.yaml`，再用独立任务做前向测试。
