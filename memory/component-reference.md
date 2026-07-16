---
name: component-reference
description: JoSIM 项目元件参考 — 所有已验证元件的 I/O 参数、测试数据、可视化索引
metadata:
  type: reference
  node_type: memory
---

# JoSIM 项目元件参考手册

> **模型**: jjmit (Ic×RN=1.6mV) | **仿真器**: josim-cli v2.7

---

## 一、ColdFlux 标准元件 (8/35 已验证)

### 1.1 JTL — 约瑟夫森传输线

| 属性 | 值 |
|------|-----|
| JJ 数 | 2 (B1/B2, area=2.5/2.5, IC=250µA) |
| 端口 | a(输入), q(输出) |
| 类型 | 异步 |
| 功能 | SFQ 脉冲传播, B1→B2 顺序翻转 |
| 测试文件 | `test/standard/test_jtl.cir` |
| 可视化 | `test/standard/jtl.html` |

**I/O 特性**:
- 输入: SFQ 脉冲 (2ps, 经 3Ω+0.5pH 注入)
- 输出: 1 SFQ (B1→B2 各翻转 1 次)
- 验证: P(B2)/2π = 1.00 SFQ ✅

### 1.2 SPLIT — SFQ 分路器

| 属性 | 值 |
|------|-----|
| JJ 数 | 3 |
| 端口 | a(输入), q0(输出1), q1(输出2) |
| 类型 | 异步 |
| 功能 | 1→2 扇出 |
| 测试文件 | `test/standard/test_split.cir` |
| 可视化 | `test/standard/split.html` |

### 1.3 MERGE — SFQ 汇合器

| 属性 | 值 |
|------|-----|
| JJ 数 | 7 |
| 端口 | a, b(输入), q(输出) |
| 类型 | 异步 |
| 测试文件 | `test/standard/test_merge.cir` |
| 可视化 | `test/standard/merge.html` |

### 1.4 DFF — D 触发器

| 属性 | 值 |
|------|-----|
| JJ 数 | 7 |
| 端口 | a(D输入), clk, q |
| 类型 | 钟控 |
| 测试文件 | `test/standard/test_dff.cir` |
| 可视化 | `test/standard/dff.html` |

### 1.5 XOR — 异或门

| 属性 | 值 |
|------|-----|
| JJ 数 | 11 |
| 端口 | a, b, clk, q |
| 真值表 | 0⊕0=0, 1⊕0=1, 1⊕1=0, 0⊕1=1 |
| 测试文件 | `test/standard/test_xor.cir` |
| 可视化 | `test/standard/xor.html` |

### 1.6 AND2 — 与门

| 属性 | 值 |
|------|-----|
| JJ 数 | 15 |
| 端口 | a, b, clk, q |
| 真值表 | 1∧1=1, 1∧0=0 |
| 测试文件 | `test/standard/test_and2.cir` |
| 可视化 | `test/standard/and2.html` |

### 1.7 NDRO — 非破坏读出

| 属性 | 值 |
|------|-----|
| JJ 数 | 11 |
| 端口 | a(写), b(复位), clk, q |
| 功能 | 写→读(有输出)→复位→读(无输出) |
| 测试文件 | `test/standard/test_ndro.cir` |
| 可视化 | `test/standard/ndro.html` |

### 1.8 NOT — 反相器

| 属性 | 值 |
|------|-----|
| JJ 数 | 8 |
| 端口 | a, clk, q |
| 真值表 | NOT(0)=1, NOT(1)=0 |
| 测试文件 | `test/standard/test_not.cir` |
| 可视化 | `test/standard/not.html` |

---

## 二、BVM — 双稳态涡旋存储器

| 属性 | 值 |
|------|-----|
| 结 | JM1(120µA), JM2(140µA), JS1/JS2(74µA) |
| 端口 | WL, BL, SE, SL |
| 存储状态 | "1": P(JM1)=±0.94×2π, "0": P(JM1)≈0 |
| SL 输出阻抗 | ~130Ω |
| SL 峰值电流 (读) | 68-78µA (取决于 SL 负载) |
| 测试文件 | `test/final/bvm/test_bvm_final.cir` |
| 可视化 | `test/final/bvm/bvm_standalone.html` |

**验证状态**: ✅ 独立工作正常 (写/读/半选)

---

## 三、BQ — 缓冲/量化器

### 3.1 标准 BQ (bq_cell.cir)

| 属性 | 值 |
|------|-----|
| 结 | BJs(50µA), BJL1(36µA), BJL2(54µA) |
| 偏置 | IBias=35µA (70% of BJs IC) |
| 输入电感 | Lin=0.8pH |
| 独立触发阈值 | ~90µA (矩形脉冲) |
| 输出 | Vpk=1035µV (90µA 驱动) |
| 来源 | 基于 SUST 2024 论文, IC 缩小 ~3× |

### 3.2 量化特性

| I_IN | 总 SFQ (相位) | Load JTL B1 | Vpk | 可用? |
|------|-------------|-------------|-----|------|
| 70µA | 48 | 0.1 | 306µV | ❌ |
| 90µA | 48 | 0.1 | 352µV | ❌ |
| 110µA | 54 | **3.1** | 751µV | ✅ |
| 130µA | 60 | 3.1 | 672µV | ✅ |
| 150µA | 66 | 3.1 | 756µV | ✅ |
| 170µA | — | 3.1 | 724µV | ✅ |

**结论**: BQ 有阈值效应——<90µA 无输出, ≥110µA 输出 ~3 SFQ。
但输出 SFQ 数不随输入电流比例变化（饱和在 3.1 SFQ）。
**不满足**"电流→可变 SFQ 数"的量化器要求。

**可视化**:
- `test/final/qb/bq_standalone_90uA.html`
- `test/final/qb/bq_quant_90uA.html`
- `test/final/qb/bq_quant_130uA.html`
- `test/final/qb/bq_quant_170uA.html`

---

## 四、BVM→BQ 级联测试

| 实验 | BQ | SL I_pk | BJs 相位 | 离散 SFQ | Vpk | 结果 |
|------|-----|---------|---------|---------|-----|------|
| 基线 | 标准(50µA) | 68µA | 1.0 SFQ | 0 | 157µV | ❌ |
| 低 IC v3 | BJs=20µA | 34µA | 14 SFQ | 0 | 129µV | ❌ |
| K 变压器 n=2 | 标准 | 75µA | 0 SFQ | 0 | 77µV | ❌ |
| 论文 BQ | JS=133µA | 78µA | 0 SFQ | 0 | 97µV | ❌ |

**可视化**: `test/final/single_bvm_qb/baseline.html`

---

## 五、SFQ 发生器

| 元件 | JJ | 测试 | 状态 |
|------|-----|------|------|
| sfq_gen_clk | area=3.5 (IC=350µA) | 4/4 正确 | ✅ |
| sfq_gen_i | area=3.5 (IC=350µA) | 10/10 正确 | ✅ |

---

## 六、待测试元件

- OR2 (12 JJ), XNOR (19 JJ), BUFF (4 JJ)
- PTL 变体 (JTLT/SPLITT/MERGET/AND2T/OR2T/XORT/NOTT/DFFT/NDROT/BUFFT)
- Interface (DCSFQ, SFQDC, PTLTX, PTLRX)
- ALWAYS0 系列 (8 个)
