# BQ/QB (Buffer/Quantizer) JoSIM 仿真 — 最终总结

## 涉及的三篇论文

| # | 论文 | 仿真器 | QB/BQ 角色 |
|---|------|--------|-----------|
| [25] | **BVM** (Karamuftuoglu 2025, SUST 38) | **JoSIM** | 不涉及 QB |
| [28] | **Synapse/BQ** (Razmkhah 2024, SUST 37) | **JSIM** | 定义 BQ 结构 (Figure 4) |
| — | **MVM** (Karamuftuoglu 2025, arXiv:2507.04648) | **JoSIM** | 使用 QB 连接 BVM 阵列→T1 |

## QB 结构的唯一来源

QB 的结构定义来自 **Synapse 论文 Figure 4**。MVM 论文引用 [28] 指向同一来源，没有提供额外结构。

```
Synapse 论文 (JSIM)           MVM 论文 (JoSIM)
      ↓                            ↓
  定义 BQ 结构 ─────────→ 使用相同 QB 结构
  (Figure 4)             连 BVM 阵列做 MVM
```

## 我们的 QB 实现 vs 论文

### 拓扑：完全一致 ✓

逐项对照 BQ.md（从论文 Figure 4 提取的连接表），8 个元件的节点连接无任何差异。

### JJ 参数：估算值

| JJ | IC | RN (估算) | R0 (估算) | CAP (估算) | 数据来源 |
|----|-----|----------|----------|-----------|---------|
| JS | 133μA | 1.9Ω | 5.7Ω | 0.7pF | 论文+估算 |
| JL1 | 112μA | 2.2Ω | 6.6Ω | 0.55pF | 论文+估算 |
| JL2 | 189μA | 1.3Ω | 3.9Ω | 1.0pF | 论文+估算 |

**论文只给了 IC**。RN/R0/CAP 是我们基于 RN·IC≈0.25mV 和 βc≈1 估算的。MITLL SFQ5ee 工艺的真实参数未公开，这可能是差异的主要来源。

### 行为差异

| | Synapse 论文 (JSIM) | MVM 论文 (JoSIM) | 我们 (JoSIM) |
|------|-----|-----|-----|
| 仿真器 | JSIM | JoSIM | JoSIM |
| 离散 SFQ 脉冲 | 声称有 | 声称有 (0-4 pulses) | **无离散 2π** |
| 输入类型 | SFQ 脉冲 (来自 Synapse) | BVM 累加电流 | 电流源 |
| 输出 | 量化 SFQ 脉冲 | 脉冲数 ∝ 激活 BVM 数 | V_OUT 振荡 |
| P_JS 行为 | 未知 | 未知 | 连续斜坡 |

### 参数扫描结果

- **CAP 降低** (βc 1.0→0.07)：平台增多，但无离散 2π 阶跃
- **RN 翻倍/减半**：**完全无影响** — V_JS 由电路拓扑决定，不由 RN 决定
- 结论：离散 SFQ 缺失不是 JJ 参数问题

### 我们已验证的正确项
- 约瑟夫森关系 V=(Φ₀/2π)×dφ/dt 精确验证 (<3%误差)
- IBias 方向修正 (N_MID→IBias 泄放)
- BQ 对输入电流的响应: Φ₀ 累积 ∝ (I_IN−IC)×Δt
- 低电流不触发 (I_IN < IC 时 P_JS≈0)

## 两个论文中 QB 的用法对比

| | Synapse 论文 BQ | MVM 论文 QB |
|------|-----|-----|
| 输入来源 | Synapse SQUID 加权 | BVM 阵列 SL 累加 |
| 输入类型 | SFQ 脉冲序列 | 模拟累加电流 |
| 功能描述 | "sum fluxes, quantized SFQ pulses" | "thresholding element" |
| 脉冲产生 | 磁通累积≥3Φ₀ 触发 | 电流幅度→脉冲数 |
| 后级 | JJ-Soma | T1 加法器 |

MVM 论文描述 QB 为 **"thresholding element"** 而非磁通积分器——暗示更简单的电流→频率转换行为。

## 下一步建议

1. **改变 QB 行为定义**：不再追求离散 2π 相变。MVM 论文将 QB 描述为阈值检测器——可能每个 V_OUT 振荡周期即计为一个 "SFQ 脉冲"

2. **获取 MITLL SFQ5ee 精确参数**：联系论文作者或查找 MITLL 公开数据获取 RN/R0/CAP 值

3. **直接复现 MVM 论文 Figure 2b**：用 4 BVM + QB 阵列，以 JoSIM 仿真，计数 V_OUT 振荡峰作为输出脉冲

4. **推进 T1 仿真**：无论 QB 行为如何，T1 是乘法器链的下一级，可以并行推进
