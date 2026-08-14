---
name: feedback-notify-changes
description: 每次改动后必须及时告知用户和 Codex（mailbox）；用户确认后才 commit
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0a6c3d20-0d5b-452e-a234-939c2e31e4bd
  modified: 2026-08-14T14:57:13.850Z
---

用户要求（2026-08-14）：我对项目做的任何更改/更新（文档、代码、实验、状态同步）都要**及时告知用户和 Codex**——通过 mailbox 发 [INFO] 消息给 Codex，并在对话中向用户说明改了什么。

**Why**: 三代理协作中 Codex 需要了解 Claude 的所有动作才能做独立审计；用户是最终权威，需要知情后才能决定提交。此前改动常不通知，用户无法跟踪。

**How to apply**:
- 每次完成文档/代码/证据改动后，发 mailbox 消息给 Codex（type=INFO），列出：改了哪些文件、为什么改、与哪个 audit/contract 一致、有没有触碰 frozen evidence
- 对话中向用户简报改动清单
- **不主动 commit**——提交由用户确认后执行；commit 后再次通知 Codex
- 数值引用统一用最新 accepted 报告（如 S0-004 corrected report / C02），不引用被取代的旧报告
