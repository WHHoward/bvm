---
name: coldflux-library
description: ColdFlux RSFQ 标准元件库 — 35 个元件，7 个已验证，jjmit 模型参数，JoSIM 仿真约定
metadata: 
  node_type: memory
  type: project
  originSessionId: c5521155-33ba-4655-a787-c46e6bb6b2b1
---

## ColdFlux RSFQ Standard Cell Library

**来源**: IARPA SuperTools/ColdFlux Cell Library v3.0 (MIT-LL SFQ Process)
**PDF**: `arti/ColdFlux_RSFQ_Logic_Cell_Library_for_MIT_LL_SFQ_Process_v3p0.pdf`
**电路文件**: `circuits/standard/*.cir` (35 个元件)
**元件索引**: `circuits/standard/INDEX.md`

### jjmit 模型参数

```
.model jjmit jj(rtype=1, vg=2.8m, cap=0.07p, r0=160, rn=16, icrit=0.1m)
```

| 参数 | 含义 | 值 |
|------|------|-----|
| IC (per area) | 临界电流密度 | 100µA/area |
| RN (per area) | 正常态电阻 | 16Ω/area |
| R0 (per area) | 漏电阻 | 160Ω/area |
| CAP (per area) | 结电容 | 0.07pF/area |
| Vg | 能隙电压 | 2.8mV |

### ColdFlux 偏置方法

- 2.6mV 等效 DC 偏置
- `IBias = (B1+B2)*Ic0*BiasCoef`（例如 JTL: 5×100µA×0.7 = 350µA）
- `RB = B0Rs/area`（B0Rs = IcRs/Ic0×B0 = 100µ×6.86/100µ×1 ≈ 6.86Ω·area）

### 7 个已验证元件

| 元件 | JJ数 | 类型 | 功能 |
|------|------|------|------|
| **JTL** | 2 | 异步 | SFQ 传输线，B1→B2 传播 |
| **SPLIT** | 3 | 异步 | 1→2 扇出，双输出各得 1 SFQ |
| **MERGE** | 7 | 异步 | 2→1 汇聚，两路输入合并 |
| **DFF** | 7 | 钟控 | D 触发器，B3+L3(8.64pH)+B4 存储环 |
| **XOR** | 11 | 钟控 | 双对称 A/B 侧，L3/L6 电流差编码 |
| **AND2** | 15 | 钟控 | 双级并行输入，1∧1=1 |
| **NDRO** | 11 | 钟控 | 非破坏读出，写→读→复位→读 |

**Why:** JoSIM 仿真的核心测试对象，所有 ColdFlux 实验基于这些元件。
**How to apply:** 引用 `circuits/standard/<CELL>.cir`，子电路名 `THmitll_<CELL>`。

[[sfq-physics]] [[test-methodology]]
