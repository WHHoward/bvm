# REVIEW JH-20260817-BVM-S2-TIMING-001 / A01

Review disposition: REWORK
Recommended risk: CRITICAL
Recommended evidence mode: FROZEN
Evidence confidence: HIGH
Residual risk: MEDIUM

Reviewed delivery snapshot: 无独立 snapshot commit（attempts 未跟踪）。审查基线 = execution snapshot S=a0577b32 + frozen preregistration。

## Scope
PASS

Evidence:
- write_paths = `test/final/bvm/runs/bvm-s2-init-timing-20260817-01/**` + `research/tasks/JH-20260817-BVM-S2-TIMING-001/attempts/**`。交付物全部在内。
- 恰 4 run（A/B × 正/负，12Ω，0.0125ps，tstop 92ps，no-read）；netlist 语义与 preregistration 完全一致（A=[9,10] S2 vs B=[10,11] S1 上升沿、公共 ±100µA plateau 至 20ps、21ps 返回、I_SE=0、无读脉冲）。
- git：S0/S1/S2/MAINT-001..007/test-final 无修改；无 JoSIM 越界；attestation S=a0577b32、ACK observed=a0577b32 一致；request 绑定 767292b1…（我未单独重算，需补核）。

## Acceptance criteria（对照 preregistration + receipt）
- [x] 实验设计 — PASS — 4 run 精确匹配 run_matrix；probes/windows/metrics/阈值/disposition 规则与 FROZEN preregistration 一致；无额外案例/扫描/读脉冲。
- [x] 数据层 — PASS — analysis.json 的 p2p/对比/disposition 与我独立 Decimal 重算逐位一致（见 Independent checks）。
- [x] 独立验证器 — PASS — verify_timing.py 只 import csv/json/pathlib/sys/decimal（不 import 分析器）；verify.log "VERIFY PASS: 4 runs, 4 windows x 2 junctions, 2 contrasts, disposition ... recomputed from raw+spec"。
- [x] 确定性报告 — FAIL（报告内容完整性）— report-consistency PASS（report.md==analysis.json 的确定性渲染），但渲染内容残缺（见 Findings Major#1）。
- [x] bundle/inventory — PASS — evidence-bundle 34 条目（12 raw+8 inputs+3 logs+2 manifest+2 spec+1 analyzer+1 receipt(receipt-pending)+1 renderer+1 report+1 structured_result+1 verifier+1 inventory）；34/34 哈希+bytes 与磁盘一致；不含最终 receipt（PRE-receipt 规则）✓；inventory.yaml 完整。
- [x] closure/binary — PASS — closure-hashes.txt 3 项（binary 48655cb3…、bvm_cell ea734654…、jjmit 19862d1f…）与 preregistration fixed_closure 一致。
- [x] claim ceiling — PASS（数据层）— analysis.json disposition=CONSISTENT_TIMING_SENSITIVITY_SUPPORTED，preregistration claim_ceiling 明确有界；无 mechanism/logical/SFQ/fluxoid/Gate/convergence 主张（report.md grep 为空亦无越界）。

## Independent checks
- 我独立从 4 个 raw CSV 用 Decimal 时间戳重算：
  - JM2 p2p [80,90)：A=0.0584342、B=0.0054827（双极性一致）→ 与 analysis.json 逐位一致
  - JM1 p2p：A=0.003528、B=0.000351 → 一致
  - ΔJM2=+0.0054827-0.0584342=-0.0529515 双极性同号、|Δ|=0.05295≥0.020；readiness 分类双极性均变（A not-ready 0.058>0.020 → B ready 0.0055≤0.020）
  - disposition=CONSISTENT_TIMING_SENSITIVITY_SUPPORTED 正确（满足两注册判据）→ PASS
- bundle 34/34 哈希+bytes 与磁盘一致 → PASS
- report --check 重跑：PASS（确定性成立）→ 但内容见 Major#1
- verify_timing.py 独立性、netlist 语义、attestation S、git 边界、closure-hashes → 全部 PASS

## Hidden-error probes
- 双极性"一致"是否隐藏符号反转 → p2p=max(P)-min(P) 极性对称（|P| 同幅振荡），正负极性 p2p 相同属预期；Δ 双极性同号且分类均变，disposition 判定正确。→ 不成立
- 是否误将 p2p 当事件/逻辑 → 仅 readiness 分类（0.020 rad 阈值），无 SFQ/event/logical 主张。→ 不成立
- Decimal 时间戳是否被 float 污染 → 独立重算用 Decimal 精确匹配，与 analysis.json 一致。→ 不成立
- 报告是否呈现结果（报告层完整性）→ **证伪失败：report.md 仅含 windows，run_id/spec_id 为 "?"，无 disposition/对比/readiness 表/有界声明**。→ 成立（Major）
- bundle 是否含最终 receipt/遗漏 → 不含最终 receipt（receipt-pending 为 pre-receipt），34/34 一致。→ 不成立
- 越界/科学证据 → 无 S0/S1/S2/MAINT 修改、无额外案例、claim ceiling 有界。→ 不成立

## Claim ceiling
PASS（数据层）：disposition 严格限于 preregistration 的有界干预效应；无机制/收敛/逻辑/硬件主张。

## Findings
### Critical
- None.

### Major
1. **报告层内容缺失（必需交付物 report.md 未呈现实验结果）**：
   - report.md 仅含 windows 列表；`run_id: ?`、`spec_id: ?`；**无 disposition、无 JM2/JM1 p2p 表、无 Δ 对比、无 readiness 分类、无有界声明**——读者仅凭 report.md 无法得知实验结果。
   - 根因：render_structured_report.py 期望 `structured.metadata.run_id/spec_id` + `metrics` + `notes`，而本实验的 analysis.json 用顶层 `run_id` + `runs/contrasts/disposition` 结构，二者 schema 不匹配 → run_id 渲染为 "?"，结果区（runs/contrasts/disposition）无对应渲染分支。
   - report-consistency PASS 仅证明"report == analysis.json 的确定性渲染"，不改变报告内容残缺的事实。
   - 修正建议：扩展 renderer（或新增本实验专用渲染分支）以渲染 run_id/spec_id、disposition、readiness 表、Δ 对比与 preregistration claim ceiling 声明，重新确定性生成 report.md 并更新 report-consistency；数据层无需重跑。

### Minor
2. mailbox 交付说明称 bundle "33 条目"，实际 34（含 receipt-pending 的 'receipt' role）；计数口径差 1，内容完整无实质影响。
3. closure-hashes.txt 仅含 3 个冻结闭源项（binary+2 netlists），非逐文件 run-root 哈希；inventory 已覆盖全部交付物，语义可接受（preregistration fixed_closure 定义如此），供知悉。

## Residual uncertainty
- 数据层残余不确定性低：p2p/Δ/disposition 独立 Decimal 重算逐位一致；唯一实质缺口为报告层（Major#1，不影响数据正确性）。request.sha256 绑定我未独立重算（据 receipt 绑定），低风险。

## Codex focus
1. 裁决 Major#1：报告层修正路线（扩展确定性 renderer 呈现 disposition/对比/readiness/claim ceiling 后重新渲染 report.md），数据层无需重跑。
2. 知悉：实验数据层（p2p、Δ、disposition）经独立验证正确；有界 claim（CONSISTENT_TIMING_SENSITIVITY_SUPPORTED）成立；S0/S1/S2/MAINT 未触碰。
