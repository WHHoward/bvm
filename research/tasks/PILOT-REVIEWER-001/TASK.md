# TASK PILOT-REVIEWER-001

Risk: CRITICAL
Evidence mode: LITE

Task revision commit: resolve as the Git commit that first adds this TASK.md.
Execution baseline commit: same resolved Task revision commit.
Delivery snapshot owner: CODEX

## Goal

在隔离 worktree 中重新验证当前 Copilot Reviewer 的只读边界、三个最低核心 skills 的可发现性，以及 sandbox RESULT 的最小证据审查。

## Allowed paths

- `research/tasks/PILOT-REVIEWER-001/attempts/A01/REVIEW.md`
- `research/mailbox/from-copilot/**`

## Acceptance criteria

- [ ] 阅读 TASK、PILOT-REVIEWER-000 README/RESULT、当前 reviewer Agent 和三个最低核心 wrapper。
- [ ] 记录 worktree 审查前后 Git 状态，除 A01 REVIEW 外无任何改动。
- [ ] 审查 sandbox 的 scope、Preflight、claim ceiling 和无科研结论边界。
- [ ] 用可复现命令验证三个核心 wrapper 到 canonical source 的链接。
- [ ] 写 REVIEW（含 disposition、风险/模式建议、独立检查、残余不确定性、Codex focus）并 mailbox 通知 Codex。

## Stop conditions

- Observed HEAD 不等于本 TASK 的 resolved execution baseline；
- worktree 初始状态不干净；
- 必须修改 TASK、RESULT、README、实现、raw evidence 或范围外文件；
- 无法读取当前 reviewer Agent 或三个核心 wrapper。

命中时停止，写 `BLOCKED`，不得自行扩大范围。

## Claim ceiling

仅验证 Workflow-lite Pilot 0 的 Reviewer 环境与只读行为；不支持任何科研、物理或 todo 结论。
