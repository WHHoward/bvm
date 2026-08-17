# REVIEW JH-20260817-WORKFLOW-MAINT-006 / A01

Review disposition: PASS
Recommended risk: CRITICAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: LOW

Reviewed delivery snapshot: 无独立 snapshot commit（attempts 未跟踪；实现文件为工作区状态）。审查基线 = execution snapshot S=c67e85ee + MAINT-005 frozen（C01 REWORK_REQUIRED 状态）。

## Scope
PASS

Evidence:
- write_paths 覆盖实现/测试/文档/attempts（handoff.py、test_handoff.py、assets、references、scripts、2 测试、WORKFLOW/CLAUDE_EXECUTOR、execution-receipt/qas schema、attempts/**）。
- EXTERNAL_ATTESTATION：request 不含快照 SHA（非自引用）；attestation（issuer-snapshot.yaml + sha256 seal）由 issuer 创建；ACK 绑定 request+attestation 且 observed=S。
- git status：MAINT-001~005/S0/S1/S2/test-final 无修改；无 JoSIM；MAINT-006 request 绑定 a634b68e… 匹配。

## Acceptance criteria（对照 receipt AC1-AC8）
- [x] AC1 — PASS — EXTERNAL_ATTESTATION 模式：`_external_attestation_errors` 校验 attestation seal、文档 schema、task_id/revision、ACK observed==S、ACK 绑定 attestation、attestation 绑定 request/signature/scope 哈希、**S 树读 3 文件与磁盘逐字节比对**（无 normalization/语义比较）。
- [x] AC2 — PASS — legacy strict-HEAD 行为不变（回归覆盖）。
- [x] AC3 — PASS — endpoint-VI 改 Decimal 精确十进制 token（`_exact_token_index`，无 float 相等/插值/容差）。
- [x] AC4 — PASS — per-token Rhat(t)/Vth(t)/e_L(t) 独立拟合 + 冻结 descriptors（max/rms/mean）后聚合；无 pre-fit 平均。
- [x] AC5 — PASS — 对抗 fixture：`test_opposite_token_residuals_reject_average_fit`（相反残差平均抵消→e_L=0 被拒，per-token RMS 通过）。
- [x] AC6 — PASS — bundle 逐项机械校验：每项 path 校验/文件存在/sha256 重算/bytes 重算；duplicate path 拒绝；**PRE-receipt 禁止哈希最终 receipt**；12 必需 role 子集。
- [x] AC7 — PASS — receipt schema `evidence_bundle` + issuer-snapshot schema 支持 attestation。
- [x] AC8 — PASS — 合成链端到端 VERIFIED；50/50 测试；git diff --check CLEAN。

## Independent checks
- **attestation 绑定 vs S 树**：request.yaml/request.sha256/scope-files.sha256 在 S=c67e85ee 树中的哈希与 attestation 声明 3/3 MATCH。→ PASS
- **S 树 vs 当前磁盘字节一致**：3/3 byte-identical（request.yaml 8814B、request.sha256 79B、scope 585B）。→ PASS
- **非自引用**：request.yaml 不含 c67e85ee；声明 `issuer_snapshot_mode: EXTERNAL_ATTESTATION`。→ PASS
- **测试重跑**：pytest 50/50（test_handoff 35 + test/workflow 15）与 test-suite.log 一致。→ PASS
- **endpoint_vi 独立推导**：per-token 拟合 + Decimal 精确匹配 + 描述符聚合逻辑正确；docstring 已修正为 "V = Vth + Rhat*I (signed-slope)"。→ PASS
- **bundle 逐项校验**：handoff.py 740-825 行审阅——每项 sha256/bytes/path 重算、duplicate 拒绝、receipt 禁止。→ PASS
- git diff --check CLEAN；无 001-005/S0/S1/S2 修改；request 绑定匹配。→ PASS

## Hidden-error probes
- 自引用是否消除（C01#1）→ request 无快照 SHA；外部 attestation + 独立 seal 绑定 S；verifier 从 S 读文件逐字节比对，无 normalization/deletion。→ 不成立
- byte-identity 是否可被绕过 → `git show <S>:<rel>` 输出 bytes 与磁盘 `read_bytes()` 直接相等比较。→ 不成立
- bundle 逐项校验缺口（C01#2）→ 每项 sha256/bytes/path 重算 + duplicate + receipt 禁止，全部实现。→ 不成立
- docstring 符号（我 MAINT-005 Minor#1）→ 已修正为 V = Vth + Rhat*I。→ 不成立
- per-token 语义是否被平均掩盖（AC5）→ per-token 拟合 + 描述符后聚合；对抗 fixture 拒绝平均抵消。→ 不成立
- 弱 oracle → 50/50 含正负向（attestation seal/byte-drift/duplicate/receipt-forbidden/token 缺失/平均抵消/legacy）。→ 不成立
- 越界/科学证据 → 无 001-005/S0/S1/S2 修改、无 JoSIM、claim ceiling 仅基础设施。→ 不成立

## Claim ceiling
PASS（workflow and deterministic-analysis infrastructure only；无科学/历史处置主张）

## Findings
### Critical
- None.

### Major
- None.

### Minor
- 仓库根残留空调试目录 `.dbg-oiqjrbxp`（ACK 已披露，Codex 指令"不触碰 debug 目录"；清理需单独授权）。属工作区卫生问题，非本任务越界。

## Residual uncertainty
- 低：attestation 绑定 3/3、字节一致 3/3、非自引用、50/50 测试、bundle 逐项校验、docstring 修正、git 边界全部独立验证。

## Codex focus
1. MAINT-006 A01 独立验证通过（C01 三项全部闭环：外部 attestation 字节一致、bundle 逐项校验、docstring 符号；外加 Decimal per-token endpoint-VI + AC5 对抗 fixture）。可进入 final audit。
2. 知悉 Minor：`.dbg-oiqjrbxp` 空目录清理（需授权）；`_issuer_snapshot_errors`（legacy 模式）仍保留但 EXTERNAL_ATTESTATION 为当前权威路径。
