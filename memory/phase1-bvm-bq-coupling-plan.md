---
name: phase1-bvm-bq-coupling-plan
description: Paper A Phase 1 详细执行计划 — BVM→BQ 耦合双路线实验，含任务拆解、时间规划、验收标准
metadata:
  type: project
  node_type: memory
---

# Paper A Phase 1: BVM→BQ 接口耦合实验 — 详细执行计划

> **目标论文**: "Interface Design and Impedance Matching for BVM-to-QB Coupling in Superconducting In-Memory Computing"
> **Phase 1 目标**: 完成双路线实验，收集全部数据，投 arXiv 预印本
> **日期**: 2026-07-13 | **计划版本**: v1.0

---

## 零、实用性再确认

### BVM→QB 接口问题值得讨论吗？

**结论：值得。理由如下。**

| 论点 | 证据 |
|------|------|
| **整个 BVM 领域都在仿真阶段** | 2024 SUST 论文和 2025 arXiv 论文都是纯 SPICE/JoSIM 仿真，无流片 |
| **接口是系统瓶颈** | 32×32 BVM 阵列需要每列共享 SL→QB 读出链，阻抗失配在阵列规模下放大 |
| **BVM 在与其他 SFQ 存储竞争** | VTM、nTron、JMRAM 都在争取成为标准超导存储——BVM 的读出可靠性直接影响竞争力 |
| **设计阶段的质量决定一切** | 没有硬件可以调参，仿真级的设计决策有放大效应 |
| **Chen et al. (2025) 证明了同类问题的价值** | SFQ→CMOS 接口匹配能发表 IEICE，说明评审认可接口设计是 legitimate research contribution |
| **USC 组论文的沉默是信号** | 他们只说了 "threshold matched"，没提 impedance——要么没发现（我们的机会），要么认为不重要（我们可以证明它重要） |

### 反驳"可能不重要"的论点

| 质疑 | 反驳 |
|------|------|
| "USC 组调阈值就行了" | 单 cell 可以调阈值，但 4×4、8×8 阵列的多 cell 累加场景下，阻抗失配导致电流传递率的非线性——阈值调不了 |
| "纯仿真有什么实际意义" | 整个 BVM 领域都是纯仿真。我们的接口设计方法论是仿真阶段的正确工作 |
| "审稿人可能觉得太工程" | 框架定位：首次系统表征（类似 Chen et al. 的 TIA vs VA 比较），不是"我们修了一个 bug" |

---

## 一、文件清单

### 将修改的文件

| 文件 | 修改内容 |
|------|---------|
| `circuits/qb/bq_cell.cir` | 创建低 IC 变体: BJs area 0.15-0.30 参数扫描版本 |
| `circuits/qb/bq_cell_lowic.cir` | **新建**: 低 IC 检测结 BQ 子电路 |
| `circuits/coupling/tx_1to2.cir` | **新建**: K 元件 1:2 变压器子电路 |
| `test/final/single_bvm_qb/test_bvm_bq_baseline.cir` | **新建**: BVM→BQ 级联基线测试 |
| `test/final/single_bvm_qb/test_bvm_bq_lowic.cir` | **新建**: 低 IC 方案测试 |
| `test/final/single_bvm_qb/test_bvm_bq_tx.cir` | **新建**: 变压器方案测试 |
| `memory/paper-directions-analysis.md` | 更新实验结果 |
| `memory/pim-roadmap-design.md` | 更新 Phase 1 进度 |

### 不修改的文件

- `circuits/bvm/bvm_cell.cir` — BVM 保持不变
- `circuits/models/jjmit.cir` — JJ 模型不变
- `test/standard/*` — 标准元件测试不动

---

## 二、任务拆解

### Task 1: BVM→BQ 级联基线测试（建立 failure baseline）

**目标**: 复现并量化 BVM→BQ 的失效行为，作为论文的 Problem Characterization 数据

**Files:**
- Create: `test/final/single_bvm_qb/test_bvm_bq_baseline.cir`
- Read: `circuits/bvm/bvm_cell.cir`, `circuits/qb/bq_cell.cir`

- [ ] **Step 1: 创建基线测试网表**

```spice
* BVM→BQ Baseline Coupling Test — Problem Characterization
* Quantifies impedance mismatch: ~15uA reaches BQ, BJs needs 50uA
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/bvm/bvm_cell.cir
.include ../../../circuits/qb/bq_cell.cir

* BVM instance
XBVM1 WL1 BL1 SE1 SL1 BVM

* SL load: 8x jjmit(area=3.2) stack
B_LD1 SL1 nld1 jjmit area=3.2
B_LD2 nld1 nld2 jjmit area=3.2
B_LD3 nld2 nld3 jjmit area=3.2
B_LD4 nld3 nld4 jjmit area=3.2
B_LD5 nld4 nld5 jjmit area=3.2
B_LD6 nld5 nld6 jjmit area=3.2
B_LD7 nld6 nld7 jjmit area=3.2
B_LD8 nld7 0 jjmit area=3.2

* BQ instance (baseline: BJs IC=50uA)
XBQ1 SL1 QB_OUT IBIAS BQ
R_LOAD QB_OUT 0 10

* Write "1": WL+BL @10-20ps
I_WL1 0 WL1 pwl(0 0 9p 0 10p 100U 20p 100U 21p 0 100p 0)
I_BL1 0 BL1 pwl(0 0 9p 0 10p 100U 20p 100U 21p 0 100p 0)

* Read: SE @30-40ps
I_SE1 0 SE1 pwl(0 0 29p 0 30p 100U 40p 100U 41p 0 100p 0)

* BQ bias
I_IBIAS 0 IBIAS pwl(0 0 1p 35u)

.tran 0.1p 100p

* Key measurements
.print I(L_SL|XBVM1) I(Lin|XBQ1)
.print P(B_JM1|XBVM1) P(BJs|XBQ1) P(BJL1|XBQ1) P(BJL2|XBQ1)
.print V(SL1) V(QB_OUT)
.end
```

- [ ] **Step 2: 运行基线仿真**

```bash
./build/josim-cli -o /tmp/baseline.csv test/final/single_bvm_qb/test_bvm_bq_baseline.cir
```

- [ ] **Step 3: 提取关键指标**

```bash
python3 -c "
import csv
with open('/tmp/baseline.csv') as f:
    rows = list(csv.reader(f))
    header = rows[0]
    # Find I(SL) and QB output
    # Expected: I(SL) peak ~15uA, QB output = NO SFQ (failure)
    print('Baseline: BVM SL current peak, QB output SFQ count')
"
```

- [ ] **Step 4: 记录基线数据**

预期结果（用于论文 Fig.3 Problem Characterization）:
- BVM SL 电流峰值: ~55µA (存储环读出)
- BQ 输入端电流: ~15µA (27% 传递)
- BJs IC: 50µA (未触发)
- QB 输出: 0 SFQ (失败)
- 缺口: 35µA

**验收标准**: 仿真完成，数据确认 BVM 独立工作但 BQ 无输出

---

### Task 2: 低 IC 检测结 BQ 变体设计

**目标**: 创建参数化的低 IC BQ 子电路

**Files:**
- Create: `circuits/qb/bq_cell_lowic.cir`

- [ ] **Step 1: 创建低 IC BQ 子电路**

```spice
* BQ Buffer Cell — Low-IC Variant for BVM Coupling
* BJs IC reduced from 50uA to 20uA (area 0.5→0.2)
* IBias scaled proportionally: 35uA→14uA (70% rule)
* BJL1/BJL2 IC and shunt resistors rescaled to preserve Bc≈1
*
* Parameters:
*   BJs  area=0.20  IC=20uA   RN=80Ω   (was 0.50, 50uA, 32Ω)
*   BJL1 area=0.14  IC=14uA   RJ1=82Ω  (was 0.36, 36uA, 33Ω)
*   BJL2 area=0.22  IC=22uA   RJ2=52Ω  (was 0.54, 54uA, 22Ω)
*   IBias = 14uA (was 35uA)
*
* Trigger check: I_arrive(15uA) + IBias(14uA) = 29uA > IC_BJs(20uA) ✓

.subckt BQ_LOWIC IN OUT IB

Lin IN 1 0.8p
L0 4 OUT 1.323p
L1 2 3 3.91p
L2 3 4 3.91p
BJs 1 2 jjmit area=0.20
BJL1 2 0 jjmit area=0.14
RJ1 2 0 82
BJL2 4 0 jjmit area=0.22
RJ2 4 0 52
RB IB 3 6

.ends BQ_LOWIC
```

- [ ] **Step 2: 创建低 IC 方案测试网表**

```spice
* BVM→BQ Low-IC Coupling Test
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/bvm/bvm_cell.cir
.include ../../../circuits/qb/bq_cell_lowic.cir

XBVM1 WL1 BL1 SE1 SL1 BVM

* SL load (same as baseline)
B_LD1 SL1 nld1 jjmit area=3.2
* ... (8x stack)
B_LD8 nld7 0 jjmit area=3.2

* Low-IC BQ
XBQ1 SL1 QB_OUT IBIAS BQ_LOWIC
R_LOAD QB_OUT 0 10

* BVM write/read (same as baseline)
I_WL1 0 WL1 pwl(0 0 9p 0 10p 100U 20p 100U 21p 0 100p 0)
I_BL1 0 BL1 pwl(0 0 9p 0 10p 100U 20p 100U 21p 0 100p 0)
I_SE1 0 SE1 pwl(0 0 29p 0 30p 100U 40p 100U 41p 0 100p 0)

* Reduced bias for low-IC BQ
I_IBIAS 0 IBIAS pwl(0 0 1p 14u)

.tran 0.1p 100p
.print I(L_SL|XBVM1) P(BJs|XBQ1) P(BJL1|XBQ1) P(BJL2|XBQ1) V(QB_OUT)
.end
```

- [ ] **Step 3: 运行低 IC 方案仿真**

```bash
./build/josim-cli -o /tmp/lowic_baseline.csv test/final/single_bvm_qb/test_bvm_bq_lowic.cir
```

**验收标准**: BQ 输出 ≥1 SFQ 脉冲

---

### Task 3: 低 IC 方案参数扫描

**目标**: 找到 BJs area 的最优工作区间

**Files:**
- Create: `test/final/single_bvm_qb/scan_lowic.sh`

- [ ] **Step 1: 创建参数扫描脚本**

```bash
#!/bin/bash
# Low-IC BJs parameter sweep: area from 0.15 to 0.30, step 0.05
for area in 0.15 0.20 0.25 0.30; do
    ibias=$(python3 -c "print($area * 70)")  # 70% of IC
    
    # Generate test file with current area value
    sed "s/area=0\.20/area=$area/g; s/I_IBIAS 0 IBIAS pwl(0 0 1p 14u)/I_IBIAS 0 IBIAS pwl(0 0 1p ${ibias}u)/g" \
        test/final/single_bvm_qb/test_bvm_bq_lowic.cir \
        > /tmp/scan_lowic_${area}.cir
    
    ./build/josim-cli -o /tmp/scan_lowic_${area}.csv /tmp/scan_lowic_${area}.cir
    
    # Extract results
    python3 -c "
import csv
with open('/tmp/scan_lowic_${area}.csv') as f:
    rows = list(csv.reader(f))
    # Find QB output SFQ count from BJs phase
    # ... 
    print(f'area=${area}: SFQ_count={count}, success={count>=1}')
"
done
```

- [ ] **Step 2: 运行参数扫描**

```bash
bash test/final/single_bvm_qb/scan_lowic.sh | tee /tmp/lowic_scan_results.txt
```

- [ ] **Step 3: 绘制触发窗口图**

预期产出：BJs area vs SFQ 输出数 的图表（论文 Fig.5a）

**验收标准**: 确认触发窗口宽度（至少 3 个 area 值成功）

---

### Task 4: K 元件变压器方案

**目标**: 设计并测试变压器耦合方案

**Files:**
- Create: `circuits/coupling/tx_k_element.cir`

- [ ] **Step 1: 创建 K 元件变压器子电路**

```spice
* K-Element Transformer 1:2 for BVM→BQ Coupling
* Turns ratio n = sqrt(L_sec/L_pri) = sqrt(8p/2p) = 2
* Current gain = n * k = 2 * 0.9 = 1.8
* BVM I_out ~15uA → TX I_out ~27uA → BQ gets 27uA+35uA=62uA > 50uA ✓

.subckt TX_1TO2 IN OUT GND
L_PRI IN GND 2p
L_SEC OUT GND 8p
K_TX L_PRI L_SEC 0.9
.ends TX_1TO2
```

- [ ] **Step 2: 创建变压器方案测试网表**

```spice
* BVM→TX→BQ Coupling Test
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/bvm/bvm_cell.cir
.include ../../../circuits/coupling/tx_k_element.cir
.include ../../../circuits/qb/bq_cell.cir

XBVM1 WL1 BL1 SE1 SL1 BVM

* TX between BVM SL and BQ IN
XTX SL1 TX_OUT 0 TX_1TO2

XBQ1 TX_OUT QB_OUT IBIAS BQ
R_LOAD QB_OUT 0 10

* BVM signals (same as baseline)
I_WL1 0 WL1 pwl(0 0 9p 0 10p 100U 20p 100U 21p 0 100p 0)
I_BL1 0 BL1 pwl(0 0 9p 0 10p 100U 20p 100U 21p 0 100p 0)
I_SE1 0 SE1 pwl(0 0 29p 0 30p 100U 40p 100U 41p 0 100p 0)
I_IBIAS 0 IBIAS pwl(0 0 1p 35u)

.tran 0.1p 100p
.print I(L_SL|XBVM1) I(L_PRI|XTX) I(L_SEC|XTX)
.print P(BJs|XBQ1) V(QB_OUT)
.end
```

- [ ] **Step 3: 运行变压器方案仿真**

```bash
./build/josim-cli -o /tmp/tx_baseline.csv test/final/single_bvm_qb/test_bvm_bq_tx.cir
```

**验收标准**: BQ 输出 ≥1 SFQ

---

### Task 5: 变压器参数扫描

**目标**: 扫描匝数比 n 和耦合系数 k

- [ ] **Step 1: 扫描 n=1.5, 2.0, 2.5, 3.0 和 k=0.7, 0.8, 0.9**

共 4×3=12 组仿真

- [ ] **Step 2: 记录每组的结果（电流增益、BQ 触发、延迟）**

产出：n-k 热力图（论文 Fig.5b）

---

### Task 6: 双方案对比分析

**目标**: 生成论文 Comparative Analysis 的所有数据

- [ ] **Step 1: 对比指标**

| 指标 | 低 IC 方案 | 变压器方案 |
|------|-----------|-----------|
| BQ SFQ 输出 | ≥1 | ≥1 |
| IBias 功耗 | 14µA×2.6mV=36.4nW | 35µA×2.6mV=91nW |
| 面积代价 | 0 (仅改 area) | TX: 2×10×10µm² |
| 时序延迟 | 0 (无额外元件) | ~0.5ps (TX 延迟) |
| 噪声裕度 | 9µA (45%) | 12µA (24%) |
| 参数敏感性 | 中 (BJs area ±0.05) | 低 (n±0.5, k±0.1) |

- [ ] **Step 2: 生成雷达图和对比表**（论文 Fig.6）

---

### Task 7: 扰动鲁棒性测试

**目标**: 定义"可发布的工作区间"

- [ ] **Step 1: IBias 扰动 (±20%)**
- [ ] **Step 2: 脉冲宽度扰动 (1.5ps, 2ps, 3ps)**
- [ ] **Step 3: JJ 模型参数扰动 (IC ±10%)**

**验收标准**: 确定两种方案的工作窗口边界

---

### Task 8: 论文初稿撰写（使用 ARS skills）

详见 Paper A 论文大纲（paper-directions-analysis.md §三.方向1）

- [ ] **Step 1: 调用 `ars-plan` 生成论文大纲和证据映射**
- [ ] **Step 2: 调用 `academic-paper` 生成初稿**
- [ ] **Step 3: 调用 `ars-reviewer` 内部审稿**
- [ ] **Step 4: 修改定稿**
- [ ] **Step 5: 投 arXiv 预印本**

---

## 三、时间规划（弹性版）

**工作节奏**: 每周 4 天，每天 3-5 小时 (12-20h/week)

```
Week 1:
  Day 1 (3-5h):
    ├── Task 1: BVM→BQ 基线测试 (1.5h)
    └── Task 2: 低 IC BQ 设计 + 测试 (2-3h)
  
  Day 2 (3-5h):
    ├── Task 3: 低 IC 参数扫描 (2-3h)
    └── Task 4: K 元件变压器设计 (开始, 1-2h)
  
  Day 3 (3-5h):
    ├── Task 4: K 元件变压器 (完成, 1-2h)
    └── Task 5: 变压器参数扫描 (2-3h)
  
  Day 4 (3-5h):
    ├── Task 6: 双方案对比分析 (1.5h)
    └── Task 7: 扰动鲁棒性测试 (2-3h)

Week 2:
  Day 5 (3-5h):
    ├── Task 7: 鲁棒性测试 (收尾, 1h)
    └── Task 8: ARS ars-plan 论文大纲 (2-3h)
  
  Day 6 (3-5h):
    ├── Task 8: ARS academic-paper 初稿 (3-5h)
  
  Day 7 (3-5h):
    ├── Task 8: ARS ars-reviewer 内部审稿 (2h)
    └── Task 8: 修改定稿 (2-3h)
  
  Day 8 (2-3h):
    └── 最终检查 + 投 arXiv

──────────────────────────
总计: 8 个工作日 (~2 周)
工时: 25-35 小时 (含余量)
```

### 关键里程碑

| 日期 | 里程碑 | Gate 条件 |
|------|--------|-----------|
| W1D2 结束 | 低 IC 方案完成 | ≥1 个 area 值 BQ 输出 SFQ |
| W1D4 结束 | 全部实验数据收集完毕 | 6 组实验全部完成 |
| W2D2 结束 | 论文初稿完成 | ARS reviewer 评分 ≥4/5 |
| W2D4 | arXiv 预印本提交 | 预印本编号 |

---

## 四、验收标准

### 实验可靠性规范（所有实验必须遵守）

#### 1. 可复现性要求

| 要求 | 做法 |
|------|------|
| **固定仿真参数** | `.tran` 步长固定为 0.1ps，不随意调整 |
| **版本追踪** | 每个 .cir 文件头部记录修改日期和变更说明 |
| **原始数据保留** | 所有 CSV 输出保存到 `/tmp/` 并以实验名命名，不覆盖 |
| **模型一致性** | 所有实验使用同一份 `circuits/models/jjmit.cir` |

#### 2. 结果验证

| 验证项 | 方法 |
|--------|------|
| **SFQ 计数** | 用 P(B|X) 相位变化除以 2π，不依赖肉眼判断电压波形 |
| **BVM 状态确认** | 每次实验前确认 P(JM1) = ±0.94×2π ("1"状态) 或 ≈0 ("0"状态) |
| **基线对照** | 每次实验包含独立 BVM 和独立 BQ 的对照仿真 |
| **重复性** | 关键数据点（如最优 BJs area）跑 2 次确认结果一致 |

#### 3. 数据记录

```
每次实验记录以下信息：
  - 实验名称 + 日期
  - .cir 文件的 git commit hash
  - josim-cli 版本 (josim-cli --version)
  - 关键参数值 (BJs area, IBias, n, k 等)
  - 结果摘要 (SFQ 计数, 是否触发, 峰值电流)
  - CSV 文件路径
```

#### 4. 常见陷阱

| 陷阱 | 预防 |
|------|------|
| **偏置未稳定** | 检查 bias 在 5ps 后达到稳态值 |
| **脉冲宽度不一致** | 所有 PWL 严格使用 2ps 模板 |
| **时序错误** | 钟控元件: 数据必须在时钟之前 |
| **Load JTL 误触发** | 确认 Load JTL 的 IC 高于预期 SFQ 幅度 |
| **CSV 时间列舍入** | 分析时用 `float(row[0]) * 1e12` 转为 ps |

### Phase 1 总 Gate

- [ ] 基线测试量化了阻抗失配（数据 ≥3 个时间点的 I(SL) 和 I(BQ_in)）
- [ ] ≥1 条路线 BQ 输出 ≥1 SFQ
- [ ] 参数扫描覆盖 ≥3 个参数值
- [ ] 对比分析表完成（≥6 个指标）
- [ ] 鲁棒性测试完成（≥2 个扰动维度）
- [ ] 论文初稿完成（使用 ARS skills）
- [ ] arXiv 预印本已提交

[[pim-roadmap-design]] [[paper-directions-analysis]] [[bvm-bq-coupling]]
