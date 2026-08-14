# 组会汇报 — 2026-08-14

> **汇报周期**: 2026-08-10 → 2026-08-14
> **上次汇报内容**: Phase −1 计量修复（M4–M11）与 BVM source preflight 准备
> **一句话主线**: 本周完成 **BVM-S0 源端特征化闭环**：从"两个写过程是否有可观察初态"（D0 readiness）到"固定 12 Ω fixture 下 12-run canonical source 实验"，经过完整的封存/审计链，最终 Codex scientific audit 裁决为 **artifact VALID + scientific disposition INCONCLUSIVE**——建立了**有界的 fixed-fixture simulation facts**，但**未建立 resolution-independent source baseline**（预注册 0.1→0.05 ps control-latency 差 0.85 ps > 0.5 ps band）。

---

## 1. 本周期工作总览

| # | 工作 | 结果 | 关键产出 |
|---|---|---|---|
| 1 | D0 initial-state readiness（三阶段判别） | ✅ **VALID，75 ps bound** | `bvm-s0-d0-settle-20260814-01/` |
| 2 | BVM-S0 12-run canonical source 实验 | ✅ 12 runs 完成、证据封存 | `bvm-s0-canonical-20260814-01/` |
| 3 | S0-001→S0-002/003→S0-004 封存与报告链 | ✅ 全链 ACCEPTED | evidence-seal + corrected report |
| 4 | Copilot skeptical review ×2 + Codex scientific audit C02 | ✅ **VALID + INCONCLUSIVE** | `S0-004/audits/C02/verdict.yaml` |

## 2. 核心结果表（bounded scientific facts，引用 S0-004 corrected report / C02）

**固定 fixture**：拷贝的 `bvm_cell.cir` + `jjmit.cir` 闭包、`XBVM1 WL1 BL1 SE1 SL1 BVM`、仅 `R_LD SL1 0 12`、read 脉冲 96–106 ps（project-derived，过 D0 75 ps readiness bound）、0.1/0.05/0.025 ps × 170 ps。

### 2.1 源端响应（baseline-subtracted，窗口 [94,130) ps）

| 案例 | 量 | 0.1 ps | 0.05 ps | 0.025 ps | latency |
|---|---:|---:|---:|---:|---:|
| **init_positive_read** | V(SL1) peak | **0.890 mV** | **0.901 mV** | **0.904 mV** | ≈ 5.0 ps |
| | I(L_SL) peak | **74.18 µA** | **75.06 µA** | **75.30 µA** | ≈ 5.0 ps |
| **init_negative_read** | V(SL1) peak | **−0.307 mV** | **−0.315 mV** | **−0.317 mV** | ≈ 10 ps |
| | I(L_SL) peak | **−25.57 µA** | **−26.27 µA** | **−26.39 µA** | ≈ 10 ps |
| matched controls（两种） | V(SL1) / I(L_SL) | 仅 **15–18 nV** / **1.3–1.5 nA**（噪声级残余） | — | — | — |

> 状态相关：正读与负读的源端响应**幅度和 latency 都不同**（5 vs 10 ps），且都远高于 matched zero-read control——这是"两种 operational initialization 产生 state-conditioned source response"的直接观察。

### 2.2 直接 JJ 可观测量

| 量 | 观察 |
|---|---|
| direct JM1/JM2 activity-window [94,108) ps phase changes | 均**远小于 ±1 turn**（如 JM1 0.068792 rad ≈ 0.011 turns @0.1ps） |
| pre [80,90) ps admissibility | 全时间步通过：JM1 p2p 0.00039 rad、JM2 p2p 0.00655 rad；pos/neg L-inf 分离 11.8221 rad（≥0.100 要求） |
| pre/post [140,150) ps operational signatures | 未出现 gross inversion（post 与 pre 同侧）；**不得**声称已证明 nondestructive logical read |
| phase–area 残差 | 报告性（~1e-4 turns），未设容差 |

### 2.3 收敛判定（预注册规则）

| 相邻对 | 结果 |
|---|---|
| 0.1 → 0.05 ps | **FAIL**：matched-control source-peak latency −0.70 ps vs +0.15 ps = **0.85 ps > 0.5 ps** task-local band |
| 0.05 → 0.025 ps | PASS（适用比较全过） |

→ **numerical_status = INCONCLUSIVE**（第一个必需相邻对未过，阶梯不可扩展、band 不可改）。

## 3. 明确区分：已接受 vs 未接受

| ✅ 已接受（bounded facts） | ❌ 未接受 |
|---|---|
| fixed-fixture source-side simulation observations（§2 表） | resolution-independent source baseline |
| raw/provenance validity（59 项 seal、24 项 manifest、逐字节校验） | logical 0/1（read0/read1）语义 |
| 两种 operational initialization 的 state-conditioned source response | state preservation（读下状态保持） |
| direct JM1/JM2 P/V 逐 timestep 命名窗口观察 | SFQ / fluxoid count |
| D0 75 ps operational readiness（测试网格内） | receiver / JTL 接收 |
| pre/post signatures 无 gross inversion（观察，非证明） | INTERFACE_GATE_V1 / candidate / route |
| | published / hardware reproduction |

> **INCONCLUSIVE 不是实验失败**：12-run 数据有效、provenance 完整、响应可复现；它只是说"按预注册的收敛规则，不能把单一网格的结果升级为与时间步无关的源端基线"。这是诚实的有界结论，为下一轮收敛任务留下了明确的设计输入。

## 4. 本周遇到的问题与解决过程

| # | 问题 | 根因 | 解决 |
|---|---|---|---|
| 1 | S0-001 delivery 机械失败（verify-task 不过） | 合同 deliverable D3 `raw/**/*.csv` 与 3 级 raw 布局（`raw/<case>/<step>/run-01.csv`）不匹配：`handoff.py` 的 `PurePosixPath.match` 中 `**` 只匹配一段目录（M8 D1/D6 同类工具缺陷） | 交付 BLOCKED（保留全部 12-run 证据）→ Codex 签发 superseding |
| 2 | S0-002 reseal | 需要精确清单修复 D3 不可满足 | evidence-seal.yaml（59 项精确路径 + SHA-256）+ seal_check.py（缺/增/篡改真实拒绝） |
| 3 | Copilot 发现 verify-log provenance defect | 成功 verify 输出未单独保留；receipt 的 verify 命令错误指向 seal-check.log；旧 verify-task.log 残留 ERROR 内容 | S0-003：closure-record.yaml 绑定全部 hash、独立 verify-s0-002.log、旧失败日志标记 SUPERSEDED_FAILURE_EVIDENCE |
| 4 | Copilot 科学审查发现旧 analysis.md 数值表与 raw/analysis.json 不一致 | human-readable 表格手写取值错误（如 phase_delta 0.108836 vs 实际 0.068792）；**raw 与 analysis.json 本身正确** | S0-004：stdlib-only 脚本从 12 frozen CSV 用实际时间独立重建全部数值 → 与 frozen JSON 全量比对（fail on mismatch）→ 确定性渲染 corrected-analysis.md（字节级重渲染一致、篡改毒化拒绝） |
| 5 | 最终 scientific audit | 预注册 0.1→0.05 ps control-latency 0.85 ps > 0.5 ps band | **VALID + INCONCLUSIVE** 如实裁决；不事后改 criteria、不升级 baseline |

> 经验：报告数值必须由脚本从证据确定性生成（杜绝手写表格）；日志必须与命令一对一映射；工具 glob 缺陷要按合同机制报告而非绕过。

## 5. 下一步建议（未执行，等待授权）

下一轮（建议新一周开始，等待用户授权）：

1. **新建独立 preregistered source convergence/characterization task**：保留 S0 fixture 与两写过程，产生新的 immutable runs；
2. **重新设计 zero-control noise-floor waveform metric 的 applicability**：control 案例只有噪声级峰值（15–18 nV），其 latency/FWHM 比较在物理上无意义——新的任务应预注册最小 abs-peak 阈值，低于阈值时 latency/FWHM 比较标记 NOT_APPLICABLE（避免噪声峰值的采样网格伪影再次主导收敛判定）；
3. **考虑预注册可扩展 timestep ladder**（如 0.2/0.1/0.05/0.025 ps 或动态细化规则），明确首个必需相邻对必须全过的判据；
4. 仍不启动 receiver、BQ、DCSFQ_BVM、INTERFACE_GATE_V1 或参数调优——这些需要 S0 之后的事实层与独立授权。


## 7. 可视化附件（BVM-S0，v2 修正版——从 frozen raw / S0-004 corrected data 生成）

> 生成脚本：`test/final/bvm/runs/bvm-s0-canonical-20260814-01/plots/plot_bvm_s0.py` +
> `generate_story.py`（stdlib + matplotlib/plotly，确定性重渲染；图中数值已程序化
> 验证与 raw 重算逐位一致，无手填值；topology 以 **active 未注释 netlist** 为准：
> SE→N3、WL/BL→N1、无 N4/N7）
> 完整 figure index（每图回答什么问题/可 claim 什么/不可 claim 什么）：
> `test/final/bvm/runs/bvm-s0-canonical-20260814-01/plots/README-figure-index.md`
> 交互式 guided story：`bvm-s0-story.html`（四幕 + 边界 + Explore raw traces 附录）

### Core set（5 个核心视觉）

| # | 图 | 文件名（相对 plots/） |
|---|---|---|
| 1 | Timing + conceptual topology（注册窗口 + write-like 标注 + 概念拓扑） | `fig1-timing-conceptual.png` |
| 2 | State-conditioned source response：V(SL1) pos vs neg + controls inset + I≈V/12Ω 标注 | `fig2-source-response.png` |
| 3 | Storage/initialized operational signatures：PRE + POST−PRE delta（无 gross inversion 观察） | `fig3-storage-signatures.png` |
| 4 | Read-waveform timestep comparison（完整波形 0.1/0.05/0.025 ps） | `fig4-timestep-comparison.png` |
| 5 | Control residual + registered INCONCLUSIVE blocker（nV/nA；grid sensitivity 措辞） | `fig5-control-residual-blocker.png` |

### Appendix / supporting

| # | 图 | 文件名（相对 plots/） |
|---|---|---|
| A1 | Detailed ACTIVE topology（技术参考） | `figA1-detailed-topology.png` |
| A2 | Source current I(L_SL)（Ohm/KCL 与 V(SL1) 同信息） | `figA2-source-current.png` |
| A3 | Phase–area same-JJ identity check（residual view；非独立物理证据） | `figA3-phase-area-identity.png` |
| A4 | Project pipeline（historical 实线 / future 虚线） | `figA4-project-pipeline.png` |

所有图区分 observed / derived / inference；不启动任何新实验。v1 图（fig1-bvm-topology
等 8 张）已由 v2 集取代并删除，旧文件名不再引用。
## 6. 一句总结

> 本周把 BVM 源端从"没有可验证初态"推进到"**两种可操作初态 + 固定 fixture 下可复现、状态相关的源端响应（有界观察）**"，并经过完整的封存/对抗审查链；按预注册规则其科学判定是 INCONCLUSIVE（而非失败）——下一轮是设计正确的收敛/特征化任务，而不是急着接 receiver 或调参。
