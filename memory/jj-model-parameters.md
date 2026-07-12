---
name: jj-model-parameters
description: JJ 模型参数演变历史 — V0 参数是 BVM 唯一工作集 (Ic*RN=0.25mV)，ColdFlux 用 jjmit (Ic*RN=1.6mV)，混合模型方案
metadata: 
  node_type: memory
  type: project
  originSessionId: c5521155-33ba-4655-a787-c46e6bb6b2b1
---

## JJ 模型参数演变

### 当前统一模型

`circuits/models/jjmit.cir`:
```
.model jjmit jj(RTYPE=1, VG=2.8m, CAP=0.07p, r0=160, rn=16, icrit=0.1m)
```
IC=100µA×area, RN=16Ω/area, R0=160Ω/area, CAP=0.07pF×area → Ic×RN=1.6mV

### 参数演变（4 轮）

| 轮次 | Ic×RN | R0/RN | CAP | 结果 |
|------|-------|-------|-----|------|
| V0 | 0.25mV | 3 | 0.07pF | **BVM 唯一工作集** |
| V1 (JSIM) | — | — | — | 失败 |
| V2 (JoSIM) | — | — | — | 失败 |
| V3 (T2017) | 1.7mV | 10 | — | 写操作过强，多涡旋 |
| V4 (grid scan 60组合) | — | — | — | 全部失败 |

### 关键结论

- **BVM 需要 V0 参数** (Ic×RN=0.25mV) 才能工作
- **ColdFlux/BQ 需要 jjmit 参数** (Ic×RN=1.6mV)
- **混合模型方案**：BVM 用 V0 + BQ 用 ColdFlux —— 这已被验证可行

### 之前存在的 5 个模型文件

历史上有 `mitll_models.cir` (V0)、`mitll_models_jsim.cir`、`mitll_models_t2017.cir`、`mitll_models_coldflux.cir`、`mitll_models_mixed.cir`。现已统一为 `jjmit.cir`。

### BVM 结类型分级

| 结 | IC | 角色 |
|----|-----|------|
| JM1 | 120µA | 开关结 |
| JM2 | 140µA | 非开关结 |
| JS1/JS2 | 74µA | 检测结 |
| jj320 | (load) | 负载结 |

**Why:** BVM 和其他电路需要不同的 JJ 参数才能工作，不可互换。
**How to apply:** 预设 BVM 测试需要专门的模型参数，ColdFlux 标准元件用 jjmit。

[[coldflux-library]] [[bvm-bq-coupling]]
