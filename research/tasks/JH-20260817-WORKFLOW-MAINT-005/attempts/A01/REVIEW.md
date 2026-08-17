# REVIEW JH-20260817-WORKFLOW-MAINT-005 / A01

Review disposition: PASS
Recommended risk: CRITICAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: LOW

Reviewed delivery snapshot: 无独立 snapshot commit（attempts 未跟踪；实现文件为工作区状态）。审查基线 = baseline git_head 9ae2b1f0 + MAINT-004 BLOCKED 交付哈希。

## Scope
PASS

Evidence:
- write_paths 覆盖全部实现/测试/文档/attempts（handoff.py、test_handoff.py、quantitative_analysis_verifier.py、build_evidence_bundle.py、2 测试文件、WORKFLOW.md、CLAUDE_EXECUTOR.md、quantitative-analysis-spec.schema.json、handoff-protocol.md、execution-receipt.yaml asset、attempts/**）。
- **hash_paths 修复验证**：恰为 3 个冻结输入（AGENTS.md、docs/HANDOVER.md、docs/research/METRIC_SPEC_V2.md），与 write_paths **零重叠**（MAINT-004 的"hash_paths 覆盖全部 writable 源"缺陷已解除）。
- git status：MAINT-001~004/S0/S1/S2/test-final 无修改；无 JoSIM；MAINT-005 request 绑定 0f7986e3… 匹配。

## Acceptance criteria（对照 receipt AC1-AC7）
- [x] AC1 — PASS — issuer-snapshot 模式：ACK observed_git_head == snapshot 执行权威；legacy no-snapshot strict-HEAD 不变（回归覆盖）。
- [x] AC2 — PASS — 真实 git 对象 positive/negative 回归（test_real_snapshot_positive_with_parent_different_head / test_snapshot_byte_drift_fails / test_legacy_strict_head_still_required，用真实 HEAD=58909bc）。
- [x] AC3 — PASS — endpoint-VI verifier：`affine_residual` kind 被 schema 拒绝；V-I 仿射用端点载荷同时刻精确 token；无插值/重采样。
- [x] AC4 — PASS — Rhat/Vth/e_L 从精确 token 计算；cross-run token 缺失拒绝；e_L 独立载荷插值值被拒。
- [x] AC5 — PASS — multi-entry 递归 pre-receipt bundle：path-set/hash/byte 机械重算（多 role 条目、目录递归展开、篡改文件机械检测）。
- [x] AC6 — PASS — stale 文档修正 + scientific_claim_ceiling 措辞。
- [x] AC7 — PASS — 合成 CRITICAL/FROZEN 链端到端 VERIFIED（test_synthetic_chain_verifies_end_to_end）。

## Independent checks
- **零代码变更声明**：当前磁盘 7 个实现文件（handoff.py/test_handoff.py/verifier/bundler/2 测试/qas-schema）SHA-256 与 MAINT-004 BLOCKED receipt 记录 7/7 一致。→ PASS
- **测试重跑**：pytest 40/40（test_handoff 25 + test/workflow 15，PYTEST_DISABLE_PLUGIN_AUTOLOAD=1）→ 与 test-suite.log 一致。→ PASS
- git diff --check CLEAN；无 001-004/S0/S1/S2 修改；request 绑定匹配。→ PASS
- endpoint_vi 独立推导：fixture 点（V,I）严格共线于 V=Vth+Rhat·I（Rhat=-20,Vth=2e-3），代码 rhat/vth/e_L 计算与测试期望逐位一致。→ PASS
- hash_paths 3 冻结输入与 write_paths 零重叠（python 解析 request 验证）。→ PASS

## Hidden-error probes
- 符号约定是否内部自洽（endpoint_vi）→ 代码+测试自洽：V = Vth + Rhat·I，Rhat=有符号斜率（源为负）；e_L=最坏 |V−(Vth+Rhat·I)|。**但 docstring 写 `Vth - Rhat*I` 与代码 `vth + rhat*i` 不一致**（见 Findings Minor#1）。→ 部分成立（文档层）
- 零代码变更是否属实（004→005 隐藏重写）→ 7/7 哈希逐字节一致，无隐藏变更。→ 不成立
- hash_paths 修复是否真解除冻结冲突 → 3 冻结输入零重叠 write_paths。→ 不成立
- 插值/重采样是否混入 → spec 强制 interpolation=prohibited + 精确 token 零容差 + 负向测试。→ 不成立
- 测试是否弱 oracle → 40/40 含正负向（错 Phi0/符号/阈值/插值/affine 拒绝/token 缺失/篡改/字节漂移/legacy）。→ 不成立
- 越界/科学证据 → 无 JoSIM、无 001-004/S0/S1/S2 修改、claim ceiling 仅基础设施。→ 不成立

## Claim ceiling
PASS（workflow and deterministic-analysis infrastructure only；无科学/历史处置主张）

## Findings
### Critical
- None.

### Major
- None.

### Minor
1. **`endpoint_vi` docstring 与代码公式不一致**（`scripts/quantitative_analysis_verifier.py`）：docstring 称 "e_L is the worst |V - (Vth - Rhat*I)|"，但代码计算 `vth + rhat * i`（模型 V = Vth + Rhat·I，Rhat=有符号 dV/dI 斜率，测试 fixture RHAT=-20 证实）。代码+测试自洽且无计算错误；docstring 为陈旧/误导表述，建议改为 `Vth + Rhat*I`，并可在 spec schema 的 endpoint_vi 段补充符号约定说明（Rhat 为有符号斜率而非 Thevenin 电阻）以防 spec 作者误配正号。
2. （知悉）`_exact_token_time` 用 `raw['time'].index(t)` 线性查找；正确性无虞，大数据量下性能可忽略。
3. **`memory/bvm-chain-status-20260817.md` 在 MAINT-005 窗口内被更新**（mtime 20:21:43，不在 write_paths 内）——为项目状态记忆文件（会话机制维护，diff 为 MAINT-004 BLOCKED→MAINT-005 VERIFIED 事实状态条目，非科学/协议产物）；非数据或协议问题，供 Codex 知悉。

## Residual uncertainty
- 低：零代码变更 7/7 哈希、40/40 测试、hash_paths 零重叠、endpoint_vi 独立推导、git 边界、request 绑定全部独立验证；唯一残余为 docstring 文档表述（Minor#1）。

## Codex focus
1. MAINT-005 A01 独立验证通过（7/7 零代码变更、40/40 测试、hash_paths 修复、AC1-AC7 全部支持、无越界）。可进入 final audit。
2. 裁决 Minor#1：endpoint_vi docstring 公式修正（`Vth - Rhat*I` → `Vth + Rhat*I`）与 spec 符号约定说明——可选修正轮或接受为知悉项（不影响计算正确性）。
