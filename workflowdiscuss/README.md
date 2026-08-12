# Workflow Design Archive

This directory contains **historical workflow-design discussions, proposals, reviews, rejected alternatives, and superseded drafts**.

**It is NOT authoritative for normal project execution.**

Agents MUST NOT read this directory by default.

## Current authority

1. `AGENTS.md` — repository-wide invariants (不可违反)
2. `research/WORKFLOW.md` — 正式协作协议 / FROZEN backend (josim-handoff/v1)
3. `research/WORKFLOW-lite.md` — 轻量协作接口（Pilot），仅在该协议明确适用时使用
4. `memory/project-todo.md` — 当前科研任务状态
5. 当前 TASK contract — 本次具体授权

科研状态见 `docs/HANDOVER.md`；mailbox 只是通知层（`research/mailbox/README.md`）。

## 结构

```text
workflowdiscuss/
├── README.md                  ← 本文件
├── current-reference/         ← 仍被 active protocol 直接引用的少量设计文件
└── archive/
    ├── proposals/             ← 各轮提案（rc、batch、整合、最终方案、最小修改方案）
    ├── reviews/               ← Claude / Codex / Copilot 的多轮审阅意见
    ├── old-versions/          ← 被取代的旧版本草案
    └── architecture/          ← 多 Agent 架构设计
```

## 何时读取本目录

- 显式审阅 workflow 历史时；
- 调查某个 workflow 决策的来由时；
- 当前 authority 明确引用本目录中的文件时（目前仅 `current-reference/WORKFLOW-lite-2.0-FINAL-IMPLEMENTATION.md` 被 `research/WORKFLOW-lite.md` 的 implementation_ref 引用）。

**不要从已归档的 proposal / review 推断当前要求。** 已采纳的设计决策已落实在 `AGENTS.md`、`research/WORKFLOW.md`、`research/WORKFLOW-lite.md`、`memory/project-todo.md` 与 `docs/HANDOVER.md` 中。

## 历史说明（2026-08-12 整理）

- 本目录前身为多轮三方讨论（WORKFLOW-lite 2.0 → Batch → 成本优化 → 最终研究流程）的存放处；
- 2026-08-12 用户采纳"最终研究流程与协作方案"（最小修改版）后，讨论材料归档于此，工作流设计讨论结束；
- 归档采用移动（git mv / mv）方式，未删除任何文件；git history 完整保留。
