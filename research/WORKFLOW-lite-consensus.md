---
title: WORKFLOW-lite 2.0 三方协作共识（最终统一版）
document_type: consensus
status: AGREED
date: 2026-08-11
authority: 用户最终拍板；三方（Codex/Claude/Copilot）按此理解和执行
protocol_ref: research/WORKFLOW-lite.md（Pilot 协议本体）
---

# WORKFLOW-lite 2.0 三方协作共识

> **Historical / Decision Record（2026-08-11 共识）— 非执行权威。**
> 本文件是三方共识的历史决策记录，不单独构成执行规则；协议正文与唯一执行界面为 `research/WORKFLOW.md`（FROZEN 后端）与 `research/WORKFLOW-lite.md`（轻量 Pilot 接口）。判断执行要求时以这两个文件为准。

> 用户于 2026-08-11 统一最终协作方式。本文件是三方共识的正式记录；协议细节以 `research/WORKFLOW-lite.md` 为准。

## 角色分工

| 角色 | 职责 | 不做 |
|---|---|---|
| Codex | Planner + Final Auditor：TASK、风险等级、Evidence Mode、最终审计、ACCEPT/REWORK/BLOCKED | — |
| Claude | Executor：Preflight、实现、测试、证据产出、RESULT.md | 不负责最终验收 |
| Copilot | Evidence Reviewer / Peer Reviewer：reviewer Agent + Review Skills，独立证据复核（隐藏错误/测试盲区/数值/证据链/overclaim） | 不做最终科学裁决 |
| User | Final Scientific Authority：路线、metric freeze、physical Gate、paper-level claim | — |

## 正式工作流（LITE）

```text
Codex → TASK.md → Claude Preflight+Execute → attempts/Axx/RESULT.md
  → Delivery Snapshot Commit → Copilot Reviewer → attempts/Axx/REVIEW.md
  → Codex Final Audit → ACCEPT / REWORK / BLOCKED
```

REWORK → 新建 A02/A03，不覆盖旧 RESULT/REVIEW。

## 两个独立维度

- **Risk**（NORMAL/CRITICAL）= 审多深
- **Evidence Mode**（LITE/FROZEN）= 证据冻结多严格
- NORMAL+LITE 普通工程；CRITICAL+LITE 关键计量/数值/window/unit/threshold；CRITICAL+FROZEN final Gate/metric freeze/论文核心数据/路线决策
- FROZEN 复用 `josim-handoff/v1`，不另建重型协议

## FROZEN 不事后补票

预期用于 final Gate / metric freeze / paper-critical 的结果，必须**在产生关键证据前**声明 CRITICAL+FROZEN。LITE 结果只能作 exploration 或下一 FROZEN run 的设计依据。LITE 中需冻结 → 保留原 attempt → Codex 新建 FROZEN attempt / v1 contract → 重新产生正式证据。

## TASK 与 Git

- LITE 用 Git 作轻量完整性机制
- TASK 明确：Task revision commit / Execution baseline commit / Delivery snapshot owner（默认 CODEX）
- 默认 Observed HEAD == Execution baseline == Task revision；不同必须 TASK 明示原因
- TASK.md 不允许 Claude/Reviewer 修改；修订由 Codex 显式 revision + 重新 commit

## Preflight

- 不写单独 ACK 文件，但执行前必须 Preflight
- 固定顺序：创建 Axx/RESULT.md → 先写 Preflight → PASS → 才允许修改实现/运行正式实验
- 至少检查：Task revision / Execution baseline / Observed HEAD / branch-worktree / git status / allowed paths / Risk / Evidence Mode / claim ceiling / ambiguity
- Preflight 写后不得回填改写；纠正只能追加 correction note

## RESULT 科学语义

Claude 区分：`execution_status` / `executor_artifact_assessment` / `proposed_physical_verdict`。

```text
execution completed ≠ artifact valid ≠ physical PASS
≠ Reviewer PASS ≠ Codex ACCEPT ≠ User scientific adoption
```

Claude 的 artifact assessment 是 provisional。

## Delivery Snapshot

- Reviewer/Codex 审同一稳定 snapshot commit，不审变化 worktree
- 默认 owner = Codex；仅 TASK 明确 `CLAUDE_EXPLICITLY_AUTHORIZED` 时 Claude 可创建受限 delivery commit（不 amend/rebase、不夹带无关改动）

## Reviewer

- 核心原则：**Try to falsify the executor's strongest bounded claim**
- 检查：no-op/constant-output、wrong branch、weak oracle、boundary、stale artifact、hidden state、numerical、unit/sign/window、provenance、reproducibility、activity vs event、local vs downstream、phase wrap、Δφ/(2π) 与 voltage-time-area、zero-input control、timestep/solver、claim ceiling
- Reviewer PASS = evidence-level PASS，非 physical PASS 或 Codex ACCEPT

## Skills 单一规范源

- `.agents/skills/` = canonical；`.github/skills/` = Copilot wrapper
- superconducting-simulation-review 不复制物理规则，复用 `josim-evidence-audit` + references
- 初始仅 3 个核心 skill（adversarial / numerical / superconducting）；其余 Pilot 验证后再加

## REVIEW 必含两字段

```text
Recommended risk: NORMAL | CRITICAL
Recommended evidence mode: LITE | FROZEN
```

Reviewer 可建议升级，不修改 TASK；Codex 决定，User 可强制。拿不准 → Risk 倾向 CRITICAL、Evidence Mode 倾向 FROZEN。

## 消息层 vs 事实层

```text
mailbox = 通知层（"有人给你发消息，让你去看东西"）
TASK.md / RESULT.md / REVIEW.md / Git snapshot = 事实层（真正应该相信和审计的东西）
josim-handoff/v1 = 正式科研证据冻结层（FROZEN）
```

典型用法：Codex→Claude "M12 TASK 已签发，正式要求见 TASK.md"；Claude→Reviewer "M12/A01 完成，snapshot=abc1234，正式结果见 RESULT.md"；Reviewer→Codex "review 完成，findings 见 REVIEW.md"。

## todo / HANDOVER

仅 Codex ACCEPT 后可更新为完成；Claude 不自证完成；Reviewer PASS 不自动推进状态。

## Pilot 顺序

- Pilot 0：只验证 Reviewer Agent/Skills/read-only 行为，不运行真实科研；未通过 → Reviewer 仅 advisory
- Pilot 1：M12（CRITICAL+LITE，因新机制首跑而非物理风险）
- Pilot 2：M5 measurement implementation（CRITICAL+LITE）
- Pilot 3：M5 物理解释 / M6（CRITICAL+FROZEN）

## 当前状态

```text
Design: FINAL
Implementation: READY
Protocol Deployment: PILOT
```

Pilot 验证完成前不自动替代 AGENTS.md / research/WORKFLOW.md。

## 五句原则

1. 轻量默认，不等于取消机械防线。
2. 强 Reviewer，不等于第二个 Codex。
3. Git 负责 LITE 轻量可追溯性；SHA-256 负责关键科研证据冻结。
4. mailbox 负责"通知"；TASK/RESULT/REVIEW/Git 负责"事实"。
5. 复杂度花在发现真实错误上，而不是花在日常手续上。
