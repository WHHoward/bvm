# JoSIM Handoff Protocol v1

本文是 `josim-handoff` 的完整语义合同。JSON Schema 是结构约束，本文件解释状态、所有权和异常处理。项目级说明见 `research/WORKFLOW.md`。

## 1. 不变量

- request 是唯一授权源；聊天中的补充不能静默扩大其范围。
- `ISSUED` request 必须有 `request.sha256`，ACK/receipt/audit 必须逐级绑定前序文件的原始字节 SHA-256。这里的“签名”是哈希封存，不是带私钥的身份认证；信任仍依赖文件权限与 Git 审查。
- 时间戳也必须单调：`request.issued_at ≤ ACK.created_at ≤ receipt.created_at ≤ audit.created_at`（同一 attempt）。`verify-task` 强制检查这一顺序；已接受的历史记录若发现纯 metadata 时间错误，只能以 hash-bound `errata/chronology.yaml` 精确列出异常对，不能回写 request、receipt 或 audit，也不能豁免任何新的时间错误。
- request 一经 ACK 不得原地修改。合同变化创建新 revision；同一合同重跑创建新 attempt。
- raw 输入与运行产物不可覆盖；失败运行也是证据。
- task 执行完成不等于物理成功，物理失败不等于执行失败。
- 人类批准的路线变化、metric spec 冻结和论文结论不能由执行者自行决定。

## 2. 文件布局

```text
research/tasks/<task-id>/
├── request.yaml
├── request.sha256                 # 仅 ISSUED request；逻辑取代不改旧文件
├── baseline/
│   ├── git-status.txt
│   └── scope-files.sha256
├── attempts/<attempt-id>/
│   ├── ack.yaml
│   ├── receipt.yaml
│   └── logs/...
└── audits/<audit-id>/verdict.yaml
```

JoSIM 实验的大文件和不可变 raw 仍放在 `test/final/<route>/runs/<run-id>/`；task receipt 以路径和哈希引用它们，不复制第二份。

## 3. 四个相互独立的状态维度

| 维度 | 值 | 回答的问题 |
|---|---|---|
| workflow | `DRAFT/ISSUED/ACKED/RUNNING/DELIVERED/BLOCKED/DEVIATED/AUDITED/CLOSED/SUPERSEDED` | 交接走到哪一步 |
| execution | `COMPLETED/BLOCKED/DEVIATED` | 执行合同是否完成 |
| artifact | `VALID/INVALID/NOT_AUDITED` | 产物能否作为证据 |
| physical | `PASS/FAIL/INCONCLUSIVE/NOT_APPLICABLE` | 已声明物理主张是否成立 |

审计处置另记为 `ACCEPTED/REWORK_REQUIRED/REJECTED`。典型组合：

- `COMPLETED + VALID + FAIL + ACCEPTED`：实验做对了，可信地否定了预注册主张。
- `COMPLETED + INVALID + NOT_APPLICABLE + REWORK_REQUIRED`：命令跑完，但数据不能用于物理结论。
- `BLOCKED + NOT_AUDITED + NOT_APPLICABLE`：预检发现授权或依赖缺口，未执行。

不得用 `INVALID` 表示电路物理失败，也不得用 `FAIL` 表示缺数据。

`SUPERSEDED` 是由新 request 的 `supersedes` 指针推导出的逻辑状态；旧 request 仍保持 `ISSUED` 原文和原签名，不回写状态。

## 4. 所有权

| 角色 | 可写 | 不可自行决定 |
|---|---|---|
| 用户 | 最终批准 | — |
| Codex | request、audit、todo、HANDOVER、ADR | 若参与核心执行，不得宣称独立审计 |
| Claude Code | ACK、实现/网表、run 产物、receipt | 最终 Gate、路线冻结、论文主张 |
| CI/校验脚本 | 机械验证输出 | 科学解释 |

执行期间 Claude 不修改 `request.yaml`、`request.sha256`、`audits/**`、`memory/project-todo.md`、`docs/HANDOVER.md` 或 `CHANGELOG.md`。若任务确实需要其中一项，由 Codex 另签发明确合同或在接受审计后更新。

## 5. Request 字段语义

- `task_id/revision/parent_todo_id/depends_on`：唯一身份和任务图位置。
- `supersedes`：可选的新合同→旧 task/revision 指针；不得通过修改旧合同表达取代关系。
- `task.objective/research_question/non_goals/claim_ceiling`：目标与最大允许主张。
- `scope.read_paths/write_paths/frozen_paths/locks`：路径授权；全部使用仓库相对路径，禁止 `..`。
- `baseline`：绑定 base commit、dirty 策略及快照。`ALLOW_NONOVERLAP` 只允许已知且与 write paths 无重叠的既有修改。
- `authorization`：编辑、JoSIM 运行、网络、安装、创建 worktree、commit、删除/覆盖的显式布尔权限。
- `contracts`：必须加载的 skills、先读文件、HANDOVER 与 metric spec 的路径/哈希/冻结状态。
- `deliverables/acceptance`：每个输出、条件和证明材料。
- `invalid_conditions`：一旦发生，产物不能用于物理判定。
- `inconclusive_conditions`：产物有效但不能区分待检验主张。
- `stop_conditions`：执行者必须停止并回报的条件。
- `issuance_blockers`：非空时 request 必须保持 `DRAFT`，不得 ACK。

`claim_ceiling` 只限制本任务能支持的最大证据层级；它不预先保证该层级会通过。

## 6. ACK 规则

ACK 必须发生在第一次编辑或运行前，并包含：request hash、观察到的 Git/dirty/scope 状态、读取完成情况、工具/依赖、预计修改路径、假设与 blocker。`decision: BLOCKED` 时不允许继续实施。

ACK 的 `created_at` 不得早于 request 的 `issued_at`；receipt 不得早于同 attempt 的 ACK；audit 不得早于同 attempt 的 receipt。写文件或补写元数据时使用当前带时区的 ISO-8601 时间，不得为了“看起来连续”回填旧时间。

如果执行中才发现 request 与仓库冲突，不修改 ACK 掩盖历史；在 receipt 记 `DEVIATED` 或 `BLOCKED`。新的尝试使用新的 attempt ID。

## 7. Receipt 规则

receipt 逐项列出实际执行产物的改变路径及角色、执行命令/退出码/日志、产物哈希、测试结果、偏离和 blocker。ACK 由 `ack_sha256` 单独绑定，receipt 自身不能自哈希，因此二者不列入 `changes[]`；除这两个协议封装文件外，任务产生的实现、测试、日志和数据不得遗漏。观察与解释分栏；物理 verdict 只能是 proposal。未运行的测试写 `NOT_RUN` 及原因，不能省略。

## 8. 审计规则

Codex 先做机械验证，再在不读取执行者解释的前提下复核实现和 raw 证据。物理任务按 `josim-evidence-audit` 检查同一 JJ、端点、方向、窗口、对照、负载和收敛。

- 执行者漏做合同要求：`REWORK_REQUIRED`。
- 产物被覆盖、缺 provenance、哈希不符或数据损坏：artifact `INVALID`、physical `NOT_APPLICABLE`，通常 `REJECTED` 或重跑。
- 预注册实验本身产生真实歧义：可 `VALID + INCONCLUSIVE + ACCEPTED`，再设计最小判别实验。
- 审计接受后才能把任务完成状态上推到 todo/HANDOVER。

## 9. Git、worktree 与并行

- 优先由 Codex/用户预先提供 `claude/<task-id>` 分支和独立 worktree，绑定 request 中的 base commit。Claude 只有在 `authorization.create_worktree: true` 时才能自行创建。
- 当前协调层未提交或 worktree 有重叠修改时，request 保持 `DRAFT`；不要靠 stash/reset 清理用户工作。
- 只有 write paths、run IDs、构建目录和锁均不重叠时才并行。
- `locks` 是 Codex 签发时检查的声明式冲突键，不是操作系统租约；v1 没有中央锁服务，执行者只能检查仓库中可见的活动 request 并在发现冲突时停止。
- M4（单位层）、M5（窗口/控制）和 M6（电压面积）存在语义依赖，不应并行签发；独立的 M12 绘图修复可在隔离路径并行。
- 不使用 `git add -A`；提交时只 stage request 授权路径。
