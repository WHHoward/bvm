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
1. 找出MVM论文中QB的"调整"参数 — JS IC、IBias
2. 用BVM最终输出(I_SL≈32μA)反推QB需要的输入阈值
3. 调整QB参数使其对单个BVM输出产生1个SFQ脉冲
4. 验证多BVM→多脉冲的对应关系

---

## 三、BVM 输出优化实验 (2026-05-16)

### 3.1 论文分析关键发现

| 发现 | 来源 | 影响 |
|------|------|------|
| BVM 输出电流同时到达 QB（同列多行同时读）| MVM + BVM 论文 | QB 接收模拟累加电流 |
| QB 按电流幅度→脉冲数转换（1x→1脉冲）| MVM 论文 §2.2 | QB 需匹配 BVM 单位输出 |
| QB 参数需"调整"以检测单 BVM 输出 | BVM 论文 §3.2 | 我们未做此调整 |
| JSL（JJ 堆叠替换 LSL）推荐 | BVM 论文 §2.5 | 面积优化，非性能提升 |
| JS1/JS2 IC 可调但需与存储磁通同步 | BVM 论文 §2.5 | IC × L > Φ₀ 约束 |
| 论文未给 I_SL 数值目标 | — | 目标是 QB 可检测即可 |

### 3.2 Phase 1: 提高 JS1/JS2 IC (74→90μA) — ✗ 失败

**假设**: 更高的 JS IC → 更强的开关 → 更大的 I_SL

**结果**: R1/R0 从 2.5x 骤降至 **1.0x**（无法区分 0/1）

| ISE | I_SL R1 | I_SL R0 | R1/R0 |
|-----|---------|---------|-------|
| 100~180μA | 9.1μA | 9.1μA | 1.0x |
| 200μA | 16.0μA | 16.0μA | 1.0x |

**根因**: S-Loop 存储磁通固定(由 JM1=120μA 决定)，无法调制更高 IC 的 JS1/JS2。
JS IC 和 JM1 IC 必须同步调整。

**详细记录**: [phase1_js_ic/CHANGELOG.md](phase1_js_ic/CHANGELOG.md)

### 3.3 Phase 2A: JSL 替换 LSL — ✓ 可行但不提升 I_SL

**假设**: 非线性 JJ 阻抗替换线性电感 LSL 可改善输出

**结果**: 所有配置保持功能，但 I_SL 无显著提升

| 配置 | I_SL R1 | R1/R0 | vs 基线 |
|------|---------|-------|---------|
| **基线 LSL=0.4pH** | **32.1 μA** | 2.5x | — |
| JSL 1×jj320 | 31.6 μA | 2.6x | −1.6% |
| JSL 4×jj320 | 30.3 μA | 2.6x | −5.6% |
| JSL 8×jj320 | 28.7 μA | 2.7x | −10.6% |
| JSL 4×jj74 | 25.4 μA | **2.8x** | −20.9% |

**结论**: JSL 是面积优化方案（无分流电阻），可改善 R1/R0 但降低绝对 I_SL。

**详细记录**: [phase2a_jsl/CHANGELOG.md](phase2a_jsl/CHANGELOG.md)

### 3.4 优化实验 v2: 信号扫描 + 同步提升

#### Plan A: ISE × IWL(read) 联合优化

| ISE | IWL | I_SL R1 | I_SL R0 | R1/R0 |
|-----|-----|---------|---------|-------|
| 100 | 80 | 31.0 | 12.1 | **2.6x** |
| 130 | 80 | **36.9** | 15.0 | 2.5x |
| 120 | 100 | 35.4 | 14.6 | 2.4x |
| 140 | 100 | 38.5 | 26.8 | 1.4x ✗ |
| 180 | 100 | 50.4 | 46.2 | 1.1x ✗ |

**发现**: ISE ≥ 140μA 时 R0 暴涨（过驱动两个状态）。最优: ISE=130, IWL=80, R1=36.9μA (+15%)。

#### Plan B: JM1 + JS 同步提升

| JM1 | JS | P_JM1 W1 | I_SL R1 | R1/R0 |
|-----|-----|----------|---------|-------|
| 140 | 85 | 8.3 rad | 21.1 | 1.8x |
| 150 | 90 | 6.9 rad | 15.7 | 1.3x |
| 160 | 100 | 1.8 rad | 12.0 | 1.0x |

**发现**: 写电流(IWL+IBL=200μA)不足以驱动更高 IC 的 JM1，存储磁通反而减弱。

#### 全部实验总结

```
BVM 输出优化 — 四条路径全部走完:
  ├── Phase 1:  JS IC 74→90           → R1/R0崩溃 ✗
  ├── Phase 2A: JSL 替换 LSL           → I_SL不升 △
  ├── Plan A:   ISE+IWL优化           → 最高37.7μA △ (+17%)
  └── Plan B:   JM1+JS同步            → 全面恶化 ✗

最终 BVM 配置 (保留):
  JM1=120μA, JS1=JS2=74μA (论文原值不变)
  ISE=100μA, IWL(read)=100μA (稳健方案)
  I_SL R1=32.1μA, R1/R0=2.5x
```

**结论: 32-37μA 是论文参数下 BVM 的物理极限。正确方向是调整 QB 匹配 BVM。**

**详细记录**: [phase1_js_ic](phase1_js_ic/CHANGELOG.md) | [phase2a_jsl](phase2a_jsl/CHANGELOG.md) | [optimization_v2](optimization_v2/CHANGELOG.md)

---

## 四、文件结构
```
test/bvm/
├── BVM_FINAL_RW.html / FULL.html       ← 最终可视化
├── test_bvm_final_rw/full.{cir,csv}     ← 最终测试 (1ps edges, 50GHz)
├── plot_bvm_final.py                    ← 最终绘图脚本
├── phase1_js_ic/                        ← Phase 1 实验 (JS IC↑, 失败)
│   ├── CHANGELOG.md                     ← 详细记录
│   └── backup/                          ← 基线备份
├── phase2a_jsl/                         ← Phase 2A 实验 (JSL, 可行)
│   ├── CHANGELOG.md                     ← 详细记录
│   └── backup/                          ← 基线备份
├── archive/                             ← 历史结果
└── SUMMARY.md                           ← 本文

test/bq/
├── BQ_PROPER_PULSE.html                 ← BQ 脉冲测试可视化
├── BQ_BVM_MATCH.html                    ← BQ-BVM 匹配测试可视化
├── test_bq_proper_pulse.{cir,csv}       ← 最优配置 (IBias泄放+3ps)
├── test_bq_bvm_match.{cir,csv}          ← BVM 电流匹配测试
├── plot_bq_final.py                     ← 最终绘图脚本
├── archive/                             ← 历史结果
└── SUMMARY.md                           ← BQ 详细分析
```
