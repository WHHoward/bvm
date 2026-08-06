---
name: bvm-bq-coupling-experiments
description: BVM→BQ 耦合实验全记录 — 基线/低IC/变压器方案及数据分析
metadata:
  type: project
  node_type: memory
  date: 2026-07-17
---

# BVM→BQ 耦合实验记录

> **目标**: BVM 级联后根据电流强度产生对应数量的 SFQ 脉冲（不限于 BQ）
> **josim-cli**: v2.7.2837d13 | **模型**: jjmit

---

## 独立验证 ✅

| 模块 | 测试 | 结果 |
|------|------|------|
| BVM | test_bvm_final.cir | JM1 = \|0.94\| SFQ (写入"1"正确) |
| BQ | test_qb_final.cir | 90µA→190 SFQ, Vpk=1035µV |

---

## 实验 1: 基线 (BVM→BQ 直接级联)

**配置**: BVM → 8×jjmit(area=3.2) SL load → 标准BQ (BJs IC=50µA, IBias=35µA)

| 指标 | 值 |
|------|-----|
| SL 峰值电流 | 68.4µA |
| BJs 相位 | 0→1.00 SFQ (连续滑移, 无离散事件) |
| V(OUT_Q) 峰值 | 157µV |
| 结论 | ❌ BJs 相位前进2π但 dφ/dt≈0.2 rad/ps, V=(Φ₀/2π)×0.2≈70µV, 太低 |

**数据**: `/tmp/exp_baseline.csv`（已丢失）

> ✅ **2026-08-06 Step 0 已解决矛盾（见 BASELINE.md）**: 冻结口径下 BJs net=+6.27 SFQ
> （电压态滑移，0 快速事件），3 次运行 md5 一致；"1.00" 为计数误读，GPT 的
> "−0.00001" 无法由任何变体重现；SL 68.4µA / Vout 157µV 三份记录精确一致。
> 基线结论成立：级联无离散 SFQ 输出。

---

## 实验 2-4: 低 IC BQ 方案

| 版本 | 设计 | 结果 | 根因 |
|------|------|------|------|
| v1 | BJs/BJL1/BJL2 全缩放, RJ1=82Ω, RJ2=52Ω | 35.9 SFQ 独立测试 | 阻尼不足 (βc~5.4) |
| v2 | +RJs=33Ω shunt, RJ1=20Ω, RJ2=16Ω | 8.0 SFQ, Vpk=282µV | BJs shunt不必要 |
| v3 | 仅BJs缩放(IC=20µA), BJL1/BJL2保持原值 | SL 33.6µA, 0 SFQ | **内在矛盾** |

**低 IC 方案内在矛盾**:
```
L_J = Φ₀/(2π·IC)
IC=50µA → L_J=6.6pH  → L_total=7.4pH
IC=20µA → L_J=16.5pH → L_total=17.3pH (+133%)
SL电流: 68.4→33.6µA (-51%)
触发阈值降低的好处被电感增大完全抵消
```

**数据**: `/tmp/exp_lowic_*.csv`

---

## 实验 5: K 元件变压器

**来源**: SPICE 标准互感耦合元件。`K L1 L2 Kc` 耦合两个电感，通过互感 M=K√(L1·L2) 实现电流变换。

**设计**: n=2 (L_PRI=2pH, L_SEC=8pH), K=0.9, 串联注入

| n | I_PRI | I_SEC | BJs | 结果 |
|----|-------|-------|-----|------|
| 2.0 | 94µA | 24µA | -0.0 SFQ | ❌ |
| 2.5 | ~94µA | 26µA | -0.0 SFQ | ❌ |
| 3.0 | ~94µA | 23µA | -0.0 SFQ | ❌ |

**失效原因**:
1. L_PRI=2pH 在 500GHz 下阻抗仅 Z=6.3Ω, 与 8×jjmit 负载并联, 分流严重
2. M=K√(L_PRI×L_SEC)=3.6pH, 在 SFQ 时间尺度 (~30ps) 下耦合能量不足
3. L_SEC 串联在 BQ 输入路径中, 感抗 Z=25Ω 限制了次级电流
4. **本质上**: K 元件适合连续正弦波耦合 (MHz-GHz), 不适合 ps 级 SFQ 脉冲的瞬时能量传递

**数据**: `/tmp/exp_tx_*.csv`

---

## 重新定义问题

**目标**: BVM SL 输出电流 → 转换为对应数量的 SFQ 脉冲

**关键约束**:
- BVM 输出是**缓慢振荡**的 (30-40ps 窗口, 非 2ps 快脉冲)
- 接收端需要能处理这种"慢"信号, 或先转换为快 SFQ

**不限于 BQ 的方案空间**:
1. 脉冲整形: BVM→DCSFQ (DC→SFQ) → 快脉冲 → BQ/JTL
2. JTL 链: BVM→低IC JTL 级联 → 逐级压缩 → 快 SFQ
3. 自定义阈值检测器: 直接用 overdamped JJ 做电流→SFQ 转换
4. sfq_gen 变体: 修改触发灵敏度匹配 BVM 输出

---
