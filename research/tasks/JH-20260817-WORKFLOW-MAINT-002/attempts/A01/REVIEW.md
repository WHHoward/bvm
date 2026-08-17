# REVIEW JH-20260817-WORKFLOW-MAINT-002 / A01

Review disposition: PASS
Recommended risk: CRITICAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: LOW

Reviewed delivery snapshot: 无独立 snapshot commit（attempts 未跟踪；实现文件为工作区修改状态）。审查基线 = baseline git_head 58909bc + MAINT-001 frozen 哈希。

## Scope
PASS

Evidence:
- write_paths 覆盖的实现文件改动：handoff.py、test_handoff.py、3 schemas、WORKFLOW.md、CLAUDE_EXECUTOR.md、scripts/、test/workflow/、attempts/**（均在内）；`delete_or_overwrite: true` 用于 15 个 .handoff-standin 清理（现 0 残留）。
- MAINT-001 request/ack/receipt 哈希未变（与 inventory 一致）；无 S0/S1/S2/test-final 修改；无 JoSIM；MAINT-002 request 绑定 32f52bf6… 匹配。

## Acceptance criteria
- [x] AC1 — PASS — `scope.hash_paths` 可选字段：`_scope_manifest_errors` 优先用 hash_paths、缺省回退 read_paths（legacy 不变）；schema 新增 `scope.hash_paths`。writable 实现文件不再要求保留执行前哈希。
- [x] AC2 — PASS — `issuer_snapshot_commit` 模式：`_issuer_snapshot_errors` 要求 ACK observed_git_head == snapshot，且 `git show <snap>:<task>/request.yaml|request.sha256|baseline/scope-files.sha256` 与磁盘字节一致；legacy strict-HEAD 不变（回归覆盖）。
- [x] AC3 — PASS — `evidence_bundle` 机械校验：bundle.path ∈ receipt artifacts 且 sha256 匹配、递归 inventory 的 12 required roles（raw/inputs/logs/manifest/spec/analyzer/verifier/structured_result/renderer/report/inventory/receipt）集合相等；`scientific_claim_ceiling` schema 仅与 mandatory contract claim_ceiling 并存。
- [x] AC4 — PASS — MAINT-001 包递归封存 13 条目（10 IMPLEMENTATION_PACKAGE + 3 HISTORICAL_PROTOCOL_SCOPE_DEFECT），001 文件未动；我独立 13/13 哈希+字节一致。
- [x] AC5 — PASS — 测试 cleanup 修复（_make_request 绝对路径）+ 15 个 standin 已删；我重跑后 0 残留。
- [x] AC6 — PASS — audit_verdict schema 新增可选 `scientific_claim_ceiling`（非推断、仅与 contract claim_ceiling 并存）。
- [x] AC7 — PASS — execution-receipt schema 新增可选 `evidence_bundle`（hashed artifact 字段）。

## Independent checks
- 我独立重跑 test_handoff.py → 9/9；test/workflow → 11/11（禁用 ROS pytest 插件后干净环境通过；与 test-suite.log 一致）。→ PASS
- verify-maintenance-evidence.py 重跑 → `SEAL OK: 13 entries (3 HISTORICAL_PROTOCOL_SCOPE_DEFECT); post-write OK`，exit 0。→ PASS
- 13 条目封存哈希+字节与磁盘逐一一致；MAINT-001 三文件哈希与 inventory 一致（未触碰）。→ PASS
- schema 对象级语义 diff（忽略格式化）：仅 4 处新增（task-request: `issuer_snapshot_commit`/`hash_paths`；receipt: `evidence_bundle`；audit: `scientific_claim_ceiling`），无删除/值变更——大行数（+1113）纯为格式化重排。→ PASS
- handoff.py diff（+71 行）：hash_paths 回退、snapshot 树字节校验、bundle 12 角色集合相等、verify_task 接线，全部聚焦且向后兼容。→ PASS
- standin 清理：重跑测试后 0 残留（cleanup 修复生效）。→ PASS

## Hidden-error probes
- hash_paths 是否只在正确分支生效（wrong-branch）→ `request["scope"].get("hash_paths")` 缺省回退 read_paths；legacy 回归测试覆盖。→ 不成立
- snapshot 校验是否可绕过（空 snapshot、错误 head）→ `if not snap: return []`（legacy）、ACK head != snap → error；负向测试 `test_issuer_snapshot_mode_rejects_wrong_snapshot`。→ 不成立
- schema 大 diff 是否掩盖语义破坏 → 对象级 diff 仅 4 处新增；无删除/放宽。→ 不成立
- evidence_bundle 校验是否弱（只查存在性）→ 校验 path∈artifacts + sha256 + 12 角色集合精确相等；测试含 missing raw/log/script 拒绝。→ 不成立
- 测试是否污染工作区（standin 泄漏）→ 0 残留；standin 为 provisional 记录流程，清理修复生效。→ 不成立
- 越界修改 S0/S1/S2/MAINT-001 → git 干净（仅 MAINT-001 未跟踪交付物与本次实现改动）。→ 不成立

## Claim ceiling
PASS（workflow and deterministic-analysis infrastructure only；无科学/历史处置主张）

## Findings
### Critical
- None.

### Major
- None.

### Minor
- schema 文件以整体格式化重排提交，使 diff 膨胀至 1100+ 行（语义仅 4 处新增）；不影响正确性，但降低可审性。建议后续维护任务避免同文件混入格式化。
- `_issuer_snapshot_errors` 依赖 `git show`（subprocess）；在无 git 或浅克隆环境下不可用（本仓库环境正常）。知悉即可。

## Residual uncertainty
- 低：代码语义 diff、schema 对象 diff、13 条目封存、测试重跑、standin 清理、git 边界、request 绑定全部独立验证。

## Codex focus
1. MAINT-002 A01 独立验证通过（AC1-AC7、9/9+11/11、13 条目封存、hash_paths/snapshot/bundle 实现正确、standin 0 残留、S0/S1/S2 未触碰）。可进入 final audit。
2. 知悉 Minor：schema 格式化重排膨胀 diff（建议后续避免）；`git show` 依赖正常环境。
