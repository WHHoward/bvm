# REVIEW JH-20260817-BVM-S1-002 / A02

Review disposition: PASS
Recommended risk: CRITICAL
Recommended evidence mode: FROZEN
Evidence confidence: HIGH
Residual risk: MEDIUM

Reviewed delivery snapshot: 无独立 snapshot commit（A01/A02 文件均为未跟踪工作区状态）。审查基线 = 当前工作区 + A01 frozen 证据哈希 + A02 corrected 产物。

## Scope
PASS（科学内容）/ 见 Findings #1（交付记录结构偏差）

Evidence:
- A02 仅新增：run root 的 `analysis-corrected.json/.md`、`gen_analysis_corrected.py`、`verify_analysis_corrected.py`，`attempts/A02/ack.yaml`；无 JoSIM 运行（raw 仍为 12 run-01.csv）。
- A01 frozen 未触碰：analysis.json（5232a142…）、analysis.md（9b708265…）哈希未变；closure-hashes.txt 50/50 逐项核对一致（raw/inputs/stdout/stderr/manifest 未变）。
- 无 ladder/window/band/claim-ceiling 变更；无物理/Gate/logical/SFQ/fluxoid 主张；S0 未触碰。
- 唯一越界物：run root 内 `.ruff_cache/`（16K lint 缓存，非科学产物，见 Minor#2）。

## Acceptance criteria（A02 对照 Codex REWORK 指令 codex-20260817-113205）
- [x] (1) 同脚本确定性生成 corrected JSON+MD，修正 neg:I 05→025 pointwise PASS/band floor 标签 → gen_analysis_corrected.py 单脚本生成两者；我独立重跑字节一致（sha256 前后相同，exit 0）。
- [x] (2) 全部注册 control 观测 + 1%/0.2% bands → control RMS/time-normalized L1/pair max/RMS + control-corrected source waveforms（exact common timestamps）+ control-corrected act deltas 均在 corrected JSON；全部 chk PASS（我独立抽查 12 case-step-col 全 PASS）。
- [x] (3) 负读 FWHM 双侧半高穿越 ≈1.07 ps + 终点措辞修正 → corrected md §4 报告 1.073/1.067/1.066 ps（与我独立重算一致）；§1 措辞改为"末样本 169.95/169.975/169.9875 ps，窗口止于 150 ps 完整覆盖"。
- [x] (4) 独立 raw recomputation 证明 → verify_analysis_corrected.py（不 import 生成器）13/13 PASS（含 A01 三个哈希断言）；我另行独立重算 corrected JSON 关键值（neg:I pw/band、FWHM、control max/rms/l1n、platforms）全部一致。
- [x] (5) verdict 不变 → VALID artifact + numerical INCONCLUSIVE，6 个注册 pair fails 与 A01 完全一致；无新物理/Gate 解释。
- [ ] (指令"A02日志" + 标准 attempt receipt) → 见 Findings #1：A02 目录仅有 ack.yaml；无 A02 命令日志、无 A02 receipt；A01 receipt 于 11:40 被追溯修改绑定 A02 产物；verify-task-final 重跑显示 2 ACK + 1 receipt VERIFIED。

## Independent checks
- 独立重跑 `gen_analysis_corrected.py` → exit 0，输出与交付物字节一致（确定性成立）。→ PASS
- 交付验证器 `verify_analysis_corrected.py` → 13/13 PASS。→ PASS
- 我独立从 raw 重算（不调用生成器/验证器）：neg:I 05→025 pw=0.4952≤0.50（chk_pw=True）且 chk_rms=False（verdict 不变）；FWHM pos 6.6681/6.6534/6.6502、neg 1.0730/1.0671/1.0658（与我此前独立重算一致）；control max≈12 nV/RMS≈4 nV/L1n≈3.8e-6 全部 ≤band；platforms 保留（与 A01 json 一致）。→ PASS
- A01 完整性：analysis.json/analysis.md/closure-hashes 50/50 哈希未变。→ PASS
- 无第四 timestep、无新 raw、无 interpolation/resampling/time alignment（generator 仅用 exact-decimal 时间戳）。→ PASS

## Hidden-error probes
- corrected 报告是否仍含 A01 表格错误 → 已根治：neg:I 05→025 pointwise PASS（band 0.50）、neg 行 band 全部 floor-limited（5.00/1.00/0.50/0.10）。→ 不成立
- control 观测是否真正补齐且正确 → 已补齐：RMS/L1/pair + bands 全 PASS；control-corrected waveforms/deltas 存在；我独立重算 L1n 与 json 一致。→ 不成立
- 负读 FWHM 是否仍称"无 crossing" → 已修正：报告 ≈1.07 ps（双侧半高穿越）。→ 不成立
- verdict/claim ceiling 是否被改动 → 未变：INCONCLUSIVE + 6 fails；无物理/Gate 升级。→ 不成立
- A01 是否被污染 → 未变（哈希 + closure 50/50 + 无新 raw）。→ 不成立
- 生成器是否隐藏非确定性/篡改 → 重跑字节一致；无隐藏路径。→ 不成立

## Claim ceiling
PASS

corrected 报告保持 A01 的 bounded claim（VALID + INCONCLUSIVE）；无新物理/Gate/logical 解释；S0/C02 未改动。

## Findings
### Critical
- None.

### Major
1. **A02 交付记录结构偏离 Codex 指令与 handoff 协议**（过程/溯源，不影响科学正确性）：
   - Codex 指令明确要求"A02日志"；但 attempts/A02 仅有 `ack.yaml`，无 A02 命令日志（gen/verify 运行日志）、无独立 A02 receipt。
   - A01 的 `receipt.yaml` 于 11:40:03 被追溯修改以绑定 A02 产物（changes/artifacts 段混入 A02-gen/verify/json/md），A01 记录不再 pristine；receipt `commands:` 段仍只有 A01 三条命令，无 A02 命令条目。
   - verify-task-final.log 于 11:40:10 重跑显示 `2 ACK, 1 receipt, 0 audit / VERIFIED`（即合并后的单 receipt）。
   - 缓解：A02 全部产物已在（修改后的）receipt 中以 SHA-256 绑定；verify-task VERIFIED；A02 ack.yaml 规范（含 planned_commands/expected_changed_paths）；科学内容经我独立验证完全正确。
   - 需 Codex 裁决：接受"合并 receipt + 缺失 A02 日志"安排，或要求补 A02 receipt/logs（属 executor 补记动作）。

### Minor
2. **run root 内 `.ruff_cache/`**（16K lint 缓存）——不可变 run root 内的非科学污染；建议清除（需授权）或后续任务处理。
3. **正读 FWHM 定义变更未显式标注**：A01 报 5.900/5.892/5.890 ps（filtered-crossing 定义），A02 改标准双侧半高定义后报 6.668/6.653/6.650 ps。新定义更标准且 pair 差判据仍通过（0.0147/0.0033 ps ≤0.25），但 corrected md 只说明负读 FWHM 修复，未提示正读 FWHM 数值亦因定义变更而变化；跨报告对比时需知悉。
4. **corrected 生成器 verdict 逻辑未将 control chk 接入 fails**：verdict 仅检查 readiness/timestamp/adjacent-pair；control chk（max/rms/l1/pair）虽全部计算并报告且当前全 PASS，但若某 control band 失败不会进入 verdict.fails。属潜在健壮性缺口，当前数据无影响。
5. **corrected md §3 中 0.025ps 的 control pair 显示 05_to_025**（渲染逻辑取相邻粗对）；定义性选择，control 全 PASS 无影响。
6. **AC5 platform 表仍未入 md**：corrected md 将 platforms/deltas/areas 委托给 JSON（数据在 json 中，与 A01 一致）；与 A01 Minor#6 相同，可接受。

## Residual uncertainty
- A02 无命令日志 → 无法从日志复核 gen/verify 的确切执行，但已由"重跑字节一致 + 验证器 13/13 + 我的独立重算"三重覆盖，残余不确定性低。
- 正读 FWHM 定义变更（5.90→6.67 ps）跨报告差异（Minor#3）需 Codex/读者知悉；不涉验收（pair 差判据两定义均通过）。

## Codex focus
1. 裁决 Findings #1（Major，过程/溯源）：A01 receipt 被追溯修改 + A02 缺独立 receipt/日志 + Codex 指令"A02日志"未满足——接受合并安排还是要求补 A02 记录。科学内容已独立验证正确，无需重跑/重算。
2. 知悉：A01 的 3 Major + 3 Minor 已全部正确闭环；corrected 报告确定性、与 raw/json 一致、verdict 不变。
3. 可选知悉：正读 FWHM 定义变更（Minor#3）与 .ruff_cache 污染（Minor#2）是否需处理。
