# JoSIM × BVM：Mailbox 驱动三 Agent 协作的最小改造指令

> **用途**：交给 Claude Code，在已经完成 workflow cleanup 的基础上做一次极小的 mailbox-operating-rule 改造。  
> **目标**：以后用户能够主要通过一句：
>
> **“查看你的 mailbox，然后开始你的工作。”**
>
> 驱动 Codex / Claude Code / Copilot 在已有正式任务之间接力，而不需要用户每次重新解释上下文。
>
> **原则**：mailbox 只负责通知与索引；正式授权、科学事实和科研状态仍来自 TASK / RESULT / REVIEW / audit / Git snapshot。

---

# 1. 本轮不要再做 workflow redesign

workflow cleanup 已经结束。

本轮禁止：

- 再设计一套新的 workflow；
- 实现完整 Batch P0；
- verify-batch；
- Decision Cache；
- complexity scoring；
- automatic routing；
- complex Audit Packet；
- Scientific ADR automation；
- FROZEN v1.1 大改；
- 大规模目录重构；
- 修改 M4/M5/M6 scientific history；
- 启动 M7。

本轮只做：

> **Mailbox operating rule + 最小角色接力规则。**

---

# 2. 先检查当前 cleaned workflow

先读取当前实际仓库状态，不假定旧目录结构仍然存在。

至少检查：

```text
AGENTS.md
当前 canonical WORKFLOW
当前 mailbox README / mailbox instructions
CLAUDE_EXECUTOR 或等价 executor-specific 文件
当前 reviewer / Codex 角色规则
memory/project-todo.md
```

然后搜索：

```bash
rg -n "mailbox|TASK|RESULT|REVIEW|audit|BLOCKED|ACCEPT|REWORK" \
  AGENTS.md research docs memory .agents .github
```

目标：

1. 找到 mailbox 当前定义；
2. 找到三角色当前交接方式；
3. 避免重复写一套并行规则；
4. 只在最合适的现有 authority 文件中增加最小规则。

如果 cleanup 后已经存在完全等价规则，只需补缺口，不要复制。

---

# 3. 增加一个统一的 Mailbox Operating Rule

建议放入：

- mailbox 自己的 README / protocol；
- 并在 `AGENTS.md` 中只放一条简短 pointer。

不要在多个文件复制完整规则。

建议 canonical wording：

```text
Mailbox Operating Rule

When the user says:

“查看你的 mailbox，然后开始你的工作”
or equivalent wording,

the agent MUST:

1. Read the newest relevant unprocessed mailbox message for its role.
2. Resolve every referenced canonical artifact before acting.
3. Treat mailbox text only as notification/index metadata.
4. Never treat mailbox text itself as task authority, scientific evidence,
   acceptance, route approval, or todo closure.
5. Obey the referenced TASK / RESULT / REVIEW / audit / snapshot.
6. Check that the message is current and not superseded.
7. If the message is stale, conflicting, ambiguous, missing its referenced
   artifact, or has no valid action for this role:
      STOP and report BLOCKED.
8. Do not invent new work merely because the mailbox is empty.
9. After completing the role:
      write the formal artifact first,
      then use mailbox only to notify the next role.
```

中文说明也可以保留，但 canonical rule 最好只有一份。

---

# 4. Mailbox 必须明确“不是 Authority”

请明确写死：

```text
mailbox != execution authority
mailbox != scientific fact layer
mailbox != audit verdict
mailbox != project state
```

正式来源：

```text
TASK
RESULT
REVIEW
AUDIT / VERDICT
GIT SNAPSHOT / HASH
PROJECT TODO
```

如果 mailbox 和正式 artifact 冲突：

> **正式 artifact 优先。**

如果无法判断哪个更新：

> `BLOCKED`，不要自行猜测。

---

# 5. 只保留最小消息类型

不要建立复杂消息 schema。

当前只需要支持以下语义：

```text
TASK_READY
REVIEW_REQUEST
REWORK_REQUEST
AUDIT_READY
BLOCKED
CLOSED
```

如果现有 mailbox 已有等价命名，优先复用，不要为了名称统一而制造 migration。

每条 mailbox message 最少包含：

```text
role / recipient
message type
canonical artifact path
task id
attempt / snapshot（如果当前协议已有）
short action hint
status
```

不要把完整 scientific reasoning 放进 mailbox。

---

# 6. Claude Code 的 mailbox 行为

当用户对 Claude 说：

> “查看你的 mailbox，然后开始你的工作。”

Claude 应：

```text
mailbox
  ↓
最新 relevant TASK_READY / REWORK_REQUEST
  ↓
打开正式 TASK / REVIEW
  ↓
检查 scope / AC / stop conditions / claim ceiling
  ↓
执行
  ↓
写正式 RESULT / updated evidence
  ↓
mailbox 通知下一个 reviewer / auditor
```

Claude 可以在授权 scope 内连续推进。

只有以下情况停止：

- scientific semantics 需要改变；
- scope 需要扩大；
- acceptance criteria 有歧义；
- stop condition 命中；
- canonical artifact 缺失；
- mailbox 与 TASK 冲突；
- 同根因反复失败且需要重新设计实验。

不要因为普通 implementation bug 就重新找 Codex。

---

# 7. Copilot 的 mailbox 行为

当用户对 Copilot 说：

> “查看你的 mailbox，然后开始你的工作。”

Copilot 应：

```text
mailbox
  ↓
最新 REVIEW_REQUEST
  ↓
读取 TASK
读取 RESULT
读取指定 snapshot / diff / evidence
  ↓
adversarial review
  ↓
写正式 REVIEW
```

Copilot 默认：

- 不修改 implementation；
- 不扩大 scope；
- 不改变 scientific semantics；
- 不更新 todo；
- 不给最终 scientific ACCEPT。

若有 Major finding：

```text
REVIEW
↓
mailbox → Claude / Codex
```

若无 Major：

```text
REVIEW
↓
mailbox → Codex AUDIT_READY
```

具体 recipient 应沿用当前 cleaned workflow 的角色定义。

---

# 8. Codex 的 mailbox 行为

当用户对 Codex 说：

> “查看你的 mailbox，然后开始你的工作。”

Codex 首先判断 mailbox 请求属于：

```text
PLANNING
或
AUDIT
```

## Planning

如果存在一个已由用户决定启动的新科研项：

```text
project-todo / user decision
↓
Codex 定义正式 TASK
↓
mailbox TASK_READY → Claude
```

Codex 不应仅因为 mailbox 中写“做 M8”就自行创造未授权科研路线。

## Audit

```text
AUDIT_READY
↓
读取 TASK
RESULT
REVIEW
raw evidence / snapshot
↓
独立 audit
↓
ACCEPT / REWORK / BLOCKED
```

正式 verdict 写入 canonical audit artifact。

然后 mailbox 只发送状态通知。

---

# 9. 用户一句话驱动已有工作，而不是创造新研究

请把下面的边界写清：

## 可以只说

> “查看你的 mailbox，然后开始你的工作。”

适用于：

- 已签发 TASK；
- 已生成 REVIEW_REQUEST；
- 已生成 REWORK_REQUEST；
- 已生成 AUDIT_READY；
- 已有正式 artifact 等待下一角色。

## 不应该只说这一句

适用于：

- 创建全新科研方向；
- 启动尚未授权的 Mx；
- 改 route；
- 改 MetricSpec；
- 改 Interface Gate；
- 创建 paper claim。

这些仍然需要用户先明确：

> “请规划/启动 X。”

然后 Codex 生成正式 TASK。

---

# 10. 推荐的最简接力

典型 Scientific Implementation：

```text
User
  ↓
Codex creates TASK
  ↓ mailbox TASK_READY
Claude executes
  ↓ writes RESULT
  ↓ mailbox REVIEW_REQUEST
Copilot reviews
  ↓ writes REVIEW
  ├─ Major → mailbox REWORK_REQUEST → Claude
  └─ clean → mailbox AUDIT_READY → Codex
Codex audits
  ↓ writes verdict
  ↓ mailbox CLOSED / REWORK
User
```

用户平时可以只说：

```text
“查看你的 mailbox，然后开始你的工作。”
```

而不需要重新粘贴上下文。

---

# 11. 普通任务不要强制 mailbox 五段接力

Mailbox 不应把简单任务复杂化。

例如：

- plotting；
- README；
- parser；
- ordinary refactor；
- path fix；
- mechanical metadata；
- provenance table formatting。

可以：

```text
User → Claude → done
```

或者：

```text
User → Claude → Copilot optional review → done
```

不需要 Codex，不需要完整 mailbox chain。

Mailbox automation 的目标是：

> **减少交接解释。**

不是：

> **让所有工作都必须经过五个角色状态。**

---

# 12. Scientific Gate 才使用完整接力

以下类型需要完整 formal handoff：

```text
M8 convergence
M9 MetricSpec freeze
M11 baseline
INTERFACE_GATE
route verdict
bounded negative result
paper-critical result
```

流程：

```text
Codex TASK / preregistration
↓
Claude execution
↓
independent review
↓
Codex audit
↓
User adoption where required
```

Mailbox 只是让这条链更容易驱动。

---

# 13. 避免 unread / processed 状态过度工程化

如果当前 mailbox 已经有 handled / closed / superseded 机制，直接沿用。

如果没有，不要为了这个任务写数据库或状态机。

最简单可以通过：

- 文件状态字段；
- mailbox entry status；
- latest superseding message；
- Git history

解决。

本轮不需要：

```text
message queue daemon
automatic scheduler
automatic agent invocation
webhook
database
```

---

# 14. 加一个“无任务则不行动”规则

这是必须项。

当 Agent 被告知：

> “查看 mailbox，然后开始工作。”

但：

- mailbox 没有 relevant unprocessed message；
- 最新 message 已 CLOSED；
- referenced task 已 ACCEPTED；
- recipient 不是自己；
- message 已 superseded；

必须回答类似：

```text
NO_PENDING_WORK
```

而不是：

> 自己从 project-todo 挑下一个任务开始做。

只有 Codex 在得到用户明确“规划下一任务”的指令后，才可以创建下一正式任务。

---

# 15. 加一个 stale-message 防线

至少检查：

- task id；
- attempt；
- current task state；
- referenced artifact 是否存在；
- 是否已有更新 verdict；
- 是否有 superseding mailbox message。

如果：

```text
mailbox says REVIEW_REQUEST
but task is already ACCEPTED
```

则：

```text
STALE
→ 不执行
```

---

# 16. 建议用户以后使用的四句话

整理完成后，请确保这四种话都能自然工作：

### Codex

```text
查看你的 mailbox，然后开始你的工作。
```

### Claude

```text
查看你的 mailbox，然后开始你的工作。
```

### Copilot

```text
查看你的 mailbox，然后开始你的工作。
```

### 继续同一个任务

```text
查看你的 mailbox，然后继续你的工作。
```

Agent 应根据角色和正式 artifact 自动判断具体动作。

---

# 17. 修改范围

只允许最低必要修改。

优先：

```text
mailbox README / mailbox protocol
AGENTS.md 中一个简短 pointer
必要的 role-specific executor/reviewer instructions
```

不要重新复制完整 workflow。

不要把 mailbox rule 写到五六个文件里。

目标：

> **one canonical mailbox rule + lightweight pointers**

---

# 18. 验收测试

完成后请做至少以下 dry-run，不启动真实科研：

## Case A — Claude TASK_READY

模拟：

```text
TASK_READY → valid TASK
```

确认 Claude 能明确：

- 应读哪个 TASK；
- 可以做什么；
- 什么情况停止。

## Case B — Copilot REVIEW_REQUEST

确认：

- 找到 TASK + RESULT；
- 不把 mailbox 当 evidence；
- review 后写 REVIEW。

## Case C — Codex AUDIT_READY

确认：

- 审 TASK / RESULT / REVIEW / raw；
- verdict 不写在 mailbox 里作为唯一事实。

## Case D — stale message

模拟：

```text
mailbox says TASK_READY
but task already CLOSED
```

应：

```text
STALE / NO_PENDING_WORK
```

不得重新执行。

## Case E — empty mailbox

应：

```text
NO_PENDING_WORK
```

不得自动从 todo 启动下一项科研。

这些 dry-run 只检查规则，不运行 JoSIM。

---

# 19. 完成后报告

请告诉用户：

1. 修改了哪些文件；
2. canonical mailbox rule 最终在哪里；
3. AGENTS 如何指向它；
4. Claude / Copilot / Codex 各自 mailbox 行为；
5. stale / empty mailbox 如何处理；
6. 是否存在重复 authority；
7. dry-run 结果；
8. `git diff --stat`；
9. `git status --short`。

并明确确认：

```text
没有启动 M7
没有修改科研结论
没有实现 Batch
没有实现自动 routing
没有让 mailbox 成为 authority
```

完成后停止。

下一步用户会让 Codex 正式签发 M7，然后开始实际科研。
