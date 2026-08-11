# TASK PILOT-REVIEWER-000

Risk: CRITICAL
Evidence mode: LITE

Task revision commit: the Git commit that first adds this `TASK.md`; resolve with `git log --diff-filter=A --format=%H -- research/tasks/PILOT-REVIEWER-000/TASK.md | tail -n 1`.
Execution baseline commit: same as the resolved Task revision commit.

Delivery snapshot owner: CODEX

## Goal

验证 Copilot `reviewer` Agent 在真实仓库中能以只读方式审查既有 sandbox RESULT，并且只新增当前 attempt 的 `REVIEW.md`，不触碰实现、TASK、RESULT、原始证据或无关文件。

## Allowed paths

- `research/tasks/PILOT-REVIEWER-000/attempts/A01/REVIEW.md`
- `research/mailbox/from-copilot/**`

## Acceptance criteria

- [ ] Reviewer 明确读取本 TASK、`README.md`、A01 `RESULT.md` 与 `.github/agents/reviewer.agent.md`。
- [ ] REVIEW 记录审查前/后的 `git status --porcelain=v1 --untracked-files=all`，并说明差异仅为本 attempt 的 `REVIEW.md`。
- [ ] REVIEW 至少检查 RESULT 的 scope、claim ceiling、Preflight 格式和“无科学结论”的边界；不把 sandbox 当作研究任务或物理证据。
- [ ] REVIEW 对 Reviewer 配置和至少一个 canonical skill wrapper 的可发现性给出可复现命令与结果。
- [ ] REVIEW 明确 `PASS`、`REWORK` 或 `BLOCKED`，并列出 residual uncertainty；完成后经 mailbox 通知 Codex。

## Required evidence

- `research/tasks/PILOT-REVIEWER-000/attempts/A01/REVIEW.md`
- REVIEW 中记录的只读命令、退出码/结果与 Git 状态对比。
- 一封关联本 task ID 的 Copilot→Codex mailbox 消息。

## Stop conditions

- 当前 Git HEAD 不等于本 TASK 的 resolved execution baseline；
- 工作树在 Reviewer 开始前已存在无法归属的 dirty 文件；
- 无法确认 `reviewer` Agent、其 skills 或尝试目录；
- 为完成验证必须修改 TASK、RESULT、README、实现、raw evidence 或仓库范围外文件；
- 执行任何验证会覆盖、删除或重写已有证据。

命中任一条件时，停止并写 `Review disposition: BLOCKED`；不得自行扩大范围。

## Claim ceiling

Workflow-lite Reviewer 环境与只读边界的**一次 sandbox 验证**。不支持任何 JoSIM、电路、计量、SFQ、物理 Gate、todo 完成或研究路线结论。
