---
name: dcsfq-bvm-design
description: DCSFQ_BVM 新元件设计（H7 主路线）— 决策记录、缩放参数、Phase 0 决策门、验证链；方案二三与 H6 保留为后备
metadata:
  type: project
---

# DCSFQ_BVM 元件设计（H7 主路线）

**Why**: BQ 8 轮失败根因三件套（BJs 裸结欠阻尼 βc≈5.4 / 电流源通量泵 / 输出级 ~100µA 推不动 250µA JTL）。DCSFQ 骨架每个结都有 RB+LRB 阻尼、输出 B3=250µA 天然 JTL 兼容、输入是阈值判别器——三个根因全部在结构上解决。

**How to apply**:
- 用户 2026-08-06 拍板: **新元件 + 方案一最小缩放** — B1/B2 225→80µA (触发阈值 ≈25µA)，IB1≈100µA，RB≈8.6Ω (6.86/area)，LRB≈4.85/5.35pH；**B3/IB2/L1-L6 冻结不动**
- **决策门 P0.1**: 现有 `circuits/standard/DCSFQ.cir` 行为测试 — 边沿触发 → 方案一继续；电平触发滑移 → 升格方案二 (IB1 读窗口门控)，不无限迭代
- 完整 spec: `docs/superpowers/specs/2026-08-06-dcsfq-bvm-cell-design.md` (commit 8faa4f3)
- 验证链: V1 偏置稳定 → V2 阈值判别扫描 → V3 JTL 接收 → V4 BVM 级联 → V4b 去负载链对照；最终 Gate: 读1→恰好 1 SFQ，读0→0
- **保留后备**: H6 (修 BQ，加阻尼+偏置+输出级 JTL 化)、方案二 (门控)、方案三 (双端口时钟) — 见 [[bvm-bq-coupling-experiments]] [[GuidanceFromGpt]] §九.4/§十

[[bvm-bq-coupling]] [[project-todo]] [[bq-v4-modification-plan]]
