---
name: skill-router
description: Use when starting any task in the JoSIM project — before Bash, Write, Edit, or any action. Read this file and output the required skill list BEFORE doing anything else. No exceptions.
---

# Skill Router — JoSIM Pre-Action Checklist

> **IRON RULE: Before ANY Bash/Write/Edit call, read this file and output required skills.**
> 5-second self-check. No task is too simple to skip.

## ⚡ Quick Self-Check (MUST run before first tool call)

```
1. User wants to: [write code? / run sim? / visualize? / debug? / read PDF? / design?]
2. Skills needed:  [____________________]
3. Output format:  "Skills for this task: [list]. Starting with [first skill]."
```

## Mapping Table (scan in 3 seconds)

| Task contains... | Skills required |
|-----------------|----------------|
| 仿真/测试 .cir + 可视化 | `josim-viz` → `dataviz` |
| 写代码/创建文件 | `superpowers:writing-plans` → `superpowers:test-driven-development` |
| 调试/不工作/bug | `superpowers:systematic-debugging` |
| .pdf 文件/论文 | `document-skills:pdf` |
| 设计/架构/方向 | `superpowers:brainstorming` |
| 修改 src/ 或 include/ | `ecc:cpp-review` |
| 总结/提交/完成 | `project-summary` → `verification-before-completion` |
| 会话开始/查进度 | `todo-manager` |
| 论文/文献 | `academic-research-skills:deep-research` |
| **多任务/批量实验/可并行** | **优先 subagent 分发**（`superpowers:dispatching-parallel-agents`），主会话保持审阅与决策 |

## Subagent 使用原则（2026-08-06 起，用户要求）

1. **多任务或可并行的实验批次 → 优先派发 subagent**（如 P0.0 与 P0.1 并行），主会话做审阅、决策门判定与文档同步
2. 独立任务必须互不依赖：**不同 subagent 写不同文件**（文件前缀隔离），提交时只 add 自己的文件，避免并行提交冲突
3. 单个 2-5 分钟的机械步骤（建目录、单次运行）仍可 inline；重活/独立实验/大文件扫描交给 subagent
4. subagent 的上下文配方：HANDOVER → 相关 spec → 相关 plan task → 冻结口径（sfq_metrics.py/相对路径/禁 sed/禁 /tmp）

## Priority: Process → Implement → Output → Verify (ALWAYS)

## Red Flags

| If you think... | STOP. You're rationalizing. |
|----------------|---------------------------|
| "Just do it directly" | Simple = most likely to benefit |
| "Run sim first" | Check skills BEFORE action |
| "I know what to do" | Knowing ≠ doing properly |
| "Already verified" | Fresh run or it didn't happen |

## Mandatory Output

After reading this, output ONE line before your first tool call:
> `[skill-router] Task: <summary>. Skills: <list>.`

Example: `[skill-router] Task: run BVM test + visualize. Skills: josim-viz, dataviz.`
