---
title: WORKFLOW-lite 2.0-rc1 的 Codex 最终评审意见
document_type: discussion_note
status: FOR_USER_REVIEW
date: 2026-08-11
related:
  - workflowdiscuss/WORKFLOW-lite-2.0-rc1.md
  - discussion/workflow-lite-codex-review.md
  - research/WORKFLOW.md
  - AGENTS.md
---

# WORKFLOW-lite 2.0-rc1 的 Codex 最终评审意见

> 本文是讨论记录，不修改现行协议，也不授予任务执行、验收或路线决策权限。

## 最终结论

`WORKFLOW-lite 2.0-rc1` 已解决上一版的主要设计缺口：加入执行前 Preflight，保留 attempt 历史，恢复执行/产物/物理判断的分离，规定 Critical 输入输出的哈希记录，并把 `josim-handoff/v1` 定位为 Formal Freeze 后端。

结论是：**可作为受控试点方案，但尚不能自动取代现行 `AGENTS.md` 与 `research/WORKFLOW.md`。** 在完成下列六项语义修订、并经过试点验证前，它应保持 `PILOT`。

## 已认可的核心设计

```text
风险等级（NORMAL / CRITICAL）
    ×
证据模式（LITE / FROZEN）
```

这是适合本项目的正确抽象：风险等级决定 Codex/Reviewer 的审查深度；证据模式决定是否需要不可变任务合同、哈希链和正式冻结。普通工程任务不必承担全部手续；关键科学证据不能因流程轻量化而失去可追溯性。

以下设计应保留：

1. `claim ceiling`、allowed paths、acceptance criteria 和 stop conditions 始终必填；
2. Copilot 是 evidence-level peer reviewer，不是第二个 Codex 或最终物理裁决者；
3. Critical 任务中 Codex 必须直接审查 raw evidence、单位、窗口、控制、数值与解释；
4. Git 用于日常代码历史，SHA-256 用于关键科研输入/输出的版本识别；
5. RESULT/REVIEW 按 attempt 保留，不覆盖历史交付；
6. 用户始终保留路线、metric freeze、physical Gate 和论文主张的最终决定权。

## 试点前必须修订的六项

### 1. 解决首个 Pilot 的风险等级矛盾

第 20 节把“新协作机制首次试点”列为自动 `CRITICAL`，第 33 节却将 M12 标为 `NORMAL + LITE`。二者不能同时成立。

建议：M12 作为首个真实 Lite 试点时使用：

```text
Risk: CRITICAL
Evidence mode: LITE
Claim ceiling: plotting/unit implementation verified only; no physical Gate.
```

原因不是把 M12 的物理结论升级，而是新流程、Copilot Agent 和 skill 包首次进入真实任务本身具有机制风险。流程证明可靠后，后续普通工程任务再使用 `NORMAL + LITE`。

### 2. TASK Git 冻结必须区分两个提交

仅写 `Baseline` 仍有歧义：TASK 本身被提交后，Claude 的 `Observed HEAD` 应等于任务提交还是其父提交？

建议 TASK 明确记录：

```text
Task revision commit: 包含不可修改 TASK.md 的提交
Execution baseline commit: Claude Preflight 必须检出的提交
```

默认规则可设为：

```text
Observed HEAD == Execution baseline commit == Task revision commit
```

若两者确需不同，TASK 必须解释原因并指定允许的差异。

### 3. Preflight 必须在执行前写入且不可回填

Preflight 若仅作为最终 RESULT 的一个可编辑段落，无法证明它在修改实现前已经完成。

建议规定：

```text
Claude 首先创建 attempts/A01/RESULT.md，写入完整 Preflight；
Preflight 通过后才能修改实现或运行实验；
该段落之后不得回写，后续内容只追加。
```

这保留 M4-002 所体现的 baseline/worktree 防线，而不恢复独立 ACK 文件。

### 4. 明确 Git 交付快照的责任人

Lite 以 Git 作为日常追溯机制，就必须明确 Copilot 和 Codex 审查哪一个不可变代码快照。若 Claude 的代码、RESULT 和输出都只是可继续变化的未提交工作树，审查对象并不稳定。

建议在 RESULT 完成后设一个轻量交付点：

```text
Claude 完成 RESULT
→ 由明确授权的责任人创建仅含 allowed paths 的 task snapshot commit
→ Copilot 审查该 commit
→ Codex 最终审查该 commit
```

协议必须明确提交者：允许 Claude 做一次不重写的任务提交，或由 Codex/用户执行快照提交。若不允许 Claude commit，不能把这项责任留为空白。

### 5. executor 的 artifact 判断必须标为暂定

Claude 可以报告“文件可读、路径一致、未发现明显断裂”，但不能自行赋予最终 artifact validity。建议把 RESULT 中的字段写成：

```text
executor_artifact_assessment:
  VALID | INVALID | NOT_AUDITED
```

或明确 `artifact_status` 在 RESULT 中仅为 provisional。最终对证据可用性的接受仍属于 Codex 的处置。

### 6. FROZEN 必须在执行前预注册，不能事后补票

对于 final Gate、metric freeze、论文核心数字或路线决定，不能先在 LITE 下得到好结果，再追溯称其为冻结证据。

建议写死：

```text
若任务预期用途是 final Gate、metric freeze、论文核心数字或路线决定，
必须在执行前指定 CRITICAL + FROZEN。
已完成的 LITE 运行只能作为探索或下一次 FROZEN run 的设计依据，
不得追溯升级为其原始冻结证据。
```

## 还需明确的落地规则

### Copilot 约束的验证

`.github/agents/reviewer.agent.md` 的提示边界不是文件系统 ACL。正式依赖 Reviewer 前，应在真实 VS Code/Copilot 环境完成 pilot 验证：agent 是否被识别、skills 是否可发现、是否只写 attempt-local `REVIEW.md`、复跑命令是否污染 worktree、是否发生实现修改或范围扩大。

约束未被验证时，Copilot 只能被视为只读建议者，不能成为协议层的正式 review。

### 单一 skill 规范源

若 `.github/skills/` 是 Copilot 所需镜像，须写明 canonical source 与同步/差异检查方式。仓库当前已有 `.agents/skills/`；两个目录中的同名 skill 不得长期独立演化并产生语义漂移。

### 与现行权威文件的关系

当前 `AGENTS.md` 仍要求 Codex→Claude 委派使用 `research/WORKFLOW.md` 与 `josim-handoff`。因此 pilot 期间 Lite 应表述为：

```text
经用户/Codex 明确指定的试点模式
```

而不能仅凭 RC 文件自动成为所有新委派的默认规则。试点成功后，再一次性同步 `AGENTS.md`、`research/WORKFLOW.md`、`research/CLAUDE_EXECUTOR.md` 及相关 skills，避免双重权威。

## 建议试点顺序

1. **M12**：`CRITICAL + LITE`，验证 TASK freeze、Preflight、attempt、Reviewer、skills、task snapshot 与 Codex 深度审查；不产生物理 Gate；
2. **M5 的实现部分**：`CRITICAL + LITE`，验证数值审查、事件窗口、零输入控制与 raw evidence；
3. **M5 物理解释或 M6**：`CRITICAL + FROZEN`，验证 Lite 到 v1 Formal Freeze 的衔接；
4. 记录 Reviewer 是否发现问题、误报率、Preflight 是否捕获问题、实际流程成本与审查质量；完成 2–3 个任务后再决定是否升为 FINAL。

## 最终采纳建议

在上述修订完成前：

```text
WORKFLOW-lite 2.0-rc1 = 可试点的协作设计
research/WORKFLOW.md + josim-handoff/v1 = 当前权威协议
```

在修订完成并通过试点后，建议采用：

```text
WORKFLOW-lite 2.0 = 默认协作界面
josim-handoff/v1 = CRITICAL + FROZEN 的正式证据冻结后端
```

这样能将流程复杂度集中在真正的科研风险上，同时保留对单位、事件语义、原始数据、时间窗、收敛和论文主张所需的严谨性。
