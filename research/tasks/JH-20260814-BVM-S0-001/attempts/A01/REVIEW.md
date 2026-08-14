# REVIEW JH-20260814-BVM-S0-001 / A01（科学证据审查）

Review disposition: **REWORK**
Recommended risk: CRITICAL
Recommended evidence mode: FROZEN
Evidence confidence: HIGH（raw 与 analysis.json）
Residual risk: MEDIUM

Reviewed snapshot: `8372856`（descendant `5acc00d`）；封存链 S0-002（evidence-seal 59 项）与 S0-003（RESEALED_ONLY）已核，本审查聚焦 S0-001 的**科学内容**。

## Scope
PASS

- read-only；仅新增本 REVIEW.md；
- 未修改任何 task/source/raw/analysis/authority；
- 审查对象：S0-001 request/design/receipt、`analyze_s0.py`、`analysis.json`、`analysis.md`、12 个 raw CSV、manifest、closure-hashes。

## 科学核心：独立验证通过的项目（数据层全部正确）

- **控制匹配**：read/control 网表 diff 仅读脉冲幅度（WL/SE 96-105 ps +100 µA → 0）与注释行；其余逐字节一致 ✅
- **初始化**：pos/neg 网表 diff 仅 WL/BL 初始化极性（+100U vs −100U）✅
- **时间步**：0.1/0.05/0.025 网表 diff 仅 `.tran` ✅
- **探针方向/同 JJ 映射**：`B_JM1 N1→n_jm1o`、`B_JM2 n_jm2i→N2`、`V(SL1) SL1→0`、`L_SL N8→SL1`（bvm_cell.cir 核验）；`vts=+1, rd=+1` ✅
- **75-ps readiness 使用**：读脉冲 96-106 ps（设计输入，仅作为设计依据，未转移 D0 结论）✅
- **Pre-window admissibility [80,90)**：独立重算 JM1 p2p=0.00039、JM2 p2p=0.00655、pos/neg L-inf=11.8221，全部满足带 ✅
- **源波形 [94,130)**：独立重算 V(SL1) 峰值 0.890 mV（101 ps）、latency 5.0 ps、FWHM 1.4 ps；I(L_SL) 74.18/75.06/75.30 µA（0.1/0.05/0.025 ps）、latency 5.00/5.00/5.02 ps——与 analysis.json **逐位一致** ✅
- **控制噪声级**：独立重算 V(SL1) 峰值 ~17.9/15.5 nV（0.1/0.05 ps）✅
- **收敛 INCONCLUSIVE**：独立确认 control 峰值延迟 0.1ps=−0.70 ps、0.05ps=+0.15 ps，差 **0.85 ps > 0.5 ps 带**（粗对 FAIL）；0.05→0.025 PASS；numerical_status=INCONCLUSIVE ✅
- **evidence_quality=INCONCLUSIVE**、无 receiver/Gate/逻辑/route 结论，claim ceiling 合规 ✅
- **QA**：12 run exit 0、stderr 空、样本数 1699/3399/6799、列齐备 ✅

## Findings

### Critical
- None.

### Major
- **`analysis.md`（封存交付物 D5）的 "Observed" 表格数值与 `analysis.json`（D4）及 raw CSV 不一致。**

  具体（`init_positive_read / 0.1 ps`）：
  | 量 | analysis.md（L92/L122） | analysis.json / raw（独立重算） |
  |---|---|---|
  | JM1 phase_delta_rad | +0.108836 | **+0.068792** |
  | JM1 phase_delta_turns | +0.017322 | **+0.010949** |
  | JM1 area_turns | +0.017312 | **+0.011125** |
  | JM1 residual_turns | +0.000010 | **−0.000176** |
  | JM2 post mean（L122） | +0.316922 | **+0.312313** |
  | JM1 post mean（L122） | +5.911005 | **+5.910628** |

  另：L94 `init_negative_read/0.1ps/JM1 −0.108826` vs analysis.json `−0.098687`，同样不一致。报告的 0.108836 不属于任何 case×step（0.1ps=0.0688、0.05ps=0.1077、0.025ps=0.1176），平台 post 值亦不属于任何条目。

  - 为何重要：analysis.md 是**封存的人类可读交付物**（D5），其 "Observed" 表格是读者/Codex 引用测量值的主要入口；数值与机器输出（D4）和 raw 不符，构成**报告层证据不一致**。raw 与 analysis.json 经独立重算**完全正确**——所以这是报告完整性问题，不是数据/物理问题，但必须修正。
  - 最小可复现证据：
    ```bash
    grep -n "0.108836\|5.911005\|0.316922" test/final/bvm/runs/bvm-s0-canonical-20260814-01/analysis.md
    python3 -c "import json;d=json.load(open('.../analysis.json'));print(d['phase_area']['JM1']['init_positive_read/0.1ps'])"
    ```
  - 所需修正：以 analysis.json/raw 为准**重建 analysis.md 的 Observed 表格**（新 attempt 或 correction note；**不得改动 raw/analysis.json**）。

### Minor
- 无其他实质项。源电流/电压波形、admissibility、收敛判定均独立验证通过。

## Claim ceiling
PASS — analysis.md/analysis.json 均未声称 receiver/Gate/逻辑/route 结论；INCONCLUSIVE 表述正确。

## Residual uncertainty
- 未复算全部 12 run × 2 JJ 的 phase-area（抽查 0.1ps 四 case 的 JM1 + 部分 JM2）；已覆盖关键量。
- Major 为 D5 报告数值不一致；不改变 raw/analysis.json 的科学正确性。

## Codex focus
1. **裁决 Major**：要求修正 analysis.md 的 "Observed" 表格（phase-area 与 platform）以匹配 analysis.json/raw；raw 与 analysis.json 无需改动。
2. S0 科学内容核心（控制匹配、方向、同 JJ、实际时间积分、源波形、admissibility、INCONCLUSIVE 收敛）经独立验证**正确**。
3. 收敛 INCONCLUSIVE（0.85 ps control 延迟带超限）独立确认，符合注册程序；可据此推进后续 receiver 判别实验设计（如 analysis.md 建议）。
