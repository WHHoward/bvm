# REVIEW JH-20260817-BVM-S2-SEAL-001 / A01

Review disposition: PASS
Recommended risk: NORMAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: LOW

Reviewed delivery snapshot: 无独立 snapshot commit（attempts 为未跟踪工作区状态）。审查基线 = 当前 HEAD ffcb2d48（= S2-SEAL-001 request baseline git_head）+ S2-001/run-root frozen 状态。

## Scope
PASS

Evidence:
- write_paths = `research/tasks/JH-20260817-BVM-S2-SEAL-001/attempts/**`。交付物全部位于 `attempts/A01/`。
- git status 当前 M 集与 S2-SEAL-001 签发 baseline git-status.txt 完全一致（diff 为空）——5 个 M 文件（S2-001 request/baseline、S2-SEAL-001 request/baseline/scope）均为 Codex 签发状态（mtime 15:04–15:44，早于 Claude A01 的 15:49–15:56），**非 A01 越界修改**。
- S2-001/run-root 未触碰；无 JoSIM；无科学处置。

## Acceptance criteria
- [x] AC1 — PASS — 原始 S2 request/ACK/receipt 哈希验证并绑定为 HISTORICAL_PROTOCOL_NOT_FINAL_AUTHORITY；原 verify-task 失败原因（ACK baseline.git_head 不匹配：request 96599fca vs ACK b3a467d9，且 ACK preflight 记录 request.yaml M vs HEAD）如实记录，未修复/改写任何原始文件。我独立核实该 git_head 声明准确。
- [x] AC2 — PASS — 递归枚举 run root 全部 76 个 regular 文件（48 RAW + 18 INPUT + 2 S2_RUN_ROOT_FILE(.ruff_cache) + 2 ANALYSIS_RESULT + 2 EXECUTION_TOOL + 1 ANALYSIS_TOOL + 1 CLOSURE + 1 LOG + 1 MANIFEST），逐项 path/SHA-256/bytes/layer；缺失/多余即失败。我独立验证 76/76 哈希+字节一致、path-set 精确相等。
- [x] AC3 — PASS — verify_inventory.py 重算全部哈希 + path-set 相等证明（76==76）+ 写后复查；仅写 attempts/A01/。我独立重跑字节一致（确定性）。
- [x] AC4 — PASS — receipt 哈希映射全部 successor 文件与 AC1-AC3；run_josim=false；proposed_physical_verdict NOT_APPLICABLE；已请求 Copilot review。

## Independent checks
- 我独立 SHA-256 + 字节数重算全部 76 个 run-root 文件 → 76/76 与 evidence-inventory.yaml 一致。→ PASS
- 3 条历史协议记录哈希（request/ack/receipt）→ 3/3 一致。→ PASS
- 独立 run-root 全枚举（os.walk）→ 76 live == 76 inventory；missing=[]、extra=[]。→ PASS
- verify_inventory.py 重跑 → `INVENTORY OK: 76 files (76 live == 76 inventory); 3 records; post-write OK`，输出字节一致。→ PASS
- git_head 上下文核实：S2 request baseline=96599fca…、S2 ACK observed=b3a467d9…（request.yaml M vs HEAD）、S2-SEAL-001 baseline=ffcb2d48=当前 HEAD。→ 声明准确
- request.sha256 与 request.yaml 一致（cc3496fc…）；M 集与签发基线一致。→ PASS

## Hidden-error probes
- inventory 是否遗漏 run-root 文件（递归覆盖、隐藏/缓存文件）→ 76/76 精确覆盖；.ruff_cache 2 文件亦在册（完整枚举，合理）。→ 不成立
- 哈希/字节造假或陈旧 → 独立重算 + 写后复查 + 确定性重跑三重覆盖。→ 不成立
- 历史协议绑定语义 → request/ack/receipt 标 HISTORICAL_PROTOCOL_NOT_FINAL_AUTHORITY 且注释说明原 verify 失败原因（git_head 不匹配），不掩盖、不重签。→ 不成立
- 越界修改 S2-001/run-root → M 集与签发基线一致、mtime 归属明确、git 无新改动。→ 不成立
- 科学重解释 → 无：NOT_APPLICABLE；claim ceiling 仅 provenance/inventory。→ 不成立

## Claim ceiling
PASS（provenance_and_recursive_evidence_integrity_only；无科学处置）

## Findings
### Critical
- None.

### Major
- None.

### Minor
- `.ruff_cache/` 2 个文件以默认捕获层 `S2_RUN_ROOT_FILE` 入册，但 inventory header 的层级清单（S2_EXECUTION_*/S2_ANALYSIS_*/HISTORICAL_PROTOCOL）未声明该 catch-all 层；建议 header 注明 S2_RUN_ROOT_FILE 为未识别 run-root 文件的兜底层（lint 缓存属 run-root 常规文件，完整枚举正确）。
- S2 run root 仍含 `.ruff_cache`（与 S1 已清理不同）；系既有状态，非本任务所致，可供 Codex 知悉（如需清理需单独授权）。

## Residual uncertainty
- 低：76/76 哈希+字节、3/3 历史协议、path-set 精确相等、确定性、git 边界、request 绑定全部独立验证。

## Codex focus
1. S2-SEAL-001 A01 独立验证通过（76/76 递归 inventory、3 条历史协议绑定、git_head 声明准确、确定性、无越界）。可进入 final audit，作为 S2 证据 rebinding 的索引层。
2. 知悉 Minor：.ruff_cache 入册层未在 header 声明；S2 run root 的 .ruff_cache 是否清理由你定夺（需单独授权）。
