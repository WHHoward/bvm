# BVM→BQ Coupling Experiment Log

> **开始**: 2026-07-13 | **josim-cli**: v2.7.2837d13 | **模型**: jjmit (Ic×RN=1.6mV)

> ✅ **2026-08-06 Step 0 基线冻结**: 本文件中的旧数值（0.94 / 1.00 / 190）与冻结口径
> 不一致，详见同目录 `BASELINE.md`。以冻结口径 + `scripts/sfq_metrics.py` 为准。

---

## 独立功能验证

| 模块 | 测试文件 | 关键指标 | 结果 |
|------|---------|---------|------|
| BVM | `test_bvm_final.cir` | JM1@25ps = \|0.94\| SFQ | ✅ PASS |
| BQ (标准) | `test_qb_final.cir` | 90µA→190 SFQ, Vpk=1035µV | ✅ PASS |

---

## 实验 1: 基线耦合测试

**文件**: `test_bvm_bq_baseline.cir`
**日期**: 2026-07-13
**配置**: BVM(v6) → 8×jjmit(area=3.2) SL load → 标准BQ(BJs IC=50µA, IBias=35µA)

| 指标 | 值 |
|------|-----|
| BVM JM1 (W1后) | 0.94 SFQ ✅ |
| SL 峰值电流 | 68.4µA |
| BQ BJs 最终相位 | 1.00 SFQ (连续滑移) |
| 离散 SFQ 事件 | 0 |
| V(OUT_Q) 峰值 | 157µV |
| 结论 | ❌ BJs 相位前进了2π但dφ/dt太慢，无法产生干净SFQ |

**数据文件**: `/tmp/exp_baseline.csv`

---

## 实验 2: 低 IC BQ v1（全部结缩放）

**文件**: `bq_cell_lowic.cir` v1
**日期**: 2026-07-13
**配置**: BJs(0.20,IC=20µA), BJL1(0.14,IC=14µA), BJL2(0.22,IC=22µA), RJ1=82Ω, RJ2=52Ω

| 指标 | 值 |
|------|-----|
| 独立测试 (45µA) | 35.9 SFQ → 严重 multi-SFQ |
| 结论 | ❌ RJ1=82Ω/RJ2=52Ω 阻尼不足 (βc~5.4, 欠阻尼振荡) |
| 根因 | 缩放时应保持 R_eff=RN∥RJ 不变，而非保持 RJ=RN |

**数据文件**: `/tmp/exp_lowic_standalone.csv`

---

## 实验 3: 低 IC BQ v2（修正阻尼 + BJs 加 shunt）

**文件**: `bq_cell_lowic.cir` v2
**日期**: 2026-07-13
**配置**: BJs(0.20)+RJs=33Ω, BJL1(0.14)+RJ1=20Ω, BJL2(0.22)+RJ2=16Ω

| 指标 | 值 |
|------|-----|
| 独立测试 (45µA) | 8.0 SFQ, 0 离散事件, Vpk=282µV |
| 结论 | ❌ RJs=33Ω 分流了 BJs 电流，且原拓扑不需要 BJs 并联电阻 |

**数据文件**: `/tmp/exp_lowic_v2.csv`

---

## 实验 4: 低 IC BQ v3（仅缩放 BJs，保留 BJL1/BJL2 原值）

**文件**: `bq_cell_lowic.cir` v3
**日期**: 2026-07-13
**配置**: BJs(0.20,IC=20µA), BJL1/BJL2 保持原值 (area=0.36/0.54), RJ1=33Ω, RJ2=22Ω

| 指标 | 值 |
|------|-----|
| BVM JM1 | 0.94 SFQ ✅ |
| SL 峰值电流 | 33.6µA (vs 68.4µA 基线) |
| BQ BJs 最终相位 | 14.0 SFQ |
| 离散 SFQ 事件 | 0 |
| V(OUT_Q) 峰值 | 129µV |
| 结论 | ❌ BJs IC↓ → L_J↑ (6.6→16.5pH) → 电流传递率下降 |
| 根因 | **低 IC 方案的内在矛盾：IC↓降低阈值 但 L_J↑减少电流传递** |

**数据文件**: `/tmp/exp_lowic_v3.csv`, `/tmp/exp_lowic_coupled.csv`

---

## 低 IC 方案总结

```
IC = 50µA → 20µA:
  + 触发阈值降低 (50→20µA)
  - 约瑟夫森电感增大 L_J = Φ₀/(2π·IC): 6.6→16.5pH
  - 输入总电感 L_total: 7.4→17.3pH (2.3×)
  - SL 电流传递: 68.4→33.6µA (下降 51%)
  - 有效过驱动比: 提升有限 (被 L_J 增加抵消)
  
结论: 低 IC 方案存在根本性物理矛盾, 放弃此路线。
转向 K 元件变压器方案——在不改变 BJs IC 的前提下进行电流放大。
```

---

---

## 实验 6: BQ v4 独立验证 (Step 1, 2026-08-06)

**文件**: `circuits/qb/bq_cell_v4.cir` | **josim-cli**: v2.7.2837d13 (build/josim-cli)
**修改**: BJL1 IC 36→90µA, BJL2 IC 54→70µA, RJ1 33→56Ω, RJ2 22→36Ω, L0 1.323→2.5pH

| 测试 | 结果 | 判定 |
|------|------|------|
| S1.2 无输入偏置稳定 | BJs=0.0, 0 fast_events, Vpk=68µV | ✅ |
| S1.3 SFQ 注入 (1.5mV+3Ω) | BJs +12.57 SFQ/脉冲 (过驱动环振), JTL B1=+0.68 | ❌ |
| S1.4 电流扫参 70-150µA | BJs 602-829 SFQ 滑移全程; JTL B1: 70/90µA→0.68, ≥110µA→38.4 (无控) | ❌ |
| S1.5 JTL 接收计数 | BVM 相关水平 (70µA) 收到 0 SFQ | ❌ |
| S1.6 支路诊断 | BJL1 0 fast_events (吞噬修复 ✅) 但 BJL2 也 0 (输出死亡 ❌) | ⚠️ |

**关键对照 (同测试台 90µA)**: v2 Vpk=1035µV (无 JTL) vs v4 Vpk=186µV — **v4 输出比 v2 差 5.5×**

**Gate 判定: ❌ v4 独立验证失败**

**根因**:
1. BJs 无分流 + βc≈5.4 欠阻尼 → 任何过驱动即持续电压态滑移
2. v4 IC 顺序修正副作用: BJL1 不再吞噬但 BJL2 也不触发 → 输出级死亡
3. 输出级无法驱动 250µA JTL 负载 (v2/v4 均失败)

**数据**: `test/final/qb/data/bq_v4_*.csv` (全部 md5 确定性验证)

## 实验 5: K 元件变压器方案 (待进行)
