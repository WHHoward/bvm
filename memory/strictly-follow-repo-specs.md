---
name: strictly-follow-repo-specs
description: 用户要求严格参考仓库规范——当前合同明确指令优先于历史惯例，动作前先查证规范
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 410a0a8b-0b91-49f6-a1fe-ceddb4d01726
  modified: 2026-08-18T16:08:49.643Z
---

用户（2026-08-19）明确反馈："以后你应该严谨的参考我们仓库中的规范"。

**Why:** 2026-08-18 SEAL-002 A01 交付后，我凭历史惯例（STABLE-LOAD/TIMING 等任务的 REVIEW_REQUEST 接力）补发了 claude→copilot REVIEW_REQUEST，但当前合同 TASK_READY 明确限定 "Do not create verifier/C_verify or audit; stop and report paths/SHAs"——producer 阶段到"报告后停止"为止，后续 review/audit 由 Codex 按审计阶段统一安排。用户指出后我撤回消息。指令冲突时我选了惯例而非合同，是错误。

**How to apply:**
- 动作前先查证：当前任务 request/TASK_READY 的明确边界 > WORKFLOW.md / mailbox README 的流程规定 > 历史惯例。冲突时以当前合同为准。
- 收到用户追问（如"为什么没做 X"）时，先查规范确认 X 是否本阶段职责，而不是直接补做。
- 合同说 "stop and report" 就是停止——不自行扩展下一步角色动作（review/audit/commit 之外的流程动作都算）。
- mailbox REVIEW_REQUEST 必需字段：task_id / attempt_id / delivery_snapshot / result_path（mailbox README §类型表）；正式动作仍走协议文件。

相关：[[mailbox-full-scan]]、[[feedback-notify-changes]]
