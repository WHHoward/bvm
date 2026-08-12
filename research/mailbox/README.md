# Claude ↔ Codex ↔ Copilot Mailbox（异步对话模块）

Claude、Codex 与 Copilot 之间的**非正式异步消息渠道**：提问、澄清、状态同步、提醒、讨论。消息通过仓库文件传递，各方（以及用户）随时可读。

> **边界（重要）**：mailbox 是**通知层**，不是**事实层**。mailbox 传"有人给你发消息，让你去看东西"；真正的事实来源是 TASK.md / RESULT.md / REVIEW.md / Git snapshot（LITE），FROZEN 再加 request/ACK/receipt/audit-verdict/SHA-256（josim-handoff/v1）。正式动作必须在 `research/tasks/<task-id>/` 走协议文件；mailbox 消息不携带合同授权。典型用法：Codex→Claude "M12 TASK 已签发，正式要求见 TASK.md"；Claude→Reviewer "A01 完成，snapshot=abc1234，正式结果见 RESULT.md"。

## Mailbox Operating Rule（canonical，唯一一份）

> When the user says **"查看你的 mailbox，然后开始你的工作"**（或等价表述），Agent MUST：

1. Read the newest relevant **unprocessed** mailbox message for its role.
2. Resolve every referenced canonical artifact before acting.
3. Treat mailbox text only as notification/index metadata.
4. Never treat mailbox text itself as task authority, scientific evidence, acceptance, route approval, or todo closure.
5. Obey the referenced TASK / RESULT / REVIEW / audit / snapshot.
6. Check that the message is current and not superseded.
7. If the message is stale, conflicting, ambiguous, missing its referenced artifact, or has no valid action for this role: **STOP and report `BLOCKED`.**
8. Do not invent new work merely because the mailbox is empty.
9. After completing the role: write the formal artifact first, then use mailbox only to notify the next role.

**Chinese 摘要**：mailbox 只回答"轮到谁、去看哪个正式文件"；行动依据永远在正式 artifact 里。

### mailbox ≠ authority（明确写死）

```text
mailbox != execution authority
mailbox != scientific fact layer
mailbox != audit verdict
mailbox != project state
```

正式来源只有：`TASK` / `RESULT` / `REVIEW` / `AUDIT / VERDICT` / `GIT SNAPSHOT / HASH` / `PROJECT TODO`。mailbox 与正式 artifact 冲突时**正式 artifact 优先**；无法判断哪个更新时报 `BLOCKED`，不自行猜测。

### 无任务则不行动（NO_PENDING_WORK）

当被要求"查看 mailbox 然后开始工作"，但满足任一条件：

- 没有 relevant unprocessed message；
- 最新消息已 CLOSED；
- 引用任务已 ACCEPTED；
- recipient 不是自己；
- 消息已被 superseded；

必须回答 **`NO_PENDING_WORK`**，**不得**自己从 project-todo 挑下一个任务开始做。只有 Codex 在用户明确"规划下一任务"指令后才能创建下一正式任务。

### stale-message 防线

至少检查：task id、attempt、当前 task state、引用 artifact 是否存在、是否已有更新 verdict、是否有 superseding 消息。例：mailbox 说 REVIEW_REQUEST 但任务已 ACCEPTED → **STALE → 不执行**。

## 消息类型（最小集，可选字段 `type:`）

| type | 语义 | 典型 sender→recipient |
|---|---|---|
| `TASK_READY` | 新任务已签发 | Codex→Claude |
| `REVIEW_REQUEST` | 请做 evidence review（必含 task_id / attempt_id / delivery_snapshot / result_path） | Claude→Copilot |
| `REWORK_REQUEST` | 有 Major finding，请修复 | Copilot→Claude（经 Codex 确认） |
| `AUDIT_READY` | 稳定 delivery 等待审计 | Copilot→Codex |
| `BLOCKED` | 停止，需要裁决 | 任一→Codex/User |
| `CLOSED` | 任务闭环 | Codex→Claude |
| `INFO`（默认） | 非接力通知 | 任一→任一 |

旧消息没有 `type` 字段（向后兼容，validate 不要求）；新消息通过 `--type` 写入。**不要**把完整 scientific reasoning 放进 mailbox——正文只放索引、路径、下一步。

## 三角色 mailbox 行为

- **Claude（执行者）**：读最新 `TASK_READY` / `REWORK_REQUEST` → 打开正式 TASK/REVIEW → 检查 scope/AC/stop conditions/claim ceiling → 在授权 scope 内连续推进（普通 implementation bug 不找 Codex）→ 写正式 RESULT → **对 LITE Scientific Implementation 创建 immutable delivery snapshot（默认 EXECUTOR-owned，见 WORKFLOW-lite §8）** → mailbox REVIEW_REQUEST（必须含 task_id / attempt_id / delivery_snapshot / result_path）→ 通知下一角色。仅当：scientific semantics 要变、scope 要扩、AC 有歧义、stop condition 命中、canonical artifact 缺失、mailbox 与 TASK 冲突、同根因反复失败需要重设计实验时停止。
- **Copilot（reviewer）**：读最新 `REVIEW_REQUEST` → 读 TASK + RESULT + **REVIEW_REQUEST 指定的 snapshot**（declared `reviewed_attempt` / `reviewed_snapshot`，不得只审 "latest"）→ adversarial review → 写正式 REVIEW（声明 reviewed attempt/snapshot）。默认不修改实现、不扩 scope、不改语义、不更新 todo、不给最终 ACCEPT。Major → mailbox REWORK_REQUEST → Claude（修复必须产生**新 attempt / 新 snapshot**，不得静默修改旧 snapshot）；clean → mailbox AUDIT_READY → Codex（含 reviewed snapshot 与 REVIEW path）。
- **Codex（planner/auditor）**：先判断请求是 PLANNING 还是 AUDIT。Planning：仅当用户已决定启动某科研项时定义正式 TASK，mailbox 发 TASK_READY；不得仅因 mailbox 写"做 M8"就自行创造未授权路线。Audit：读 TASK/RESULT/REVIEW/raw → 独立审计 → verdict 写入 canonical audit artifact → mailbox 只发状态通知。

## 最简接力（Scientific Implementation）

```text
User → Codex 定义 TASK → mailbox TASK_READY → Claude 执行 → 写 RESULT
     → mailbox REVIEW_REQUEST → Copilot review → 写 REVIEW
     ├─ Major → mailbox REWORK_REQUEST → Claude
     └─ clean → mailbox AUDIT_READY → Codex audit → 写 verdict → mailbox CLOSED/REWORK
```

**普通任务（plotting/README/parser/refactor/path fix/机械 metadata）不需要五段接力**：`User → Claude → done` 或 `User → Claude → Copilot（可选）→ done`，不叫 Codex。只有 Scientific Gate（M8 收敛、M9 MetricSpec freeze、M11 baseline、INTERFACE_GATE、route verdict、bounded negative result、paper-critical result）才走完整 formal handoff（Codex 预注册 → Claude FROZEN 执行 → 独立 review → Codex 深度审计 → 用户采纳）。

## 用户可用的一句话驱动

```text
"查看你的 mailbox，然后开始你的工作。"   ← Codex / Claude / Copilot 各自按角色行动
"查看你的 mailbox，然后继续你的工作。"   ← 继续同一任务
```

适用：已签发 TASK、已生成 REVIEW_REQUEST / REWORK_REQUEST / AUDIT_READY、已有正式 artifact 等待下一角色。**不适用**：创建全新科研方向、启动未授权 Mx、改 route、改 MetricSpec、改 Interface Gate、创建 paper claim——这些需要用户先明确"请规划/启动 X"。

## 目录结构

```text
research/mailbox/
├── README.md
├── from-claude/     ← Claude 写的消息（Codex/Copilot 读这里）
├── from-codex/      ← Codex 写的消息（Claude/Copilot 读这里）
├── from-copilot/    ← Copilot 写的消息（Claude/Codex 读这里）
└── scripts/
    ├── mailbox.py        ← CLI：send / list / read / validate / log
    └── test_mailbox.py   ← 17 个单元测试（stdlib only）
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
type: INFO            # 可选：TASK_READY | REVIEW_REQUEST | REWORK_REQUEST | AUDIT_READY | BLOCKED | CLOSED | INFO
subject: 一行主题
---
正文（自由 markdown，只放索引/路径/下一步，不放完整推理）
```

## 用法

```bash
# 发送（默认 claude -> codex；--type 可选）
python3 research/mailbox/scripts/mailbox.py send \
  --to codex --subject "M7 已交付，等待审计" --type AUDIT_READY \
  --body "receipt 已写，worktree 产物待复核。" --task M7

# Codex 回复
python3 research/mailbox/scripts/mailbox.py send \
  --to claude --subject "Re: M7 已交付" --reply-to claude-20260809-193400

# 列出全部 / 过滤（含 type 标签）
python3 research/mailbox/scripts/mailbox.py list
python3 research/mailbox/scripts/mailbox.py list --to claude

# 阅读 / 完整对话时间线 / 校验
python3 research/mailbox/scripts/mailbox.py read <message_id>
python3 research/mailbox/scripts/mailbox.py log
python3 research/mailbox/scripts/mailbox.py validate <path>
```

## 用户如何查看对话

对话就是仓库里的 markdown 文件，任何人（包括你）都能看：

- **最省事**：`python3 research/mailbox/scripts/mailbox.py log` —— 双向消息按时间合并成完整对话记录；
- 或在 IDE 里直接打开 `research/mailbox/from-claude/`（Claude 写的）和 `research/mailbox/from-codex/`（Codex 写的），文件名即 `message_id`，列表可见主题；
- 双方不会私自删除消息（append-only），你的查看不会影响任何状态。

## 纪律

- **append-only**：消息发出后不编辑、不删除；回复用 `--reply-to` 链接；
- **message_id** 由 `from-时间戳` 自动生成（同秒自动加后缀），唯一性由 CLI 保证；
- 双方会话开始时跑一次 `list` 检查来信；重要事项同时用 `related_task` 关联任务目录；
- **processed/unread 状态不做状态机**：用 superseding 消息 + 任务正式状态判断"是否最新"；
- 不依赖第三方：纯 Python 标准库；
- 测试：`python3 research/mailbox/scripts/test_mailbox.py`
