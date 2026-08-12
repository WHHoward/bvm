---
title: WORKFLOW-lite 2.0 — 最终实施方案
document_type: implementation_plan_and_protocol
design_version: 2.0
protocol_status: PILOT
implementation_status: READY_FOR_IMPLEMENTATION
date: 2026-08-11
intended_executor: Claude Code
authority_note: 本文件定义用户批准的目标方案；在 Pilot 通过并同步权威文件前，现行 AGENTS.md / research/WORKFLOW.md / josim-handoff/v1 仍保持其原有权威。
---

# WORKFLOW-lite 2.0 — 最终实施方案

> 本文件不是新的研究任务授权。
>
> 它的用途是：**让 Claude Code 把仓库改造成可运行 WORKFLOW-lite 2.0 Pilot 的状态。**
>
> 完成仓库改造后，必须先执行 **Pilot 0（Reviewer 环境/权限验证）**；未经用户或 Codex 明确授权，不得自动开始 M12、M5、M6 等研究任务。

---

# 0. 最终决策摘要

经过 Claude、Copilot、Codex 多轮审阅后，最终采用以下架构：

```text
风险等级：
NORMAL / CRITICAL

证据模式：
LITE / FROZEN
```

二者互相独立。

核心协作链：

```text
Codex
Planner
  ↓
TASK.md
  ↓
Claude
Preflight + Executor
  ↓
attempts/Axx/RESULT.md
  ↓
Delivery Snapshot Commit
  ↓
Copilot Reviewer + Skills
  ↓
attempts/Axx/REVIEW.md
  ↓
Codex Final Audit
  ↓
ACCEPT / REWORK / BLOCKED
```

涉及最终科研冻结时：

```text
CRITICAL + FROZEN
  ↓
josim-handoff/v1
```

最终设计原则：

> **轻量默认，但不取消执行前机械防线。**

> **Reviewer 要强，但不能成为第二个 Codex。**

> **Git 提供 LITE 的轻量不可变快照；文件级 SHA-256 留给关键科研证据。**

> **FROZEN 必须在关键证据产生前预注册，不允许事后补票。**

> **把复杂度花在发现真实错误上，而不是花在日常手续上。**

---

# 1. 协议与现有权威文件的关系

在 Pilot 阶段：

```text
WORKFLOW-lite 2.0
=
经用户/Codex 显式指定时使用的 Pilot 协作界面

research/WORKFLOW.md + josim-handoff/v1
=
当前正式权威协议 / FROZEN 后端
```

因此：

1. 不得仅因为本文件存在，就自动把所有新任务切换到 Lite；
2. Lite Pilot 必须由用户或 Codex 显式指定；
3. 已归档任务保持原协议，不重写历史；
4. Pilot 通过后，再统一同步：
   - `AGENTS.md`
   - `research/WORKFLOW.md`
   - `research/CLAUDE_EXECUTOR.md`
   - 相关 skills
5. 同步完成前，不制造“双重默认协议”。

---

# 2. 一套协议，两种证据模式

## 2.1 LITE

用于：

- 默认工程协作；
- 非最终科研冻结；
- 探索性实现；
- 计量实现开发；
- 普通修复与验证。

LITE 依赖：

```text
Git commit / blob
+
TASK
+
Preflight
+
attempt history
+
Reviewer independent checks
```

Git 本身就是轻量哈希链：

```text
blob
→ tree
→ commit
→ parent commit
```

所以 LITE 并不是“没有完整性机制”。

LITE 放弃的是：

- 每个协议文件的独立 SHA 文件；
- request/ACK/receipt/verdict 的完整文件级 hash binding；
- 默认的重型机器 schema 链。

---

## 2.2 FROZEN

用于：

- final physical Gate；
- metric freeze；
- paper-critical number；
- 论文核心 figure；
- 研究路线关键决定；
- 需要长期证明“审查的是哪一份证据”的任务；
- 重大 evidence conflict。

FROZEN 直接复用：

```text
josim-handoff/v1
```

及其：

- request；
- ACK；
- receipt；
- audit/verdict；
- SHA-256；
- frozen snapshot；
- append-only evidence；
- 已有 schema / tooling。

不要重新发明第二套 Formal Freeze 协议。

---

# 3. 风险等级

## 3.1 NORMAL

典型：

- 绘图；
- CLI；
- 文档；
- 无科学语义的重构；
- 普通测试；
- 非 metric 语义辅助工具。

NORMAL 决定：

```text
Reviewer 抽样深度较低
Codex final audit 较轻
```

---

## 3.2 CRITICAL

只要任务影响或可能影响下列任一项，即为 CRITICAL：

- physical Gate；
- SFQ / JTL / phase propagation；
- metric definition；
- measurement semantics；
- unit；
- window；
- threshold；
- tolerance；
- numerical integration；
- timestep；
- solver / convergence；
- raw evidence selection；
- metric freeze；
- research route；
- paper-level claim；
- paper-critical data / figure；
- frozen evidence；
- 历史关键 baseline；
- 新协作机制首次真实运行。

原则：

```text
拿不准
→ CRITICAL
```

用户可强制升级任何任务。

Reviewer 可建议升级，但不得自行修改 TASK 风险等级。

---

# 4. Evidence Mode 的保守规则

TASK 必须明确：

```text
Evidence mode: LITE | FROZEN
```

如果任务从一开始预期用于：

- final Gate；
- metric freeze；
- 论文核心数字；
- 论文 figure；
- research route decision；

则必须：

```text
执行前
→ CRITICAL + FROZEN
```

禁止：

```text
先 LITE 得到好结果
→ 事后把这次结果追溯称为 FROZEN
```

已完成的 LITE run：

```text
只能作为探索证据
或下一次 FROZEN run 的设计输入
```

不能自动获得 FROZEN 效力。

证据模式拿不准时：

```text
Reviewer:
Recommended evidence mode: FROZEN

Codex:
最终决定
```

用户也可以直接要求 FROZEN。

---

# 5. LITE → FROZEN 的迁移规则

如果一个 LITE task 在执行过程中发现：

```text
后续结果将用于 final Gate / metric freeze / paper claim
```

必须：

1. 保留当前 LITE attempt 原样；
2. 当前 LITE evidence 只作为探索/设计依据；
3. Codex 创建 **新的 FROZEN attempt / v1 contract**；
4. FROZEN request 在新关键 evidence 产生之前签发；
5. 已有 LITE artifact 可以作为只读 input 引用；
6. 不在同一个 attempt 混用 Lite 三文件和 v1 重型合同；
7. 新 FROZEN run 产生真正可冻结证据。

示意：

```text
A01 LITE
  ↓
发现需要正式冻结
  ↓
A01 保留
  ↓
Codex 发起 FROZEN contract
  ↓
A02 / frozen run
  ↓
request → ACK → receipt → audit
```

---

# 6. 角色边界

## 6.1 User — Final Authority

用户最终决定：

- route；
- metric freeze；
- physical Gate adoption；
- paper-level claim；
- risk 强制升级；
- FROZEN 强制启用；
- 重大偏离是否接受。

---

## 6.2 Codex — Planner + Final Auditor

Codex：

### Task 前

负责：

- Risk；
- Evidence mode；
- TASK revision；
- Execution baseline；
- Goal；
- allowed paths；
- acceptance criteria；
- required evidence；
- stop conditions；
- claim ceiling。

### Task 后

负责：

```text
NORMAL
→ light final audit

CRITICAL
→ raw-evidence deep audit
```

只有 Codex 可以：

```text
ACCEPT
REWORK
BLOCKED
```

Reviewer PASS 不等于 Codex ACCEPT。

---

## 6.3 Claude — Executor

Claude：

- 先做 Preflight；
- 再修改实现；
- 只改 allowed paths；
- 完成 acceptance；
- 保存 required evidence；
- 写 RESULT；
- 不覆盖历史/frozen evidence；
- 遵守 claim ceiling；
- 遇 Stop Condition 就 BLOCKED。

Claude 不得：

- 修改 TASK；
- 静默改风险；
- 静默改 evidence mode；
- 自行扩大 scope；
- 自行冻结 metric；
- 自行批准 final physical Gate；
- 自行把 todo/HANDOVER 标为完成；
- 自行把 provisional artifact assessment 当最终证据接受。

---

## 6.4 Copilot Reviewer — Evidence Reviewer

Reviewer：

> **尝试证伪 executor 的最强 bounded claim。**

Reviewer 检查：

- semantic diff；
- scope；
- tests；
- weak oracle；
- hidden branch；
- boundary；
- negative/control；
- numerical correctness；
- units；
- windows；
- thresholds；
- evidence provenance；
- stale artifacts；
- reproducibility；
- JoSIM/SFQ/JTL 专项证据；
- claim ceiling。

Reviewer 不得：

- 修改实现；
- 修改 TASK；
- 修改 RESULT；
- 修改 raw；
- 修改 frozen evidence；
- ACCEPT task；
- 给最终 physical verdict；
- 冻结 metric；
- 批准 paper claim。

---

# 7. TASK 的两个 Git 提交概念

TASK 必须显式记录：

```text
Task revision commit
Execution baseline commit
```

---

## 7.1 Task revision commit

包含当前不可修改 `TASK.md` 的 Git commit。

它回答：

> 当前执行的是哪一版 TASK？

---

## 7.2 Execution baseline commit

Claude 开始 Preflight 时，预期 worktree HEAD 所在的 commit。

它回答：

> Claude 应从哪个代码快照开始工作？

---

## 7.3 默认规则

默认：

```text
Observed HEAD
==
Execution baseline commit
==
Task revision commit
```

这是最简单、最推荐的模式。

如果两者必须不同：

TASK 必须显式写：

```text
Task revision commit: ...
Execution baseline commit: ...
Allowed baseline difference:
- ...
Reason:
- ...
```

不得依靠口头解释。

---

# 8. TASK.md 模板

```markdown
# TASK <TASK-ID>

Risk: NORMAL | CRITICAL
Evidence mode: LITE | FROZEN

Task revision commit: <commit>
Execution baseline commit: <commit>

Delivery snapshot owner: CODEX | USER | CLAUDE_EXPLICITLY_AUTHORIZED

## Goal
...

## Allowed paths
- ...

## Acceptance criteria
- [ ] ...

## Required evidence
- ...

## Stop conditions
- baseline mismatch
- scope conflict
- metric/unit/window ambiguity
- frozen evidence conflict
- repeated same-root-cause failure
- required evidence unavailable
- task definition must change to make result pass
- ...

## Claim ceiling
...
```

---

# 9. TASK 冻结规则

默认：

```text
TASK.md
→ Codex/authorized coordinator 写完
→ commit
→ TASK revision fixed
```

规则：

1. Claude 不修改；
2. Reviewer 不修改；
3. TASK 实质变更只能由 Codex revision；
4. 每次 revision 创建新 commit；
5. revision 后必须重新 Preflight；
6. 禁止静默覆盖 TASK。

---

# 10. Preflight：必须先写，不能事后补

Lite 不创建独立 ACK 文件。

但 Preflight 是必须的。

Claude 的执行顺序必须是：

```text
1. 读取 TASK
2. 创建 attempts/Axx/RESULT.md
3. 写完整 Preflight block
4. Preflight PASS
5. 才允许修改实现 / 运行会改变任务状态的实验
6. 后续 RESULT 只追加
```

Preflight block 写出后：

> **不得回填、重写、润色原始 Preflight。**

如果发现 Preflight 记录错误：

```text
追加：
Preflight correction note
```

保留原始记录。

---

# 11. Preflight 内容

至少记录：

```text
Task revision commit
Execution baseline commit
Observed HEAD
branch/worktree
git status --porcelain=v1 --untracked-files=all
allowed paths understood
Risk understood
Evidence mode understood
claim ceiling understood
ambiguities
Preflight result
```

示例：

```markdown
## Preflight

Task revision commit: abc1234
Execution baseline commit: abc1234
Observed HEAD: abc1234
Branch/worktree: feature/m12-lite
Git status:
  <output or concise summary>

Allowed paths: understood
Risk: CRITICAL
Evidence mode: LITE
Claim ceiling: understood
Ambiguity: none

Preflight result: PASS
```

---

# 12. Preflight BLOCKED 条件

默认：

```text
Observed HEAD != Execution baseline commit
→ BLOCKED
```

除非 TASK 明确允许差异。

以下也 BLOCKED：

- unexpected dirty worktree；
- scope 冲突；
- TASK ambiguity；
- frozen evidence 可能被覆盖；
- metric/unit/window 定义不足以可靠执行；
- required input 不存在。

Preflight BLOCKED 后：

```text
不得继续实现
```

---

# 13. Attempt 历史

目录：

```text
research/tasks/<TASK-ID>/
├── TASK.md
└── attempts/
    ├── A01/
    │   ├── RESULT.md
    │   └── REVIEW.md
    ├── A02/
    │   ├── RESULT.md
    │   └── REVIEW.md
    └── ...
```

A01 失败：

```text
保留 A01
→ 新建 A02
```

禁止覆盖历史 RESULT / REVIEW。

Git 历史作为进一步恢复机制。

---

# 14. RESULT 中的四维语义

RESULT 必须区分：

```yaml
execution_status:
  COMPLETED | BLOCKED | DEVIATED

executor_artifact_assessment:
  VALID | INVALID | NOT_AUDITED

proposed_physical_verdict:
  PASS | FAIL | INCONCLUSIVE | NOT_APPLICABLE
```

注意字段名称：

```text
executor_artifact_assessment
```

而不是最终 `artifact_status`。

原因：

> Claude 只能报告执行者视角的暂定 artifact assessment。

最终 evidence 是否可接受属于 Reviewer/Codex 后续审查。

严格区分：

```text
execution completed
≠
artifact usable
≠
physical condition satisfied
≠
review passed
≠
Codex accepted
≠
user adopted scientific claim
```

---

# 15. RESULT.md 模板

```markdown
# RESULT <TASK-ID> / Axx

execution_status: COMPLETED | BLOCKED | DEVIATED
executor_artifact_assessment: VALID | INVALID | NOT_AUDITED
proposed_physical_verdict: PASS | FAIL | INCONCLUSIVE | NOT_APPLICABLE

## Preflight
<first-written immutable block>

## Summary
...

## Changes
- ...

## Verification
- command → result

## Evidence
- path
- run id
- relevant parameter
- control
- representative case
- SHA-256 when required

## Changed files
- ...

## Limitations / anomalies
- ...

## Claim
...
```

---

# 16. Delivery Snapshot Commit

Lite 使用 Git，Reviewer/Codex 必须审查**稳定的代码快照**。

所以 RESULT 完成后，进入：

```text
Delivery Snapshot
```

流程：

```text
Claude RESULT complete
  ↓
Claude stops modifying task
  ↓
authorized snapshot owner creates task snapshot commit
  ↓
Reviewer reviews that commit
  ↓
Codex audits that same commit
```

---

# 17. Snapshot Owner：明确责任，不留空白

TASK 必须写：

```text
Delivery snapshot owner:
CODEX | USER | CLAUDE_EXPLICITLY_AUTHORIZED
```

默认：

```text
Delivery snapshot owner: CODEX
```

原因：

- Claude 是 executor；
- 默认不让 executor 自己决定最终交付快照；
- Codex/用户作为协调方创建稳定审查点。

如果为了工作流效率，明确授权 Claude：

```text
Delivery snapshot owner: CLAUDE_EXPLICITLY_AUTHORIZED
```

则 Claude 只能：

1. 创建一次非 amend 的 task delivery commit；
2. 只包含：
   - TASK allowed paths 的改动；
   - 当前 attempt 的 RESULT；
   - TASK 明确允许的 evidence metadata；
3. 不使用 `git add -A`；
4. 不夹带 unrelated changes；
5. 不 amend/rebase/rewrite；
6. commit 后停止修改，等待 Reviewer。

---

# 18. Delivery Snapshot 必须记录

RESULT 追加：

```text
Delivery snapshot commit: <commit>
Snapshot owner: <role>
Snapshot scope check: PASS
```

Reviewer 与 Codex都必须基于该 commit。

Reviewer 不应审查一个持续变化的 worktree。

---

# 19. Reviewer 的两维度建议字段

REVIEW 必须包含：

```text
Recommended risk:
NORMAL | CRITICAL

Recommended evidence mode:
LITE | FROZEN
```

Reviewer 不修改 TASK。

如果 Reviewer 认为：

```text
Risk 应升级
或
Evidence mode 应升级
```

则写：

```text
REWORK / BLOCKED
+
recommendation
+
reason
```

Codex 决定是否：

- 升级；
- 重签；
- 新建 FROZEN attempt；
- 保持原设置。

---

# 20. Reviewer Skill 设计：单一 Canonical Source

不得同时维护两套独立科学审查规则。

仓库已有：

```text
.agents/skills/
```

因此最终规定：

> **`.agents/skills/` 是 review/scientific skill 的 canonical source。**

`.github/skills/` 只是 Copilot adapter / wrapper。

---

# 21. Skill Canonical 规则

如果已有 canonical skill：

```text
.agents/skills/josim-evidence-audit/
.agents/skills/josim-experiment/
```

必须复用。

不得复制一份稍微不同的物理规则到：

```text
.github/skills/
```

从而长期独立演化。

---

# 22. Copilot wrapper skill

例如：

```text
.github/skills/superconducting-simulation-review/SKILL.md
```

不要复制完整相位/SFQ规则。

它应该：

1. 声明何时触发；
2. 指示 Reviewer 读取 canonical：
   - `.agents/skills/josim-evidence-audit/SKILL.md`
   - 对应 references，例如 `phase-evidence-contract.md`
3. 要求遵循 canonical 规则；
4. 只增加 Reviewer 角色边界和 handoff 行为；
5. 不重新定义物理公式/判据。

---

# 23. 初始 Skill Pack：只建 3 个核心

Pilot 前只要求：

```text
1. adversarial-review
2. numerical-science-review
3. superconducting-simulation-review
```

其中：

### adversarial-review

Canonical 可新建于：

```text
.agents/skills/reviewer-adversarial/
```

Copilot wrapper：

```text
.github/skills/adversarial-review/
```

---

### numerical-science-review

Canonical：

```text
.agents/skills/reviewer-numerical/
```

并复用：

```text
.agents/skills/josim-experiment/
```

里的：

- run discipline；
- 不覆盖 raw；
- manifest / run ID；
- evidence path。

Copilot wrapper：

```text
.github/skills/numerical-science-review/
```

---

### superconducting-simulation-review

不新造独立科学规则。

只包装：

```text
.agents/skills/josim-evidence-audit/
```

以及其 references。

Copilot wrapper：

```text
.github/skills/superconducting-simulation-review/
```

---

# 24. 后续 Skill

只有 Pilot 证明有需要时再新增：

```text
semantic-diff-review
test-gap-analysis
evidence-provenance-review
reproducibility-review
```

不要在 Pilot 前一次性建设全部七个。

原则：

> **先证明三项核心 Skill 被真实调用、能发现问题、不会漂移，再扩展。**

---

# 25. Reviewer 审查哲学

Reviewer 采用：

```text
Contradiction-first review
```

核心问题：

> 什么隐藏错误能让 RESULT 看起来正确，但实际上错？

而不是：

> 怎么证明 Claude 已经是对的？

---

# 26. Reviewer Progressive Deepening

```text
Stage 0
TASK / Contract

↓
Stage 1
Snapshot / Git / semantic diff

↓
Stage 2
Hidden-bug hypotheses

↓
Stage 3
Independent evidence triangulation

↓
Only when suspicious:
deeper targeted skill review
```

NORMAL：

- 3–5 个 plausible hypotheses；
- 检查最高价值项；
- 至少一个独立 evidence check（如适用）。

CRITICAL：

- 5–10 个 plausible hypotheses；
- critical tests；
- control；
- boundary/sensitivity；
- raw evidence；
- numerical cross-check；
- provenance；
- Codex focus。

---

# 27. Reviewer 的典型隐藏错误探针

至少考虑：

```text
No-op challenge
Constant-output challenge
Wrong-branch challenge
Weak-oracle challenge
Boundary challenge
Metamorphic challenge
Differential challenge
Stale-artifact challenge
Hidden-state challenge
Coupling challenge
Overclaim challenge
```

JoSIM/SFQ 任务重点考虑：

```text
phase wrap / unwrap
sign/orientation
Δφ/(2π)
voltage-time-area consistency
activity vs event
local vs downstream
zero-input control
event-window boundary
startup transient
duplicate event count
timestep sensitivity
solver sensitivity
```

物理规则必须来源于 canonical `josim-evidence-audit`。

---

# 28. REVIEW.md 统一模板

```markdown
# REVIEW <TASK-ID> / Axx

Review disposition: PASS | REWORK | BLOCKED
Recommended risk: NORMAL | CRITICAL
Recommended evidence mode: LITE | FROZEN

Evidence confidence: HIGH | MEDIUM | LOW
Residual risk: LOW | MEDIUM | HIGH

Reviewed delivery snapshot: <commit>

## Scope
PASS | FAIL | UNKNOWN

Evidence:
- ...

## Acceptance criteria
- [x] ... — PASS — evidence
- [ ] ... — FAIL — evidence

## Independent checks
- ...

## Hidden-error probes
- ...

## Claim ceiling
PASS | FAIL | AMBIGUOUS

## Findings

### Critical
- None.

### Major
- None.

### Minor
- None.

## Residual uncertainty
- ...

## Codex focus
1. ...
2. ...
```

---

# 29. Reviewer PASS 的含义

Reviewer PASS 只表示：

> 在当前 review scope、当前 delivery snapshot、当前可用 evidence 下，未发现要求 rework 的证据层问题。

它不表示：

```text
final physical PASS
metric frozen
paper claim approved
task ACCEPTED
```

---

# 30. Reviewer Prompt 不是 ACL

必须明确：

> `.github/agents/reviewer.agent.md` 的“只写 REVIEW.md”只是行为约束，不是操作系统级权限控制。

因此：

```text
Pilot 0
```

是强制前置。

在 Pilot 0 通过前：

```text
Reviewer = advisory only
```

不能成为协议层正式审查者。

---

# 31. Pilot 0 — Reviewer 环境/约束验证

Pilot 0 不依赖真实研究任务。

目标：

验证 Copilot Reviewer 基础设施。

必须检查：

1. `.github/agents/reviewer.agent.md` 是否被识别；
2. `.github/skills/` wrapper 是否被发现；
3. Reviewer 是否能够读取 canonical `.agents/skills/`；
4. Reviewer 是否实际使用 canonical `josim-evidence-audit`；
5. Reviewer 是否只生成指定测试 attempt 的 `REVIEW.md`；
6. Reviewer 是否修改实现文件；
7. Reviewer 运行检查后是否污染 worktree；
8. Reviewer 是否执行禁止的 Git 操作；
9. Reviewer 是否错误扩大 scope。

---

# 32. Pilot 0 的机械只读验证

在 Reviewer 前记录：

```text
git status --porcelain=v1 --untracked-files=all
```

Reviewer 完成后再次记录：

```text
git status --porcelain=v1 --untracked-files=all
```

期望差异：

```text
仅当前测试 attempt 的 REVIEW.md
```

不得出现：

- source modification；
- raw evidence modification；
- TASK modification；
- RESULT modification；
- unexpected generated tracked files；
- unrelated config changes。

如果出现：

```text
Pilot 0 = FAIL
Reviewer 降级为 advisory only
```

直到修复。

---

# 33. Pilot 1 — 首个真实 Lite 任务

最终采用 Codex 的保守规则：

```text
M12
Risk: CRITICAL
Evidence mode: LITE
```

注意：

M12 本身不是高物理风险。

之所以 CRITICAL：

> **新流程 + Reviewer Agent + Skills 第一次进入真实任务，机制本身具有风险。**

Claim ceiling：

```text
plotting/unit implementation verified only
no physical Gate
```

验证：

- TASK freeze；
- two-commit semantics；
- Preflight；
- attempt history；
- delivery snapshot；
- Reviewer；
- skill invocation；
- Codex CRITICAL audit；
- token/流程成本。

Pilot 1 通过后：

> 后续普通工程任务才允许恢复 `NORMAL + LITE`。

---

# 34. Pilot 2 — M5 计量实现

```text
Risk: CRITICAL
Evidence mode: LITE
```

验证：

- event/window；
- numerical review；
- zero-input control；
- raw evidence；
- critical input/output SHA；
- Reviewer numerical skill；
- josim evidence canonical reuse；
- Codex raw audit。

---

# 35. Pilot 3 — M5 物理解释 / M6

```text
Risk: CRITICAL
Evidence mode: FROZEN
```

验证：

- FROZEN pre-registration；
- Lite → FROZEN transition；
- v1 request/ACK/receipt；
- formal hash binding；
- raw evidence audit；
- physical interpretation；
- final evidence freeze。

---

# 36. CRITICAL + LITE 的 SHA-256 规则

不恢复完整 hash chain。

但关键科研输入/输出必须记录：

```text
path
SHA-256
run ID / manifest identity when available
```

用于回答：

> Reviewer/Codex 到底审了哪一版关键数据？

典型：

- raw CSV；
- netlist；
- derived metric table；
- critical control artifact。

SHA 不用于证明：

- 谁执行了命令；
- AI 身份；
- 命令历史真实性。

---

# 37. frozen / historical evidence

禁止：

- 覆盖；
- 原路径重跑；
- 原地修改；
- 用“重新生成”替换旧 raw。

新执行：

```text
new run ID
new path
new attempt
```

必要时用 SHA 标识。

---

# 38. mailbox 与科研 skills 继续适用

Lite 只改变：

```text
协作层协议
```

不取消项目其他正交工具。

继续适用：

- mailbox 非正式沟通；
- josim-experiment；
- josim-evidence-audit；
- 其他科研 domain skills；
- 现有 run/manifest/evidence discipline。

不要误解为：

```text
用了 WORKFLOW-lite
→ 就不再用原有科研 skill
```

---

# 39. todo / HANDOVER 更新

只有：

```text
Codex ACCEPT
```

之后才允许：

```text
todo/HANDOVER → completed
```

Claude 不得自证完成。

Reviewer PASS 也不得自动更新项目状态。

---

# 40. verify-task 语义

必须拆分：

```text
execution snapshot verification
```

与：

```text
current drift check
```

前者回答：

> executor 当时是否在正确 snapshot 上执行？

后者回答：

> ACCEPT 之后仓库又发生了什么变化？

正常更新 HANDOVER/todo 不得让历史 ACCEPTED task 被误判为“当时执行无效”。

---

# 41. REWORK

发现问题：

```text
A01
↓
REWORK
↓
A02
```

A01 保留。

REWORK 必须写清：

```text
observed discrepancy
why it matters
reproducible evidence
minimum required correction
reverification requirement
```

---

# 42. repeated root cause

连续两个 attempt 同根因失败：

```text
STOP
```

升级给：

```text
Codex / User
```

禁止 AI 无限 trial-and-error。

---

# 43. Pilot 指标

每个 Pilot 记录：

1. Reviewer 是否发现 Claude 未发现的问题？
2. Reviewer findings 是否被 Codex确认？
3. false positive rate 是否可接受？
4. Preflight 是否捕获 baseline/scope 问题？
5. Reviewer 是否只写 REVIEW.md？
6. Reviewer review 前后 git status 是否保持实现只读？
7. Reviewer 是否实际调用 canonical skill？
8. skill 是否出现语义漂移？
9. CRITICAL raw audit 是否仍可靠？
10. NORMAL/LITE 未来是否明显减少机械审查成本？
11. Codex 是否减少重复机械检查？
12. 用户是否能理解 task 当前处于 execution / review / audit / scientific adoption 哪一层？

---

# 44. Pilot 升级条件

完成 2–3 个真实任务后，只有满足：

```text
Preflight works
Reviewer constraints validated
skills discoverable
canonical skill reuse works
snapshot review stable
no material evidence loss
Critical audit remains strong
workflow friction meaningfully reduced
```

才允许：

```text
protocol_status: PILOT
→ FINAL
```

然后统一修改：

- `AGENTS.md`
- `research/WORKFLOW.md`
- `research/CLAUDE_EXECUTOR.md`
- agent/skill references
- verify tooling

让 Lite 成为真正默认接口。

---

# 45. Claude Code 的实施范围

Claude Code 现在要做的是**协议基础设施改造**，不是执行 M12/M5。

应实施：

## A. 协议文件

创建/更新目标：

```text
research/WORKFLOW-lite.md
```

内容以本文件的协议规则为准。

---

## B. Reviewer Agent

创建/更新：

```text
.github/agents/reviewer.agent.md
```

要求：

- Contradiction-first；
- Progressive Deepening；
- Recommended risk；
- Recommended evidence mode；
- delivery snapshot commit；
- task-local REVIEW only；
- canonical skill reuse；
- Pilot 0 aware；
- 不复制科学规则。

---

## C. Canonical Skills

检查现有：

```text
.agents/skills/josim-evidence-audit/
.agents/skills/josim-experiment/
```

不要覆盖。

仅在缺失时新建 reviewer canonical skills：

```text
.agents/skills/reviewer-adversarial/
.agents/skills/reviewer-numerical/
```

---

## D. Copilot Skill Wrappers

只创建三个：

```text
.github/skills/adversarial-review/SKILL.md
.github/skills/numerical-science-review/SKILL.md
.github/skills/superconducting-simulation-review/SKILL.md
```

wrapper 必须指向 canonical sources。

不得复制一份独立的 JoSIM 物理审计规则。

---

## E. Templates

建议创建：

```text
research/templates/workflow-lite/TASK.template.md
research/templates/workflow-lite/RESULT.template.md
research/templates/workflow-lite/REVIEW.template.md
```

模板字段必须和协议完全一致。

---

## F. Pilot 0 测试材料

创建一个不会触发真实科研执行的 sandbox task，例如：

```text
research/tasks/PILOT-REVIEWER-000/
```

只用于验证 Reviewer：

- agent discovery；
- skill discovery；
- read-only behavior；
- REVIEW output；
- git status cleanliness。

不要把它混入真正研究 todo。

---

# 46. Claude Code 不应该做的事

本次协议实施任务中，不得：

- 自动开始 M12；
- 自动开始 M5/M6；
- 修改科研结论；
- 修改 frozen historical evidence；
- 重写 M4 历史；
- 删除 josim-handoff/v1；
- 删除旧 skill；
- 把 `.github/skills` 变成独立科学规则源；
- 自动把 Lite 标为 FINAL；
- 自动把 `AGENTS.md` 切成 Lite 默认；
- 自行更新研究 todo 为完成。

---

# 47. 实施步骤

Claude Code 按顺序：

```text
1. Inspect
2. Plan exact file changes
3. Preserve existing canonical skills
4. Write WORKFLOW-lite
5. Update reviewer agent
6. Add 3 wrapper/core skills
7. Add templates
8. Add Pilot 0 sandbox
9. Run static consistency checks
10. Report diff
11. STOP
```

---

# 48. 实施前检查

Claude Code 先检查：

- `AGENTS.md`
- `research/WORKFLOW.md`
- `research/CLAUDE_EXECUTOR.md`
- `.agents/skills/`
- `.github/agents/`
- `.github/skills/`
- existing reviewer files
- existing handoff tooling
- existing task directory conventions

不要凭本文件假设仓库里一定已有某路径。

如果现有结构与计划冲突：

```text
保留现有 canonical layout
+
最小适配
```

不要为了目录美观重构整个仓库。

---

# 49. 静态一致性检查

实施完成后至少检查：

## Protocol ↔ Templates

字段一致：

- Risk；
- Evidence mode；
- task revision commit；
- execution baseline；
- delivery snapshot owner；
- Preflight；
- executor artifact assessment；
- proposed physical verdict；
- Recommended risk；
- Recommended evidence mode。

---

## Protocol ↔ Reviewer

Reviewer 必须理解：

- snapshot；
- CRITICAL；
- FROZEN；
- claim ceiling；
- review disposition；
- Codex final authority。

---

## Wrapper ↔ Canonical Skill

确保：

```text
wrapper
→ canonical path exists
```

不得产生 dead reference。

---

## No duplicate JoSIM truth

搜索类似：

```text
phase evidence
Δφ/(2π)
voltage-time area
SFQ event
```

确认 `.github/skills/superconducting-simulation-review` 没有复制另一套独立规则。

---

# 50. 实施结果报告格式

Claude Code 最终只需报告：

```markdown
# WORKFLOW-lite 2.0 Implementation Result

Status: COMPLETED | BLOCKED

## Files added
- ...

## Files modified
- ...

## Canonical skill reuse
- ...

## Reviewer configuration
- ...

## Templates
- ...

## Pilot 0 sandbox
- ...

## Static checks
- PASS/FAIL

## Known differences from plan
- ...

## Not executed
- M12
- M5
- M6
- real Reviewer Pilot
```

不要自动把“仓库改造完成”解释成：

```text
WORKFLOW-lite 2.0 FINAL
```

它仍然是：

```text
PILOT
```

直到真实 Pilot 验证。

---

# 51. 最终状态机

Lite task：

```text
TASK COMMITTED
  ↓
PREFLIGHT
  ├─ BLOCKED
  ↓
EXECUTION
  ↓
RESULT COMPLETE
  ↓
DELIVERY SNAPSHOT
  ↓
REVIEW
  ├─ REWORK → NEW ATTEMPT
  ├─ BLOCKED
  ↓
CODEX AUDIT
  ├─ REWORK → NEW ATTEMPT
  ├─ BLOCKED
  ↓
ACCEPT
  ↓
todo/HANDOVER update
```

如果需要正式科研冻结：

```text
LITE exploration
  ↓
decision to freeze
  ↓
NEW FROZEN ATTEMPT
  ↓
v1 request
  ↓
ACK
  ↓
execution
  ↓
receipt
  ↓
review/audit
  ↓
final frozen evidence
```

---

# 52. 最终职责矩阵

| 工作 | Claude | Copilot Reviewer | Codex | User |
|---|---:|---:|---:|---:|
| TASK drafting | ❌ | ❌ | ✅ | 可要求 |
| TASK revision | ❌ | ❌ | ✅ | 最终权 |
| Preflight | ✅ | 检查 | 抽查 | — |
| implementation | ✅ | ❌ | 通常 ❌ | — |
| RESULT | ✅ | ❌ | 读 | — |
| delivery snapshot | 默认 ❌ | ❌ | 默认 ✅ | 可执行/授权 |
| Reviewer skill review | ❌ | ✅ | 读 | — |
| REVIEW | ❌ | ✅ | 读 | — |
| recommended risk | ❌ | ✅ | 决定 | 可强制 |
| recommended evidence mode | ❌ | ✅ | 决定 | 可强制 |
| critical raw audit | 提供 evidence | 辅助 | ✅ 必须 | — |
| physical verdict | proposed only | ❌ final | 审查 | 最终采用 |
| metric freeze | ❌ | ❌ | 建议 | 最终采用 |
| paper claim | ❌ | ❌ | 审查 | 最终采用 |
| ACCEPT | ❌ | ❌ | ✅ | 可否决/最终科研采用 |
| todo/HANDOVER complete | ❌ | ❌ | ACCEPT 后 | 可决定 |
| FROZEN initiation | ❌ | recommend | ✅ | 可强制 |

---

# 53. 十条不可删除的底线

以后即使继续简化，也保留：

```text
1. Goal 明确。
2. Allowed paths 明确。
3. Acceptance criteria 明确。
4. Stop conditions 明确。
5. Claim ceiling 明确。
6. 执行前 baseline 可核对。
7. TASK 不允许静默修改。
8. Reviewer 有独立证据来源。
9. CRITICAL 科学任务由 Codex 从 raw evidence 深度复核。
10. 用户保留 route / metric freeze / physical Gate / paper claim 最终权。
```

---

# 54. 给 Claude Code 的最终执行指令

将本文件交给 Claude Code 时，使用：

```text
请按照《WORKFLOW-lite 2.0 — 最终实施方案》执行“协议基础设施改造”。

你的任务是把仓库准备到可以运行 Pilot 0 的状态，不是开始任何真实科研任务。

要求：
1. 先检查仓库现有 AGENTS.md、research/WORKFLOW.md、research/CLAUDE_EXECUTOR.md、.agents/skills、.github/agents、.github/skills 和 josim-handoff 工具链。
2. 保留现有权威协议与历史任务，不重写 M4 历史。
3. 创建/更新 research/WORKFLOW-lite.md。
4. 创建/更新 .github/agents/reviewer.agent.md。
5. .agents/skills 作为 canonical source；.github/skills 仅做 Copilot wrapper。
6. 首批只实现 adversarial-review、numerical-science-review、superconducting-simulation-review 三个 Reviewer Skill；JoSIM/SFQ 物理规则必须复用现有 josim-evidence-audit，不得复制平行规则。
7. 创建 TASK / RESULT / REVIEW 模板，并与协议字段完全一致。
8. 创建不触发真实科研工作的 Pilot 0 Reviewer sandbox。
9. 做静态一致性检查并报告所有变更。
10. 完成后停止，不启动 M12、M5、M6，不把协议标为 FINAL，不更新研究 todo/HANDOVER 为完成。

若仓库现实结构与本文件假设冲突，优先保留现有 canonical 资产并做最小适配；不要为了匹配示例路径而大规模重构。
```

---

# 55. 最终结论

最终采用：

```text
WORKFLOW-lite 2.0
=
Risk-aware collaboration interface

LITE
=
Git-backed lightweight evidence workflow

FROZEN
=
josim-handoff/v1 formal evidence backend

Copilot
=
strong evidence reviewer

Codex
=
planner + final auditor

Claude
=
executor

User
=
final scientific authority
```

当前阶段：

```text
Design: FINAL
Implementation: READY
Protocol deployment: PILOT
```

下一实际步骤只有一个：

```text
Claude Code 实施协议基础设施
→ Pilot 0
→ Pilot 1
→ Pilot 2
→ Pilot 3
→ 再决定 PILOT → FINAL
```
