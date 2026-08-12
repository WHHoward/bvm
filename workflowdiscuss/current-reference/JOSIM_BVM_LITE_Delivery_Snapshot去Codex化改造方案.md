# JoSIM × BVM：LITE Delivery Snapshot 去 Codex 化的小型流程改造方案

> **用途**：交给 Claude Code，在 **当前 M7-LITE-001 完成并 ACCEPT 后**实施。  
> **目标**：进一步减少不必要的 Codex 调用，让 Codex 只负责真正需要高能力推理的“任务定义 + 最终科学审计”，把机械性的 delivery snapshot 创建移交给 Claude 或确定性脚本。  
> **重要边界**：本方案不是新的大规模 workflow redesign；不改 Batch、不改 FROZEN Scientific Gate、不改变当前 M7 已签发 TASK。

---

# 1. 为什么要改

当前 Scientific Implementation 的典型链条是：

```text
Codex 签 TASK
↓
Claude 执行
↓
Codex 创建 delivery snapshot
↓
Copilot review
↓
Claude 修复（如有）
↓
Codex final audit
```

其中“创建 delivery snapshot”本质上属于：

- commit；
- hash；
- snapshot binding；
- path verification；
- metadata recording。

这类工作是机械性的，不需要 Codex 的高水平科研推理。

因此当前流程多了一次 `Claude → Codex → Copilot` 的中间接力，增加了 Codex 调用次数、上下文重建、用户等待和额度消耗，但没有明显增加科学严谨性。

---

# 2. 核心决策

从本改造生效后：

## 对 LITE Scientific Implementation

例如：

- M7 类 calibration implementation；
- Source Characterization implementation；
- Receiver Characterization implementation；
- bounded exploratory / calibration coding task；

delivery snapshot 改为由：

```text
Claude
或
deterministic snapshot script
```

创建。

Codex 不再负责中间 snapshot creation。

## Codex 继续负责

```text
TASK issuance
scientific scope
acceptance criteria
stop conditions
claim ceiling
final audit
scientific conflict resolution
route / metric / Gate decisions
```

也就是说：

> **Codex 一头一尾，中间不驻场。**

---

# 3. 新的 LITE Scientific Implementation 流程

改造后：

```text
User
↓
Codex
定义正式 TASK
↓
mailbox TASK_READY
↓
Claude
执行 TASK
↓
Claude
写 RESULT
↓
Claude / deterministic script
创建 immutable delivery snapshot
↓
mailbox REVIEW_REQUEST
↓
Copilot
review 指定 snapshot
↓
若有 Major
    ↓
Claude 修复
    ↓
创建新 attempt / 新 snapshot
    ↓
Copilot 再审
↓
无 Major
↓
mailbox AUDIT_READY
↓
Codex
final audit
↓
ACCEPT / REWORK / BLOCKED
```

这样 Codex 每个普通 Scientific Implementation 理想上只有：

```text
1 次：任务签发
1 次：最终审计
```

---

# 4. 当前 M7-LITE-001 不要中途修改

这是必须明确的迁移边界。

当前已经签发的：

```text
M7-LITE-001
```

TASK 明确规定：

```text
Delivery snapshot owner: CODEX
```

因此：

> **M7-LITE-001 必须按当前 TASK 执行到底。**

不要为了减少一次 Codex 调用而中途改变 owner，否则会造成 task semantics drift。

本方案只在：

```text
M7-LITE-001 ACCEPT
```

之后生效。

---

# 5. 哪些任务适用

适用：

```text
NORMAL + LITE
CRITICAL + LITE
```

且任务属于：

```text
Scientific Implementation
```

例如：

- implementation；
- calibration code；
- bounded characterization；
- deterministic regression；
- ordinary experiment implementation。

---

# 6. 哪些任务暂时不适用

以下暂时保留现有严格机制：

```text
CRITICAL + FROZEN
Scientific Gate
```

例如：

- M8 decisive convergence；
- M9 METRIC_SPEC freeze；
- M11 baseline；
- INTERFACE_GATE freeze；
- route verdict；
- final margin；
- paper-critical confirmatory evidence。

这些任务仍然可以要求：

```text
Codex-controlled task contract
FROZEN evidence
independent review
Codex final audit
User adoption where required
```

本次改造不要碰它们。

---

# 7. Delivery Snapshot 必须具备的性质

虽然由 Claude 创建，但 snapshot 不能变成“Claude 自己说自己交付了”。

## 7.1 Immutable

snapshot 一旦作为 review target 发布：

```text
不可修改
```

如果需要修复：

```text
new attempt
或
new delivery snapshot
```

## 7.2 明确绑定 attempt

至少记录：

```text
task_id
attempt_id
snapshot_commit
base_commit
RESULT path
changed paths
```

## 7.3 REVIEW 必须绑定具体 snapshot

Copilot REVIEW 中必须明确：

```text
reviewed_attempt:
reviewed_snapshot:
```

不能只写：

```text
reviewed latest
```

## 7.4 不允许 executor 在 review 后静默修改同一 snapshot

如果 Copilot 提出 Major：

```text
A01 snapshot
↓
REVIEW
↓
Claude repair
↓
A02 / new snapshot
```

不能直接修改 A01。

---

# 8. 推荐的 snapshot ownership

推荐：

```text
snapshot_owner: EXECUTOR
snapshot_creation: DETERMINISTIC
```

Claude 负责触发。

实际 snapshot creation 尽可能由确定性命令完成，例如：

```text
git status --short
git diff --stat
git diff
git rev-parse HEAD
hash relevant artifacts
commit allowed delivery files
record snapshot commit
```

如果仓库已有 snapshot helper：

> 优先复用。

不要为了这次改造再设计一套大型 snapshot framework。

---

# 9. Claude 的职责边界

Claude 可以：

```text
执行 TASK
写 RESULT
创建 delivery snapshot
发送 REVIEW_REQUEST
```

Claude 不可以：

```text
自行 ACCEPT
自行更新 scientific Gate
自行把 LITE 升级为 FROZEN
自行修改 task semantics
自行扩大 scope
```

snapshot ownership 不等于 scientific authority。

---

# 10. Copilot 的职责不变

Copilot 只 review：

```text
明确指定的 immutable snapshot
```

检查：

- diff；
- tests；
- evidence；
- oracle；
- unit；
- sign；
- window；
- stale artifact；
- provenance；
- overclaim。

Copilot 不负责最终 ACCEPT。

---

# 11. Codex 的职责进一步收敛

改造后 Codex 只在以下节点出现：

## 开头

定义 TASK，包括：

- objective；
- scope；
- acceptance；
- stop condition；
- claim ceiling。

## 中间只有异常才叫 Codex

例如：

- scientific semantics 需要改；
- scope 需要扩大；
- Claude / Copilot 发生实质冲突；
- 同一 root cause 连续失败；
- evidence 出现无法解释的矛盾。

## 结尾

```text
final audit
```

Codex 独立检查：

- TASK；
- RESULT；
- REVIEW；
- raw evidence；
- snapshot；
- acceptance criteria。

输出：

```text
ACCEPT
REWORK
BLOCKED
```

---

# 12. Mailbox 接力对应修改

改造后建议：

```text
TASK_READY
Codex → Claude

REVIEW_REQUEST
Claude → Copilot
必须包含：
- task id
- attempt id
- snapshot commit
- RESULT path

REWORK_REQUEST
Copilot / Codex → Claude

AUDIT_READY
Copilot → Codex
必须包含：
- reviewed snapshot
- REVIEW path

CLOSED / REWORK
Codex → Claude/User
```

不要新增更多 message type。

---

# 13. 需要修改的文件

Claude Code 应先检查 cleaned workflow 当前结构，再决定最低必要修改。

优先可能包括：

```text
research/WORKFLOW-lite.md
research/mailbox/README.md
LITE TASK / RESULT / REVIEW templates
必要的 executor/reviewer role instructions
```

`AGENTS.md` 最多增加一条短 pointer。

不要在多个文件复制完整规则。

---

# 14. TASK 模板需要调整

未来 LITE Scientific Implementation 的 TASK 中：

旧：

```text
Delivery snapshot owner: CODEX
```

改为：

```text
Delivery snapshot owner: EXECUTOR
```

或者：

```text
Delivery snapshot owner: CLAUDE
```

如果希望模型无关，优先：

```text
EXECUTOR
```

---

# 15. REVIEW_REQUEST 最小字段

建议确保 mailbox 或 RESULT 中能明确提供：

```yaml
task_id:
attempt_id:
delivery_snapshot:
result_path:
review_mode:
```

不需要复杂 schema。

目标只是：

> reviewer 永远知道自己审的是哪一个 immutable delivery。

---

# 16. Pilot / 验收方式

不要马上全仓库推广。

在 **M7 ACCEPT 之后**，选择下一项适合的：

```text
CRITICAL + LITE Scientific Implementation
```

作为一次小型实际验证。

验收条件：

1. Codex 只签 TASK；
2. Claude 完成执行；
3. Claude 成功创建 stable snapshot；
4. Copilot 能准确 review 指定 snapshot；
5. Claude 修复时不会覆盖旧 snapshot；
6. Codex 能直接审 stable evidence；
7. 没有 provenance ambiguity；
8. 没有因为 snapshot ownership 转移降低科学审计质量；
9. 比旧流程少一次纯机械 Codex 调用。

如果满足：

> 将 `EXECUTOR-owned snapshot` 作为 LITE Scientific Implementation 默认规则。

---

# 17. 不要顺手实现的东西

本轮明确禁止扩大到：

```text
完整 Batch P0
verify-batch
Decision Cache
complexity scoring
automatic routing
complex Audit Packet
automatic Scientific ADR
FROZEN v1.1
大型 workflow redesign
```

这些继续保持 backlog。

---

# 18. Claude Code 的实施顺序

请按以下顺序：

```text
1. 等 M7-LITE-001 ACCEPT
2. 读取当前 cleaned workflow
3. 找到 delivery snapshot ownership 的 canonical 定义
4. 最小修改 LITE Scientific Implementation 规则
5. 更新相应模板
6. 更新 mailbox REVIEW_REQUEST 指引
7. 保持 FROZEN Scientific Gate 不变
8. 跑现有 workflow/mailbox tests
9. 做一次 dry-run
10. 提交一个独立 workflow tweak commit
```

---

# 19. Dry-run

至少模拟：

```text
Codex TASK_READY
↓
Claude fake RESULT
↓
Claude create fake delivery snapshot
↓
REVIEW_REQUEST(snapshot=X)
↓
Copilot REVIEW(snapshot=X)
↓
AUDIT_READY
↓
Codex final audit
```

确认：

- snapshot 唯一；
- review 绑定正确；
- repair 创建新 snapshot；
- mailbox 不成为 authority；
- Codex 不需要介入 snapshot creation。

不运行真实 JoSIM 科研任务。

---

# 20. 完成后报告

Claude Code 完成后告诉用户：

1. 修改了哪些文件；
2. snapshot ownership 现在的 canonical rule；
3. 哪些任务使用 EXECUTOR-owned snapshot；
4. 哪些任务仍保留严格 FROZEN/Scientific Gate 流程；
5. REVIEW 如何绑定 snapshot；
6. repair 如何产生新 snapshot；
7. workflow/mailbox tests 结果；
8. dry-run 结果；
9. `git diff --stat`；
10. `git status --short`。

并明确确认：

```text
没有修改 M7-LITE-001 已签发 TASK
没有改变 M7 科学结果
没有修改 FROZEN Scientific Gate
没有实施 Batch
没有引入新的大型 workflow
```

---

# 21. 最终目标

改造后：

## 普通 Scientific Implementation

```text
Codex
  一次 TASK
↓
Claude
  执行 + snapshot
↓
Copilot
  review
↓
Claude
  repair（如需要）
↓
Codex
  一次 final audit
```

## Scientific Gate

继续：

```text
Codex preregistration
↓
Claude FROZEN execution
↓
independent review
↓
Codex deep audit
↓
User adoption
```

核心原则：

> **Codex 用在“判断错误代价高”的地方，不用在“机械操作可以确定完成”的地方。**

这次改造的唯一目的就是：

> **减少一次无科学推理价值的中间 Codex 调用，同时保持 immutable snapshot、独立 review 和 final audit。**
