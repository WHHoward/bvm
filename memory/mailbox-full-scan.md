---
name: mailbox-full-scan
description: 用户要求 mailbox 检查必须全量（所有方向、所有新消息），不能只看最新几条
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 0a6c3d20-0d5b-452e-a234-939c2e31e4bd
  modified: 2026-08-17T10:52:38.916Z
---

用户 2026-08-17 两次强调："检查mailbox要检查全"。

**Why**：我曾用 `tail -3`/按方向 grep 只看最新几条，漏掉了 Codex 的 A02 指令（codex-20260817-181706），导致一轮往返延误。

**How to apply**：每次检查 mailbox 用 `mailbox.py list` 全量输出并扫**所有方向**（codex->claude、copilot->claude、copilot->codex 中含对 claude 有隐含要求的内容）与**所有 08-17 当天消息**；按 message_id 递增确认无遗漏后再决定动作。相关：[[bvm-chain-status-20260817]]
