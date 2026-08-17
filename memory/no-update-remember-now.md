---
name: no-update-remember-now
description: 用户要求 Claude 不要写入 .remember/now.md，该文件由用户/remember 系统自行管理
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 410a0a8b-0b91-49f6-a1fe-ceddb4d01726
  modified: 2026-08-17T11:12:53.386Z
---

用户 2026-08-17 明确指示：**不要更新 `.remember/now.md`**，像以前一样保持不动（今天曾在会话记录里 append 过一段，用户叫停）。

**Why:** `.remember/now.md` 是用户自己的记忆缓冲（remember 系统管理），Claude 的会话记录会污染它；用户希望 Claude 的记忆写入走自己的 `memory/` 目录。

**How to apply:** 不要向 `.remember/` 下任何文件写入或 append；会话/任务记录只写入 `memory/` 下的记忆文件。若确实需要记录，先问用户。相关：[[bvm-chain-status-20260817]]。
