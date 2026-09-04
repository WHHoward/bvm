# ALL-ONE SELECTIVE-READ / ADDITIVITY / ISOLATION Quick

## 首要问题

本轮优先检查四颗 historical JM2-connected BVM 是否在共享 RSL/SL 上表现为相对独立的 unit-current 源：
(1) active BVM 与 isolated single reference；(2) inactive BVM 与同位置 0000；(3) multi-active 实际响应与 one-hot 叠加预测。最终 QB/JTL 只作次级诊断。

## 边界与协议

每个 mask 独立运行；四颗 BVM 均先执行 WRITE0，再执行统一 WL+BL=+100 uA 的 all-one WRITE1，之后只在 READ 的 WL+SE 上施加 mask。mask 位序为 `b3b2b1b0 -> BVM1/BVM2/BVM3/BVM4`。70--90 ps 是全零 no-op，不是 READ。使用 historical BVMSim JM2-connected BVM、原始 BVMSim QB、六级 JTL、0.1 ps 步长；canonical BVM 未使用。

Artifact QA：`ARTIFACT_VALID`；state closure 是描述性检查，四颗在所有 mask 的 task-local stored-1111 观察为 `False`。这两个字段都不等于物理功能 PASS。

## 1. Active BVM vs isolated single reference

array READ `[110,170)` ps 与 previous single S1 `[70,130)` ps 按 READ onset 的相对采样索引对齐，不插值。single 的绝对 stimulus schedule 不同，因此这里只能作 branch waveform/scale context，不能称为同协议等价。详细数值在 `metrics.json` 的 `active_vs_single`。

| one-hot | active BVM | LIN max abs (array vs single diff) | QBIN max abs diff | RSL max abs diff | LSL max abs diff |
|---|---|---:|---:|---:|---:|
| 0001 | BVM4 | 40.621 uA | 0.46377 mV | 49.989 uA | 49.989 uA |
| 0010 | BVM3 | 41.904 uA | 0.42718 mV | 38.507 uA | 38.507 uA |
| 0100 | BVM2 | 43.524 uA | 0.43362 mV | 28.978 uA | 28.978 uA |
| 1000 | BVM1 | 46.934 uA | 0.4412 mV | 25.208 uA | 25.208 uA |

## 2. Inactive BVM vs 0000

以下是 one-hot active READ 下每个 inactive victim 的 `mask - 0000`。它回答的是 stored-1111、commanded-0 BVM 是否仍离开 0000；不是把 victim 响应归因给单一耦合路径。

| active mask | inactive victim | Delta RSL max abs (uA) | Delta LSL max abs (uA) | Delta RS max abs (uA) | Delta LS3 max abs (uA) | Delta JS1 max abs (turns) | Delta JS2 max abs (turns) |
|---|---|---:|---:|---:|---:|---:|---:|
| 0001 | BVM1 | 7.1456 | 7.1456 | 1.1974 | 2.9802 | 0.0079106 | 0.010686 |
| 0001 | BVM2 | 7.6961 | 7.6961 | 1.8447 | 4.4806 | 0.014463 | 0.01398 |
| 0001 | BVM3 | 13.851 | 13.851 | 5.1832 | 11.789 | 0.044565 | 0.042085 |
| 0010 | BVM1 | 12.271 | 12.271 | 2.3508 | 5.7153 | 0.017039 | 0.019761 |
| 0010 | BVM2 | 16.161 | 16.161 | 4.7115 | 11.205 | 0.040482 | 0.037854 |
| 0010 | BVM4 | 13.523 | 13.523 | 4.7173 | 10.666 | 0.040695 | 0.040235 |
| 0100 | BVM1 | 22.8 | 22.8 | 5.6849 | 13.491 | 0.050112 | 0.046427 |
| 0100 | BVM3 | 16.62 | 16.62 | 4.5214 | 10.778 | 0.042254 | 0.037384 |
| 0100 | BVM4 | 7.6016 | 7.6016 | 1.5863 | 3.8299 | 0.01244 | 0.01353 |
| 1000 | BVM2 | 26.454 | 26.454 | 5.8369 | 14.324 | 0.061005 | 0.049889 |
| 1000 | BVM3 | 12.39 | 12.39 | 1.9139 | 4.8266 | 0.015613 | 0.021687 |
| 1000 | BVM4 | 7.046 | 7.046 | 0.83736 | 2.1255 | 0.0058233 | 0.010271 |

## 3. Multi-active actual vs one-hot superposition

`Delta_X(mask)=X(mask)-X(0000)`；`Delta_X_pred=sum(Delta_X(one-hot))`；残差为 actual-predicted。没有预设 5%/10% 合格阈值，保留 max abs、RMS、signed integral、peak-time difference、normalized RMS 和 correlation。

| direction | mask | LIN residual max abs (uA) | LIN normalized RMS | max per-BVM LSL residual (uA) | QBIN residual max abs (mV) | QBIN normalized RMS |
|---|---|---:|---:|---:|---:|---:|
| forward | 1100 | 41.248 | 0.4142 | 83.229 | 0.57572 | 0.97779 |
| forward | 1110 | 103.08 | 0.6067 | 77.032 | 0.96501 | 0.9666 |
| forward | 1111 | 205.38 | 0.58554 | 79.628 | 1.4748 | 0.99969 |
| reverse | 0011 | 62.831 | 1.1011 | 42.809 | 0.36981 | 0.89396 |
| reverse | 0111 | 116.25 | 0.49709 | 91.301 | 0.80052 | 0.97131 |
| reverse | 1111 | 205.38 | 0.58554 | 79.628 | 1.4748 | 0.99969 |

## 4. 有界结论（仅限本 fixture）

基于上述三组优先证据，本轮不支持把四颗 BVM 描述为在当前共享 RSL/SL fixture 中提供相对独立、可近似线性叠加的 unit-current 源。

- **Observed:** one-hot active 响应随位置明显变化；array one-hot 与 isolated single 的 branch waveform 不能视为同协议等价。
- **Observed:** 每个 one-hot run 中，三个 commanded-0、但先前经过 all-one WRITE1 的 victim 都相对 0000 出现非零 RSL/LSL；差异还出现在 RS、LS3、LM3 以及 JM1/JM2 phase probes。
- **Observed:** multi-active 实际波形与 one-hot superposition 的 LIN、每路 LSL 和 QBIN 残差达到事件/波形尺度；因此当前数据不支持 near-linear accumulation。
- **Caveat:** task-local 的 all-one stored-1111 closure 没有被四颗 BVM 全部确认：JM1 WRITE1 约为 2 turns，但 JM2 约为 0.124 turns，低于本轮描述性 0.25-turn marker。因而不能把所有 victim 的小响应简单表述为完整存储态下的隔离失败，也不能据此否定所有可能的其他协议。
- **Inference:** 在本固定历史模型、固定偏置、固定步长和固定拓扑下，证据更接近 `cross-coupling/back-action + position-dependent response + non-additive accumulation`；耦合的具体物理路径仍是 Unknown。

## 5. RSL / RS||LS3 / KCL

RSL 的 `V*I` 和积分能量、RS/LS3 的支路电流分配以及五组 BVM KCL 只用于验证方向、层级和 current partition；它们不是独立性 gate。完整结果见 `metrics.json`。

## 6. QB/JTL 次级诊断

BJ2 与 JTL6 B02 保存同 JJ phase/voltage-area 与 shared strict event-list 诊断。phase turns、whole-window voltage area 和 local segment 数均不直接等于 SFQ received count。

| mask | BJ2 READ phase delta (turns) | BJ2 strict clean events (diagnostic) | JTL6 B02 phase delta (turns) | JTL6 B02 strict clean events (diagnostic) |
|---|---:|---:|---:|---:|
| 0000 | -0.00089027 | 0 | -1.5915e-08 | 0 |
| 0001 | -0.000751 | 0 | -1.5915e-08 | 0 |
| 0010 | -0.00067203 | 0 | -1.5915e-08 | 0 |
| 0100 | -0.00063172 | 0 | -1.5915e-08 | 0 |
| 1000 | -0.00062946 | 0 | -1.5915e-08 | 0 |
| 0011 | 0.99908 | 1 | 1 | 1 |
| 0111 | 2.9991 | 0 | 3 | 3 |
| 1100 | 1.9993 | 0 | 2 | 2 |
| 1110 | 2.9987 | 0 | 3 | 3 |
| 1111 | 4.9992 | 0 | 5 | 5 |

## 7. 证据分层

**Observed:** raw 中的四路控制、四个 hierarchical BVM 的直接 branch P/V/I、BVMout、QB 和六级 JTL 探针；10 个 mask 各有独立 deck/raw/log/metadata。

**Derived:** 同一 raw 网格上的 one-hot-vs-0000 差分、one-hot 叠加预测、残差统计、RSL 功率/能量、RS||LS3 分配和 KCL residual。P 原始单位是 rad；只有明确转换后的字段才是 continuous phase turns。

**Inference:** 若 inactive victim 的 Delta RSL/LSL/RS/LS3/JS 或 storage probe 显著非零，则说明当前 fixture 中存在 READ-associated cross-coupling；若 multi-active residual 相对 one-hot 叠加不小，则不能把共享 SL 解释为近似线性累加。active-vs-single 只能作为 bounded contextual comparison。

**Unknown:** 本轮不能证明论文机制、普适 RSL isolation、unit current 的工艺独立性、canonical BVM 兼容性、硬件行为或系统 QB 逻辑正确性；也没有做参数、bias、timestep、T1 或完整 16-state matrix。

## 8. 文件与 gate

主数据：`analysis/metrics.json`；独立复算：`analysis/independent_check.json`；图索引：`plots/RESULT_OVERVIEW.html`。本轮结束后 gate 必须保持 `AWAITING_USER_REVIEW`、`user_reviewed: false`、`next_step_authorized: false`，不自动启动后续实验。

当前 primary classification 不由 QB 输出数量决定，而由上述三组 array evidence 是否支持相对独立/近似 additivity 决定；在人工审阅前不升级为 PASS/FAIL 或论文结论。
