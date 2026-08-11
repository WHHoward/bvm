---
title: WORKFLOW-lite 的 Codex 审阅意见
document_type: discussion_note
status: FOR_USER_REVIEW
date: 2026-08-11
related:
  - WORKFLOW-lite.md
  - research/WORKFLOW.md
  - AGENTS.md
---

# WORKFLOW-lite 的 Codex 审阅意见

> 本文是对 `WORKFLOW-lite.md` 的讨论记录，不修改现行 `josim-handoff/v1` 协议，不授予任何任务执行或验收权限。

## 结论

`WORKFLOW-lite` 的核心方向值得采用：普通工程任务保持轻量，关键科学任务升级审查；日常代码演进依赖 Git；SHA-256 留给需要长期冻结的科研证据；Copilot 提供证据层的第二双眼睛，Codex 保留决策层复核与最终处置。

但该草案尚不应标记为可直接替代现行协议的 `FINAL` 方案。建议先把它作为默认协作界面试点，并把 `josim-handoff/v1` 保留为 `CRITICAL` 或 Formal Freeze 任务的证据冻结后端。M5/M6、指标冻结、物理 Gate 和论文级证据不能因流程轻量化而失去可追溯性。

## 建议保留的设计

1. 仅使用 `NORMAL` 和 `CRITICAL` 两个风险等级；
2. `claim ceiling`、allowed paths、acceptance criteria 和 stop conditions 始终必填；
3. Copilot 是 evidence-level peer reviewer，不是最终物理裁决者；
4. 对 `CRITICAL` 任务，Codex 必须亲自回到 raw evidence 审查单位、窗口、控制、数值和物理解释；
5. Git 用于日常代码历史，SHA-256 不被误写为身份或命令历史证明。

## 必须修改后再试点的事项

### 1. 明确与现行协议的迁移关系

当前 `AGENTS.md` 仍要求 Codex→Claude 的委派使用 `research/WORKFLOW.md` 与 `josim-handoff`。因此 Lite 不能仅靠新文件的 frontmatter 立即取代它。

建议明确：

```text
WORKFLOW-lite = NORMAL 任务的默认协作界面
josim-handoff/v1 = CRITICAL / Formal Freeze 的不可变证据冻结后端
```

在试点成功、并完成 `AGENTS.md`、`research/WORKFLOW.md` 与相关 skills 的同步前，现行协议仍是权威。

### 2. 保留四维结果语义，但不必保留四份文件

`DONE / BLOCKED` 不足以区分：执行已完成、证据无效、物理结果 `FAIL`、证据 `INCONCLUSIVE`。这在科研任务中会把“电路未通过”与“数据不可用”混为一谈。

可以维持三文件的轻量形态，但要求 `RESULT.md` 分别记录：

```text
execution_status: COMPLETED / BLOCKED / DEVIATED
artifact_status: VALID / INVALID / NOT_AUDITED
proposed_physical_verdict: PASS / FAIL / INCONCLUSIVE / NOT_APPLICABLE
```

Codex 的最终处置仍为 `ACCEPT / REWORK / BLOCKED`。这保留了科学含义，而没有恢复重型多文件状态机。

### 3. 用轻量 Preflight 替代 ACK，而不是完全取消预检

“开始执行即视为接受 TASK”会失去 M4-002 曾捕获的关键问题：执行 worktree 的 HEAD 与合同 baseline 不匹配。

建议在 Claude 首次写入前，先在 `RESULT.md` 固定一个简短 `Preflight`：

```text
observed Git HEAD
branch / worktree
git status --porcelain=v1 --untracked-files=all
TASK 已读与风险等级
是否满足 baseline、scope 和 stop conditions
```

这不是重型 ACK，但能保留执行前可追溯性。

### 4. 不覆盖 RESULT/REVIEW：保留最小 attempt 历史

草案允许在 REWORK 后更新既有 RESULT/REVIEW；这会混淆第一次交付、复核发现的问题和修复后的证据。

建议使用很小的 append-only 结构：

```text
research/tasks/<task-id>/
├── TASK.md
└── attempts/
    ├── A01/
    │   ├── RESULT.md
    │   └── REVIEW.md
    └── A02/
        ├── RESULT.md
        └── REVIEW.md
```

不要求 request/receipt/verdict 多层 SHA 链，但禁止覆盖历史交付与审查。

### 5. Critical 输入证据也应冻结

SHA-256 不应只用于“最终论文”或最终 Gate。只要 Critical 任务依据 raw CSV、网表或派生数据支持关键判断，就应记录所用输入/输出的路径与 SHA-256。否则后续无法确定审查的究竟是哪一版数据。

普通代码任务仍可只使用 Git。

### 6. 风险升级权应属于 Codex

Copilot 可在 REVIEW 中写 `recommended_risk: CRITICAL`，但不能自行将任务风险等级改写为 CRITICAL 或 NORMAL。发现单位、窗口、物理含义、控制或原始数据异常时，应写 `REWORK` 或 `BLOCKED`，由 Codex 决定是否升级、重签或进入 Formal Freeze。

### 7. 先验证 Copilot 约束在真实环境中有效

`.github/agents/reviewer.agent.md` 的角色边界设计良好，但提示词不是强制访问控制。正式依赖前应在实际 VS Code/Copilot 环境中验证：

1. agent 配置是否被识别；
2. 是否确实能限制写入到当前任务的 `REVIEW.md`；
3. `.github/skills/` 中列出的 skills 是否真实存在、可发现且内容正确；
4. 是否能复跑只读检查而不污染执行 worktree。

验证失败时，Reviewer 应退化为只读意见，不得被视作协议层审查。

## Codex 深度审查的不可降级范围

即使 Copilot `REVIEW=PASS`，下列情形仍要求 Codex 直接阅读 raw evidence，而不能只读摘要：

- physical Gate、SFQ/JTL/相位传播结论；
- metric 定义或冻结；
- 路线切换和论文级主张；
- 单位、端点、方向、窗口或时间步收敛争议；
- raw evidence 与结论冲突；
- `FAIL`、`INCONCLUSIVE`、`INVALID` 或权限/冻结输入漂移。

## 现有校验器的相关缺口

M4-003 的经验显示：任务审计接受后，正常更新 `docs/HANDOVER.md` 或 `memory/project-todo.md` 会改变旧任务的冻结读取文件；现有 `verify-task` 会把这种后续状态更新误报为旧任务失效。

无论采用 Lite 或保留 v1，都应区分：

```text
执行时快照验证：判断 Claude 是否在正确输入上执行
当前工作树漂移检查：提示审计后仓库是否继续变化
```

两者不能共用一个“历史任务失败”的结论。

## 建议试点路径

1. 不立即替代现行协议；
2. 先选 M12 作为 NORMAL 试点：它与 Phase −1 计量语义独立，且不会形成物理 Gate；
3. 运行 2–3 个任务，记录实际摩擦、遗漏与 Reviewer 的有效发现；
4. 之后才决定是否让 M5 的纯实现部分采用 Lite；M5 的科学解释和 M6 仍按 Critical/正式冻结处理；
5. 试点有效后，再统一修改 `AGENTS.md`、`research/WORKFLOW.md`、`research/CLAUDE_EXECUTOR.md` 和相关 skills，避免双重权威。

## 最小底线

```text
任务目标明确
写入范围明确
验收条件明确
停止条件明确
claim ceiling 明确
执行前 baseline 可核对
Reviewer 有最小独立证据来源
Critical 科学任务由 Codex 从 raw evidence 深度复核
用户保留路线、metric freeze、physical Gate 与论文主张的最终决定权
```
