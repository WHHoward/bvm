---
name: sfq-physics
description: SFQ 脉冲物理 — 2ps 脉冲宽度、数据先于时钟的时序规则、磁通量子 Φ₀=2.07mV·ps、相位移与 SFQ 的关系
metadata: 
  node_type: memory
  type: project
  originSessionId: c5521155-33ba-4655-a787-c46e6bb6b2b1
---

## SFQ 脉冲物理与仿真约定

### 关键物理量

| 量 | 值 | 含义 |
|----|-----|------|
| Φ₀ | 2.07 mV·ps | 单磁通量子 |
| 1 SFQ | 结相位前进 2π (≈6.28 rad) | 1 个磁通量子通过结 |
| 约瑟夫森关系 | V = (Φ₀/2π)·dφ/dt | 相位导数→电压 |
| RCSJ 模型 | I = Ic·sin(φ) + (Φ₀/2πRN)·dφ/dt + (Φ₀C/2π)·d²φ/dt² | 结动态方程 |

### 脉冲宽度：必须用 2ps

**Why:** 5ps 脉冲（16p→21p）通过 3Ω 注入电阻产生 ~500µA 峰值，超过大部分结的 IC，导致一个脉冲触发多次翻转（multi-SFQ）。改为 2ps（16p→18p）后每个脉冲精确产生 1 SFQ。

**PWL 模板:**
```spice
V_IN IN 0 pwl(0 0 10p 0 12p 0 13p 1.5m 15p 1.5m 16p 0 100p 0)
```
上升沿 1ps + 平台 2ps + 下降沿 1ps = 总宽 ~2ps

### 钟控逻辑时序规则（核心发现）

**数据 SFQ 必须先于时钟 SFQ 到达。**

| 时序 | 正确 | 错误 |
|------|------|------|
| 数据@15ps → 时钟@35ps | ✓ | — |
| 时钟@12ps → 数据@18ps | — | ✗（数据在时钟之后，被忽略） |

原因：ColdFlux 钟控单元（XOR/AND2/DFF/NDRO）内部有存储超导环。数据先到达→存储在环中→时钟到达→读取状态→输出。

### 相位分析

- 使用 `-j 2pi` (josim-plot2.py) 将相位除以 2π，每跳 1.0 = 1 SFQ
- Load JTL 的 B1 相位累积总量 = 输出 SFQ 个数
- 电压事件检测：|V| > 200µV → SFQ 脉冲

### 注入电路

```spice
V_IN IN 0 pwl(...)    # 电压源
R_IN IN N1 3           # 串联 3Ω → I_peak ≈ 500µA
L_IN N1 SFQ_IN 0.5p    # 缓冲电感
```

[[coldflux-library]] [[test-methodology]]
