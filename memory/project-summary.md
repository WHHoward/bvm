---
name: project-summary
description: JoSIM × BVM 项目综合快照 — 2026-08-09 相位单位审计后
metadata:
  node_type: memory
  type: project
  last_updated: 2026-08-14
---

# JoSIM × BVM 项目综合总结

**当前阶段**：Reference / Source / Receiver Characterization（2026-08-14）。

**完整说明**：`docs/guide/project-guide.md`。

**会话交接**：`docs/HANDOVER.md`。

**任务权威**：`memory/project-todo.md`。

**2026-08-14 状态（BVM-S0 闭环）**：M4–M11 已接受（M9 冻结测量/报告语义、M10 历史 endpoint 重建、M11A/M11B 双基线）。本周完成 BVM-S0 链：**D0** initial-state readiness 闭环（75 ps operational readiness bound，`JH-20260814-BVM-S0-D0-003` ACCEPTED）；**BVM-S0** 12-run canonical source 实验（4 案例 × 0.1/0.05/0.025 ps，固定 12 Ω fixture）完成；S0-001 原始证据、S0-002/003 sealing/provenance 链、S0-004 deterministic corrected report 与 Copilot skeptical review 均完成；Codex scientific audit **C02**（`JH-20260814-BVM-S0-004/audits/C02/verdict.yaml`）最终裁决 **artifact=VALID + scientific disposition=INCONCLUSIVE**。INCONCLUSIVE 的直接原因是预注册的 0.1→0.05 ps matched-zero-control peak-latency 差 = 0.85 ps > 0.5 ps task-local band；不允许事后修改 S0 criteria，也不得把 S0 升级为 converged baseline。

**已接受（bounded facts）**：fixed-fixture source-side simulation observations（正读 V(SL1) 0.890/0.901/0.904 mV、I(L_SL) 74.18/75.06/75.30 µA、latency≈5 ps；负读 −0.307/−0.315/−0.317 mV、−25.57/−26.27/−26.39 µA、latency≈10 ps；matched controls 仅 15–18 nV / 1.3–1.5 nA）；raw/provenance validity；两种 operational initialization 的 state-conditioned source response；direct JM1/JM2 activity-window phase changes 均远小于 ±1 turn；pre/post operational signatures 未出现 gross inversion。

**未接受**：resolution-independent source baseline、logical 0/1、state preservation、SFQ/fluxoid count、receiver、`INTERFACE_GATE_V1`、candidate/route、published/hardware reproduction。

**下一步（未执行，等待用户授权）**：新建独立 preregistered source convergence/characterization task，重新设计 zero-control noise-floor waveform metric applicability，考虑预注册可扩展 timestep ladder；任何 receiver/BQ/DCSFQ_BVM/Gate/tuning 工作均不授权。

## 一句话目标

把 BVM 的状态相关、负载相关电流波形转换成恰好一个可被标准 JTL 接收的 SFQ 事件，再交给 T1/RSFQ 数字逻辑。

## 项目边界

研究工作没有修改 JoSIM 的核心求解器。`src/`、`include/`、构建核心和上游 CTest 与上游树一致；项目新增的是 BVM/BQ/DCSFQ_BVM/T1/ColdFlux 网表、实验数据、脚本、论文和文档。

## 2026-08-09 关键审计

JoSIM `P()` 输出 raw phase rad。`scripts/sfq_metrics.py` 未除 \(2\pi\)，且把过阈值采样间隔数误叫 `fast_events`。因此 Step 0 冻结口径失效，所有相位/SFQ 数和事件判断需重算。

正确关系：

\[
N_{\Phi_0}=\Delta\phi_{\rm rad}/(2\pi)=\int Vdt/\Phi_0
\]

等号只能在同一 JJ、同一对端点、同一方向和同一时间窗下使用；它给出 JJ 净相位绕转，不是完整环 fluxoid 数。

## 经人工重算的状态

- BVM→BQ 基线：JM1 −0.9406 圈；BJs +0.9983 圈；BJL1/BJL2 净值仅 0.0706/0.0598 圈。输出支路未证明完成有效量化；该网表只接 10 Ω 负载，没有测 JTL。
- BVM P2：W1/W0 的 JM1 约 +0.938/−0.937 圈；这推翻了用原始 rad 值证明“±6 涡旋”的旧证据链。100 µA 读近似非破坏，120 µA R0 擦除负态；严格环 fluxoid 数仍待完整计算。
- BQ v4：六周期测试在 110–150 µA 已测点时，下游 JTL 相对首脉冲前参考约每周期 +1 圈；70/90 µA 未见逐周期累积。这与约 1:1 传播相容，但不是完整 SFQ Gate。v4 重新成为候选；68.4 µA 是旧 BQ-v2 加载值，v4 真实级联波形尚未知。
- 标准 DCSFQ：300 µA 减 0 µA 控制后，B1/B2/B3 为 −1/+1/+1 圈，不是 7–8 次爆发。
- DCSFQ_BVM：68.4 µA 测试输入下未见完整输出；输入增量耦合约 0.285。45–55 µA 目标依据失效。标准单元的 150/300 µA 只是两个离散内部响应点，不是已定位输出阈值。

## 不受单位错误影响的数据

- BVM 峰值电流随负载约 43.9–97.8 µA；
- FWHM 约 6.8–11.2 ps；
- 有效峰值 Thevenin 拟合约 40 Ω / 4 mV（只适用于已测波形）；
- BQ 基线输出电压峰值约 157 µV；
- 分流 0.285、P2 读电流/擦除、CSV 字节级重复性。

## 当前路线

先修指标、控制、事件窗口、同 JJ 电压积分和时间步收敛；再用校准数据冻结 `METRIC_SPEC_V2.md`，新 JSON 写入各实验 `data/metrics_v2/`。之后才公平并行复核：

**2026-08-11 进展**：M4 已建立 raw rad→圈与活动命名基础；M5 已由 `M5-LITE-PILOT-001` 的 A02 Copilot 复审和 Codex 审计接受。`scripts/sfq_metrics_v2.py` 现在实现 pre/activity/post 半开窗口、显式方向、匹配零输入控制与活动聚类；历史 DCSFQ 0/300 µA CSV 的一圈重放只是算术回归，活动簇不计作物理事件，也不构成 Gate。下一项是 M6 的同 JJ 电压面积交叉校验。

1. BQ v4：单 PWL、90–110 µA 细扫、真实 BVM 波形、0/1、JTL 与鲁棒性；
2. DCSFQ_BVM：撤回固定阈值，正确极性、有界参数矩阵、JTL 与真实级联。

最终 Gate：按事先冻结的数值容差，读 1 时下游恰好一个事件、读 0 时零事件、重复无多发/丢失、BVM 状态保持，并通过步长与参数裕度。

## 暂停的旧叙事

- 用 `P(JM1)≈±5.9` 证明 BVM ±6 多涡旋；
- BQ v4 输出级死亡、整个 BQ 拓扑已系统排除；
- DCSFQ 300 µA 多滑移爆发；
- 45–55 µA 已冻结目标；
- `fast_events` 是 SFQ 个数；
- 本地材料已证明“全球文献空白”。

这些旧内容在日志中保留用于追溯，但不得作为当前结论引用。
