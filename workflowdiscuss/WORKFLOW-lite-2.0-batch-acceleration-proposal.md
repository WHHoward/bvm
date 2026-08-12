---
title: WORKFLOW-lite 2.0 — Batch Execution / Delegated Closure 加速提案
document_type: discussion_proposal
status: FOR_THREE_PARTY_REVIEW
date: 2026-08-11
purpose: 在不削弱关键科研审计的前提下，将 Codex 从 task-level 管理者降频为 batch-level / scientific-gate 审计者
---

# WORKFLOW-lite 2.0 — Batch Execution / Delegated Closure 加速提案

> 本文供 **Claude / Copilot / Codex 三方审阅**。
>
> 本文当前**不修改现行协议、不授权任何研究任务**。
>
> 目标是讨论：在 Claude 与 Copilot 可承担大量内部工作，而 Codex 额度稀缺的现实条件下，如何把 Codex 从“每个任务都参与”调整为“只参与批次与科学关键节点”。

## 1. 核心问题

当前流程中，一个普通任务通常需要 Codex 至少两次接触：

```text
Codex 签发 TASK
    ↓
Claude 执行
    ↓
Copilot Review
    ↓
Codex Final Audit
```

如果后续任务较多，则 Codex 消耗近似：

```text
~2 次 Codex 接触 / Task
```

而当前资源结构更适合：

```text
Claude  → 承担实现、测试、重跑、修复
Copilot → 承担持续 Review、证据复核、测试盲区、数值检查
Codex   → 只用于 Batch Gate、Scientific Gate、Exception
User    → 最终科研权威
```

因此建议把 Codex 的角色从：

```text
Task-level Planner + Every-task Auditor
```

调整为：

```text
Batch Architect
+
Scientific Gate Auditor
+
Exception Resolver
```

核心目标：

> **把 Codex 从“每个任务 2 次”降到“每个批次约 1 次”，同时不削弱科学关键节点的审计。**

---

## 2. 总体结构

建议采用：

```text
Codex
  ↓
BATCH CONTRACT
  ↓
Claude + Copilot FREE INNER LOOP
  ↓
Stable Candidate
  ↓
Delivery Snapshot
  ↓
Copilot FORMAL REVIEW
  ↓
Codex Batch / Scientific Gate Audit
  ↓
ACCEPT / REWORK / BLOCKED
```

核心句：

> **Never send an unstable attempt to Codex.**

即：

> **未经过 Claude + Copilot 内部闭环稳定的结果，不进入 Codex。**

---

## 3. 从 Task-centric 改为 Batch-centric

原来：

```text
M7
→ TASK
→ Claude
→ Copilot
→ Codex

M8
→ TASK
→ Claude
→ Copilot
→ Codex
```

建议改为：

```text
BATCH-B
├── M7 Regression
└── M8 Timestep Convergence
```

Codex 对整个 Batch 只签一次总体合同。

例如：

```markdown
# BATCH-B TASK

Risk: CRITICAL
Evidence mode: LITE

## Scope
- M7 regression tests
- M8 timestep convergence

## Internal delegation
Claude may sequence, rerun and repair subtasks inside this batch.
Copilot may perform repeated pre-review and evidence review.

## Claim ceiling
Implementation / convergence evidence only.
No metric freeze or final physical Gate unless explicitly authorized.

## Batch acceptance
- M7 acceptance criteria satisfied
- M8 convergence criteria satisfied
- no unresolved Major/Critical reviewer findings
- stable delivery snapshot produced

## Codex checkpoint
Batch completion only.

## Escalation triggers
- metric semantics must change
- unit/window/threshold definition must change
- evidence mode must become FROZEN
- scope must expand
- physical interpretation becomes disputed
- repeated same-root-cause failure
```

---

## 4. 两层执行结构

### 4.1 FREE INNER LOOP

由：

```text
Claude + Copilot
```

内部完成：

```text
implementation
simulation
testing
debugging
numerical checks
boundary tests
control cases
pre-review
rework
evidence inspection
```

不调用 Codex。

流程：

```text
Claude implementation
       ↓
Copilot PRE-REVIEW
       ↓
发现问题？
   ┌── YES ──→ Claude 修复 ──┐
   │                         │
   └─────────────────────────┘
       ↓ NO
candidate stable
```

### 4.2 OUTER GATE

只有稳定候选才进入：

```text
Delivery Snapshot
    ↓
Copilot FORMAL REVIEW
    ↓
Codex Batch / Gate Audit
```

这样 Codex 默认只看到：

```text
稳定版本
+
正式 Reviewer 结论
+
关键证据
+
Codex focus
```

而不是看到大量失败迭代。

---

## 5. PRE-REVIEW 与 FORMAL REVIEW 必须分开

Claude 的原始优化思路是：

> 把 Copilot Review 前移，在 delivery commit 前发现问题并立即修复。

这个方向应采纳，但正式术语要分开。

### PRE-REVIEW

发生在 Delivery Snapshot 前。

用途：

- 找 bug；
- 找 test gap；
- numerical check；
- boundary/control；
- stale evidence；
- claim ceiling；
- 让 Claude 在内部修复。

PRE-REVIEW：

```text
不代表正式 PASS
不绑定最终 snapshot
不进入 Codex
```

可以通过 chat、mailbox、scratch note 完成。

### FORMAL REVIEW

发生在：

```text
Delivery Snapshot 后
```

Copilot 必须审查最终稳定 snapshot，并生成：

```text
REVIEW.md
```

因此：

```text
PRE-REVIEW
= 内部质量闭环

FORMAL REVIEW
= 对最终交付快照的正式证据复核
```

即使 PRE-REVIEW 已多次通过，最终 snapshot 后仍应做一次简短 FORMAL REVIEW。

---

## 6. Delegated Closure：取消每个 Subtask 的 Codex ACCEPT

建议引入内部状态：

```text
SUBTASK_READY
```

而不是每个 subtask 都要求：

```text
ACCEPTED
```

### Claude + Copilot 可以内部关闭 Subtask

条件：

```text
acceptance satisfied
+
Copilot PRE-REVIEW 无未解决 Major/Critical finding
+
claim ceiling 未突破
+
没有 escalation trigger
```

例如：

```text
M7 → SUBTASK_READY
```

然后直接继续 M8。

### Codex 关闭整个 Batch

```text
M7 SUBTASK_READY
M8 SUBTASK_READY
       ↓
BATCH_READY
       ↓
Delivery Snapshot
       ↓
FORMAL REVIEW
       ↓
Codex
       ↓
BATCH_ACCEPTED
```

权限因此变为：

```text
Claude + Copilot
关闭“工作步骤”

Codex
关闭“审计批次”

User
关闭“科学决策”
```

---

## 7. 不建议把 User 变成新的审批瓶颈

不建议：

```text
每个工具任务
→ Copilot PASS
→ User 确认
```

否则只是把 Codex bottleneck 换成 User bottleneck。

更合理：

```text
Claude + Copilot
→ SUBTASK_READY
```

在 Batch 内自行推进。

只有：

```text
Batch Gate
Scientific Gate
Metric Freeze
Physical Gate
Route Decision
Paper Claim
```

才找 Codex / User。

---

## 8. Escalation Triggers：什么时候必须叫 Codex

Batch 化能否安全，关键就在这里。

出现以下任一项必须暂停内部推进：

```text
1. Batch scope 必须改变
2. metric definition 必须改变
3. unit / window / threshold / tolerance semantics 出现争议
4. Evidence mode 需要从 LITE 升级为 FROZEN
5. physical interpretation 出现冲突
6. raw evidence 与预期/RESULT 明显矛盾
7. 连续两轮 internal rework 同根因失败
8. candidate route 即将进入正式 Gate
9. paper-level claim 即将形成
10. frozen evidence 可能被覆盖或漂移
11. solver / timestep / convergence 影响最终结论
12. 用户明确要求 Codex 介入
```

除此之外：

```text
Claude + Copilot 自行闭环
```

---

## 9. 综合后的 Batch 规划

| Batch | 内容 | Risk / Mode | Codex 接触 |
|---|---|---|---|
| A | M6 Voltage-area cross-check | CRITICAL + FROZEN | Final audit 1 次 |
| B | M7 Regression + M8 Timestep convergence | CRITICAL + LITE | Batch audit 1 次 |
| C1 | M9 Freeze METRIC_SPEC_V2 | CRITICAL + FROZEN | Scientific Gate 1 次 |
| C2 | M11 New baseline | CRITICAL + FROZEN | Baseline audit 1 次 |
| D | Route C / BQ v4 Q1–Q6 exploration | 初始 NORMAL + LITE；触发条件时升级 | Route candidate / batch end 1 次 |
| E | Route D / DCSFQ D1–D6 exploration | 同上 | Route candidate / batch end 1 次 |
| F | System Gate S1–S4 + T1/S5 + End-to-end S6 | CRITICAL + FROZEN | 1–2 次 |

---

## 10. M8 不应被简单降级为工具类

M8 是 timestep convergence。

它可能影响：

```text
numerical validity
→ event classification
→ metric stability
→ physical evidence quality
```

所以：

```text
M8 = CRITICAL
```

但：

> **CRITICAL 不等于必须单独叫 Codex。**

正确做法：

```text
M7 + M8
→ 一个 CRITICAL + LITE Batch
→ Codex 合并审计一次
```

即：

> **通过合并审计省 Codex，而不是通过降低科学风险省 Codex。**

---

## 11. M9 与 M11 建议保留两个 Scientific Checkpoint

M9：

```text
freeze METRIC_SPEC_V2
```

M11：

```text
new baseline
```

逻辑关系：

```text
M9 metric frozen
    ↓
M11 baseline based on frozen metric
```

所以 M9 是真正的 dependency gate。

不建议为了省一次 Codex：

```text
M9 未正式接受
→ 直接让 M11 成为正式 baseline
```

可以在同一次 Codex 会话中连续处理 C1/C2，但语义上保留两个 checkpoint。

---

## 12. M10 建议

Claude 建议把 historical JSON recomputation 从 critical path 划掉或并入 C。

综合建议：

先回答：

> 是否有 downstream scientific claim / regression / baseline / paper evidence 依赖 M10？

如果：

```text
NO
```

则：

```text
DEFER
或
归入 archive hygiene
```

不占 Codex critical path。

如果：

```text
YES
```

则并入 Batch C 尾部。

---

## 13. Route C / Route D 探索适合零 Codex 内部轨道

可以并行：

```text
Route C worktree
Claude C
↕
Copilot Review C

Route D worktree
Claude D
↕
Copilot Review D
```

探索阶段 claim ceiling：

```text
exploration only
no final route claim
no physical Gate adoption
```

只有出现：

```text
candidate route
```

或 Escalation Trigger 时才叫 Codex。

---

## 14. Standing Authorization / Exploration Envelope

为了进一步减少 Codex 接触，可以让 Codex 一次授权整个探索 envelope：

```yaml
route_C_exploration:
  allowed: true

  scope:
    - Q1
    - Q2
    - Q3
    - Q4
    - Q5
    - Q6

  evidence_mode: LITE

  claim_ceiling:
    exploration_only

  no_codex_required_until:
    - candidate_gate
    - metric_change
    - physical_conflict
    - frozen_evidence_needed
    - repeated_root_cause_failure
```

这样 Claude 不需要 Q1/Q2/Q3 每一步重新申请 TASK。

---

## 15. W5 文献检索建议立即并行

W5 可作为：

```text
ZERO-CODEX PARALLEL TRACK
```

由：

```text
Claude research
+
Copilot cross-check
```

推进：

- 文献搜集；
- coverage matrix；
- prior art；
- claim taxonomy；
- gap candidate；
- citation map。

当前不需要 Codex。

但最终形成：

```text
novelty / literature-gap paper claim
```

前仍需高置信科学审查。

因此：

```text
W5 exploration
→ zero Codex

W5 final novelty claim
→ later high-confidence review
```

---

## 16. Batch Proposal 应先由 Claude 起草

为减少 Codex 写作消耗：

```text
Claude
→ Draft Batch Proposal

Copilot
→ completeness review

mailbox
→ Codex

Codex
→ edit / approve
```

建议格式：

```markdown
# Batch Proposal

## Goal
...

## Scope
...

## Risk
...

## Evidence mode
...

## Acceptance
...

## Claim ceiling
...

## Internal subtask order
...

## Escalation triggers
...

## Expected Codex checkpoints
...
```

Codex 不需要从零写完整 TASK。

---

## 17. Mailbox 的定位不变

```text
mailbox
=
communication layer
```

用于：

- Batch proposal；
- candidate ready 通知；
- PRE-REVIEW findings；
- escalation；
- Codex handoff；
- 非正式建议。

正式事实仍然是：

```text
Batch TASK
RESULT
Delivery Snapshot
FORMAL REVIEW
Codex Audit
Git
FROZEN evidence chain
```

---

## 18. M6 的“立即执行”建议

总体支持：

> M6 已经签发，不应无故继续等待。

但因为 M6 属于：

```text
CRITICAL + FROZEN
```

必须先完成 FROZEN Preflight：

```text
request
baseline
HEAD
worktree
frozen inputs
hash
scope
```

全部匹配后：

```text
ACK
→ Execute
```

不能因为“已经签发”就跳过机械预检。

---

## 19. REWORK 税的最终处理

目标：

> **Codex 尽量不看内部失败。**

建议：

```text
Claude
↕
Copilot PRE-REVIEW
↕
Claude repair
↕
Copilot PRE-REVIEW
...
```

直到：

```text
stable candidate
```

才：

```text
Delivery Snapshot
→ FORMAL REVIEW
→ Codex
```

只有 Escalation Trigger 才提前叫 Codex。

---

## 20. Batch 内状态建议

Subtask 使用：

```text
TODO
RUNNING
PRE_REVIEW
REWORK_INTERNAL
SUBTASK_READY
```

Batch 使用：

```text
BATCH_RUNNING
BATCH_READY
BATCH_REVIEWED
BATCH_ACCEPTED
BATCH_BLOCKED
```

只有 Codex 可以赋予：

```text
BATCH_ACCEPTED
```

---

## 21. Scientific Gate 仍不可降级

无论 Batch 多高效，以下内容仍必须 Codex：

```text
metric freeze
physical Gate
route adoption
paper-critical numeric claim
paper figure freeze
units/window/convergence dispute
raw-evidence conflict
FROZEN final acceptance
```

Batch 优化不是：

> “让 Codex 不再审科学结论。”

而是：

> “让 Codex 不再把额度花在内部 debug 和机械 rework 上。”

---

## 22. Codex 接触次数目标

不应把：

```text
8 次
```

设成硬上限。

正确原则：

> **没有 Scientific Gate / Batch Gate / Exception，就不调用 Codex。**

按当前 Batch：

```text
A     1
B     1
C1    1
C2    1
D     1
E     1
F     1–2
```

基础约：

```text
7–8 次主要审计
```

加 exception：

```text
约 8–12 次
```

比 task-level 约 30 次明显降低。

---

## 23. 对原时间估计的修正

Claude 原建议中的：

```text
“6 月底前……”
```

与当前日期不一致，因此不采纳该绝对时间。

仅保留相对工期作为粗略 planning estimate：

```text
M6               ~2–4 天
Batch B          ~2–3 天
Batch C          ~2–3 天
Route D/E        ~1–2 周并行
System Gate      ~1 周
```

这些都不是协议保证。

---

## 24. 建议的新职责矩阵

| 行为 | Claude | Copilot | Codex | User |
|---|---:|---:|---:|---:|
| Batch proposal draft | ✅ | Review | Approve/Edit | 可要求 |
| Batch Contract final | ❌ | ❌ | ✅ | 可决定 |
| Internal subtask execution | ✅ | ❌ | ❌ | — |
| PRE-REVIEW | 响应 | ✅ | ❌ | — |
| Internal rework | ✅ | ✅ review | ❌ | — |
| SUBTASK_READY | ✅ propose | ✅ agree | ❌ | — |
| FORMAL REVIEW | ❌ | ✅ | 读 | — |
| BATCH_ACCEPTED | ❌ | ❌ | ✅ | 可否决 |
| Scientific Gate | evidence | evidence review | ✅ audit | 最终采用 |
| Metric freeze | ❌ | ❌ | 建议/审计 | ✅ final |
| Route adoption | ❌ | ❌ | 审计/建议 | ✅ final |
| Paper claim | ❌ | ❌ | 审计 | ✅ final |

---

## 25. 对 WORKFLOW-lite 2.0 的建议增量

如果三方认可，不建议重写整个 WORKFLOW-lite。

只新增一个扩展章节：

```text
Batch Execution / Delegated Closure
```

包含：

1. Batch Contract；
2. Internal Subtasks；
3. FREE INNER LOOP；
4. PRE-REVIEW；
5. SUBTASK_READY；
6. Delivery Snapshot；
7. FORMAL REVIEW；
8. BATCH_ACCEPTED；
9. Escalation Triggers；
10. Standing Authorization / Exploration Envelope。

---

## 26. 请三方重点审阅的问题

### Q1

是否同意：

```text
Codex 从 task-level auditor
→ batch-level / scientific-gate auditor
```

？

### Q2

是否同意：

```text
Claude + Copilot
可以在 Batch scope 内自行完成多轮 internal rework，
不需要每轮 Codex
```

？

### Q3

是否同意：

```text
PRE-REVIEW
≠
FORMAL REVIEW
```

并规定正式 REVIEW 必须发生在 Delivery Snapshot 后？

### Q4

是否同意使用：

```text
SUBTASK_READY
```

替代每个 subtask 的 Codex ACCEPT？

### Q5

Escalation Triggers 是否足够？

是否需要增加/删除触发项？

### Q6

是否认可：

```text
M7 + M8
=
一个 CRITICAL + LITE Batch
```

并由 Codex 合并审计？

### Q7

是否认可：

```text
M9 与 M11
语义上保留两个 Gate
```

即使可以在同一 Codex 会话连续审？

### Q8

Route C / D 是否可以使用：

```text
Standing Authorization
+
exploration_only claim ceiling
```

直到 candidate Gate 才唤醒 Codex？

### Q9

M10 是否存在 downstream scientific dependency？

若无，是否同意从 critical path defer？

### Q10

W5 是否同意：

```text
exploration phase = zero Codex
final novelty claim = later high-confidence review
```

？

---

## 27. 最终建议架构

```text
USER
Research Director
       │
       ▼
CODEX
Batch Architect
Scientific Gate Auditor
Exception Resolver
       │
       ▼
BATCH CONTRACT
       │
       ▼
┌────────────────────────────┐
│      FREE INNER LOOP       │
│                            │
│ Claude Implementation Lead │
│            ↕               │
│ Copilot Continuous Reviewer│
│                            │
│ implement                  │
│ test                       │
│ simulate                   │
│ pre-review                 │
│ rework                     │
│ evidence checks            │
└──────────────┬─────────────┘
               │
          stable candidate
               │
               ▼
       Delivery Snapshot
               │
               ▼
       Copilot Formal Review
               │
               ▼
             CODEX
       Batch / Gate Audit
               │
       ACCEPT / REWORK
```

核心目标：

> **Codex 不再管理每一个工作步骤，而是管理批次边界、异常和科学判决。**

> **Claude 与 Copilot 承担高频、可重复、可修复的内部工作。**

> **科学关键节点的独立审计不削弱，只把机械 rework 从 Codex 视野中移除。**

---

## 28. 当前状态

```text
Proposal status:
FOR_THREE_PARTY_REVIEW

Protocol change:
NOT YET

Research task authorization:
NO
```

待 Claude / Copilot / Codex 给出意见后，再决定是否把：

```text
Batch Execution / Delegated Closure
```

正式并入 `WORKFLOW-lite 2.0`。
