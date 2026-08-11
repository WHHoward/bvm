---
title: 三方协作协议修订提案 — Copilot 独立复核
document_type: proposal
status: DRAFT
proposed_by: Copilot（VS Code）
date: 2026-08-11
related:
  - research/WORKFLOW.md
  - docs/HANDOVER.md
---

# 三方协作协议修订提案：Copilot 独立复核

> **状态：提案（DRAFT），尚未被采纳。** 本文件不修改任何协议条款，也不授予 Copilot 任何协议文件写入权。是否采纳、如何并入 `research/WORKFLOW.md`，由用户与 Codex 决定。

## 1. 背景与动机

当前 `josim-handoff/v1` 协议有一个结构性软肋：**Codex 同时是合同设计者和独立审计者**——自己签发合同，再审计自己对合同的执行，独立性天然打折。

实际摩擦证据：

- **M4 任务三次重签**：`M4-001`（带 standin 记录）→ `M4-002`（A01 预检因 worktree HEAD 与基线不符而 `BLOCKED`）→ `M4-003`（至今仍为 `DRAFT`）。而 M4 本质只是「实现 raw-rad→turns 单位层 + 单元测试」的小任务。
- **近期提交以流程元工作为主**：mailbox、模型路由、worktree 纪律、checkin 等占多数，真正的研究交付反而滞后。
- **相位单位事故（2026-08-09）**说明：单一解释链未经第二双眼睛复核，错误会一直潜伏到审计才发现。

## 2. 提案：三方角色分离

| 角色 | 职责 | 不做的事 |
|---|---|---|
| 用户（研究负责人） | 最终裁决：路线切换、指标冻结、论文级主张 | 不逐样本核对 CSV |
| Codex（指挥/决策） | 规划、拆解 todo、签发密封合同、**最终采纳判定** | 不再承担深度独立重算（移交 Copilot） |
| Claude（执行） | 受合同约束实现/运行实验、保存原始证据、提交 receipt | 不做最终采纳判定；不自行扩大范围 |
| Copilot（复核，即本提案提议的新角色） | 交付后**独立复核**：机械校验、独立重算、claim-ceiling 检查、出具 review 记录 | 审查期间对执行产物只读；不修改协议文件；不参与采纳判定 |

## 3. 新流程（简化后）

```text
Codex 签发合同
  → Claude ACK（预检）
  → Claude 受约束执行 + 提交 receipt
  → Copilot 独立复核，产出 review.yaml
  → Codex 轻量采纳审阅（读 review + 扫一眼 diff/产物）
  → verdict：ACCEPTED / REWORK_REQUIRED / REJECTED
```

打回时：

```text
Copilot 的 review 给出「具体可执行打回清单」
  → Claude 新建 attempt 修复
  → Copilot 再复核
  → 通过后才回到 Codex 采纳
```

`REWORK` 循环前移到 Copilot 这一层，Codex 只在最后介入决策，减少往返轮次。

## 4. 信任边界（已与用户确认）

- Copilot 的复核证明：**产物自洽、可复现、证据支持结论——且只到合同声明的 `claim_ceiling` 为止**。
- 它**不证明**「Claude 当时确实执行了某条命令」：Copilot 与 Claude 共享同一文件系统，无法做身份级证明；这一点上 Copilot 与 Codex 受同样的证据限制。
- 因此「检查通过」的语义是：**Codex 可以信任这份基于证据的复核到 claim ceiling**，而非绝对信任。Codex 仍保留最终采纳权与论文级主张决定权。
- Copilot 的 review 记录本身可复现（记录命令、哈希、重算步骤），供用户/Codex 低成本抽查。

## 5. 复核独立性规则（已与用户确认）

1. 审查期间，Copilot 对执行产物**只读**；发现问题写入 review，不直接改。
2. 问题 → 记入 review → 打回 Claude 修复（新 attempt）→ Copilot 复核。
3. Copilot 不修改 `request.yaml`、`baseline/`、`receipt.yaml`、`verdict.yaml`、`memory/project-todo.md`、`docs/HANDOVER.md`、`CHANGELOG.md` 等协议/上层文件。
4. 若 Copilot 参与了某任务的实现（例如用户直接要求 Copilot 写代码），则该任务的复核应改由 Claude 或另行安排，避免自我审计。

## 6. 复核清单（Copilot 实际检查什么）

1. **机械层**：schema 校验；request/ack/receipt 哈希链；changed paths 在 `scope.write_paths` 内且与 receipt 自报一致；产物 SHA-256。
2. **独立重算**：从原始 CSV/产物独立重算关键数字（如 $\Delta\phi_{\rm rad}/(2\pi)$ 圈数、同一 JJ 的电压面积交叉校验），不依赖 Claude 的解释文本。
3. **证据层**：区分 artifact `VALID/INVALID`、activity vs event、local vs downstream；检查结论是否超出 `claim_ceiling`。
4. **输出**：简短 review 记录，给出 `PASS` 或「具体可执行打回清单」，不用含糊的 `INCONCLUSIVE` 代替漏项。

## 7. 本提案简化的部分

- **Codex 深度独立复核 → 降级为轻量采纳审阅**：读 Copilot 的 review + 扫一眼 diff/产物即可。
- **模型路由表（Sol/Terra/Luna 分层）→ 建议从协议正文移除或降级为注释**：三方职责已天然定义分工，路由细节属于环境配置（`.codex/agents/*.toml`），不该写进协议正文。
- **不新增快速通道设计**（按用户意见，快速通道无需重新设计）。
- **不新增 schema、不新增状态机状态、不新增流程环节**。

## 8. 文件层最小改动

- **新增**：`research/tasks/<task-id>/attempts/<attempt>/review.yaml` —— Copilot 写，append-only。
- **保留**：`verdict.yaml` 仍由 Codex 写，并在其中引用 `review.yaml`。
- 其余结构（`request.yaml` / `ack.yaml` / `receipt.yaml` / `baseline/` / `audits/`）不变。

## 9. 试点建议

以 **M4**（当前 `DRAFT` 的 `JH-20260811-M4-003`）作为首个试点：

- 任务小、已三次重签、正缺一个顺畅的出口；
- 实现型、无物理主张，最适合验证「Copilot 复核 → Codex 采纳」的时效与质量；
- 试点通过后再决定是否正式并入 `research/WORKFLOW.md`（正文修改由 Codex 负责）。

## 10. 非目标（本提案不改变）

- 四维结果分离（`execution_status` / `artifact_status` / `physical_verdict` / `audit_disposition`）不变。
- 哈希密封、append-only、`claim_ceiling`、读写边界等硬不变量不变。
- 物理 Gate 判定口径不变（由 `josim-evidence-audit` 与 `METRIC_SPEC_V2` 决定）。
- 不改变 Claude 的执行者职责与 `BLOCKED`/`DEVIATED` 语义。

## 11. 待用户/Codex 确认的事项

1. `review.yaml` 的字段与命名是否合适？
2. Codex 采纳审阅的深度下限：哪些情况（如物理 Gate、矛盾证据）Codex 必须亲自重算，不能仅凭 review？
3. 试点（M4）通过后，是否正式并入 `WORKFLOW.md`？
4. 本提案是否需要在 mailbox 中向 Codex 同步一份摘要？
