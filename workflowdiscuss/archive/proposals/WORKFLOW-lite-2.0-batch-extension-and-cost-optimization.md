---
title: WORKFLOW-lite 2.0 — Batch Extension 最终建议与第三方成本优化
document_type: three_party_review_synthesis_and_cost_optimization
status: FOR_THREE_PARTY_REVIEW
date: 2026-08-11
basis:
  - Copilot 对 Batch Acceleration 提案的审阅意见
  - Claude 对 Batch Acceleration 提案的审阅意见
  - Codex 对 Batch Acceleration 提案的审阅意见
purpose: 汇总三方共识、收敛 Batch Extension，并从独立第三方视角提出在不降低科研审查质量前提下进一步降低 Codex 与上下文成本的机制
---

# WORKFLOW-lite 2.0 — Batch Extension 最终建议与第三方成本优化

> 本文供 **Claude / Copilot / Codex 三方再次审阅**。
>
> 本文不自动修改现行协议，不授权任何研究任务。
>
> 文档分为两部分：
>
> 1. **三方反馈收敛后的 Batch Extension 建议**；
> 2. **Third-party optimization：独立第三方视角提出的进一步降成本方案**。
>
> 第二部分是新增建议，不代表三方已经同意。

---

# Part I — 三方反馈后的最终收敛

# 1. 核心方向已经形成共识

三方已经基本一致支持：

```text
Codex
从：
task-level 高频管理者

调整为：
Batch Architect
+
Scientific Gate Auditor
+
Exception Resolver
```

同时：

```text
Claude
=
Implementation Lead

Copilot
=
Continuous Evidence Reviewer

User
=
Research Director / Final Scientific Authority
```

核心优化原则保持：

> **Never send an unstable attempt to Codex.**

但必须同时增加一句：

> **Do not hide unstable attempts from Codex.**

也就是：

```text
失败 iteration
不需要 Codex 逐个处理

但
必须可追溯、可发现、可复验
```

---

# 2. 建议最终 Batch 架构

```text
                     CODEX
                 Batch Contract
                      │
                      ▼
        ┌─────────────────────────┐
        │     FREE INNER LOOP     │
        │                         │
        │ Claude Implementation   │
        │          ↕              │
        │ Copilot PRE-REVIEW      │
        │          ↕              │
        │ Claude Internal Rework  │
        │                         │
        │ RESULT + LEDGER         │
        │ SUBTASK_READY           │
        └────────────┬────────────┘
                     │
              BATCH-MANIFEST
                     │
                     ▼
              Stable Candidate
                     │
                     ▼
             Delivery Snapshot
                     │
                     ▼
           Fresh/Continuity Review
                     │
                     ▼
                   CODEX
            Batch / Gate Audit
                     │
              BATCH_ACCEPTED
```

---

# 3. Batch 必须拥有事实层

Mailbox 仍然只是：

```text
Communication Layer
```

Batch 的正式事实必须落盘。

推荐：

```text
research/tasks/<BATCH-ID>/
├── BATCH.md
├── BATCH-MANIFEST.md
│
├── subtasks/
│   ├── M7/
│   │   ├── RESULT.md
│   │   └── LEDGER.md
│   │
│   └── M8/
│       ├── RESULT.md
│       └── LEDGER.md
│
└── attempts/
    └── A01/
        ├── RESULT.md
        └── REVIEW.md
```

其中：

```text
BATCH.md
=
Codex 授权边界

BATCH-MANIFEST.md
=
append-only Batch 索引

RESULT.md
=
subtask / batch 执行事实

LEDGER.md
=
内部 PRE-REVIEW 与 rework 的最小留痕

attempts/Axx/REVIEW.md
=
最终 snapshot 的正式 Review
```

---

# 4. BATCH.md 必须定义什么

最少包含：

```text
Batch ID
Risk
Evidence mode
Execution baseline
Task/Batch revision
Allowed paths
Subtasks
Dependencies
Locks
Parameter envelope
Acceptance criteria
Claim ceiling
Escalation triggers
Delivery snapshot rule
Codex checkpoint
```

Batch Contract 的目标不是详细规定每一步怎么实现。

它定义的是：

> Claude + Copilot 在什么边界内可以自由工作。

---

# 5. BATCH-MANIFEST.md：轻量 append-only 索引

Codex 不需要读所有失败日志。

但必须能够知道：

```text
发生过哪些 attempt
哪些失败
哪些被 supersede
哪些 evidence 被使用
哪些参数被锁定
哪些 escalation 曾触发
最终 snapshot 是什么
```

推荐条目：

```yaml
- subtask: M7
  attempt: S01
  input_snapshot: <commit>
  state: REWORK_INTERNAL
  finding_summary:
    - P01 boundary case missing
  evidence:
    - path: ...
      sha256: ...
  superseded_by: S02

- subtask: M7
  attempt: S02
  state: SUBTASK_READY
  delivery_candidate: <commit>
  escalation_triggered: false
```

原则：

> **Manifest 是索引，不是大日志。**

---

# 6. PRE-REVIEW 必须留最小 Ledger

完全不留痕会让 inner loop 变成黑箱。

但也不应恢复重型审计。

每个 subtask 维护：

```text
LEDGER.md
```

推荐：

```yaml
subtask: M7
state: SUBTASK_READY

execution_status: COMPLETED
executor_artifact_assessment: VALID
proposed_physical_verdict: NOT_APPLICABLE
claim_ceiling: OK

acceptance_checks:
  AC1:
    status: PASS
    checked_by: Claude
    reviewed_by: Copilot
    evidence: [...]
  AC2:
    status: PASS
    checked_by: Claude
    reviewed_by: Copilot
    evidence: [...]

pre_review_findings:
  - id: P01
    issue: boundary case missing
    severity: Major
    status: FIXED
    fix_snapshot: ...

  - id: P02
    issue: stale fixture
    severity: Major
    status: FIXED
    fix_snapshot: ...

scientific_semantics_changed: false
escalation_triggered: false
```

---

# 7. SUBTASK_READY 的意义必须严格降权

`SUBTASK_READY` 仅表示：

> 在当前 Batch Contract 内，Claude + Copilot 认为该工作步骤足以继续 Batch 内的下一步。

它不是：

```text
ACCEPTED
physical PASS
artifact finally accepted
route adopted
metric frozen
paper evidence accepted
todo completed
```

必须显式保留四维语义：

```text
execution status
executor artifact assessment
proposed physical verdict
claim ceiling
```

并写：

```text
SUBTASK_READY has no authority outside the current Batch.
```

---

# 8. 下游污染半径规则

新增硬性 Escalation Trigger：

> **如果一个已经被下游 subtask 使用的 SUBTASK_READY 结果后来被重新质疑，立即停止依赖链并升级 Codex。**

示例：

```text
M7 SUBTASK_READY
      ↓
M8 depends on M7
      ↓
M7 acceptance questioned
      ↓
STOP M8
      ↓
Codex escalation
```

不得因为：

```text
M7 曾经 READY
```

就继续传播错误。

---

# 9. FREE INNER LOOP 的绝对边界

Claude + Copilot 可以内部自由处理：

```text
implementation bug
test bug
logging
format
test coverage
same pre-registered rerun
non-semantic refactor
analysis tooling repair
```

但不得静默修改：

```text
topology
stimulus
control
window
direction
unit
threshold
tolerance
parameter range
interpretation target
metric definition
scientific dependency
```

核心条款：

> **Implementation repair is delegated; scientific semantics are not.**

只要这些科学输入/语义之一需要改变：

```text
STOP INNER LOOP
→ Escalation
→ Codex
```

FROZEN 工作中，语义变化以后产生的 raw evidence 必须属于：

```text
new attempt
+
new immutable run ID
```

不能当普通 internal rework。

---

# 10. PRE-REVIEW 与 FORMAL REVIEW

## PRE-REVIEW

发生在 snapshot 前。

目的：

```text
发现 bug
快速修复
减少 Codex 看见失败的概率
```

它：

```text
不是正式 PASS
不是 final evidence review
```

---

## FORMAL REVIEW

发生在 Delivery Snapshot 后。

必须：

```text
重新从 snapshot 出发
重新构造 falsification hypotheses
重新检查关键 evidence
重新验证 PRE-REVIEW 曾发现的问题类型
```

核心原则：

> **PRE-REVIEW 抓 bug；FORMAL REVIEW 还要抓“修 bug 时引入的新错”。**

不得简单复用：

```text
PRE-REVIEW PASS
→ FORMAL PASS
```

---

# 11. Continuity Review 与 Independent Review

如果同一个 Copilot参与：

```text
PRE-REVIEW
+
最终 snapshot review
```

那么最终 review 应标：

```text
review_mode: CONTINUITY
```

不能宣称完全 independent。

如果是：

```text
新上下文 / 未参与修复的 Reviewer
```

可标：

```text
review_mode: FRESH_CONTEXT
```

对于：

```text
CRITICAL + FROZEN
```

建议至少满足：

```text
Fresh-context Reviewer
```

或：

```text
Codex independent raw-evidence recomputation
```

二者之一。

---

# 12. 推荐：正式 Review 输出增加 involvement disclosure

```yaml
review_mode: CONTINUITY | FRESH_CONTEXT
reviewer_involved_in_pre_review: true | false
reviewed_snapshot: <commit>
```

防止把 continuity review 误称为 independent review。

---

# 13. Standing Authorization 的数据质量边界

探索授权：

```text
exploration_only
```

只限制 claim 还不够。

即使探索阶段，也必须继续遵守科研 evidence discipline：

```text
unique run ID
manifest
raw CSV
hash where required
no overwrite
pre-registered window
pre-registered threshold
pre-registered control
parameter envelope
```

原则：

> **Exploration claim ceiling may be relaxed; evidence discipline is not.**

新增 Escalation Trigger：

```text
任何预注册 measurement 参数需要改变
→ Codex escalation
```

---

# 14. Route C / D 的依赖边界

Standing Authorization 可以采用。

但只有：

```text
Phase −1 完成
M4–M11 完成
M11 baseline accepted
```

之后才可启动：

```text
Route C Q1–Q6
Route D D1–D6
```

因此当前：

```text
Route C/D = BLOCKED UNTIL M11
```

exploration_only 不绕过项目依赖。

---

# 15. M7 / M8 / M9 的最终建议修正

上一版建议：

```text
M7 + M8
CRITICAL + LITE
```

需要进一步细化。

如果 M8 的 decisive timestep convergence evidence 会用于：

```text
M9 tolerance
metric freeze
physical interpretation
```

则 M8 的关键 raw evidence 本身必须提前冻结。

推荐：

```text
B1
M7 regression implementation
CRITICAL + LITE

B2
M8 decisive convergence evidence
CRITICAL + FROZEN

M9
METRIC_SPEC_V2 freeze
CRITICAL + FROZEN
```

另一可接受方案：

```text
M7 + M8 entire batch
CRITICAL + FROZEN
```

但不要：

```text
M8 LITE decisive evidence
→ later retroactively treated as FROZEN input to M9
```

---

# 16. M9 / M11 仍保持两个独立 Gate

固定：

```text
M9
Metric Freeze Gate
      ↓
ACCEPTED
      ↓
M11
New Baseline Gate
```

允许：

```text
同一次 Codex 会话连续审
```

但必须：

```text
两个独立 record
两个独立 decision
```

M9 未接受时，M11 不得正式依赖 frozen metric。

---

# 17. M10 的最终判断规则

M10 不默认删除，也不默认 defer。

先生成：

```text
consumer / dependency map
```

如果：

```text
M11
regression
baseline
paper evidence
```

需要历史：

```text
BASELINE / P0 / P2 / v4
```

的新 metric 输出，则：

```text
M10 = evidence production
```

而不是 archive hygiene。

硬规则：

> **任何论文证据链引用历史 BASELINE/P0/P2/v4 数字之前，M10 必须完成。**

最终是否 defer 由 Codex决定。

---

# 18. W5 的最终建议

探索阶段：

```text
Claude research
+
Copilot cross-check
=
ZERO CODEX
```

当：

```text
coverage matrix
+
gap candidate list
```

形成后：

```text
Copilot matrix verification
+
Codex lightweight sampling checkpoint
```

之后继续推进。

最终：

```text
novelty claim / paper claim
```

仍需高置信审查。

这是额外一次较轻 Codex 接触，但可能显著减少最终 novelty claim 的返工。

---

# 19. Batch Proposal 起草机制

继续建议：

```text
Claude
→ Draft

Copilot
→ Mandatory adversarial completeness review

Codex
→ Edit / Approve
```

Copilot 不只是检查字段是否存在。

必须对抗性检查：

```text
acceptance 是否可证伪
constant implementation 能否通过
claim ceiling 是否过宽
escalation triggers 是否遗漏
scientific semantic locks 是否完整
dependency 是否明确
```

最后 Acceptance Criteria 只能由 Codex正式确认。

防止执行者 goalpost-moving。

---

# 20. Batch Size 的建议

紧耦合 Batch 不应无限扩大。

建议默认：

```text
2–3 strongly coupled subtasks max
```

除非 Codex显式批准更大的 Batch。

原因：

```text
Batch 越大
→ dependency graph 越复杂
→ contamination radius 越大
→ Codex 最终 audit 上下文反而更大
```

Batch 的目标不是：

> 把所有任务塞成一个“大任务”。

而是：

> 减少无意义 handoff，同时保持可理解的依赖边界。

---

# 21. 审计指标必须分开

以后同时记录：

```text
Codex touchpoints
```

与：

```text
Codex audit workload
```

示例：

```yaml
codex_touchpoints: 1
codex_audit_scope:
  critical_evidence_sets: 2
  raw_recomputations: 1
  scientific_gates: 1
```

目标是：

```text
减少 context switch / handoff /重复机械阅读
```

而不是：

```text
为了“只接触一次”把两份深审工作伪装成一份
```

---

# Part II — Third-party Optimization

> 以下是独立第三方视角的新建议。
>
> 这些不是三方反馈中的既有共识，建议 Claude / Copilot / Codex 单独评估。

---

# 22. Third-party Optimization A：双 Reviewer 上下文，而不是双 Reviewer 成本

目前最大的 reviewer 风险之一是：

```text
Copilot PRE-REVIEW
→ 参与修复
→ FORMAL REVIEW 被锚定
```

但 Copilot 资源不是瓶颈。

因此最划算的方案不是增加 Codex，而是：

```text
Copilot Session A
=
PRE-REVIEWER

Copilot Session B
=
FRESH FORMAL REVIEWER
```

两者使用相同 canonical Reviewer Skills。

流程：

```text
Claude
↕
Copilot-A PRE-REVIEW
↕
Claude fix
       ↓
Delivery Snapshot
       ↓
Copilot-B fresh-context FORMAL REVIEW
       ↓
Codex
```

优势：

```text
几乎不增加 Codex 成本
大幅降低 reviewer anchoring
Formal Review 更接近真正 second pair of eyes
```

注意：

这仍然不是“不同组织的独立审计”。

但从认知上下文角度比同一会话 continuity review 强很多。

### 建议

对于：

```text
CRITICAL Batch
```

默认：

```text
PRE-REVIEWER
≠
FORMAL REVIEW conversation/context
```

对于：

```text
NORMAL Batch
```

允许同一 Reviewer continuity review。

---

# 23. Third-party Optimization B：机器生成 Audit Packet

目前 Codex的隐性成本不只是“被调用一次”，而是：

> 每次都要重新读取 TASK、diff、测试、ledger、raw path、review 才能重建上下文。

这些信息大部分可以由脚本机械生成，不需要 Claude/Copilot 写长摘要。

建议 Delivery Snapshot 后自动生成：

```text
AUDIT-PACKET.md
```

或机器生成 JSON + 简短 Markdown。

例如：

```yaml
batch: B2
snapshot: abc1234
risk: CRITICAL
evidence_mode: FROZEN

changed_files:
  - ...
  - ...

subtasks:
  - M8:
      state: SUBTASK_READY
      attempts: 3
      pre_review_major_fixed: 2

acceptance:
  AC1: PASS
  AC2: PASS

semantic_locks:
  timestep_set: ...
  window: ...
  threshold: ...
  unit: ...

critical_evidence:
  - path: ...
    sha256: ...
  - path: ...
    sha256: ...

formal_review:
  disposition: PASS
  mode: FRESH_CONTEXT
  critical_findings: 0
  major_findings: 0

codex_focus:
  - convergence sensitivity
  - boundary trace X
```

Codex首先读：

```text
AUDIT-PACKET
```

然后只针对：

```text
Codex focus
+
random/critical sample
+
raw scientific Gate evidence
```

打开原文件。

### 关键边界

`AUDIT-PACKET` 只是：

```text
index / cache
```

不是证据本身。

所有底层 evidence 仍然可访问。

这可以显著降低 Codex 的输入 token 和上下文重建成本，却不降低 raw audit 能力。

---

# 24. Third-party Optimization C：Audit Packet 必须机械生成，而不是 LLM 总结

如果 Audit Packet 全由 Claude 写：

```text
可能遗漏
可能选择性总结
可能把自己的理解带进去
```

更好的办法：

```text
script
→ read BATCH-MANIFEST
→ read Git diff metadata
→ read RESULT/REVIEW headers
→ calculate hashes
→ output packet
```

Claude/Copilot只写：

```text
human findings / scientific notes
```

机械字段由程序生成。

这样：

```text
更便宜
更一致
更难出现“摘要漂移”
```

建议未来实现：

```text
tools/build-audit-packet.py
```

---

# 25. Third-party Optimization D：Decision Cache / Scientific ADR

Codex昂贵的另一类浪费是：

> 同一个科学语义问题在不同 Task/Batch 被反复解释。

例如：

```text
window 的定义
phase sign convention
event semantics
local vs downstream
timestep acceptance rule
metric naming
```

一旦 Codex/User正式决定，就应该写成：

```text
Scientific Decision Record
```

例如：

```text
research/decisions/SDR-0007-event-window.md
```

内容：

```yaml
decision: event window definition
status: ACTIVE
scope: METRIC_SPEC_V2
approved_by: Codex/User
effective_from: ...
supersedes: ...
invalidate_if:
  - metric revision
  - topology class changes
```

后续 Batch：

```text
reference SDR-0007
```

而不是每次重新让 Codex解释一遍。

### 成本收益

```text
Codex 一次决策
→ 多个后续 Batch 复用
```

尤其适合：

```text
units
window
threshold semantics
sign convention
control definition
naming
evidence interpretation rules
```

---

# 26. Third-party Optimization E：Decision Cache 必须有 invalidation 条件

Decision Cache 不能变成“永远正确”。

每个 SDR 必须写：

```text
valid_for
invalidate_if
superseded_by
```

如果触发：

```text
metric revision
new topology class
new evidence contradiction
unit model change
solver behavior change
```

则：

```text
旧 Decision 不再自动复用
→ Escalate Codex
```

这样既节省重复推理，又不会让旧决定绑死新研究。

---

# 27. Third-party Optimization F：Semantic Lock File

FREE INNER LOOP 最大风险是科学参数静默漂移。

现在靠 prompt + ledger 检查。

可以进一步机械化：

```text
SEMANTIC-LOCK.yaml
```

例如：

```yaml
topology: ...
stimulus: ...
control: ...
window:
  start: ...
  end: ...
unit: ...
threshold: ...
tolerance: ...
parameter_range: ...
interpretation_target: ...
```

Batch 开始时锁定。

Inner loop 每次关键 run 前：

```text
verify semantic lock
```

如果 run manifest 与 lock 不一致：

```text
FAIL
→ Escalation required
```

优势：

```text
不需要 Codex 人工发现参数被悄悄改了
由机器先挡住
```

这是一种典型：

> **用便宜的确定性检查替代昂贵模型审查。**

---

# 28. Third-party Optimization G：Semantic Lock 与 FROZEN 区别

Semantic Lock 不等于 FROZEN。

```text
Semantic Lock
=
防止 inner loop 静默改变科学输入

FROZEN
=
正式不可变科学 evidence chain
```

因此：

```text
CRITICAL + LITE
也可以有 Semantic Lock
```

而不需要整套 v1。

这是一个很高性价比的中间层。

---

# 29. Third-party Optimization H：Deterministic Sampling for Codex

对于非 final Gate 的 Batch Audit，如果 Codex需要抽查多个 subtask，可以避免：

```text
Claude/Copilot 自己挑“最好看的 case”给 Codex
```

建议抽样由固定规则决定。

例如：

```text
sample seed = delivery snapshot commit hash
```

然后脚本确定：

```text
1 control case
1 boundary case
1 random representative case
```

Codex审这些样本。

优势：

```text
难以 cherry-pick
抽查成本可控
结果可复现
```

对于：

```text
final physical Gate / metric freeze
```

仍按完整 critical evidence 规则，不用 sampling 代替正式审查。

---

# 30. Third-party Optimization I：Exception-only Codex Queue

Mailbox 可以进一步结构化。

不要让 Codex 收到所有：

```text
M7 开始了
M7 修了
M7 PASS
M8 开始了
...
```

建议建立：

```text
to-codex/urgent/
to-codex/batch-ready/
```

只有：

```text
Escalation Trigger
Batch Ready
Scientific Gate
```

才进入 Codex 队列。

普通 PRE-REVIEW chatter：

```text
Claude ↔ Copilot
```

不进入 Codex inbox。

这样不仅省 token，还减少：

```text
attention fragmentation
```

---

# 31. Third-party Optimization J：Batch Audit Window

如果多个独立 Batch 在很短时间内先后 Ready：

```text
Batch D ready
Batch E ready
W5 checkpoint ready
```

而它们之间没有阻塞依赖，可以让 Codex 在一次会话中：

```text
Batch Audit Window
```

连续审完多个 packet。

不是把它们变成一个 Batch。

而是：

```text
一个 Codex context session
→ 多个独立 decision record
```

优势：

```text
减少重复加载 repo context / protocol context
```

但必须：

```text
每个 Batch 独立 decision
每个 Gate 独立 record
```

这和 M9/M11：

```text
同会话
不同 Gate
```

是同一个思路。

---

# 32. Third-party Optimization K：Batch 大小按“依赖深度”而不是任务数量

不要简单规定：

```text
最多 3 个 task
```

更准确的成本指标是：

```text
dependency depth
+
semantic coupling
+
contamination radius
```

例如：

```text
3 个彼此独立的小工具任务
```

可能比：

```text
2 个强依赖科学任务
```

更安全。

建议 Batch Planner 用：

```text
Batch Complexity Score
```

简单考虑：

```text
subtask count
dependency edges
scientific locks count
shared evidence sets
shared implementation
downstream criticality
```

如果复杂度过高：

```text
split batch
```

不需要复杂数学模型，只需要一张 checklist。

---

# 33. Third-party Optimization L：Reviewer Finding Reuse

PRE-REVIEW 找到的 bug 类型不应该只存在 Ledger。

可以积累：

```text
reviewer lessons
```

例如：

```text
RL-001: activity-window coverage gap
RL-002: stale artifact
RL-003: wrapped phase end-minus-start
```

以后 Reviewer 在相关任务自动加载：

```text
known failure patterns
```

这能降低：

```text
每次重新“发明”检查策略
```

的 token 消耗。

但只记录：

```text
可泛化 failure pattern
```

不要把具体任务结论永久固化成偏见。

---

# 34. Third-party Optimization M：机器先审，模型后审

很多 Reviewer 工作其实不应该消耗模型：

```text
scope
changed files
hash
manifest completeness
semantic lock equality
missing evidence path
test exit codes
duplicate run ID
stale file references
```

建议建立 deterministic verifier：

```text
verify-batch
```

先输出：

```text
MECHANICAL PASS/FAIL
```

Copilot只处理：

```text
semantic diff
test oracle
numerical reasoning
scientific evidence
hidden error
```

Codex只处理：

```text
scientific Gate
raw evidence
exceptions
```

形成：

```text
Machine
→ cheap mechanical assurance

Copilot
→ cheap semantic/evidence review

Codex
→ scarce scientific judgment
```

这是我认为最有潜力的长期降成本方向之一。

---

# 35. Third-party Optimization N：Fail Fast on Contract, Not on Evidence

为了避免免费 inner loop 也浪费大量时间：

在任何 run 前，先机器验证：

```text
scope
semantic lock
input availability
run ID uniqueness
manifest completeness
baseline
```

只有这些通过才运行 JoSIM / analysis。

也就是：

```text
cheap deterministic preflight
→ expensive execution
```

这不仅省 Codex，也省 Claude/Copilot 的时间。

---

# 36. Third-party Optimization O：预算不是“调用次数”，而是三级成本

建议以后记录：

```text
Tier 0: machine cost
Tier 1: Claude/Copilot cost
Tier 2: Codex cost
```

原则：

```text
能 Tier 0 解决
绝不升级 Tier 1

能 Tier 1 解决
绝不升级 Tier 2

只有 scientific decision / exception
才 Tier 2
```

这可以成为整个 Workflow 的资源调度原则：

> **Lowest sufficient assurance tier.**

即：

> 使用能够满足当前风险的最低成本保证层。

---

# 37. 推荐优先级

如果三方认可，不建议一次实现所有 Third-party Optimization。

建议分优先级。

## P0 — 立即值得采用

```text
1. Fresh-context FORMAL Reviewer
2. Machine-generated Audit Packet
3. Semantic Lock
4. Exception-only Codex Queue
```

原因：

```text
成本低
收益高
不改变科学结论权限
```

---

## P1 — Batch Pilot 后实现

```text
5. Scientific Decision Record / Decision Cache
6. deterministic Codex sampling
7. verify-batch mechanical checker
8. Batch Audit Window
```

---

## P2 — 数据积累后实现

```text
9. Reviewer Lessons / failure-pattern reuse
10. Batch Complexity Score
11. 更自动化的 audit routing
```

---

# 38. 综合后的成本分层

建议最终形成：

```text
Tier 0
Deterministic Tooling
│
├─ preflight
├─ hash
├─ manifest
├─ semantic lock
├─ scope
├─ audit packet
└─ verify-batch
        │
        ▼
Tier 1
Claude + Copilot
│
├─ implementation
├─ simulation
├─ tests
├─ PRE-REVIEW
├─ rework
├─ fresh FORMAL REVIEW
└─ evidence reasoning
        │
        ▼
Tier 2
Codex
│
├─ Batch Contract
├─ Exception
├─ Scientific Gate
├─ critical raw audit
└─ final Batch acceptance
        │
        ▼
User
│
├─ route
├─ metric freeze adoption
├─ physical Gate adoption
└─ paper claim
```

---

# 39. 可能达到的优化效果

不承诺固定数字，但理论上：

原始 task-centric：

```text
~2 Codex touchpoints / task
```

Batch 化以后：

```text
~1 Codex checkpoint / meaningful batch
```

再加入：

```text
Audit Packet
Decision Cache
Exception-only Queue
Fresh Copilot review
Mechanical verifier
```

以后，Codex每次接触需要读取的内容也会明显减少。

因此优化分两层：

```text
第一层：
减少 Codex 被叫醒的次数

第二层：
减少 Codex 每次被叫醒时需要重新理解的上下文
```

第二层通常和第一层同样重要。

---

# 40. 请三方重点评审新增 Third-party Optimization

建议 Claude / Copilot / Codex 分别回答：

### T1

是否同意 CRITICAL Batch 默认：

```text
PRE-REVIEW Copilot context
≠
FORMAL REVIEW Copilot context
```

以 fresh context 降低 anchoring？

### T2

是否同意引入机器生成：

```text
AUDIT-PACKET
```

作为 Codex 首屏入口，但不替代 raw evidence？

### T3

是否同意建立：

```text
Scientific Decision Records
```

复用已经裁决的 unit/window/sign/event 等语义决定？

### T4

是否同意：

```text
SEMANTIC-LOCK
```

把 FREE INNER LOOP 的科学输入边界机械化？

### T5

是否同意对非 final Gate 的 Codex抽查使用：

```text
commit-hash-seeded deterministic sampling
```

避免 cherry-picking？

### T6

是否同意建立：

```text
Exception-only Codex Queue
```

普通 inner-loop 通知不再进入 Codex mailbox？

### T7

是否同意：

```text
Batch Audit Window
```

让多个独立 ready Batch 在同一 Codex 会话连续审，但保持独立记录？

### T8

是否同意长期实现：

```text
verify-batch
```

把机械审查尽量移到 Tier 0？

---

# 41. 最终建议

三方已经足够支持 Batch 核心架构。

建议下一步不再争论：

```text
“要不要 Batch？”
```

而是把正式扩展限定为：

```text
WORKFLOW-lite 2.0
+
Batch Execution / Delegated Closure Extension
```

正式扩展必须至少定义：

```text
BATCH.md
BATCH-MANIFEST.md
LEDGER.md
PRE-REVIEW
SUBTASK_READY
scientific semantic lock boundary
dependency contamination rule
Delivery Snapshot
Continuity/Fresh FORMAL REVIEW
Escalation Triggers
Standing Authorization
FROZEN non-retroactivity
```

同时建议优先考虑四个第三方优化：

```text
Fresh-context Formal Reviewer
Machine-generated Audit Packet
Semantic Lock
Exception-only Codex Queue
```

因为这四项最符合当前目标：

> **不降低效率，不降低科学审查深度，但进一步减少稀缺 Codex 上下文与额度消耗。**

---

# 42. 当前状态

```text
Batch core:
READY FOR EXTENSION DRAFT

Third-party optimizations:
FOR THREE-PARTY REVIEW

Protocol change:
NOT YET

Research task authorization:
NO
```

待 Claude / Copilot / Codex 对本文反馈后，再决定：

1. 哪些内容进入正式 Batch Extension；
2. 哪些 Third-party Optimization 进入 Pilot；
3. 是否开始 M7/M8 真实 Batch Pilot。
