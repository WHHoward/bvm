# TASK <TASK-ID>

Risk: NORMAL | CRITICAL
Evidence mode: LITE | FROZEN

Task revision commit: <commit>
Execution baseline commit: <commit>

Delivery snapshot owner: CODEX | USER | CLAUDE_EXPLICITLY_AUTHORIZED

## Goal
本任务要完成什么（一句可验收的话）。

## Allowed paths
- path/a/**
- path/b/**

## Acceptance criteria
- [ ] 条件 1
- [ ] 条件 2
- [ ] 条件 3

## Required evidence
- 测试；
- raw CSV；
- control；
- representative cases；
- figure；
- 其他必要证据。

## Stop conditions
遇到以下情况停止并报告 BLOCKED：
- baseline 不匹配（Observed HEAD ≠ Execution baseline commit，且 TASK 未允许差异）；
- scope 冲突（必须修改 allowed paths 之外文件）；
- metric / unit / window 定义存在实质歧义；
- 需要覆盖冻结/历史证据；
- 连续两次同根因失败；
- 发现可能改变研究结论的未预期异常；
- required evidence 不可获得。

## Claim ceiling
允许得出的最强结论。

例如：
Implementation verified only.
No final physical conclusion allowed.
