# Copilot 对 WORKFLOW-lite 2.0 Batch Acceleration 提案的审阅意见

> 审阅人：Copilot（Reviewer 角色）
> 审阅对象：`workflowdiscuss/WORKFLOW-lite-2.0-batch-acceleration-proposal.md`
> 日期：2026-08-11
> 状态：三方审阅意见之一；不修改协议、不授权任务

---

## 1. 总体判断：方向对，支持核心架构，但有三处必须加固

提案核心主张——**"Codex 管理批次边界与科学判决，而不是每个工作步骤"**——与 Copilot 在 M12（PASS）和 M5（A01 REWORK → A02 PASS）的实测经验一致，且没有削弱任何科学 Gate（§21 底线保留得很好）。

特别认同：
- **PRE-REVIEW 与 FORMAL REVIEW 严格分离**（§5）：M5 A01 的价值正是在**冻结 snapshot** 上以"新鲜对抗"发现的 activity 窗口缺口；
- **M8 保持 CRITICAL 但不单独占 Codex**（§10）："通过合并审计省 Codex，而不是通过降低科学风险省 Codex"；
- **Escalation Triggers（§8）12 条足够全面**，Q5 无需增删。

---

## 2. 必须加固的三处（核心意见）

### R1. PRE-REVIEW 的锚定效应 → FORMAL REVIEW 必须"新鲜对抗"

若内部循环中 Copilot 反复预审、Claude 按意见修复，到 FORMAL REVIEW 时 Reviewer 已多次接触该实现，**看待 snapshot 的方式会被自己的预审结论锚定**。M5 A01 能抓到缺口，恰恰因为那是第一次看该快照。

**建议**：协议增量写明——*FORMAL REVIEW 必须按 snapshot 重新独立构造证伪假设，不得直接复用 PRE-REVIEW 结论；PRE-REVIEW 曾发现的缺陷类型即使已修复也应重新检查。* 即：**PRE-REVIEW 抓 bug，FORMAL REVIEW 抓"修 bug 时引入的新错"。**

### R2. 内部闭环必须留痕，否则 batch audit 无从核验

若内部循环零痕迹，Codex 审计批次时无法确认"内部闭环是否真实"，只能凭信任——架空"每层最小独立证据"原则。

**建议**：每个 subtask 内部闭环时留**最小 ledger**（非重型协议文件）：

```text
subtask: M7
state: SUBTASK_READY
pre_review_findings: [发现X→已修, 发现Y→已修]
final_changes_since_last_ready: [...]
evidence_hashes: [...]
claim_ceiling: OK
escalation_triggered: no
```

### R3. SUBTASK_READY 必须显式携带四维语义且不可升级

SUBTASK_READY 是"工作步骤可推进"，**不是**"产物有效 + 物理成立"。多个 READY 累积易产生共识幻觉。

**建议**：SUBTASK_READY 记录显式写四维状态（execution / artifact / proposed physical / claim ceiling），并声明"subtask ready 不构成任何物理或 route 结论"。

---

## 3. 其他意见

- **R4. Standing Authorization（§14）边界写死**：exploration 产物必须标记 `exploration_only`，**不得被后续 route 决策引用为证据**；每个 exploration 批次结束即使无 escalation 也给 Codex 一份状态摘要（并入 R2 ledger）。
- **R5. Copilot 对 batch proposal 的完整性审查要有对抗性**（§16）：不只查字段齐全，要查 claim ceiling 是否可证伪、escalation triggers 是否覆盖、验收标准是否会被"常量实现"通过。
- **R6. M9/M11 保留两个 checkpoint**（§11）：完全同意，dependency gate 不能合并。
- **R7. M10 判定**（§12）：同意"先问是否有 downstream 依赖"的判断标准，但裁决权应归 **Codex**，避免执行者把不顺手的任务划出 critical path。
- **R8. M6 的 FROZEN Preflight**（§18）：完全同意，不能因"已签发"跳过机械预检（M4-002 教训）。

---

## 4. Q1–Q10 简要回答

| Q | 回答 |
|---|---|
| Q1 Codex → batch/scientific-gate auditor | ✅ 同意 |
| Q2 内部多轮 rework 不需每轮 Codex | ✅ 同意（前提：R1+R2 成立） |
| Q3 PRE-REVIEW ≠ FORMAL REVIEW | ✅ 同意，FORMAL 必须在 snapshot 后（实测验证其价值） |
| Q4 SUBTASK_READY 替代逐任务 ACCEPT | ✅ 同意（前提：R3 携带四维语义） |
| Q5 Escalation Triggers | ✅ 足够 |
| Q6 M7+M8 一个 CRITICAL+LITE Batch | ✅ 同意 |
| Q7 M9/M11 两个 Gate | ✅ 同意 |
| Q8 Route C/D Standing Authorization | ⚠️ 有条件同意（R4 边界写死） |
| Q9 M10 判定 | ✅ 同意判断标准，但裁决权归 Codex（R7） |
| Q10 W5 zero-Codex 探索 | ✅ 同意 |

---

## 5. 结论与落地建议

**核心架构可以采纳**。并入 WORKFLOW-lite 2.0 时建议按提案 §25 的做法只加一个扩展章节（Batch Execution / Delegated Closure），不重写协议。

三条硬性加固：**R1（FORMAL REVIEW 新鲜对抗）、R2（内部闭环 ledger）、R3（SUBTASK_READY 四维语义）**，加上 R4/R5 两个边界条件。

落地顺序建议：
1. 三方对 Q1–Q10 与 R1–R8 达成一致；
2. 由 Claude 起草扩展章节草稿 → Copilot 对抗性完整性审查 → Codex 审批；
3. 选一个真实 batch（如 M7+M8）试点，验证 inner loop + ledger 的实际成本与价值，再定 FINAL。
