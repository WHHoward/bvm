# RESULT <TASK-ID> / Axx

execution_status: COMPLETED | BLOCKED | DEVIATED
executor_artifact_assessment: VALID | INVALID | NOT_AUDITED
proposed_physical_verdict: PASS | FAIL | INCONCLUSIVE | NOT_APPLICABLE

## Preflight
<最先写入的不可变块，不得回填重写；错误用追加 correction note>

Task revision commit: ...
Execution baseline commit: ...
Observed HEAD: ...
Branch/worktree: ...
Git status:
  <git status --porcelain=v1 --untracked-files=all 输出或简明摘要>
Allowed paths: understood
Risk: NORMAL | CRITICAL
Evidence mode: LITE | FROZEN
Claim ceiling: understood
Ambiguity: none | <说明>
Preflight result: PASS | BLOCKED

## Summary
完成了什么。

## Changes
- ...

## Verification
- command → PASS / FAIL
- command → PASS / FAIL

## Evidence
- raw evidence path
- run id
- representative case
- control
- key numeric outputs
- SHA-256 when required (CRITICAL+LITE 关键输入/输出)

## Changed files
- ...

## Limitations / anomalies
- ...

## Claim
实际结果支持的结论。必须位于 TASK claim ceiling 内。

---

## Delivery snapshot（RESULT 完成后由授权 owner 追加）

Delivery snapshot commit: <commit>
Snapshot owner: <role>（LITE Scientific Implementation 默认 EXECUTOR）
Snapshot scope check: PASS
Snapshot binding:
  task_id: <task-id>
  attempt_id: <attempt-id>
  base_commit: <baseline>
  result_path: <attempt RESULT path>
  changed_paths: <allowed paths in snapshot>
