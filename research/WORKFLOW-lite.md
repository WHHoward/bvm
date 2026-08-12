---
title: WORKFLOW-lite 2.0 — 三方科研协作协议（Pilot）
document_type: protocol
protocol_status: PILOT
design_status: FINAL
date: 2026-08-11
authority_note: 经用户批准的 Pilot 协作界面；正式权威仍为 research/WORKFLOW.md + josim-handoff/v1（FROZEN 后端）。Pilot 通过前不修改权威文件。
implementation_ref: workflowdiscuss/current-reference/WORKFLOW-lite-2.0-FINAL-IMPLEMENTATION.md
---

# WORKFLOW-lite 2.0

轻量默认协作界面。核心设计：

```text
风险分级（NORMAL/CRITICAL）
  × 证据模式（LITE/FROZEN）
  + 轻量预检（Preflight）
  + 强 Reviewer（contradiction-first）
  + 按需证据冻结（FROZEN → josim-handoff/v1）
```

> **轻量默认，但不取消执行前机械防线。**
> **Reviewer 要强，但不能成为第二个 Codex。**
> **Git 提供 LITE 的轻量不可变快照；文件级 SHA-256 留给关键科研证据。**
> **FROZEN 必须在关键证据产生前预注册，不允许事后补票。**

## 1. 适用范围与权威关系

- 本协议是 **Pilot 协作界面**，必须由用户或 Codex **显式指定**使用；
- 已归档任务（M4-001/002/003 等）保持原协议，不重写历史；
- `research/WORKFLOW.md` + `josim-handoff/v1` 仍是正式权威协议与 FROZEN 后端；
- Pilot 通过（见 §9）后才统一同步 AGENTS.md / WORKFLOW.md / CLAUDE_EXECUTOR.md / skills。

## 2. 两个维度

| 维度 | 取值 | 含义 |
|---|---|---|
| 风险等级 | NORMAL / CRITICAL | 任务本身的科学/工程风险 |
| 证据模式 | LITE / FROZEN | 本次任务使用的证据冻结强度 |

常用组合：NORMAL+LITE（默认工程）、CRITICAL+LITE（关键实现/计量）、CRITICAL+FROZEN（final Gate / metric freeze / 论文数据）。**NORMAL 任务永不要求 FROZEN。**

风险定级保守：**拿不准 → CRITICAL**。自动 CRITICAL：新协作机制首次试点、新 Agent/Skill 首次真实使用、与 frozen evidence 或历史关键 baseline 交互、metric/unit/window/threshold 变化、物理解释、solver/timestep/收敛、论文关键数据。用户可随时强制升级。

证据模式保守：预期用于 final Gate / metric freeze / 论文核心数字的任务，必须**执行前**注册 CRITICAL+FROZEN。禁止"先 LITE 得到好结果 → 事后追溯为 FROZEN"；已完成的 LITE run 只能作为探索证据或下一次 FROZEN run 的设计输入。

## 3. 角色

| 角色 | 职责 | 不做 |
|---|---|---|
| 用户 | 最终裁决：路线、metric freeze、physical Gate、论文主张；可强制升级风险/启用 FROZEN | 不逐样本核对 |
| Codex | Planner（TASK）+ Final Auditor（NORMAL light / CRITICAL deep）；唯一 ACCEPT/REWORK/BLOCKED | Reviewer PASS 不等于 ACCEPT |
| Claude | Preflight → 实现 → RESULT；遵守 allowed paths / stop conditions / claim ceiling | 不改 TASK；不自证完成；不宣布最终 Gate |
| Copilot Reviewer | 证据层 peer review（contradiction-first）；写 REVIEW.md；可建议风险/模式升级 | 不改实现/TASK/RESULT/raw；不 ACCEPT；不给最终物理 verdict |

### 3.1 最终协作纪律（2026-08-11）

- Codex 是 Planner + Final Auditor，唯一给出 `ACCEPT / REWORK / BLOCKED`；Claude 是 Executor，只产出 Preflight、实现/证据与 `RESULT.md`；Copilot 是 Evidence Reviewer / Peer Reviewer，只写 attempt-local `REVIEW.md`；用户保留路线、metric freeze、physical Gate 与论文主张的最终决定权。
- mailbox 只传通知与索引；LITE 的正式事实是 `TASK.md`、`RESULT.md`、`REVIEW.md` 和 delivery snapshot。FROZEN 的正式事实另为 v1 的 request/ACK/receipt/audit 与 SHA-256。

## 4. 任务文件

```text
research/tasks/<TASK-ID>/
├── TASK.md                 ← Codex 签发，Git commit 密封，任何人不得静默修改
└── attempts/
    ├── A01/
    │   ├── RESULT.md       ← Claude 写（Preflight 为最先写入的不可变块）
    │   └── REVIEW.md       ← Reviewer 写（只读执行，仅此文件）
    ├── A02/                ← REWORK 时新建，A01 保留
    └── ...
```

文件命名映射：TASK.md ≈ LITE 合同；request.yaml/ACK/receipt/verdict ≈ FROZEN 合同。同一 attempt 不混用两套。

## 5. 两个 Git commit 概念

```text
Task revision commit      ← 包含当前不可修改 TASK.md 的 commit
Execution baseline commit ← Claude 开始 Preflight 时预期 worktree HEAD
```

默认三者相等（Observed HEAD == Execution baseline == Task revision）。必须不同时，TASK 显式写差异与理由。

## 6. Preflight（必须先写，不能事后补）

Claude 执行顺序：读 TASK → 创建 attempts/Axx/RESULT.md → 写完整 Preflight 块 → PASS 后才允许修改实现/运行实验。Preflight 块**不得回填重写**；发现记录错误时追加 correction note。

Preflight 至少记录：Task revision commit、Execution baseline commit、Observed HEAD、branch/worktree、`git status --porcelain=v1 --untracked-files=all`、allowed paths / risk / evidence mode / claim ceiling 理解确认、歧义、结果。

**BLOCKED 条件**（默认）：Observed HEAD ≠ Execution baseline（除非 TASK 明确允许）；意外 dirty worktree；scope 冲突；TASK 歧义；frozen evidence 可能被覆盖；metric/unit/window 定义不足；required input 不存在。

## 7. RESULT 四维语义

```yaml
execution_status: COMPLETED | BLOCKED | DEVIATED
executor_artifact_assessment: VALID | INVALID | NOT_AUDITED
proposed_physical_verdict: PASS | FAIL | INCONCLUSIVE | NOT_APPLICABLE
```

严格区分：执行完成 ≠ 产物可用 ≠ 物理条件满足 ≠ review 通过 ≠ Codex 接受 ≠ 用户采用。Claude 只能报告执行者视角的**暂定** artifact assessment。

## 8. Delivery Snapshot

RESULT 完成后，**授权 snapshot owner**（默认 CODEX；可为 USER 或 CLAUDE_EXPLICITLY_AUTHORIZED）创建一次非 amend 的 delivery commit，只含 allowed paths 改动 + 当前 attempt 的 RESULT + TASK 允许的 evidence metadata；不使用 `git add -A`；commit 后停止修改。RESULT 追加：`Delivery snapshot commit: <commit>`、`Snapshot owner:`、`Snapshot scope check: PASS`。

Reviewer 与 Codex 均审查该 commit，不审查持续变化的 worktree。

## 9. Pilot 升级条件

完成 2–3 个真实任务（M12 → M5 计量实现 → M5 物理解释/M6），满足：Preflight 有效、Reviewer 约束经验证（Pilot 0）、skills 可发现、canonical 复用生效、snapshot 审查稳定、无实质证据丢失、CRITICAL 审计仍强、流程摩擦显著下降 → 才允许 PILOT → FINAL，并统一同步权威文件。

Pilot 期间每任务记录 §43 指标（Reviewer 是否发现新问题、findings 是否被 Codex 确认、false positive 率、Preflight 是否捕获问题、只读性、canonical 调用、漂移、审计强度、成本）。

## 10. 十条不可删除的底线

1. Goal 明确；2. Allowed paths 明确；3. Acceptance criteria 明确；4. Stop conditions 明确；5. Claim ceiling 明确；6. 执行前 baseline 可核对；7. TASK 不允许静默修改；8. Reviewer 有独立证据来源；9. CRITICAL 科学任务由 Codex 从 raw evidence 深度复核；10. 用户保留 route / metric freeze / physical Gate / paper claim 最终权。

## 11. 其他

- **mailbox / josim-experiment / josim-evidence-audit 等正交工具继续适用**——Lite 只改协作层协议；
- Reviewer 的**最低核心**为 `adversarial-review`、`numerical-science-review`、`superconducting-simulation-review`：它们分别复用 `.agents/skills/reviewer-adversarial/`、`.agents/skills/reviewer-numerical/` 与 `.agents/skills/josim-evidence-audit/`。现有 7 个 `.github/skills/` wrapper 全部保留，可按任务相关性使用；它们不得建立平行物理规则；
- todo/HANDOVER 更新仅限 Codex ACCEPT 之后；
- 连续两个 attempt 同根因失败 → 停止并升级 Codex/User；
- `verify-task` 语义拆分：execution snapshot verification（当时是否在正确 snapshot 上执行）与 current drift check（ACCEPT 后仓库又发生了什么）不得混淆；正常更新 HANDOVER/todo 不得让历史 ACCEPTED 任务误判无效。
