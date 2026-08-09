# DCSFQ_BVM Phase 1 实施计划（V1-V4b 验证链）

> [!CAUTION]
> **状态：BLOCKED / SUPERSEDED（2026-08-09）。不得按本文执行。** 本计划依赖的 `sfq_metrics.py` 把 raw rad 当 SFQ，V1 又混入偏置启动，V2 的 `fast_events` 不是事件数；45–55 µA 目标来自已被推翻的 300 µA 多滑移解释；V4 的 a/q 对调也不构成极性反转。先完成 `docs/HANDOVER.md` 的 Phase −1 计量修复和基线重建，再另写修订计划。

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 V1-V4b 验证链，找到 45-55µA 工作点的**干净单 SFQ 窗口**并冻结 DCSFQ_BVM 最终参数，打通 BVM 级联（读1 → 恰好 1 个被 JTL 接收的 SFQ，读0 → 0）。

**Architecture:** 元件变体矩阵（输入网络 L2/L3 × IC 候选）→ V2 阈值判别扫描（决策门 G7，bounded）→ 定稿参数 → V3 输出级 JTL 验证 → V4 BVM 级联（含极性验证）→ V4b 去链对照。沿用 P0 冻结口径（sfq_metrics.py / md5 / pwl / 禁 sed）。

**Tech Stack:** build/josim-cli v2.7.2837d13、jjmit、scripts/sfq_metrics.py、scripts/run_exp.sh、subagent 执行 + 双审查。

**Spec 依据:** `docs/superpowers/specs/2026-08-06-dcsfq-bvm-cell-design.md` 修订 2 + `test/final/interface/P0_LOG.md`（G1-G5 + 接口规格）

**执行纪律:**
- 变体文件全部 Write 创建（禁 sed）；单次 pwl；CSV 提交 data/；md5 确定性；每 Task 双审查
- **V2 有界**：网络矩阵 4 变体 × 输入扫描 ≤8 水平 × 至多 2 轮 IC 候选——到 bound 未找到窗口即判定并转决策表（方案二/H6），不无限迭代
- 元件变体只在 `circuits/interface/` 下新增文件，**不改** `DCSFQ_BVM.cir` 原文件和标准库

---

### Task 1: 元件变体准备（输入网络 × IC 矩阵）

**Files:**
- Create: `circuits/interface/DCSFQ_BVM_L2_6p.cir`（L2 3.9→6p）
- Create: `circuits/interface/DCSFQ_BVM_L2_10p.cir`（L2 3.9→10p）
- Create: `circuits/interface/DCSFQ_BVM_L3_03p.cir`（L3 0.6→0.3p）
- Create: `circuits/interface/DCSFQ_BVM_B06.cir`（B1/B2 0.8→0.6, IB1 100u→80u）

- [ ] **Step 1: 创建 4 个变体**

每个 = 复制 `circuits/interface/DCSFQ_BVM.cir`，只改头部注释 + 对应 .param 行：

| 变体 | 改动 | 设计意图 |
|---|---|---|
| `DCSFQ_BVM_L2_6p.cir` | `.param L2=3.9p` → `6p` | 增大到地阻抗 → 逼更多输入进结支路（提耦合） |
| `DCSFQ_BVM_L2_10p.cir` | `.param L2=3.9p` → `10p` | 更强耦合试探（bound：10p 为止） |
| `DCSFQ_BVM_L3_03p.cir` | `.param L3=0.6p` → `0.3p` | 减小耦合电感 → 输入更快进结支路 |
| `DCSFQ_BVM_B06.cir` | `.param B1/B2=0.8`→`0.6`，`IB1=100u`→`80u` | IC 下调候选（保持 ~60% 工作点） |

subckt 名保持 `THmitll_DCSFQ_BVM`（同文件内唯一，变体间不冲突）。

- [ ] **Step 2: 验证 diff**

```bash
cd /home/howard/JoSIM
for f in DCSFQ_BVM_L2_6p DCSFQ_BVM_L2_10p DCSFQ_BVM_L3_03p DCSFQ_BVM_B06; do
  diff circuits/interface/DCSFQ_BVM.cir circuits/interface/${f}.cir | head -8
done
```

期望：每个变体与基线仅差头部注释块 + 1-2 行 .param。

- [ ] **Step 3: 提交**

```bash
git add circuits/interface/ && git commit -m "feat(P1): DCSFQ_BVM variants — input network L2/L3 × IC candidates"
```

---

### Task 2: V1 — 偏置稳定性（基线变体）

**Files:**
- Create: `test/final/interface/test_v1_bias.cir`

- [ ] **Step 1: 写测试网表**（无输入，偏置建立后 200ps 观察）

```spice
* P1 V1 — bias stability: no input, IB1/IB2 on, 200ps window
* PASS: B1/B2/B3 net≈0, fast_events=0
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/interface/DCSFQ_BVM.cir

XDCSFQ IN1 OUT1 THmitll_DCSFQ_BVM
R_LOAD OUT1 0 10

.tran 0.1p 200p
.print V(OUT1) P(B1|XDCSFQ) P(B2|XDCSFQ) P(B3|XDCSFQ)
.end
```

- [ ] **Step 2: 运行 + 指标**

```bash
cd /home/howard/JoSIM
scripts/run_exp.sh test/final/interface/test_v1_bias.cir test_v1_bias "P(B1|XDCSFQ),P(B2|XDCSFQ),P(B3|XDCSFQ)" --peaks "V(OUT1)"
```

- [ ] **Step 3: Gate 判定** — net ∈ [−0.05, +0.05]，fast_events=0 → ✅；否则 STOP（偏置问题先于一切）

- [ ] **Step 4: 提交**（CSV/JSON 到 data/，日志写 `test/final/interface/P1_LOG.md` 分节 V1）

```bash
git add test/final/interface/ && git commit -m "feat(P1/V1): bias stability PASS"
```

---

### Task 3: V2 — 阈值判别扫描（决定性实验，bounded）

**Files:**
- Create: `test/final/interface/test_v2_scan.cir`（模板，.param IIN + 元件变体二选一）
- 生成变体：`test_v2_scan_<variant>_<IIN>.cir`（Write，禁 sed）

- [ ] **Step 1: 写扫描模板**（以基线变体 + IIN=68.4u 为基准）

```spice
* P1 V2 — threshold discriminator scan (variant + IIN parameterized)
* Find: clean single-SFQ window at read-1 level (68.4µA), threshold 45-55µA
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/interface/DCSFQ_BVM.cir   ; ← 变体时替换这行

.param IIN=68.4u

XDCSFQ IN1 OUT1 THmitll_DCSFQ_BVM
R_LOAD OUT1 0 10
I_IN 0 IN1 pwl(0 0 10p 0 12p IIN 40p IIN 45p 0)

.tran 0.1p 200p
.print V(OUT1) P(B1|XDCSFQ) P(B2|XDCSFQ) P(B3|XDCSFQ)
.print I(L1|XDCSFQ) I(L2|XDCSFQ) I(L3|XDCSFQ)
.end
```

- [ ] **Step 2: 步骤 A — 网络矩阵耦合标定（4 runs）**

固定 IC=0.8，输入 68.4µA，测 4 个网络变体（基线/L2_6p/L2_10p/L3_03p）的增量耦合系数（I(L3)Δ/I(L1)）与是否触发：

| 变体 | 期望 |
|---|---|
| 基线 | 0.285（P0.2 复现校验） |
| L2_6p | 耦合↑（L2 分流↓），可能触发 |
| L2_10p | 耦合↑↑ |
| L3_03p | 耦合↑（L3 阻抗↓） |

记录耦合系数表 → **选择耦合最高且仍稳定的变体**进入步骤 B（若全不触发且耦合 <0.4，记"网络调整不足"，直接进入步骤 C 的 B06）。

- [ ] **Step 3: 步骤 B — 输入水平扫描（≤8 runs）**

用步骤 A 选出的变体，扫描 IIN ∈ {0, 1.4u, 20u, 40u, 50u, 60u, 68.4u, 80u}。每点记录 net/fast_events/V(OUT1)。

**寻找**：I* ∈ [45, 68.4µA] 满足——IIN ≥ I* 时 net≈1±0.3 且 fast_events ∈ [1,3]（干净单 SFQ）；IIN < I* 不触发（fast=0）；68.4µA 恰好落在单 SFQ 区。

- [ ] **Step 4: 步骤 C — IC 候选轮（bound ≤1 轮）**

若步骤 B 无干净窗口：用 B06 变体重做步骤 B（同样 ≤8 runs）。两轮后仍无窗口 → **判定 V2 失败，停止，进入 Task 7 决策表**。

- [ ] **Step 5: Gate 判定（G7）**

| 判据 | 值 |
|---|---|
| 触发阈值 I* | ∈ [45, 55]µA |
| 68.4µA 处行为 | net ∈ [0.7, 1.3]，fast ∈ [1,3]（单 SFQ，无多滑移） |
| 读0 水平 (1.4µA) | net≈0，fast=0 |
| 确定性 | 关键点 md5 ×2 |

通过 → **冻结最终参数**（哪个变体 + 工作点）到 `P1_LOG.md`；不通过 → 决策表。

- [ ] **Step 6: 提交**

```bash
git add test/final/interface/ && git commit -m "feat(P1/V2): threshold scan — single-SFQ window determination"
```

---

### Task 4: V3 — 输出级 → Load JTL 接收

**Files:**
- Create: `test/final/interface/test_v3_jtl.cir`

- [ ] **Step 1: 写测试网表**（V2 定稿变体 + 触发水平输入，OUT → ColdFlux JTL）

```spice
* P1 V3 — output stage drives standard ColdFlux JTL
* PASS: JTL B1 receives ≥1 SFQ (net ≥ 1, fast ≥ 1)
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/interface/DCSFQ_BVM.cir   ; ← V2 定稿变体
.include ../../../circuits/standard/JTL.cir

.param IIN=68.4u   ; ← V2 定稿触发水平

XDCSFQ IN1 OUT1 THmitll_DCSFQ_BVM
I_IN 0 IN1 pwl(0 0 10p 0 12p IIN 40p IIN 45p 0)
XJTL OUT1 JTLQ THmitll_JTL
R_JTLQ JTLQ 0 10

.tran 0.1p 250p
.print V(OUT1) V(JTLQ) P(B1|XDCSFQ) P(B2|XDCSFQ) P(B3|XDCSFQ) P(B1|XJTL) P(B2|XJTL)
.end
```

- [ ] **Step 2: 运行 + Gate（G8）** — JTL B1 net ≥ 1 且 fast ≥ 1（BQ 从未做到的事）。输出级不足 → 记录并进决策表（不擅自改 B3/L6——冻结项）。

- [ ] **Step 3: 提交**

---

### Task 5: V4 — BVM 级联（含极性验证）

**Files:**
- Create: `test/final/single_bvm_qb/test_bvm_bq_dcsfq.cir`（基线网表替换 BQ → DCSFQ_BVM）

- [ ] **Step 1: 写级联网表**：复制 `test_bvm_bq_baseline.cir`，删 BQ 实例与 8-JJ 链尾接点，改为 SL 链 → DCSFQ_BVM（V2 定稿变体）→ Load JTL。驱动序列、`.tran 0.1p 110p`、JM1 相位打印保持与冻结基线一致。

- [ ] **Step 2: 运行 + 极性验证**

- 正向连接：R1 后 JTL B1 是否收到 1 SFQ？
- 若 0 → 反转 DCSFQ_BVM 输入极性变体（SL→OUT 端，q→IN 端）重测（**极性是 P0.1 留的开放问题**）
- R0 窗口：JTL B1 必须 0（无误触发）

- [ ] **Step 3: Gate（G9）** — R1 → JTL 恰好 1 SFQ（net ∈ [0.7,1.3]）；R0 → 0；≥2 次 md5 一致；记录 JM1（存储保持）

- [ ] **Step 4: 提交**

---

### Task 6: V4b — 去 8-JJ 链 A/B 对照

**Files:**
- Create: `test/final/single_bvm_qb/test_bvm_bq_dcsfq_noload.cir`（同 V4，删 8-JJ 链，SL 直连 DCSFQ_BVM）

- [ ] **Step 1: 运行 + 对照记录**：与 V4 对比——I(L_SL) 峰值、触发裕度、JTL 接收数、误触发。回答 GPT §九.2："链是必要负载还是额外障碍"。

- [ ] **Step 2: 提交**

---

### Task 7: 决策门判定（G6-G9）+ 参数冻结 + 文档同步

- [ ] **Step 1: 决策表**

| 门 | 判据 | 结果 |
|---|---|---|
| G6 (V1) | 偏置稳定 | ____ |
| G7 (V2) | 45-55µA 干净单 SFQ 窗口 | ____ |
| G8 (V3) | JTL 收到 ≥1 | ____ |
| G9 (V4) | 读1→1 SFQ / 读0→0 | ____ |

**决策**（冻结，不无限迭代）：
- 全过 → **方案一最终确认**：冻结 DCSFQ_BVM 最终参数（变体 + 工作点），论文 §7 动笔条件满足，Phase 2（阵列/系统级）规划
- G7 失败 → 升格**方案二**（IB1 读窗口门控：DCSFQ_BVM 加 READ_EN 端口）或转 H6 后备
- G8/G9 失败 → 区分归因（输出级 vs 级联匹配），按 spec 决策表

- [ ] **Step 2: 文档同步（带时间标注）**：`P1_LOG.md` 汇总 + project-todo（V1-V4b 状态 + 更新日志行）+ CHANGELOG + memory/dcsfq-bvm-design.md（最终参数）+ spec 修订 3 + HANDOVER §5 更新

- [ ] **Step 3: 提交** `docs: Phase 1 complete — gate decisions + parameter freeze`

---

## 自审记录

- **Spec 覆盖**: V1-V4b → Task 2-6 ✓；G4 输入网络 → Task 3 步骤 A ✓；极性 → Task 5 ✓；去链 → Task 6 ✓；阈值 45-55µA → Task 3 Gate ✓
- **无占位符**: 模板网表完整；变体规则明确；bound 明确（V2 ≤2 轮 IC 候选，L2 ≤10p）
- **类型一致性**: 列名 `P(B1|XDCSFQ)`（大写 BJs→BJS 坑已记录）；include 3 级；subckt 名 THmitll_DCSFQ_BVM
- **纪律**: V2 有界、决策表冻结、冻结项（B3/L6/标准库）不可擅自改动
