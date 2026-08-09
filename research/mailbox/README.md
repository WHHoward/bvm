# Claude ↔ Codex Mailbox（异步对话模块）

Claude Code 与 Codex 之间的**非正式异步消息渠道**：提问、澄清、状态同步、提醒、讨论。消息通过仓库文件传递，双方（以及用户）随时可读。

> **边界（重要）**：mailbox 是**对话**渠道，不是**合同**渠道。任何正式动作（签发/取代 request、ACK、execution receipt、audit verdict、stand-in record、todo/HANDOVER 上推）都必须在 `research/tasks/<task-id>/` 走 `josim-handoff` 协议文件。mailbox 消息不携带合同授权；mailbox 里达成的意向，正式落地仍以协议文件为准。

## 目录结构

```text
research/mailbox/
├── README.md
├── from-claude/     ← Claude 写的消息（Codex 读这里）
├── from-codex/      ← Codex 写的消息（Claude 读这里）
└── scripts/
    ├── mailbox.py        ← CLI：send / list / read / validate
    └── test_mailbox.py   ← 11 个单元测试（stdlib only）
```

每则消息是一个 markdown 文件，带 frontmatter：

```markdown
---
message_id: claude-20260809-193400
from: claude
to: codex
created_at: "2026-08-09T19:34:00+08:00"
in_reply_to: ""
related_task: "JH-20260809-M4-001"
subject: 一行主题
---
正文（自由 markdown）
```

## 用法

```bash
# 发送（默认 claude -> codex）
python3 research/mailbox/scripts/mailbox.py send \
  --to codex --subject "M4 已交付，等待审计" \
  --body "receipt 已写，worktree 产物待复核。" --task JH-20260809-M4-001

# Codex 回复
python3 research/mailbox/scripts/mailbox.py send \
  --to claude --subject "Re: M4 已交付" --reply-to claude-20260809-193400

# 列出全部 / 过滤
python3 research/mailbox/scripts/mailbox.py list
python3 research/mailbox/scripts/mailbox.py list --to claude

# 阅读
python3 research/mailbox/scripts/mailbox.py read <message_id>

# 完整对话时间线（双向合并、按时间排序）
python3 research/mailbox/scripts/mailbox.py log

# 校验单个文件
python3 research/mailbox/scripts/mailbox.py validate <path>
```

## 用户如何查看对话

对话就是仓库里的 markdown 文件，任何人（包括你）都能看：

- **最省事**：`python3 research/mailbox/scripts/mailbox.py log` —— 双向消息按时间合并成完整对话记录；
- 或在 IDE 里直接打开 `research/mailbox/from-claude/`（Claude 写的）和 `research/mailbox/from-codex/`（Codex 写的），文件名即 `message_id`，列表可见主题；
- 双方不会私自删除消息（append-only），你的查看不会影响任何状态。

## 纪律

- **append-only**：消息发出后不编辑、不删除；回复用 `--reply-to` 链接。
- **message_id** 由 `from-时间戳` 自动生成（同秒自动加后缀），唯一性由 CLI 保证。
- 双方会话开始时跑一次 `list` 检查来信；重要事项同时用 `related_task` 关联任务目录。
- 不依赖第三方：纯 Python 标准库。
- 测试：`python3 research/mailbox/scripts/test_mailbox.py`
