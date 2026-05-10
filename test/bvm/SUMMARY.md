# BVM & BQ 仿真项目总结

> BVM: Karamuftuoglu et al. (2025) Supercond. Sci. Technol. 38 015020
> BQ: Razmkhah et al. (2024) Supercond. Sci. Technol. 37 065011
> 仿真器: JoSIM v2.7 | JJ模型: MITLL SFQ5ee (RN/R0/CAP为估算值)

---

## 一、BVM — 最终状态

### 配置
| 参数 | 值 | 来源 |
|------|-----|------|
| 频率 | 50GHz (10ps脉冲, 1ps陡沿) | 论文一致 |
| IW (WL/BL) | 100μA | 半选安全 (100<JM1 IC=120μA) |
| ISE | 100μA | 与IW同级 |
| WL读时 | 100μA | 与写一致 (论文方案: 无单独偏置) |
| SL负载 | **12串联 jj320** | 与论文一致 |
| JM1/JM2 IC | 120/140μA | 论文一致 |
| JS1/JS2 IC | 74μA | 论文一致 |

### 最终结果 (1ps陡沿)
| | Read-Write | Full Truth Table |
|------|------|------|
| P_JM1 W1后 | +12.4 rad (2Φ₀) | +12.2 rad (2Φ₀) |
| P_JM1 W0后 | −11.9 rad | −18.5 rad |
| I_SL Read-1 | **32.1 μA** | **32.3 μA** |
| I_SL Read-0 | 11.2 μA | 11.3 μA |
| **R1/R0** | **2.9x ✓** | **2.9x ✓** |
| 半选保护 | — | ✓ |
| PWL边沿 | **1ps** (5ps→1ps改进) | 写入增强×2 |
| NDRO (非破坏读出) | ✓ | ✓ |

### 已验证功能
- 写入 (W1/W0) ✓ — P_JM1翻转, I(LM1)锁存
- 半选保护 (WL-only, BL-only) ✓ — 存储态不扰动
- 非破坏读出 ✓ — 读后P_JM1不变
- 二元读出区分 ✓ — 存1→22μA, 存0→6μA (近零)

### 与论文的结构对比
所有R/L/JJ参数逐项匹配论文Fig.2(b) ✓。SL负载修正为12串联jj320(与论文一致)。唯一差异: JJ的RN/R0/CAP为估算值(论文用MITLL SFQ5ee真实工艺参数,未公开)。

### 可视化
- [BVM_FINAL_RW.html](BVM_FINAL_RW.html) — 读写测试
- [BVM_FINAL_FULL.html](BVM_FINAL_FULL.html) — 全功能真值表

---

## 二、BQ/QB — 当前状态分析

### 2.1 结构验证
BQ结构(Fig.4, Razmkhah 2024): 拓扑与论文完全一致 ✓
- Lin=0.8pH, L0=1.323pH, L1=L2=3.91pH
- JS=133μA, JL1=112μA, JL2=189μA
- RB=8.5Ω, IBias方向修正为 N_MID→IBias (泄放复位)

### 2.2 功能验证
- **约瑟夫森关系**: V=(Φ₀/2π)×dφ/dt, 误差<3% ✓
- **磁通积分**: Φ₀ ∝ (I_IN−IC)×Δt, 5级DC测试验证 ✓
- **低电流不触发**: I_IN<JS IC时不产生相位累积 ✓
- **IBias泄放**: JL1/JL2保持负偏置, 环路可复位 ✓

### 2.3 多电流测试数据
| I_IN | 超出IC(133μA) | ΔP_JS | Φ₀累积 |
|------|---------------|-------|---------|
| 80μA | −53μA | 1.7 rad | 0.3 Φ₀ |
| 133μA | 0μA | 53.1 rad | 8.4 Φ₀ |
| 150μA | +17μA | 66.4 rad | 10.6 Φ₀ |
| 180μA | +47μA | 84.9 rad | 13.5 Φ₀ |
| 200μA | +67μA | 96.9 rad | 15.4 Φ₀ |

### 2.4 核心问题: 无离散SFQ脉冲

**现象**: P_JS连续斜坡(非离散2π台阶), V_OUT连续振荡(非脉冲序列)
- DC阶跃输入: 连续相位累积
- SFQ脉冲输入(4×180μA×3ps): 仍连续累积, 0次离散2π事件
- CAP扫描(βc 1.0→0.07): 无效
- RN扫描(×0.5→×2): 无效

**可能原因**:

| 因素 | 分析 |
|------|------|
| JSIM vs JoSIM | BQ论文用JSIM, 不同仿真器的RCSJ模型实现可能有差异 |
| JJ模型参数 | RN/R0/CAP为估算值, 真实MITLL SFQ5ee参数可能产生不同开关行为 |
| 输入方式 | 电流源直接注入 vs 真实SFQ脉冲驱动 — 可能影响结的开关-复位循环 |
| MVM论文 | 同用JoSIM+同QB结构, 声称有0-4脉冲输出 → QB在JoSIM下应能工作 |

### 2.5 MVM论文的关键线索

> *"The current needed to generate an SFQ pulse from the QB circuit is **adjusted to the output**."*

MVM论文用JoSIM仿真同一QB电路并得到了0-4脉冲输出(Fig.2b)。论文明确说QB参数被"调整"以匹配BVM输出。这意味着:
1. QB可以在JoSIM下工作 ✓
2. 需要调整参数来匹配输入信号
3. 我们未做这个"调整"步骤

### 2.6 下一步 (BQ)
1. 找出MVM论文中QB的"调整"参数 — 可能是JS IC、IBias或负载
2. 用BVM最终输出(I_SL≈22μA)反推QB需要的输入阈值
3. 调整QB参数使其对单个BVM输出产生1个SFQ脉冲
4. 验证多BVM→多脉冲的对应关系

---

## 三、文件结构
```
test/bvm/
├── BVM_FINAL_RW.html / FULL.html    ← 最终可视化
├── test_bvm_final_rw/full.{cir,csv}  ← 最终测试 (12-series SL load)
├── test_bvm_100/150/200uA.{cir,csv}  ← 历史参考
├── archive/                          ← 旧结果
└── SUMMARY.md

test/bq/
├── PLOT_bq_compare.html / PLOT_bq_pulses.html
├── test_bq_80~200uA.{cir,csv}        ← 5级DC测试
├── test_bq_sfq_pulses.{cir,csv}      ← SFQ脉冲测试
└── SUMMARY.md
```
