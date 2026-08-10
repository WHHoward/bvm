---
name: josim-checkin
description: One-screen project status reminder — mailbox, open task contracts, todo head, worktrees, working-tree state. Use at session start, or when the user asks "where are we?", "what's next?", "check the project", or looks unsure of the current state; read-only, does not mutate files.
---

# JoSIM 会话签到（checkin）

## 什么时候用

- **每次会话开始**（与"查信箱"一起，见 `josim-handoff` 的会话开始规则）；
- 用户问"我们到哪了 / 下一步做什么 / 检查一下状态 / 提醒我"；
- 收到 Codex 来信、新审计结果、或用户提到某个任务时，先 checkin 再行动。

## 步骤

1. 运行一键状态：

```bash
python3 scripts/checkin.py
```

2. 按输出决定行动：
   - **[1] Mailbox 有 Codex 来信** → 先 `mailbox.py read <id>` 处理，再谈其他；
   - **[2] 有 DELIVERED 等审计任务** → 提醒用户"等 Codex 审计"，不重复执行；
   - **[3] todo 有 🔴 但无阻塞** → 按依赖链提示下一项；
   - **[4] 活跃 worktree** → 确认没有遗留未清理的工地；
   - **[5] master 有未提交改动** → 提醒提交或说明归属。

3. 输出给用户的提醒要**简短、可行动**（一句话 + 建议动作），不要全文转述。

## 纪律

- checkin 是**只读**命令，不修改任何文件；
- 与 `josim-todo-manager`（任务状态权威）的区别：checkin 是"一键状态 + 提醒"，todo-manager 是"任务定义与完成标准"；
- 不确定下一步时，按依赖链给出推荐项，但**不主动开工**（等待期/暂停任务除外）。
