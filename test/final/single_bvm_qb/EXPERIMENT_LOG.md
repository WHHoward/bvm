# BVM→BQ Coupling Experiment Log

> **开始**: 2026-07-13 | **josim-cli**: v2.7.2837d13 | **模型**: jjmit (Ic×RN=1.6mV)

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

## 实验 5: K 元件变压器方案 (待进行)
