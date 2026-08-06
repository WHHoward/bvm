---
name: dcsfq-bvm-design
description: DCSFQ_BVM 新元件设计（H7 主路线）— 决策记录、缩放参数、Phase 0 决策门、验证链；方案二三与 H6 保留为后备
metadata:
  type: project
---

# DCSFQ_BVM 元件设计（H7 主路线）

**Why**: BQ 8 轮失败根因三件套（BJs 裸结欠阻尼 βc≈5.4 / 电流源通量泵 / 输出级 ~100µA 推不动 250µA JTL）。DCSFQ 骨架每个结都有 RB+LRB 阻尼、输出 B3=250µA 天然 JTL 兼容、输入是阈值判别器——三个根因全部在结构上解决。

**How to apply**:
- 用户 2026-08-06 拍板: **新元件 + 方案一最小缩放** — B1/B2 225→80µA，IB1≈100µA，RB≈8.6Ω (6.86/area)，LRB≈4.85/5.35pH；**B3/IB2/L1-L6 冻结不动**
- 完整 spec: `docs/superpowers/specs/2026-08-06-dcsfq-bvm-cell-design.md` (8faa4f3, 修订 2)
- 验证链: V1 偏置稳定 → V2 阈值判别扫描 → V3 JTL 接收 → V4 BVM 级联 → V4b 去负载链对照；最终 Gate: 读1→恰好 1 SFQ，读0→0
- **保留后备**: H6 (修 BQ)、方案二 (门控)、方案三 (双端口时钟) — 见 [[bvm-bq-coupling-experiments]] [[GuidanceFromGpt]] §九.4/§十

## Phase 0 实测结果 (2026-08-06，全部双审查通过)

- **G2: 边沿触发确认** — 现有 DCSFQ sustained 148ps 零累积，bump/sustained 事件逐位一致 → 方案一无需门控
- **阈值**: 现有元件 ∈ (150,300]µA（300µA 多滑移爆发 → 干净单 SFQ 需近阈值过驱动）；**目标阈值修订为 45-55µA**（原 25µA 废止；需高于 R0 边沿振铃 ~40µA 且读1 过驱动 ≤1.5×）
- **接口规格实测**: I_peak 43.9-97.8µA、Zth≈39.6-41.2Ω（非 15Ω）、FWHM 6.8-11.2ps、68.4µA=链+BQ 加载值、R0 振铃 ±40µA、存储不扰动
- **G4 分流 0.285** < 0.3 → Phase 1 需调输入网络 (L2/L3) 或下调 B1/B2；68.4µA 下起点元件不触发（自洽）
- **G5 确定性 5/5 md5** ✅
- 数据: `test/final/interface/P0_LOG.md` + P0_LOG_P00-P03；元件: `circuits/interface/DCSFQ_BVM.cir`
- **极性待 V4 验证**: 输入耦合进 B2 支路、与 B1 偏置方向相反

[[bvm-bq-coupling]] [[project-todo]] [[bq-v4-modification-plan]]
