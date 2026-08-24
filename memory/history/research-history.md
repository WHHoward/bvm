---
name: research-history
description: 项目完整研究历程时间线（2026-07-12 至今）——阶段、实验、结论演变、转折点；跨会话/跨模型交接的第一手历史权威
metadata:
  type: project
  last_updated: 2026-08-24
---

# 研究历程（2026-07-12 至今）

> **用途**：本文件是项目**研究叙事**的权威记录（为什么做、做了什么、结论如何演变）。
> 与 `CHANGELOG.md`（材料性变更日志）、`project-todo.md`（任务状态）互补。
> 每个条目标注：日期、做了什么、结果、产物路径、当前认知状态（✅ 仍有效 / ⚠️ 已修正或失效）。
> 新重大进展必须按 `josim-project-summary` 的"研究历程记录"规则追加。

## 一、项目一句话定义

把 BVM（超导存储单元）在"读 1"时输出的、随负载变化的**几十 µA 电流波形**，转换成**恰好一个可被标准 JTL/RSFQ 逻辑接收的 SFQ 事件**，供 T1 等数字单元计数求和——接口元件是本项目的研究缺口。

## 二、阶段总览

| 阶段 | 时间 | 主题 | 结局 |
|---|---|---|---|
| 0. 基础建设 | 7/12 | ColdFlux 标准库提取 + 验证 | ✅ 7 核心单元验证通过 |
| 1. 路线设计 | 7/13-7/17 | PIM 路线图、BVM→BQ 双路线、论文策略 | ✅ 路线冻结 |
| 2. BQ 尝试 | 7/17-8/6 | BVM→BQ 耦合 7 轮实验 + BQ v4 | ❌ 8 轮全败（结构不匹配） |
| 3. 路线转向 | 8/6 | DCSFQ_BVM 新元件 + Phase 0 表征 | ✅ Phase 0 完成（G1-G5） |
| 4. 计量审计 | 8/9 起 | **P() 单位事故**发现 + Phase −1 修复 | ✅ 计量与双基线闭环（M4–M11、M12 已验收；物理 Gate 未启动） |
| 5. 工作流升级 | 8/9 | Codex–Claude 双代理 + stand-in + mailbox | ✅ 基础设施就绪 |
| 6. Receiver Exploration | 8/17-8/23 | BVM source → detector → passive/direct → DCSFQ/JTL → active interstage | 🔄 detector/source separation 已建立，canonical exactly-one chain 未闭合 |

## 三、详细时间线

### 2026-08-13：M11 metadata errata 与下一阶段切换

**做了什么**：为 M11A/M11B 的 immutable protocol records 记录最小、hash-bound 的时间戳 errata；`handoff.py` 新增默认 chronology guard（request ≤ ACK ≤ receipt ≤ audit）。M11A C03 以 immutable A02 log 核对并更正 M4/M5/M6/M7 regression metadata 为 15/29/21/18，M9/M10 为 59/13。

**结果/产物**：M11A/M11B 的 ACCEPTED scientific baseline 不变；`docs/research/BVM_SOURCE_CHARACTERIZATION_PREFLIGHT.md` 成为下一阶段的未签发 source-side preparation。

**认知**：✅ Phase −1 measurement repair 与双基线已闭环，项目进入 Reference/Source/Receiver characterization；⚠️ 仍未运行新实验、未升级 `published_qb` R0/UNKNOWN，未定义任何 interface/candidate Gate。

### 2026-08-13：M11 双子门与 W5B 当前知识状态接受

**做了什么**：接受 M11A 的 Measurement Calibration Baseline（`JH-20260813-M11A-001` C02）及 scope-correct 的 M11B Scientific Reconstruction Baseline（`JH-20260813-M11B-003` C01）。M11B 固定七对象 matrix：BVM storage/source-output、published QB、BQ v4、standard DCSFQ、DCSFQ_BVM、canonical JTL；每项都有结构化 evidence、observable、provenance、reproduction/characterization status、UNKNOWN 与下一判别器。M11B-001/002 的合同/指针问题保留为 rework 历史。

**结果/产物**：`docs/research/SCIENTIFIC_RECONSTRUCTION_OBJECT_MATRIX_V1.yaml` 成为 W5B 唯一 canonical registry，`docs/research/REFERENCE_PROVENANCE.md` 仅作指针；`research/tasks/JH-20260813-M11B-003/audits/C01/verdict.yaml` 为 `ACCEPTED`。

**认知**：✅ 当前 reconstruction/provenance knowledge state 已诚实冻结，M11 两子门均已闭环；⚠️ 这不补全电路物理知识、论文参数、行为复现、characterization 或 candidate Gate，W5A/W5C 仍独立开放，任何后续运行须单独预注册。

### 2026-08-12：M8 预注册有界时间步收敛接受

**做了什么**：`JH-20260812-M8-001` 在六个 loaded canonical JTL 匹配控制运行产生前固定 0.1/0.05/0.025 ps、窗口、观测量、任务局部带宽和不增加第四层的停止规则。A01 raw 证据完整但合同闭环无效，故保留为 `REWORK_REQUIRED`；不重跑 raw 的 `JH-20260812-M8-002` 对六份冻结 CSV 独立重算并取得可验证 FROZEN 闭环。

**结果/产物**：`research/tasks/JH-20260812-M8-002/audits/C01/verdict.yaml` 为 `ACCEPTED`。两个相邻 refinement 的全部预注册适用量均在运行前任务局部带宽内；M4–M7 的 83 项回归复跑通过。

**认知**：✅ 该 loaded canonical JTL 校准 fixture 在注册 procedure 下显示有界数值收敛；⚠️ 不冻结全局容差、不代表 SFQ/接收事件/系统 Gate，M9–M11 仍未完成。

### 2026-08-12：M7 校准测试与历史回归接受

**做了什么**：完成 `M7-LITE-001` 的 M7A（合成 ground truth）、M7B（直接同 JJ V/P 的 canonical JTL 测量管线重放）与 M7C（DCSFQ 0/300 µA 控制重放、BQ v4 六周期平台常量）校准。A01 的数值检查通过但因缺少独立 analysis 和完整 scope evidence 被 `REWORK_REQUIRED`；A02 保留 A01 原始证据并补齐绑定 analysis、范围日志与独立 Copilot 复审。

**结果/产物**：`research/tasks/M7-LITE-001/attempts/A02/CODEX-AUDIT.md` 为 `ACCEPTED`。83 项 M4–M7 测试通过；canonical JTL 相位—面积残差仅记录，未设接受容差。

**认知**：✅ 计量实现、canonical transient 管线和指定历史 raw 算术具备接受的校准/回归证据；⚠️ 这不是物理事件、JTL Gate、路线、容差或收敛结论，M8–M11 仍未完成。

### 阶段 0：基础建设（7/12）

**做了什么**：从 ColdFlux 论文 PDF 提取 RSFQ 标准单元库（35 个网表）；修复 7 个核心单元测试（JTL/SPLIT/MERGE/DFF/XOR/AND2/NDRO，2ps 脉冲 + data-before-clock 时序）；验证 NOT 门真值表（NOT(0)=1, NOT(1)=0）；清理 31 个冗余文件。

**产物**：`circuits/standard/`（35 网表）、`test/standard/test_not.cir`、josim-viz / project-summary / skill-router skills、CHANGELOG.md、10 个 memory 文件。

**认知**：✅ ColdFlux 库是可靠的测试基准；⚠️ 后续审计发现该阶段结论基于旧 V0 模型时代参数。

### 阶段 1：路线设计（7/13-7/17）

**做了什么**：
- PIM 路线图（4 阶段：BVM→BQ→T1→4×1 阵列→PoC）
- ARS 深度研究确认 BVM→BQ 接口是文献空白（仿真-only 是领域常态）
- 双论文策略：Paper A（BVM→QB 接口耦合）、Paper B（BVM 乘法器可扩展性）
- Phase 1 双路线计划：低 IC BJs 缩放 + K 元件变压器

**产物**：`memory/archives/pim-roadmap-design.md`、`paper-directions-analysis.md`、`phase1-bvm-bq-coupling-plan.md`。

**认知**：⚠️ 路线图顶层方向仍有效，但 Phase 1 双路线细节已过时（08-06 标注）。

### 阶段 2：BQ 尝试与失败（7/17-8/6）

**做了什么**：7 轮 BVM→BQ 耦合实验（基线、低 IC×3、K 变压器×3、论文参数 BQ、电阻负载）全部失败。

**关键发现链**：
1. BVM 输出 ~30ps 慢振荡，无法驱动任何 IC>50µA 的 SFQ 接收结
2. 根因 1：BJL1 IC 36µA < BJs IC 50µA → 电流沉
3. BQ v4 修复（BJL1 IC 36→90µA）→ 反而更差（输出路径死亡，v2 的 5.5× 劣化）
4. 冻结 3 条物理根因（8/9 后确认仍有效，因为基于电压行为）：
   - BJs 裸结无外部阻尼（βc≈5.4 欠阻尼，jjmit 固有）
   - 电流源注入 = 通量泵（滑移量由窗口决定，602-829 SFQ/300ps）
   - 输出级驱动不足（~100µA < ColdFlux JTL 阈值 250µA）

**认知**：❌ BQ 拓扑（裸结输入 + 并联输出）结构性不适配 BVM 慢读出电流 → **停止缩放迭代，转向专用接口元件**。✅ 电压态滑移机制结论仍有效（不依赖相位单位）。

### 阶段 3：路线转向 DCSFQ_BVM + Phase 0（8/6）

**做了什么**：
- 从 ColdFlux DCSFQ 骨架设计 DCSFQ_BVM 单元（B1/B2 225→80µA、IB1≈100µA、RB≈8.6Ω 阻尼网络）
- 按用户要求：缩放起点以实测 BVM 输出行为为准（P0.0 负载扫描）
- Phase 0 六任务（P0.0-P0.3）+ 决策门 G1-G5，subagent 并行执行

**Phase 0 关键结果**：
- P0.0：BVM 输出接口规格实测——5 种负载下 43.9-97.8µA、Zth≈40Ω（推翻旧 ~15Ω）、FWHM 6.8-11.2ps（修正 30-40ps 文档假设）、R0 边缘振铃 ±40µA
- P0.1：现有 DCSFQ 触发阈值 >150µA（目标曾定 ~45-55µA，**8/9 后撤回**）
- P0.2：DCSFQ_BVM 输入网络耦合系数 0.285（<0.3 警示线）；68.4µA 测试输入未触发
- P0.3：md5 确定性 5/5 重跑一致
- G1-G5：边沿触发判定（bump/sustained 逐位同，B2 恒定 6.76Φ₀×148ps 无累积）

**认知**：✅ 接口规格、耦合系数、确定性（电流/电压测量，不依赖相位单位）；⚠️ 触发目标与"DCSFQ 300µA 多滑移"等相位类结论在 8/9 被审计修正。

### 阶段 4：P() 单位事故与 Phase −1（8/9）⭐ 最重要转折

**事故**：JoSIM 相位模式 `P()` 输出 **raw rad（弧度）**，旧脚本 `sfq_metrics.py` 把它当"圈数/SFQ 数"用，同时把过阈值**采样点数**叫 `fast_events`（事件数）。

**三个独立验证**：
1. JTL 输入 `7.0574 rad = 2π + arcsin(0.7)` 精确吻合
2. 单结 `219.91 rad = 精确 35.000 圈`
3. 旧基线重算：BJs `+0.998 圈`、JM1 `−0.94 圈` = 单涡旋

**被修正的结论**：
| 旧结论 | 修正后 |
|---|---|
| "BVM 多涡旋 +5.89"（P2） | 0.94 圈 = 单涡旋 |
| "300µA 多滑移爆发 7-8 次" | 减零输入控制后 B1/B2/B3 各约 ±1 圈 |
| "BQ v4 下游收到 38 个失控事件" | 38 rad ≈ 6 圈 ≈ 六个输入周期，与 1:1 相容 |
| "45–55µA 触发目标" | 撤回 |
| `fast_events` = 脉冲数 | 是采样点数，不是事件数 |

**仍然有效**：接口规格、0.285 耦合、md5 确定性、BQ v4 电压态滑移机制、L_J 矛盾（数学推导）。

**Phase −1 修复管线（M4-M12）**：修计量 → 事件窗口/控制 → 电压面积校验 → 测试 → 收敛 → 冻结 METRIC_SPEC_V2 → 重算历史 → 冻结新基线 → 解锁路线 C/D 重测。

### 阶段 5：工作流升级（8/9）

**做了什么**：
- Codex–Claude 双代理协议（`research/WORKFLOW.md`）：Codex 签发合同 + 独立审计；Claude 受约束执行；四维结果分离（execution/artifact/physical/audit）
- Stand-in 机制（§15）：Codex 额度耗尽时经用户授权 Claude 临时代理，PROVISIONAL 待 Codex 审查
- Mailbox（`research/mailbox/`）：Claude↔Codex 异步对话渠道
- **M4-001 候选实现**：`scripts/sfq_metrics_v2.py`（rad→圈显式换算 + 禁事件语义）+ 16 测试全过，在独立 worktree `/home/howard/JoSIM-m4` 执行；其合同链在 2026-08-11 被拒绝，产物仅保留为重做参考

**认知（2026-08-11 修正）**：⚠️ M4-001 的候选代码与测试保留，但 stand-in 重签已封存 request、且 receipt 披露未授权删除日志，Codex 已拒绝 S01；M4 仍 🔴，必须用新的 superseding 合同在干净 worktree 重做。

### 2026-08-11：M4 计量脚本基础重新交付并接受

**做了什么**：以干净基线签发 superseding 合同 `JH-20260811-M4-003`；Claude 在隔离 worktree 执行 A01，Codex 独立复跑测试、核对 SHA-256 证据链与范围，并写入审计 `C01`。

**结果/产物**：✅ `scripts/sfq_metrics_v2.py` 将 `P()` 的 raw rad 显式除以 \(2\pi\) 得到圈数，并把阈值输出限定为活动样本数与活动区间；15 项独立回归测试通过。合同、回执与接受审计位于 `research/tasks/JH-20260811-M4-003/`，最终判决为 `ACCEPTED`。

**认知**：✅ M4 的实现完成；⚠️ 这不是 SFQ 事件计数、下游接收或系统 Gate。M5 的稳定窗/零输入控制和 M6 的同 JJ 电压面积交叉校验仍是后续必要条件。

### 2026-08-11：M5 窗口与零输入控制实现接受

**做了什么**：以 `CRITICAL+LITE` 任务 `M5-LITE-PILOT-001` 在 M4 基础上实现 pre/activity/post 半开窗口、显式方向、匹配零输入控制和连续活动聚类。A01 被 Copilot 发现 activity 窗统计/不足样本校验缺口；Codex 独立复现后要求保留 A01 并创建 A02。A02 补齐 activity 统计、0/1 样本拒绝和 409 样本断言，随后通过第二轮 Copilot 复审与 Codex 审计。

**结果/产物**：✅ M5 29 项与 M4 15 项回归均通过；对冻结 DCSFQ bump 0/300 µA CSV 的独立算术重算得到 B1/B2/B3 约一圈，pre/activity/post 为 30/409/900 样本。证据链：`research/tasks/M5-LITE-PILOT-001/attempts/A01/`、`attempts/A02/`；最终裁决：`attempts/A02/CODEX-AUDIT.md`。

**认知**：✅ 窗口、方向、零输入控制和活动聚类的实现已可用；⚠️ 活动簇不是物理事件，CSV 重放不是 Gate。M6 电压面积、M7 回归套件、M8 收敛、M9 指标冻结及后续基线重建仍待完成。

### 2026-08-13：M9 测量规格冻结与 M10 历史重建接受

**做了什么**：✅ 接受 `JH-20260813-M9-004` 的 `METRIC_SPEC_V2.md`，冻结 raw-radian normalization、same-JJ mapping/sign、window/control、activity、实际时间面积、收敛与输出语义；随后接受 `JH-20260813-M10-004` 对 BASELINE/P0/P2/BQ v4 的 `metrics_v2/` endpoint-arithmetic/provenance 重建。M10-003 的 scope-hash 冲突保留为 REWORK 历史，M10-004 逐项重新封存 11 个保存产物。

**结果/产物**：`docs/research/METRIC_SPEC_V2.md`，`docs/research/HISTORICAL_METRICS_V2_CORRECTION_TABLE.md`，`research/tasks/JH-20260813-M9-004/audits/C01/verdict.yaml`，`research/tasks/JH-20260813-M10-004/audits/C01/verdict.yaml`。

**认知**：✅ 历史 raw 的 rad→turn endpoint 表达与可追溯性已完成；⚠️ 全局容差、同 JJ BQ/BVM P/V mapping、SFQ/fluxoid、下游与系统 Gate 均未由 M9/M10 建立。

### 2026-08-14：BVM-S0 链闭环 — D0 readiness → 12-run canonical source → VALID + INCONCLUSIVE

**做了什么**（四段合同链，全部由 Codex 签发、Claude 执行、独立审计）：
1. **D0 initial-state readiness**（`JH-20260814-BVM-S0-D0-001/002/003`）：先判别两个写过程是否产生可区分、稳定的操作性初态。D0-001 因使用 `/usr/local/bin/josim-cli`（非仓库记录的 `build/josim-cli`）被判 INVALID（C04 provenance 失败）；D0-002 用授权二进制重跑（INCONCLUSIVE，JM2 state_early p2p=0.0708 rad > 0.02 guard）；D0-003 延长到 130 ps 五窗口 settle 判别，JM2 振铃单调衰减（0.0708→0.0240→0.0084→0.0029→0.0010 rad），首个合格相邻对 (settle_75, settle_95) 且 settle_115 保持 → **operational readiness bound = 75 ps（测试网格内），VALID**。
2. **BVM-S0 12-run canonical source experiment**（`JH-20260814-BVM-S0-001`）：4 案例（init_positive/negative × read/matched zero-read control）× 0.1/0.05/0.025 ps，170 ps，固定 12 Ω，read 脉冲 96–106 ps（project-derived，过 75 ps bound）。12 runs 全部 exit 0，pre-window admissibility 全时间步通过（JM1/JM2 p2p ≤ 0.02 rad、pos/neg L-inf 11.82 rad）。但 deliverable D3 `raw/**/*.csv` 在 3 级 raw 布局（`raw/<case>/<step>/run-01.csv`）下与 handoff.py 的 `PurePosixPath.match`（`**` 只匹配一段）不兼容 → 机械 verify 失败，交付 BLOCKED（M8 D1/D6 同类工具缺陷）。
3. **S0-002/003 sealing & provenance**：S0-002 纯重封存（evidence-seal.yaml 59 项精确清单 + seal_check.py，负向毒化测试真实拒绝）；Copilot 发现 verify-log 归属矛盾（成功 verify 输出未单独保留、receipt 错误指向 seal-check.log）→ S0-003 修复（closure-record.yaml + 独立 verify-s0-002.log），ACCEPTED。
4. **S0-004 corrected report + Copilot review + Codex scientific audit**：Copilot 科学审查发现旧 analysis.md 数值表与 raw/analysis.json 不一致（手写表格取值错误，如 phase_delta 0.108836 vs 实际 0.068792；raw 与 analysis.json 本身正确）→ S0-004 用 stdlib-only 脚本从 12 frozen CSV 实际时间独立重建全部数值、确定性渲染 corrected-analysis.md（字节级重渲染一致、篡改毒化拒绝），Copilot PASS。**Codex scientific audit C02**：artifact=VALID、physical=INCONCLUSIVE、ACCEPTED。

**结果/产物**：`test/final/bvm/runs/bvm-s0-d0-settle-20260814-01/`（D0 readiness）、`test/final/bvm/runs/bvm-s0-canonical-20260814-01/`（12-run package，frozen）、`research/tasks/JH-20260814-BVM-S0-004/attempts/A01/corrected-analysis.{md,json}`（C02 引用报告）、`research/tasks/JH-20260814-BVM-S0-004/audits/C02/verdict.yaml`（scientific disposition）。

**认知**：✅ 已接受：fixed-fixture source-side simulation observations（正读 V(SL1) 0.890/0.901/0.904 mV、I(L_SL) 74.18/75.06/75.30 µA、latency≈5 ps；负读 −0.307/−0.315/−0.317 mV、−25.57/−26.27/−26.39 µA、latency≈10 ps；matched controls 仅 15–18 nV / 1.3–1.5 nA）、raw/provenance validity、两种 operational initialization 的 state-conditioned source response、direct JM1/JM2 activity-window phase changes 均远小于 ±1 turn、pre/post signatures 未出现 gross inversion；⚠️ 未接受：resolution-independent source baseline、logical 0/1、state preservation、SFQ/fluxoid count、receiver、Gate、route、published/hardware reproduction。**INCONCLUSIVE 直接原因**：预注册 0.1→0.05 ps matched-zero-control peak-latency 差 0.85 ps > 0.5 ps task-local band；不把 INCONCLUSIVE 当实验失败，也不得事后改 S0 criteria。

**本周问题与解决过程**（供组会材料引用）：① D3 glob 导致 S0-001 delivery mechanical failure → S0-002 reseal（59 项精确清单）；② Copilot 发现 verify-log provenance defect → S0-003 修复；③ Copilot 科学审查发现旧 analysis.md 数值表与 raw/analysis.json 不一致 → S0-004 从 frozen raw deterministic regeneration 修正并通过；④ 最终 scientific audit = VALID + INCONCLUSIVE。旧错误报告全部保留为历史 provenance，引用数值统一用 S0-004 corrected report / C02。

### 2026-08-17：workflow-maintenance snapshot/bundle 审计未接受

**做了什么**：签发 no-JoSIM `WORKFLOW-MAINT-004` 以修复 issuer snapshot、endpoint-VI、evidence bundle 与文档语义；A01 因 `hash_paths` 与可写路径重叠而 BLOCKED，保留为不可变失败证据。随后 `WORKFLOW-MAINT-005` 收敛 hash 输入并重放验证，Copilot 审查通过，但 Codex C01 做了独立的实现级检查。

**结果/产物**：⚠️ `research/tasks/JH-20260817-WORKFLOW-MAINT-005/audits/C01/verdict.yaml` 为 `REWORK_REQUIRED`。当前实现未满足 byte-identical request snapshot binding，且 `handoff.py` 未逐项重算 evidence bundle path/SHA-256/bytes。004 由 005 取代只解决了合同范围冲突，不构成对这两项语义的接受。

**认知**：⚠️ endpoint-VI 的有符号公式实现/测试仍是限定的 workflow code evidence，不构成科学结论；在用户明确决定非自引用 snapshot 表示之前，不扩展协议或启动科学实验。

### 2026-08-17 → 2026-08-19：BVM stable-load characterization 与 logical semantics 冻结

**做了什么**：完成固定 `dt=0.0125 ps`、四种 load、双 polarity、read/control
的 16-run source characterization；随后冻结 `BVM_LOGICAL_SEMANTICS_V1.md`，并
以连续 rewrite/read sequence 固定 logical 1/0、canonical `+READ` 和 source
phase-count 不等于 SFQ-count 的边界。

**结果/产物**：stable-load evidence 提供 fixed-fixture bounded observations，
但没有建立 universal resolution-independent source baseline；exact endpoint-V/I
diagnostic 未完全支持，VIZ-002 停止。logical semantics 进入后续 receiver
Exploration 的 canonical source context。

**认知**：✅ source/read distinction 与语义边界仍有效；⚠️ 不把 stable-load
observations 写成普适 source model。

### 2026-08-19：R0b local trigger closure

**做了什么**：以 canonical SL、`R_IN=12 Ω`、B_TRIG AREA `.50`、bias
`+15 µA` 完成 R0b single point。

**结果/产物**：read1 B_TRIG 最大 continuous monotonic segment 约 `4.997 turn`，
read0 约 `0.185 turn`，READ=0 controls 无完整 transition；phase 与同 JJ
voltage-area 一致。

**认知**：✅ local detector discrimination/complete trigger 建立；⚠️ B_TRIG
是 multi-turn detector，不构成 exactly-one SFQ delivery。

### 2026-08-19 → 2026-08-21：R1/R2 passive/direct receiver characterization

**做了什么**：测试 parallel feedback、R1a passive pickup、differential B_OUT、
coupling、damping、amplitude/duration，并完成 conditioned B_OUT local one-slip
与 retrap evidence。

**结果/产物**：R1a secondary read1 约 `5.564 µA/66.77 µV`、read0 约
`1.144 µA/13.72 µV`；raw secondary/direct B_OUT 未触发；在 fixture-specific
约 `4.5 µA/20 ps` direct drive 下 B_OUT 约 `1.004 turn` 并 retrap。

**认知**：✅ passive extraction 有 state separation，B_OUT 在刻意 conditioned
drive 下能 local slip；⚠️ R2 dwell 数值是 fixture-specific，不是 universal hard
spec，也不是 downstream JTL evidence。

### 2026-08-21 → 2026-08-22：R3–R5 extraction/capture/quantizer route pruning

**做了什么**：完成 1 fF capacitive onset extractor、weak-mutual passive capture、
reduced biased quantizer、SET shunt 和正确 saddle point。

**结果/产物**：R3-A 为 fast differentiated onset → insufficient sustained drive；
R4-A 没有 persistent read1 fluxoid-state transition；R5-C 可跨 nonlinear saddle
但没有 complete local event，且出现 read1 back-action。

**认知**：⚠️ 这些是 tested instances 的 bounded failures，不是对所有 capacitive、
mutual 或 quantizer family 的 universal impossibility；reduced quantizer point
tuning 停止。

### 2026-08-22 → 2026-08-23：R6–R10 native-QB isolation/routing 与 bias review

**做了什么**：比较 direct native QB、weak transformer isolation、winding ratio、
L1/L2 routing、BJL2 AREA 和 local BJL2 bias。

**结果/产物**：R6-A isolation preserved state-selective QB activity；R6-B、R7-A、
R9-A 分别建立 drive/routing gain，但 BJL2 仍约 `10^-3 turn`；R8 AREA `.70`
没有 threshold-like gain；R10-A local bias 出现 nonselective/free-running。

**认知**：✅ source isolation 与 passive routing gain 已被分别证明；⚠️ passive
L1/L2 和当前 local bias branch 关闭，不把 native QB simple routing tuning 写成
完整 QB architecture 的普遍否定。

### 2026-08-23：R11–R15B，问题收缩到 active interstage

**做了什么**：R11 完成 standard JTL positive control 与 canonical direct-JTL
screening；R12 复核 DCSFQ_BVM controlled local regeneration 与 canonical cascade；
R13 做 raw replay、rectification、20 ps hold；R14 完成 passive interstage analytic
precheck；R15-A/R15-B 设计、修正并测试 bias-powered active interstage。

**结果/产物**：R11 `NO_JTL_TRIGGER`；R12 controlled `300 µA` 下 B3 约 `1.03 turn`
但 canonical read1 约 `0.0365 turn`；R13 `TEMPORAL_CONDITIONING_INSUFFICIENT`；
R14 `PRECHECK_NO_GO`；R15-A 为 invalid mutual constitutive topology；R15-B
positive-definite split-winding point 执行后 verdict `ACTIVE_STAGE_NO_TRIGGER`，
`I(L1)` peak 约 `0.511 µA`、B3 最大 segment 约 `0.0000577 turn`。

**认知**：✅ BVM detector、DCSFQ controlled regeneration、JTL fixture 各自均有
bounded evidence；⚠️ canonical BVM→SFQ chain 尚未闭合。当前最有证据支持的机制
瓶颈是 `B_DET → bias-powered active state compression/regeneration`。R15-B 的
read1 post-window ringing 高于 canonical no-receiver，故 source isolation 仍是
一级约束；本点失败不等于整个 active-interstage family 被证伪。

### 2026-08-23：组会材料同步

**产物**：`docs/meeting/2026-08-23-group-meeting.md`，汇总 R0b–R15B 的 observed/
derived/inference/unknown、路线裁剪和当前 stop boundaries。

**认知**：🔄 receiver characterization 仍进行中；未升级 Candidate、未接 T1，
未形成 paper-level quantitative claim。

### 2026-08-24：JTL transport gate 与 pulse polarity evidence closure

**做了什么**：停止 M1–M5 参数延伸，消费已接受的 R11 standard-JTL positive
control、M1 ideal Q0 replay、M5-PC 和 pulse-5 原/反极性 replay raw；建立
`JTL_TRANSPORT_GATE_V1` 回顾性 provisional 分类，把 strict continuous monotonic
local event 与 settled pre→post Josephson-well transport evidence 分开。

**结果/产物**：R11、M1 ideal replay 和 pulse-5 original 在本批 provisional transport gate 下
均显示四颗 JTL JJ 的 `+1` adjacent-well、bounded pre/post 和正确的逐级 onset
order。R11 与 pulse-5 original 在该离散 transport signature 下相容，但两者仍不
等同于 physical interface。反极性 replay 不是 logical0 control，也没有形成预期
正向 one-well chain。M5-PC 的 full-window/pre→post 为约 `+2` wells。

**纠正**：M5 历史 `positive_control_valid()` 只有 `abs(turns)>=0.90`，没有 one-turn
上界；旧 approximately-one/exactly-one 解释由
`test/exploration/parallel-qb-jtl-interface-mechanism-20260824/analysis-v2/M5_PREDICATE_CORRECTION.md`
明确 supersede，raw 和旧报告保留不改。

**认知**：✅ 本批方法学层现在明确区分 local event 与 downstream transport；⚠️ ideal
replay 不能证明 physical QB→JTL，canonical BVM→JTL、T1 和最终 interface 仍未
闭合。没有修改 canonical BVM、QB/JTL topology 或运行新 JoSIM。

## 四、关键转折点速查

| 转折 | 时间 | 意义 |
|---|---|---|
| BQ v4 失败 | 8/6 | 停止 BQ 拓扑迭代，转向 DCSFQ_BVM |
| 缩放起点改为实测 | 8/6 | 用户拍板：以 BVM 实测输出为设计依据（P0.0） |
| **P() 单位事故** | 8/9 | 所有相位结论除以 2π 重算；建立"事件数必须离散平台"纪律 |
| 双代理协议 | 8/9 | 执行/产物/物理/审计四维分离，独立复核制度化 |
| M4-001 候选实现 | 8/9–8/11 | 代码测试通过但合同链被拒绝；保留证据并以新合同重做 |
| M4-003 重新交付 | 8/11 | 干净合同链与独立审计接受 M4 计量基础；未宣称物理 Gate |
| D0 readiness 75 ps | 8/14 | 两写过程的可操作初态判别闭环（VALID，测试网格内 75 ps bound） |
| BVM-S0 12-run canonical | 8/14 | 固定 12 Ω fixture 源端响应有界观察；S0-001→002/003→004 链闭环 |
| **S0 scientific disposition** | 8/14 | **VALID + INCONCLUSIVE**（0.1→0.05 ps control-latency 0.85 ps > 0.5 ps band） |

## 五、当前认知状态速查（2026-08-09）

| 结论 | 状态 |
|---|---|
| BVM 接口规格（43.9-97.8µA、Zth≈40Ω、FWHM 6.8-11.2ps） | ✅ 有效 |
| DCSFQ_BVM 输入耦合 0.285 | ✅ 有效 |
| md5 确定性 | ✅ 有效 |
| BQ 电压态滑移机制（欠阻尼 + 通量泵） | ✅ 有效 |
| 基线 BJs +0.998 圈 / JM1 −0.94 圈 | ✅ 新事实（重算后） |
| 45-55µA 目标、多涡旋、爆发计数 | ⚠️ 已撤回/修正 |
| BQ v4 "系统排除" 结论 | ⚠️ 待新规格下重测 |
| M4 计量修复 | ✅ M4-003 已接受；M5–M12 仍待完成 |
