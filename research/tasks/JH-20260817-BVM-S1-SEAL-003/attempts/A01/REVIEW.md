# REVIEW JH-20260817-BVM-S1-SEAL-003 / A01

Review disposition: REWORK
Recommended risk: NORMAL
Recommended evidence mode: LITE
Evidence confidence: HIGH
Residual risk: MEDIUM

Reviewed delivery snapshot: 无独立 snapshot commit（SEAL-003 attempts 为未跟踪工作区状态）。审查基线 = 当前工作区 + S1-002/SEAL-002 frozen 哈希。

## Scope
PASS（未触碰任何 S1-002/SEAL-002/run-root 文件）

Evidence:
- write_paths = `research/tasks/JH-20260817-BVM-S1-SEAL-003/attempts/**`。交付物全部位于 `attempts/A01/`。
- git status 无 tracked 修改；S1-002 analysis.json/md 哈希未变；SEAL-002 文件未变；无 JoSIM。
- 未删除/重命名/改写任何历史产物。

## Acceptance criteria
- [x] AC1 — PASS — 无 JoSIM；仅新增 SEAL-003 attempts/**；S1-002/SEAL-002/run-root 未修改。
- [ ] AC2 — FAIL — seal 列出 79 条且 79/79 哈希与磁盘一致、closure 50/50 交叉一致，但**未列举全部保留的 run-root source file**：`analyze_s1.py`（A01 分析生成器，analysis.md Reproduction 明确引用 "python3 analyze_s1.py # -> analysis.json"）未封存。Codex 指令要求 "must enumerate every retained run-root source file"，seal_check.py docstring 亦自称 "enumerates EVERY retained run-root source file"——不属实。
- [x] AC3 — PASS — 四层权威分离正确：A01_RAW（55，含 logs-tmp-gen.txt 标注为 input-generation/execution provenance，非仿真观测）、A01_HISTORICAL（9）、A02_CORRECTED（9）、SEAL002_HISTORICAL（6）。
- [x] AC4 — PASS — 逐条目 authority 映射正确；SEAL-002 已接受 seal 作为历史层；无历史产物被删除或标为缺失。
- [x] AC5 — PASS — receipt 有自身 A01 timestamp/commands/logs，哈希映射 D1-D3 与 AC1-AC4；verify-task 成功。

## Independent checks
- 独立 SHA-256 重算全部 79 条目 → 79/79 与 evidence-seal.yaml 一致。→ PASS
- 完整 run-root 覆盖检查（62 个磁盘文件 vs seal）→ **`analyze_s1.py` 为唯一未封存文件**。→ FAIL（Major）
- closure-hashes 50/50 交叉一致；无遗漏/无不匹配。→ PASS
- seal_check.py 重跑字节一致（确定性）+ 写后篡改校验通过。→ PASS
- logs-tmp-gen.txt 内容与 A01 gen-inputs.log 逐字节相同（均 hash 57bad5eb…；同一确定性 stdout 双份捕获），标签 A01_RAW_EXECUTION 合理。→ PASS
- request.sha256 与 request.yaml 一致（cebba0277…）。→ PASS

## Hidden-error probes
- run-root 是否有未封存文件（Claude 建议审查点 #1）→ **证伪失败：`analyze_s1.py` 未封存**（SEAL-002 亦遗漏，本次继承）。→ 成立（Major）
- 四层权威标注是否准确（#2）→ 正确：55/9/9/6，logs-tmp-gen.txt 标签与 SEAL-002 历史层合理。→ 不成立
- logs-tmp-gen.txt 与 A01 gen-inputs.log 一致性（#3）→ 逐字节相同（同确定性 stdout），合理。→ 不成立
- 哈希造假/陈旧 → 79/79 独立重算 + closure 50/50 + 确定性重跑 + 写后篡改校验。→ 不成立
- 越界写入/修改 S1 → git 干净、哈希未变、seal_check 只读。→ 不成立
- 科学重解释 → 无：proposed_physical_verdict NOT_APPLICABLE。→ 不成立

## Claim ceiling
PASS（未涉科学处置；seal 仅 provenance）

## Findings
### Critical
- None.

### Major
1. **`analyze_s1.py` 未封存 — seal 仍不完整**：
   - 磁盘 run-root 共 62 个文件；seal 79 条目覆盖 61 个 run-root 文件 + 18 个 attempts/SEAL-002 文件；**`test/final/bvm/runs/bvm-s1-canonical-20260817-01/analyze_s1.py`（SHA-256 e2c6a5204dbd8d53…）是唯一未封存的 run-root source file**。
   - 该文件是 A01 分析生成器（产出 analysis.json），在 analysis.md §7 Reproduction 中被明确引用；属 Codex 指令"every retained run-root source file"与 SEAL-003 目标"complete seal"范围。
   - seal_check.py `entries()` 显式枚举了 gen_inputs.py/run_all.sh 但遗漏 analyze_s1.py；docstring "enumerates EVERY retained run-root source file" 与 seal-check.log 的 "SEAL OK" 均未反映该遗漏（closure-hashes.txt 不含脚本，交叉验证无法捕获）。
   - 这正是 SEAL-003 被签发要修复的缺陷类别（遗漏 run-root 文件：前次为 logs-tmp-gen.txt），本次以 analyze_s1.py 形式复发。
   - 修正建议：在 seal_check.py `entries()` 增加 `e['analyze_s1.py'] = 'A01_HISTORICAL'`（与 gen_analysis_corrected.py=A02_CORRECTED 对称；或按 gen_inputs.py/run_all.sh 归 A01_RAW_EXECUTION，由 executor/Codex 定夺），重新生成 evidence-seal.yaml（80 条目）、重跑 seal-check、更新 receipt 与 verify-task。

### Minor
2. **SEAL-002 同样遗漏 analyze_s1.py**（72 条目亦无此文件）；我在 SEAL-002 审查（PASS）中未捕获——当时只做了 seal→closure 方向覆盖（closure-hashes 不含脚本，故无法发现），未做 run-root→seal 完整覆盖。作为审查方法教训记录：封存审查必须做"磁盘 run-root 全枚举 vs seal"反向覆盖。
3. **logs-tmp-gen.txt 与 A01 gen-inputs.log 内容逐字节相同**（同 hash 57bad5eb…，确定性 stdout 双份捕获）；合理但建议在 seal 注释中说明两文件内容一致以防误读为独立日志。

## Residual uncertainty
- 低：79/79 哈希、closure 50/50、确定性、四层标注均独立验证；唯一实质性缺口即 analyze_s1.py 未封存（已精确定位并给出修正）。

## Codex focus
1. 裁决 Major#1：要求 executor 在 seal 中补封 analyze_s1.py（80 条目），或明确接受"analyze_s1.py 不作封存范围"（与 SEAL-003 目标/指令冲突，不建议）。
2. 知悉 Minor#2：SEAL-002 审查亦遗漏 analyze_s1.py——后续封存类审查我将加入 run-root→seal 反向覆盖检查。
3. 除 analyze_s1.py 外，seal 其余部分（79 条目哈希、四层权威、logs-tmp-gen 标签、确定性）独立验证全部正确。
