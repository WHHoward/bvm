---
name: josim-handoff
description: Issue, execute, verify, and audit file-backed Codex–Claude task contracts for the JoSIM/BVM repository. Use when delegating implementation or experiments between agents, creating a task packet, acknowledging scope, recording an execution receipt, checking changed paths and hashes, or issuing an audit disposition; do not use it to replace `josim-experiment` or `josim-evidence-audit` scientific rules.
---

# JoSIM Codex–Claude 任务交接

## 会话开始先查信箱（2026-08-09，用户要求）

双方（Claude、Codex）在**每次会话开始**和**处理任何委派任务前**，先检查对方来信：

```bash
python3 research/mailbox/scripts/mailbox.py list          # 新消息一览
python3 research/mailbox/scripts/mailbox.py log           # 完整对话时间线
python3 research/mailbox/scripts/mailbox.py read <id>     # 读全文
```

mailbox 是对话渠道（`research/mailbox/README.md`）；正式动作仍走本 skill 的协议文件。收到消息后按内容决定是否进入对应流程（audit、rework、supersede、stand-in review 等）。

## 先确定角色

1. 把用户视为路线、指标冻结和论文主张的最终批准者。
2. 把 Codex 视为任务签发者、计划者和独立审计者。
3. 把 Claude Code 视为受约束的实现与实验执行者。
4. 若 Codex 修改了本任务的核心实现或原始产物，在审计中记录 `independence.mode: CO_EXECUTOR`；该预审必须要求后续独立复核，不能关闭任务。
5. 完整阅读 [handoff-protocol.md](references/handoff-protocol.md)，再创建或裁决任务包。

## 选择操作

| 用户意图 | 操作 |
|---|---|
| “交给 Claude 做”“生成任务包” | 签发 request |
| “执行这个 task request” | ACK 后执行并写 receipt |
| “检查 Claude 的结果” | 验证绑定后独立审计 |
| “现在进行到哪一步” | 只读运行 `verify-task` 并报告 |
| 修改/运行 `.cir` | 同时使用 `josim-experiment` |
| 判断相位、SFQ、JTL 或 Gate | 同时使用 `josim-evidence-audit` |
| 更新任务表或交接摘要 | 审计接受后使用 `josim-todo-manager` / `josim-project-summary` |

## 签发 request（Codex）

1. 从 `memory/project-todo.md` 选择一个依赖已满足的任务，并读取 `docs/HANDOVER.md` 的当前事故边界。
2. 从 [task-request.yaml](assets/task-request.yaml) 创建唯一目录 `research/tasks/<task-id>/request.yaml`。
3. 把目标改写成可验收的单一问题；列出非目标与 `claim_ceiling`，避免执行者扩大物理主张。
4. 明确只读、可写、冻结路径和锁。可写路径不得与冻结路径重叠。
5. 绑定 Git HEAD、dirty 快照、相关输入哈希、HANDOVER 和已冻结 metric spec；规格未冻结时明确写 `status: UNFROZEN`，不得虚构路径或容差。
6. 明确运行、联网、安装、创建 worktree、提交、删除或覆盖权限。未授权项一律为 `false`。
7. 写出逐条 acceptance、invalid、inconclusive 与 stop 条件。`FAIL`、`INVALID` 和 `INCONCLUSIVE` 必须可区分。
8. 验证 request；存在 issuance blocker 时保持 `DRAFT`。只把无 blocker 的 request 改为 `ISSUED` 并签名：

```bash
python3 .agents/skills/josim-handoff/scripts/handoff.py validate research/tasks/<task-id>/request.yaml
python3 .agents/skills/josim-handoff/scripts/handoff.py sign-request research/tasks/<task-id>/request.yaml
```

签名后 request 不可原地修改。合同变化创建新 request，用其 `supersedes` 指针引用旧 task/revision；旧文件与签名保持不变。相同合同的重跑只增加 attempt ID。

## ACK 与执行（Claude Code）

1. 先运行 `verify-task`。若 request 是 `DRAFT`、无签名或签名无效，只在会话中报告等待签发，不创建协议 ACK，也不编辑或运行。
2. 只有有效 `ISSUED` request 才继续读取 `contracts.read_first` 和 `required_skills`。
3. 比对 request 哈希、Git HEAD、dirty 快照、scope 哈希、工具和依赖；编辑前从 [execution-ack.yaml](assets/execution-ack.yaml) 写 `attempts/<attempt-id>/ack.yaml`。
4. 有效合同的运行前预检不满足时写 `decision: BLOCKED` 并停止；不得靠猜测绕过合同。
5. 只修改 `scope.write_paths`。不得修改 request、audit、todo、HANDOVER、CHANGELOG、冻结规格或历史 raw 数据。
6. 不使用 `git add -A`、`git reset --hard`、`git clean`、隐式 stash，且不覆盖既有 run ID。
7. 命中 stop condition、需要扩大权限或发现范围外修改时，停止并记录 `BLOCKED` 或 `DEVIATED`。
8. 完成后从 [execution-receipt.yaml](assets/execution-receipt.yaml) 写 receipt，逐项记录改动、命令、产物哈希、测试和仅作为提议的解释。执行者不得签发最终物理 Gate。

## 独立审计（Codex）

1. 先运行：

```bash
python3 .agents/skills/josim-handoff/scripts/handoff.py verify-task research/tasks/<task-id>
```

2. 按固定顺序审计：request/规格 → diff/连线/实现 → raw/log → 独立重算/测试 → 最后才读执行者的解释。
3. 分别裁决：
   - `artifact_status`: `VALID | INVALID | NOT_AUDITED`
   - `physical_verdict`: `PASS | FAIL | INCONCLUSIVE | NOT_APPLICABLE`
   - `audit_disposition`: `ACCEPTED | REWORK_REQUIRED | REJECTED`
4. 从 [audit-verdict.yaml](assets/audit-verdict.yaml) 写入 `audits/<audit-id>/verdict.yaml`，绑定 request、ACK 与 receipt 哈希。
5. 执行正确但物理假设失败时允许 `COMPLETED + VALID + FAIL + ACCEPTED`；缺执行证据导致的未知通常是 `REWORK_REQUIRED`，现象本身不可判别则可 `ACCEPTED + INCONCLUSIVE` 并签发下一项最小判别任务。
6. 只有 audit 被接受后，才根据真实证据更新 todo、HANDOVER、ADR 或论文上层文档。

## 机械校验边界

`handoff.py` 校验 schema、SHA-256 封存、跨文档哈希、scope manifest 和写路径范围。命令名 `sign-request` 中的“签名”只是内容摘要与篡改检测，不是带私钥的身份认证；信任仍依赖文件所有权与 Git 审查。该工具也不能证明电路正确、实验收敛或物理结论成立；这些仍由 `josim-experiment` 与 `josim-evidence-audit` 控制。

修改协议、schema 或脚本后运行可重复自测：

```bash
python3 .agents/skills/josim-handoff/scripts/test_handoff.py
```

## Stand-in 代理（Codex 不可用时，2026-08-09）

Codex 因额度/停机不可用时，用户可明确授权 Claude 临时代理签发、取代或状态同步等 Codex 角色动作。完整规则见 `research/WORKFLOW.md` §15。要点：

- 每会话单独获得用户授权，在 `research/tasks/<id>/standin/<Sxx>/record.yaml` 记录（模板 `assets/standin-record.yaml`，schema `standin-record.schema.json`）；
- 产物 `PROVISIONAL`，Codex `review.yaml`（`standin-review.schema.json`）确认前不生效，不得上推 todo/HANDOVER；
- stand-in 不得审计自身执行；`verify-task` 输出 `STAND-IN PROVISIONAL` 警告标记未审查的 record。
