# REVIEW JH-20260817-BVM-S1-002 / A01

Review disposition: REWORK
Recommended risk: CRITICAL
Recommended evidence mode: FROZEN
Evidence confidence: HIGH
Residual risk: MEDIUM

Reviewed delivery snapshot: 无独立 snapshot commit（A01 文件为未跟踪工作区状态；Codex 在 final audit 时创建）。审查基线 = 当前工作区 + frozen S0/S1 证据。

## Scope
PASS

Evidence:
- write_paths = `test/final/bvm/runs/bvm-s1-canonical-20260817-01/**` + `research/tasks/JH-20260817-BVM-S1-002/attempts/**`（request.yaml）。全部交付物位于其内；git status 仅见 S1-001（superseded，Codex 签发文件）+ S1-002 + mailbox；无 S0 路径改动。
- 12 runs 恰为 4 cases × 3 timesteps（0.05/0.025/0.0125 ps），无第四 timestep，无 interpolation/resampling/time alignment。
- `run_josim: true` 授权与执行一致；raw 12 CSV + stdout + stderr 齐备；stderr 无 ERROR/WARNING。

## Acceptance criteria
- [x] AC1 — PASS — 二进制 `/home/howard/JoSIM/build/josim-cli` SHA-256 48655cb3…40b2（我独立 `sha256sum` 一致）；stdout banner v2.7.2837d13。
- [x] AC2 — PASS — 12 netlist 语义正确：probe 字符串/端点/方向（V(SL1) SL1→0；I(L_SL|XBVM1) N8→SL1；P/V(B_JM1|XBVM1) N1→n_jm1o vts=+1 rd=+1；P/V(B_JM2|XBVM1) n_jm2i→N2 vts=+1 rd=+1）；R_LD SL1 0 12；read vs control 仅读段幅度差（knots 保留）；pos vs neg 仅初始化极性差；closure 字节一致（bvm_cell ea734654…、jjmit 19862d1f…）。
- [x] AC3 — PASS（数据层） — 12/12 CSV header 精确、无 NaN/Inf、时间严格递增无重复、覆盖全部注册窗口（末样本 169.95/169.975/169.9875 ps，窗口止于 150 ps）。
- [x] AC4 — PASS — readiness 独立重算：JM1 p2p 0.000372/0.000356/0.000351、JM2 0.0058071/0.0055528/0.0054827（≤0.020）、L∞ sep 11.8221 rad（≥0.100）；仅作 timestep 可比较性。
- [x] AC5 — FAIL（报告完整性） — analysis.md/json 报告了 rctrl/层级、read 观测、exact-decimal 覆盖、pre/post platform 均值与 act 端点 delta/same-JJ area（json 内），但**未报告 design 注册的 control RMS/time-normalized L1/adjacent-pair control 差异、control-corrected waveforms、control-corrected platform deltas**（见 Findings #2）。
- [x] AC6 — PASS（数据层）/ 部分 — 两对 ladder、零容差时间戳规则、层级、no-extension stop 规则均执行；verdict INCONCLUSIVE 正确且保留；但 control 1%/0.2% bands 未执行（见 Findings #2）。
- [x] AC7 — PASS — receipt 哈希映射 AC1-AC6；verify-task pre-receipt 与 final 均 VERIFIED；已请求 Copilot review。

## Independent checks
- 独立从 12 个 frozen CSV 重算（不调用 analyze_s1.py）→ readiness、rctrl、峰值/latency、全部 16 个 adjacent-pair 单元格、exact-decimal 时间戳（0 missing）、platform/area/residual 全部与 analysis.json 一致。→ PASS
- 关键单元格复核：`neg:I 05→025` pointwise=0.4952 µA，band=max(0.5 µA floor, 1%·Aref=0.264)=0.5000 µA → **PASS**（json `chk_peak_pointwise=true` 一致；analysis.md 却标 ✗——见 Findings #1）。
- closure 字节一致、binary 哈希、S1 0.05ps 原始波形与 S0 0.05ps **逐位一致**（n=3399、peak=0.9007 mV）→ 确定性 replay 与 S0 一致性成立。
- 预测命中：pos V 0.9041 mV（+0.904..+0.905 低缘，md 已注明）、pos I 75.34 µA（75.3..75.4）、neg V −0.3169 mV（−0.317）、neg I −26.41 µA（−26.4）。→ 全部命中。
- FWHM：复现 analyze_s1.py crossing-filter → pos 5.8999/5.8916/5.8896 ps（json 一致）；neg 过滤器仅接受 1 个穿越 → None（见 Findings #4）。

## Hidden-error probes
- md 表格与 json 是否一致（S0-001 同类问题）→ **证伪失败：neg:I 05→025 pointwise 单元格 md 标 ✗ / band 0.26，json 与独立重算为 PASS / band 0.50**；neg 行 band 标签全部漏 floor。→ 成立（Major）
- 注册 control 观测（RMS/L1/pair、1%/0.2% bands）是否执行 → **证伪失败：analyze_s1.py 仅算 rctrl(max)；json 无 control RMS/L1/pair 段；md "residual criterion PASS region" 仅基于 rctrl**。→ 成立（Major）
- analysis.md 是否真是 analyze_s1.py 的渲染 → **证伪失败：脚本只写 analysis.json，run root/attempts 无 md 渲染器；md 表格错误证明其非忠实机器渲染**。→ 成立（Major）
- 负读 FWHM "no finite half-height crossings" 是否属实 → **证伪失败：负叶实际有 2 个半高穿越（FWHM≈1.07 ps）**；analyze_s1.py 非对称过滤器（要求段起点在 pk/2 与 pk 之间）对负叶只接受 1 个穿越→None。→ 成立（Minor，不涉验收）
- 数值层是否被污染/越界/S0 重解释 → 不成立：json/raw 独立验证正确；verdict INCONCLUSIVE 保留；无 Gate/logical/SFQ/fluxoid 主张；S0 未触碰。→ 不成立
- INCONCLUSIVE 是否因 report 错误被误判 → 不成立：即使按 json 正确单元格，neg:I 05→025 仍因 RMS 0.1617>0.1 失败，pair 仍 fail，verdict 不变。→ 不成立

## Claim ceiling
PASS

无物理/Gate/logical 升级；INCONCLUSIVE 按 frozen no-extension 规则保留；claim ceiling（bounded_fixed_fixture_source_observations_and_numerical_convergence_under_registered_s1_procedure_only）未被突破。

## Findings
### Critical
- None.

### Major
1. **analysis.md §5/§6 表格与 analysis.json/raw 不一致（报告层）**：
   - `0.05→0.025 neg:I` pointwise 单元格 md 标 `0.50 µA (0.26) ✗`；正确 band=max(Afloor=0.5 µA, 1%·Aref=0.264)=0.50 µA，0.4952≤0.50 → **PASS**（json `chk_peak_pointwise=true`，我的独立重算一致）。md 将 PASS 误标为 FAIL。
   - neg 行全部 band 标签漏 Afloor 下限：neg:V pw (3.17→应 5.0)、neg:V RMS (0.63→1.0)、neg:I pw (0.26→0.50)、neg:I RMS (0.05→0.10)。pos 行因 Aref 大 floor 不主导，标签正确。
   - §6 表述 "pointwise and RMS amplitude/shape bands fail on all four read observables" 不精确：neg:I pointwise 实际通过（仅 RMS 失败）。
   - 最终 verdict INCONCLUSIVE **不受影响**（neg:I 05→025 仍因 RMS 0.1617>0.1 失败）。
   - 与 S0-001 Major 同类（报告表格与 json/raw 不一致）；数据层正确，故为报告修正问题。
2. **注册的 control 观测与 bands 未执行**：design「Control applicability and convergence observables」要求 report control max/RMS/time-normalized L1 与 adjacent-pair control 差异，bands 表含 control max/pair ≤1% 与 control RMS/L1/pair ≤0.2% of paired-read scale；AC5 要求 control-corrected source waveforms、design 另要求 control-corrected platform deltas。analyze_s1.py 仅实现 `rctrl`（control max 比率）；analysis.json 无 control RMS/L1/pair 段；md "residual criterion PASS region" 仅由 rctrl（≤4e-5）支撑。因 control 极低（V≈12 nV、I≈1 nA），若补齐将平凡通过，verdict 不变——但 frozen 注册程序组件缺失。
3. **analysis.md provenance 声明不实**：md "this analysis.md is a rendering" 错误——analyze_s1.py 只写 analysis.json，无 md 渲染器存留；md 表格错误（#1）证明其非忠实机器渲染。frozen D5 的 provenance 陈述需纠正或补渲染器。

### Minor
4. **负读 FWHM 说明错误**：md "(—: no finite half-height crossings on the negative lobe)" 不实——负叶有 2 个半高穿越（FWHM≈1.07 ps）；analyze_s1.py 非对称 crossing 过滤器（`(a[1]-pk/2)*(pk[1]-a[1])>=0` 要求段起点在 pk/2–pk 带内）对负峰只接受 rising-edge 穿越→None。不涉验收（负读 FWHM NOT_APPLICABLE），但陈述与数据矛盾。
5. **"endpoint covers 170 ps" 措辞不精确**：12 CSV 末样本为 169.95/169.975/169.9875 ps（JoSIM 离散输出惯例）；所有注册窗口止于 150 ps 且完整覆盖，无实际影响。
6. **AC5 platform 表未在 md 呈现**：md 将 pre/post platform/act delta 委托给 analysis.json（数据在 json 中）；可接受，但结合 #2，报告完整性偏弱。

## Residual uncertainty
- control RMS/L1/pair bands 未执行 → 无法从交付物确认其通过（虽按 rctrl≤4e-5 必然平凡通过）；属程序完整性缺口而非数据疑问。
- 负读 FWHM 定义（crossing-filter vs 标准半高穿越）在 S1 内自洽且不涉验收；与 S0 的窄窗 FWHM（1.0–1.4 ps）定义不同，二者不可直接比较——设计文档引用的"S0 FWHM 1.4 ps 设计输入"与 S1 报告值（5.90 ps）是不同量，不构成数据矛盾。

## Codex focus
1. 裁决 #1/#3：analysis.md（frozen D5）表格/§6/provenance 修正路线——建议仿 S0-004 走 correction 任务（确定性渲染 corrected report，禁就地改 frozen 证据）；数据层（raw/analysis.json/verdict）经独立验证正确，无需重跑。
2. 裁决 #2：补齐 control RMS/L1/pair 观测与 1%/0.2% bands（平凡通过，verdict 不变）或明确记录为 deviation；AC5/design 的 control-corrected 报告一并处理。
3. 知悉：S1 0.05ps 与 S0 0.05ps 原始波形逐位一致（确定性 replay 成立）；INCONCLUSIVE 科学 disposition 留待 Codex/User。
