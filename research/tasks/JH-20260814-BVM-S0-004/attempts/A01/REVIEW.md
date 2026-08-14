# REVIEW JH-20260814-BVM-S0-004 / A01

Review disposition: PASS
Recommended risk: NORMAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: LOW

Reviewed delivery snapshot: 无独立 snapshot commit（A01 文件为未跟踪工作区状态；Codex 在 final audit 时创建 snapshot）。审查基线 = 当前工作区 + S0-002 封存的根工件哈希。

## Scope
PASS

Evidence:
- write_paths = `research/tasks/JH-20260814-BVM-S0-004/attempts/**` + `research/mailbox/from-claude/**`（request.yaml L56-57）。全部交付物位于 `attempts/A01/` 内；邮箱仅 REVIEW_REQUEST 通知。无越界写入。
- git status：S0-001/002/003 无任何文件被修改；唯一新增 = S0-004 交付物 + 邮箱消息。未触碰 TASK/request/baseline/源证据。
- 授权核对：`run_josim: false, delete_or_overwrite: false`；交付物中无 JoSIM 运行产物。

## Acceptance criteria
- [x] AC1 — PASS — `logs/seal-check.log`（S0-002 seal_check 重跑 PASS，59 项，我独立复核通过）+ `source-evidence-manifest.sha256`（我独立校验 24/24 条目与磁盘哈希一致）。
- [x] AC2 — PASS — `regenerate_s0_report.py` 为 stdlib-only；从 12 个 frozen CSV 用实际时间 + 注册窗口/方向独立重建 phase-area/pre/post platform/source，与 frozen analysis.json 全量比对（容差 1e-12，任何不一致 fail nonzero）。我通读脚本 1-280 行确认无复制 analysis.json 数值进报告（analysis.json 仅作比对目标）。
- [x] AC3 — PASS — `corrected-analysis.md` 由脚本从 corrected JSON 确定性渲染；包含 4 case × 3 step 全部 phase-area/pre-post/platform/source 表、controls、INCONCLUSIVE、provenance、correction note（声明旧 analysis.md retained but superseded for human-readable numeric tables）。字节级重渲染 + 篡改检测（已存在文件与确定性渲染不一致即 fail）均成立。
- [x] AC4 — PASS — `numerical_status=INCONCLUSIVE`、`evidence_quality=INCONCLUSIVE`（0.1→0.05 ps control-latency 0.85 ps > 0.5-ps band，frozen rule）。无 fixture/stimulus/window/tolerance 变更，无 interface/Gate/logical/physical PASS/FAIL 升级。
- [x] AC5 — PASS — receipt.yaml 以 SHA-256 映射全部 script/report/data/manifest/log 产物并映射 AC1-AC4；`logs/verify-task.log` = `VERIFIED research/tasks/JH-20260814-BVM-S0-004`（无 S0-002 式错误/自引用）；已通过邮箱通知 Copilot。

## Independent checks
- 独立重跑 `regenerate_s0_report.py` → exit 0，`REGENERATE/VERIFY PASSED`（重建匹配 frozen analysis.json + 字节级重渲染一致 + 已存在 md 与确定性渲染一致）。→ PASS
- 对 corrected-analysis.json 独立抽查与本人此前从 raw 的独立重算比对（此前 S0-001 Major 中的错误值）：JM1 pos_read/0.1ps phase_delta_rad=0.068792（原误报 0.108836，现已一致）、turns=0.010949、area=0.011125、resid=-0.000176；platform pos_read/0.1ps pre JM1=5.911066 / post JM1=5.910628 / pre JM2=0.316806 / post JM2=0.312313；neg_read/0.1ps JM1=-0.098687；controls ~0（±0.002 量级）。→ 全部一致
- S0-002 evidence-seal.yaml 根工件（manifest.yaml / closure-hashes.txt / analysis.json / analysis.md）磁盘哈希 vs seal → 4/4 OK。→ 旧证据未触碰
- 12 cases × 3 steps × JM1/JM2 全量一致性：由脚本内置 1e-12 比对（reconstruction_matches_frozen_json=True）+ 我独立重跑 + 跨 case/step/control 抽查覆盖。→ PASS

## Hidden-error probes
- 独立性（脚本是否复制 analysis.json 数值）→ 未复制：报告数值全部来自对 raw CSV 的重建；analysis.json 仅作比对目标。→ 不成立
- 手工编辑/非确定性（md 是否手写）→ 篡改检测 + 我独立重跑通过，交付 md 与确定性渲染逐字节一致。→ 不成立
- 数值错误复发（S0-001 Major 的 0.108836 类错误）→ 已根治：0.068792 等正确值出现在 corrected json/md 全部相关行。→ 不成立
- INCONCLUSIVE 升级为物理/Gate 结论 → numerical_status/evidence_quality 均 INCONCLUSIVE；receipt `proposed_physical_verdict: NOT_APPLICABLE`；interpretations 明确"未提升任何物理结论"。→ 不成立
- 越界/污染（改源证据、改 request、跑 JoSIM）→ git 状态干净、run_josim=false、无 JoSIM 产物。→ 不成立
- 隐藏耦合（corrected 报告被当作物理结论接受）→ 报告本身声明"仅修正报告一致性"，S0 科学 disposition 明确留待独立科学审计。→ 不成立

## Claim ceiling
PASS

TASK research_question 仅限"新 S0 报告是否与 frozen raw/analysis.json 一致且保留 INCONCLUSIVE"。RESULT/receipt 未超出此天花板：无物理/Gate/logical 主张，物理 verdict NOT_APPLICABLE。

## Findings
### Critical
- None.

### Major
- None.

### Minor
- `corrected-analysis.json` 与 `logs/*.log` 被仓库级 `.gitignore`（`*.json` L308、`*.log` L68）忽略，不入版本控制；与 S0-001/002/003 的 analysis.json/log 惯例一致，且已由哈希 + 字节级重渲染锁定。供 Codex 知悉（可选：是否对报告 .json 强制跟踪属仓库级决策，非本任务缺陷）。
- 无独立 snapshot commit（A01 文件未跟踪、工作区审查）；与 WORKFLOW-lite 流程一致（Codex final audit 时创建 snapshot）。已记录。

## Residual uncertainty
- 72 个数值中我手工独立重算的是此前出错的 pos/neg read/0.1ps 与 platform、controls 代表值；其余由脚本 1e-12 全量比对覆盖（该比对目标 analysis.json 已在上轮审查中独立验证）。残留不确定性低。
- S0 科学 disposition（INCONCLUSIVE 是否最终接受）不在本任务范围，留待 Codex final audit / User。

## Codex focus
1. S0-004 报告层一致性已独立验证 PASS；可据此进入 S0 科学审计（无需再等待本任务的报告修正）。
2. 确认是否接受"corrected-analysis.md supersedes 旧 analysis.md 的 human-readable 数值表"这一表述层级（旧文件保留为 immutable evidence）。
3. 备选知悉项：报告 .json 的 gitignore 惯例是否维持，属仓库级决策。
