---
name: bvm-bq-coupling
description: BVM→BQ 阻抗匹配问题 — SL 输出 ~130Ω vs BQ 输入 ~350Ω，仅 ~25% 电流传递，建议低 IC 检测结或变压器耦合
metadata: 
  node_type: memory
  type: project
  originSessionId: c5521155-33ba-4655-a787-c46e6bb6b2b1
---

## BVM → BQ 耦合问题

### 问题

BVM（磁通涡旋存储器）的存储环（SL）输出阻抗约 130Ω，BQ（缓冲器）输入阻抗约 350Ω。阻抗严重不匹配导致仅 ~25% 的电流能传递到 BQ 输入。

### 电路文件

| 文件 | 内容 |
|------|------|
| `circuits/qb/bq_cell.cir` | BQ 子电路（BJs area=0.5, IC=50µA; IBias=35µA） |
| `circuits/bvm/bvm_cell.cir` | BVM 子电路 |
| `test/final/test_qb_final.cir` | BQ 独立测试（Iin=90µA，输出 1.035mV） |
| `test/final/test_bvm_final.cir` | BVM 独立测试（写/读正常） |
| `test/final/BVM_BQ_IMPEDANCE_ANALYSIS.md` | 9-section 详细阻抗分析 |

### 关键发现

- BVM 独立工作正常：P(JM1)=±0.94×2π，稳定存储
- BQ 独立工作正常：1.035mV SFQ 输出
- BVM+BQ 级联：**不工作**（~15µA 到达 BQ，远低于 BJs 需要的 50µA IC）

### 可能的解决方案

1. **低 IC 检测结** — BJs IC 降为 20-25µA（需重新设计 BQ 输入级）
2. **变压器耦合** — 使用互感提升电流（需要额外的 TX 元件）
3. **重设计 BVM 输出级** — 降低 SL 输出阻抗

### 状态

截至 2026-07-12，BVM+BQ 级联问题**尚未解决**。独立测试均正常。

[[coldflux-library]]
