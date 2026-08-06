---
name: todo-manager
description: Use when starting or ending any JoSIM work session — check progress against the master task list, update status, add new tasks, or plan the next session's work. Use when the user asks about project progress, what to work on next, or whether a task is complete.
---

# Todo Manager for JoSIM

> **Scope: JoSIM project ONLY.** Manages `memory/project-todo.md` — the master task list.

## Overview

The master TODO list at `memory/project-todo.md` is the single source of truth for all project work items. This skill defines how to read, update, and maintain it.

## Trigger Conditions

- Session start: "我们继续做xxx"
- Session end: "总结一下，提交"
- Status inquiry: "现在进度怎么样", "接下来做什么"
- Task completion: "这个做完了"

## Workflow

### Session Start

```
1. Read memory/project-todo.md
2. Report: N tasks done, M in progress, K pending
3. Identify the next unblocked task (first 🔴 with satisfied dependencies)
4. Propose: "今天做 [task]?"
```

### During Session

When a task is completed:
```
1. Update status from 🟡 → 🟢
2. Add date + brief note to 更新日志
3. If the task unblocks downstream tasks, flag them
4. 标注修改时间 (YYYY-MM-DD) 到该任务行（时间标注规则，2026-08-06 起强制，见 project-summary skill）
```

When a new task emerges:
```
1. Add to the appropriate category (一~六)
2. Estimate hours
3. Note dependencies
```

### Session End

```
1. Update all task statuses to current state
2. Add one-line to 更新日志 with date + what changed
3. Report: "今天完成了 X, Y。下一步是 Z。"
```

## Status Codes

| Code | Meaning |
|------|---------|
| 🔴 | 未开始 |
| 🟡 | 进行中 |
| 🟢 | 已完成 |
| ⏸️ | 暂停/阻塞 |

## Priority Order

1. Paper A Phase 1 (T1-T8) — active, has deadline
2. Paper A Writing (P1-P6) — blocked on T1-T7
3. 标准元件库 (S1-S5) — low hanging fruit, can do anytime
4. 基础设施 (I1-I4) — maintenance, do when convenient
5. Paper B (B1-B6) — blocked on Paper A
6. 长期 (L1-L5) — future

## Integration

- **skill-router**: todo-manager is called at session start to determine what to work on
- **project-summary**: after CHANGELOG update, sync todo status
- **writing-plans**: new plans should add tasks to the todo list

[[project-todo]] [[skill-router]]
