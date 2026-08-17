# REVIEW JH-20260817-BVM-S2-TIMING-SALVAGE-001 / A02

Review disposition: REWORK
Recommended risk: CRITICAL
Recommended evidence mode: FROZEN
Evidence confidence: HIGH
Residual risk: MEDIUM

Reviewed delivery snapshot: 无独立 snapshot commit（attempts 未跟踪）。审查基线 = execution snapshot S=099de6c3 + TIMING-001 frozen（含 analysis-schema.json）。

## Scope
PASS

Evidence:
- A02 全部产物在 `attempts/A02/**`；A01/TIMING-001/run root 未触碰（git 干净）；无 JoSIM；协议/schemas/memory/todo/HANDOVER 未修改。
- attestation S=099de6c3、ACK observed 一致（A02 ack 见下）。

## Acceptance criteria（对照 Codex REWORK 指令两项）
- [x] **(1) schema 修复 — PASS** — A02 analysis.json 顶层无 `salvage_attempt`（已移入 provenance 自由 object）；jsonschema 对冻结 TIMING-001 analysis-schema.json **PASS**（我独立重跑）；A01 analysis.json 复现 FAIL（"Additional properties are not allowed ('salvage_attempt')"）——缺陷与修复均确认。
- [ ] **(2) 完整 source-provenance 闭源 — FAIL（Major）** — Codex REWORK 明确要求 source-provenance 对**每个复用的 raw/input/closure/log/spec 文件**提供逐项 SHA-256+bytes（含 manifest、closure-hashes、全部 inputs 含 generator/matrix、冻结 preregistration/schema）。A02 `source-provenance.yaml` **与 A01 逐字节相同**（diff 空），仍仅含 4 raw_cases（csv/stdout/stderr）+ preregistration 路径，且 **`attempt: A01` 标签错误**（salvage_analyze.py 第 109 行硬编码 "A01"，尽管第 101 行分析 provenance 用 `salvage_attempt: "A02"`）。manifest/closure-hashes/inputs/generator/matrix/analysis-schema 的逐项哈希均缺失。
- [x] 独立重算 — PASS — A02 analysis.json 与 A01/TIMING-001 逐位一致（Δ=-0.0529515 双极性、JM2 A=0.0584342/B=0.0054827、disposition=CONSISTENT_TIMING_SENSITIVITY_SUPPORTED）。
- [x] bundle — PASS — 22 条目 22/22 哈希+bytes 与磁盘一致；不含最终 receipt；含 source-provenance 条目。
- [x] report — PASS — report.md 完整；--check CONSISTENT。
- [x] 约束 — PASS — A01/TIMING/run root 未动；无 JoSIM；无协议/memory 修改。

## Independent checks
- jsonschema.validate(A02 analysis.json, TIMING analysis-schema) → PASS；A01 → FAIL（复现）。→ PASS
- A02 source-provenance vs A01 → diff 空（**未实现**）。→ FAIL（Major）
- A02 analysis 与 A01/TIMING 逐字段对比 → 全 match。→ PASS
- bundle 22/22 独立重算；不含最终 receipt。→ PASS
- report --check + 字节一致。→ PASS
- git 边界：A01/TIMING/run root/协议/memory 均未动。→ PASS

## Hidden-error probes
- REWORK #2（完整 provenance）是否实现 → **证伪失败：A02 source-provenance.yaml 与 A01 逐字节相同**，缺 manifest/closure/inputs/generator/matrix/schema 逐项哈希，attempt 标签仍为 A01。→ 成立（Major）
- salvage_analyze.py 的 attempt 标签一致性 → 分析 provenance `salvage_attempt:"A02"`（正确）但 source-provenance writer 硬编码 `attempt:"A01"`（错误/不一致）。→ 成立（并入 Major）
- schema 修复是否真实 → jsonschema PASS（A02）/FAIL（A01 复现）。→ 不成立
- 重算是否一致 → 三方逐位一致。→ 不成立
- 越界 → A01/TIMING/run root/协议/memory 未动。→ 不成立

## Claim ceiling
PASS — disposition 有界（no-mechanism）；未涉科学处置。

## Findings
### Critical
- None.

### Major
1. **Codex REWORK #2（完整 source-provenance 闭源）未实现**：
   - A02 `attempts/A02/source-provenance.yaml` 与 A01 版本**逐字节相同**（`diff` 无差异），未增加 manifest/closure-hashes/全部 inputs（含 generate_inputs.py/matrix.txt）/冻结 preregistration/analysis-schema 的逐项 SHA-256+bytes。
   - 文件仍标 `attempt: A01`（salvage_analyze.py 第 109 行硬编码 "A01"，与分析 provenance 的 `salvage_attempt:"A02"` 不一致）。
   - 修正：扩展 salvage_analyze.py 的 source-provenance writer 以逐项哈希+bytes 覆盖全部复用源（manifest、closure-hashes、inputs/*.cir、generate_inputs.py、matrix.txt、preregistration.yaml、analysis-schema.json、A01/TIMING 的 request/design 引用），将 attempt 标签改为 A02，重新生成 A02-local source-provenance + bundle + inventory。

### Minor
- A02 source-provenance 中 stdout/stderr 路径仍可推导（哈希正确）；随 Major#1 一并完善。

## Residual uncertainty
- 低：schema 修复、重算一致性、bundle、report、git 边界全部独立验证；唯一实质缺口为 Major#1（完整 provenance 未实现，精确定位）。

## Codex focus
1. 裁决 Major#1：A02 未实现 REWORK #2 的完整 source-provenance 闭源（文件与 A01 相同、attempt 标签错误、缺 manifest/closure/inputs/generator/matrix/schema 逐项哈希）——需 executor 补全后重新交付，或另行指示。
2. 知悉：schema 修复（#1）与独立重算/bundle/report 均已验证正确；TIMING-001/A01 未触碰。
