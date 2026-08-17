# REVIEW JH-20260817-WORKFLOW-MAINT-003 / A01

Review disposition: PASS
Recommended risk: CRITICAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: LOW

Reviewed delivery snapshot: 无独立 snapshot commit（attempts 未跟踪；实现文件为工作区修改状态）。审查基线 = baseline git_head 58909bc + MAINT-001/002 frozen 哈希。

## Scope
PASS

Evidence:
- write_paths 覆盖：handoff.py、test_handoff.py、execution-receipt.yaml asset、handoff-protocol.md、WORKFLOW.md、CLAUDE_EXECUTOR.md、attempts/**（均在内）。
- git status：MAINT-001/002 无修改（无 M/D/R）；S0/S1/S2/test-final 未触碰；无 JoSIM；MAINT-003 request 绑定 4426b221… 匹配。
- MAINT-003 使用 MAINT-002 引入的 `hash_paths`（18 个历史文件只读哈希），机制验证正常。

## Acceptance criteria（对照 receipt AC1-AC5）
- [x] AC1 — PASS — verify-task 对必需 deliverable 覆盖改为 task-wide union（`_task_deliverable_errors`）：非 RECEIPT-role 用各 receipt artifacts 路径 union 匹配模式；RECEIPT-role（如 attempts/**/receipt.yaml）用 canonical receipt 路径匹配；单 attempt 即自身 union，legacy 行为不变。
- [x] AC2 — PASS — acceptance-ID 覆盖改为 task-wide union（`_task_acceptance_errors`）；per-receipt `_acceptance_mapping_errors` 保留 duplicate/unknown-ID 校验（不再查 required 覆盖，避免多 attempt 拆分时误报）。
- [x] AC3 — PASS — 回归：test_handoff.py 15/15（pytest + unittest 双模式，我重跑均 15/15 OK）；新增 MultiAttemptAggregationTests 6 项（union 通过 / 缺 deliverable / 缺 acceptance / unknown ID / duplicate ID / 单 attempt legacy 全覆盖）。
- [x] AC4 — PASS — evidence-inventory.yaml 20 条目（13 HISTORICAL_PROTOCOL_MULTI_ATTEMPT_DEFECT [001 4 条 + 002 9 条血缘文件] + 6 IMPLEMENTATION_PACKAGE [003 自身 handoff.py/test/协议文档/asset] + 1 OUTPUT_LOG [test-suite.log]）；20/20 哈希+字节与磁盘一致；001/002 文件未动。
- [x] AC5 — PASS — 协议文档同步（handoff-protocol.md §7 / WORKFLOW.md §8.5 / CLAUDE_EXECUTOR.md / execution-receipt.yaml asset 均含 multi-attempt/task-wide/union）；verify-task 最终 VERIFIED；git diff --check CLEAN。

## Independent checks
- 我独立重跑 pytest → 15/15；unittest（模块名调用）→ 15/15 OK。→ PASS
- 20 条目封存哈希+字节逐一与磁盘一致（13 历史 + 6 实现 + 1 日志）。→ PASS
- handoff.py 聚合函数逐行审阅：per-receipt 校验（bindings/scope/artifact/duplicate/unknown）保留；task-wide union 接线于 verify_task（receipts 非空时执行）。→ PASS
- 聚合语义单 attempt 等价性：union=单 receipt → deliverable/acceptance 覆盖与旧版一致（回归覆盖）。→ PASS
- git diff --check CLEAN；无 001/002 修改；无 S0/S1/S2 触碰。→ PASS
- MAINT-003 request.sha256 与 request.yaml 一致（4426b221…）。→ PASS

## Hidden-error probes
- 聚合是否破坏 per-receipt 完整性（over-union 掩盖缺失）→ per-receipt hash/scope/artifact/bindings 校验全部保留（代码审阅确认）；union 仅放宽 deliverable/acceptance 覆盖。→ 不成立
- RECEIPT-role deliverable 是否被绕过（任意 receipt 路径即满足）→ 需 canonical receipt 路径匹配模式（attempts/**/receipt.yaml）；duplicate/unknown 仍拒。→ 不成立
- 单 attempt 是否行为漂移 → `test_single_attempt_keeps_legacy_full_coverage_rule` 覆盖；union=单 receipt 逻辑等价。→ 不成立
- 测试是否为弱 oracle → 6 项含 2 正 + 4 负/边界（缺 deliverable、缺 acceptance、unknown、duplicate），真实构造两 attempt 任务树。→ 不成立
- 001/002 是否被改写或重签 → git 无修改、封存 20/20 与磁盘一致（含 001/002 历史文件）。→ 不成立
- 越界/科学证据 → 无 JoSIM、无 S0/S1/S2 触碰、claim ceiling 仅基础设施。→ 不成立

## Claim ceiling
PASS（workflow and deterministic-analysis infrastructure only；无科学/历史处置主张）

## Findings
### Critical
- None.

### Major
- None.

### Minor
- 邮箱交付说明称"封存 13 个 001/002 历史血缘文件"，实际 inventory 共 20 条目（13 历史 + 6 自身实现 + 1 日志）；inventory 内容完整且层级清楚，仅为表述口径（13 指历史子集），无实质影响。

## Residual uncertainty
- 低：聚合实现逐行审阅、双模式测试重跑、20 条目封存、git 边界、diff 干净、文档同步全部独立验证。

## Codex focus
1. MAINT-003 A01 独立验证通过（task-wide union 聚合正确、per-receipt 校验保留、15/15 双模式、20 条目封存、无 001/002 修改、S0/S1/S2 未触碰）。可进入 final audit。
2. 知悉 Minor：inventory 总条目 20（13 历史 + 7 自身），邮箱表述仅指历史子集。
