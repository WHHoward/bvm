# DCSFQ_BVM Phase 0 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 完成 Phase 0 四组实验（P0.0 BVM 输出表征 / P0.1 现有 DCSFQ 行为 / P0.2 DCSFQ_BVM 创建+分流标定 / P0.3 确定性），产出**接口规格**与**决策门判定**，为 Phase 1（V1-V4 验证链）定稿参数。

**Architecture:** 两个独立实验并行（P0.0 测 BVM 负载扫描、P0.1 测现有 DCSFQ 行为）→ 决策门判定缩放路线 → P0.2 创建 DCSFQ_BVM 起点元件并标定电流分流 → P0.3 全量确定性。所有结论以冻结指标口径（`scripts/sfq_metrics.py`）产出。

**Tech Stack:** `build/josim-cli` v2.7.2837d13（冻结二进制，禁 /usr/local/bin 版）、jjmit 模型（Ic×RN=1.6mV）、`scripts/sfq_metrics.py`、md5 确定性验证。

**Spec 依据:** `docs/superpowers/specs/2026-08-06-dcsfq-bvm-cell-design.md`（§2 决策门 / §4 Phase 0 / §6 工程规范）

**执行方式:** subagent-driven（2026-08-06 用户选择）——Task 2 (P0.1) 与 Task 3 (P0.0) 派发并行 subagent，文件前缀隔离（`test_dcsfq_*` vs `test_bvm_*`），各自日志写入 `P0_LOG_P01.md` / `P0_LOG_P00.md`（Task 6 合并进 `P0_LOG.md`），提交时只 add 自己的文件。

**执行纪律:**
- 所有变体 .cir 用 Write 工具直接创建，**禁止 sed 生成**（HANDOVER 坑：sed 会删含 `P()` 的 .print 行）
- 全部用单次 `pwl` 脉冲，禁周期 `pulse()`
- 原始 CSV 提交到 `test/final/interface/data/`，禁 /tmp
- 每步结果记录到 `test/final/interface/P0_LOG.md`（分 观察/机理/假设 三分类）

---

### Task 1: 目录初始化与测试台约定

**Files:**
- Create: `test/final/interface/` + `test/final/interface/data/`

- [ ] **Step 1: 建目录**

```bash
mkdir -p /home/howard/JoSIM/test/final/interface/data
```

- [ ] **Step 2: 确认路径约定**

从 `test/final/interface/` 出发，include 用 **3 级**相对路径 `../../../`（interface→final→test→root），与 `test/final/qb/` 一致。

- [ ] **Step 3: 提交（目录结构）**

```bash
cd /home/howard/JoSIM && git add test/final/interface/.gitkeep 2>/dev/null || touch test/final/interface/.gitkeep
git add test/final/interface/ && git commit -m "chore: init test/final/interface (Phase 0 testbed)"
```

---

### Task 2: P0.1 — 现有 DCSFQ 行为测试（并行组 A）

> **回答的问题**: DCSFQ 是边沿触发还是电平触发？68.4µA 输入是否达到阈值？判别器行为如何？

**Files:**
- Create: `test/final/interface/test_dcsfq_behavior_bump.cir`（模板，+ 6 个阈值变体）
- Create: `test/final/interface/test_dcsfq_behavior_sustained.cir`（+ 1 个变体）

- [ ] **Step 1: 写凸包测试模板**

`test/final/interface/test_dcsfq_behavior_bump.cir`（基准 IIN=68.4µA）：

```spice
* P0.1 — DCSFQ behavior: bump waveform (edge vs level + threshold)
* Bump: rise 2ps, hold 28ps, fall 5ps (idealized BVM read envelope)
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/standard/DCSFQ.cir

.param IIN=68.4u

XDCSFQ IN1 OUT1 THmitll_DCSFQ
R_LOAD OUT1 0 10
I_IN 0 IN1 pwl(0 0 10p 0 12p IIN 40p IIN 45p 0)

.tran 0.1p 200p
.print V(OUT1) P(B1|XDCSFQ) P(B2|XDCSFQ) P(B3|XDCSFQ)
.end
```

- [ ] **Step 2: 创建 6 个阈值变体**

每个变体 = 复制模板，只改 `.param IIN=` 一行，存入 `test/final/interface/`：

| 变体文件 | IIN 值 | 对应 BVM 语义 |
|---|---|---|
| `test_dcsfq_behavior_bump_0.cir` | 0u | 无输入 |
| `test_dcsfq_behavior_bump_1u4.cir` | 1.4u | 读0 水平 |
| `test_dcsfq_behavior_bump_20u.cir` | 20u | 阈值下方候选 |
| `test_dcsfq_behavior_bump_40u.cir` | 40u | 阈值附近候选 |
| `test_dcsfq_behavior_bump_100u.cir` | 100u | 过驱动 |
| `test_dcsfq_behavior_bump_150u.cir` | 150u | 强过驱动 |

- [ ] **Step 3: 写持续电流测试**

`test/final/interface/test_dcsfq_behavior_sustained.cir`（基准 IIN=68.4µA，保持 150ps）——**这是边沿 vs 电平触发的判定实验**：

```spice
* P0.1 — DCSFQ behavior: sustained current (150ps hold) — edge vs level trigger
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/standard/DCSFQ.cir

.param IIN=68.4u

XDCSFQ IN1 OUT1 THmitll_DCSFQ
R_LOAD OUT1 0 10
I_IN 0 IN1 pwl(0 0 10p 0 12p IIN 160p IIN 165p 0)

.tran 0.1p 250p
.print V(OUT1) P(B1|XDCSFQ) P(B2|XDCSFQ) P(B3|XDCSFQ)
.end
```

变体 `test_dcsfq_behavior_sustained_150u.cir`：仅改 `.param IIN=150u`（最坏情况电平触发检查）。

- [ ] **Step 4: 运行全部 9 个网表**

```bash
cd /home/howard/JoSIM
# 基准文件 (IIN=68.4u) 单独运行，CSV 以 _68u 命名
build/josim-cli -o test/final/interface/data/test_dcsfq_behavior_bump_68u.csv test/final/interface/test_dcsfq_behavior_bump.cir
for f in test_dcsfq_behavior_bump_0 test_dcsfq_behavior_bump_1u4 test_dcsfq_behavior_bump_20u \
         test_dcsfq_behavior_bump_40u test_dcsfq_behavior_bump_100u test_dcsfq_behavior_bump_150u; do
  build/josim-cli -o test/final/interface/data/${f}.csv test/final/interface/${f}.cir
done
build/josim-cli -o test/final/interface/data/test_dcsfq_behavior_sustained_68u.csv test/final/interface/test_dcsfq_behavior_sustained.cir
build/josim-cli -o test/final/interface/data/test_dcsfq_behavior_sustained_150u.csv test/final/interface/test_dcsfq_behavior_sustained_150u.cir
```

- [ ] **Step 5: 提取全部指标**

```bash
cd /home/howard/JoSIM
for f in test_dcsfq_behavior_bump_0 test_dcsfq_behavior_bump_1u4 test_dcsfq_behavior_bump_20u \
         test_dcsfq_behavior_bump_40u test_dcsfq_behavior_bump_68u test_dcsfq_behavior_bump_100u \
         test_dcsfq_behavior_bump_150u test_dcsfq_behavior_sustained_68u test_dcsfq_behavior_sustained_150u; do
  python3 scripts/sfq_metrics.py test/final/interface/data/${f}.csv \
    "P(B1|XDCSFQ),P(B2|XDCSFQ),P(B3|XDCSFQ)" --peaks "V(OUT1)" > test/final/interface/data/${f}.json
done
```

**期望（诚实标注，非断言）**: 现有 DCSFQ 输入级 B1=225µA，偏置 IB1=275µA（B1/B2 支路各 ~137µA ≈ 61% IC），预计触发需要端口输入 ~90-110µA。因此 **68.4µA 可能不触发（net≈0）**——这本身回答"现有元件不匹配 BVM 水平，需缩放"；**150µA 是否触发、触发后是否滑移**回答边沿/电平问题。以实测为准。

- [ ] **Step 6: P0.1 判定记录（写入 P0_LOG.md）**

记录表：每变体 net_delta / fast_events / V(OUT1) 峰值。判定两行：

| 判定 | 判据 | 结果（实测填） |
|---|---|---|
| 触发位置 | 首次出现 fast_events≥1 或 net≥0.5 的 IIN | ____µA |
| 边沿 vs 电平 | sustained 68.4/150µA 的 net：≈1 → 边沿触发；巨大（持续累积）→ 电平触发 | ____ |

- [ ] **Step 7: 提交**

```bash
cd /home/howard/JoSIM
git add test/final/interface/ && git commit -m "feat(P0.1): DCSFQ behavior test — threshold sweep + edge-vs-level (9 runs)"
```

---

### Task 3: P0.0 — BVM 输出行为表征：负载扫描（并行组 B）

> **回答的问题**: 负载如何改变 SL 读出电流？接口规格（I_peak、宽度、源阻抗、读1/0 差分裕度）是什么？——**决定 DCSFQ_BVM 缩放起点**。

**Files:**
- Create: `test/final/interface/test_bvm_load_short.cir` / `_1ohm.cir` / `_12ohm.cir` / `_50ohm.cir` / `_8jj.cir`

- [ ] **Step 1: 写模板（以短接为例）**

`test/final/interface/test_bvm_load_short.cir`——驱动序列与冻结基线完全相同，只换 SL 负载：

```spice
* P0.0 — BVM output behavior: LOAD=SHRT (0.01Ω to GND)
* Same W1/R1/W0/R0 drive as frozen baseline; only SL load changes
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/bvm/bvm_cell.cir

XBVM1 WL1 BL1 SE1 SL1 BVM

* ==== SL LOAD VARIANT ====
R_LD SL1 0 0.01

* ============ BVM Write/Read Sequence (frozen, BASELINE.md) ============
I_WL1 0 WL1 pwl(0 0 9p 0
+ 10p 100U  20p 100U  21p 0
+ 30p 0 31p 100U  40p 100U  41p 0
+ 60p 0 61p -100U 70p -100U 71p 0
+ 80p 0 81p 100U  90p 100U  91p 0
+ 110p 0)

I_BL1 0 BL1 pwl(0 0 9p 0
+ 10p 100U  20p 100U  21p 0
+ 30p 0 41p 0
+ 60p 0 61p -100U 70p -100U 71p 0
+ 80p 0 91p 0
+ 110p 0)

I_SE1 0 SE1 pwl(0 0
+ 30p 0 31p 100U  40p 100U  41p 0
+ 80p 0 81p 100U  90p 100U  91p 0
+ 110p 0)

.tran 0.1p 110p

* BVM state (storage disturbance check)
.print P(B_JM1|XBVM1) P(B_JM2|XBVM1)
* SL output
.print I(L_SL|XBVM1) V(SL1)
.print V(WL1) V(BL1) V(SE1)
.end
```

- [ ] **Step 2: 创建 4 个负载变体**

复制模板，只替换 `* ==== SL LOAD VARIANT ====` 下的负载行：

| 变体文件 | 负载行 | 语义 |
|---|---|---|
| `test_bvm_load_1ohm.cir` | `R_LD SL1 0 1` | 低阻 |
| `test_bvm_load_12ohm.cir` | `R_LD SL1 0 12` | 匹配源阻抗（~15Ω 附近） |
| `test_bvm_load_50ohm.cir` | `R_LD SL1 0 50` | 高阻 |
| `test_bvm_load_8jj.cir` | 8×jjmit(area=3.2) 串联到地（见下） | 当前基线负载（对照） |

`test_bvm_load_8jj.cir` 的负载段（基线 8-JJ 链，去掉 BQ）：

```spice
* ==== SL LOAD VARIANT (8× jjmit stack, area=3.2, IC=320µA) ====
B_LD1  SL1  nld1 jjmit area=3.2
B_LD2  nld1 nld2 jjmit area=3.2
B_LD3  nld2 nld3 jjmit area=3.2
B_LD4  nld3 nld4 jjmit area=3.2
B_LD5  nld4 nld5 jjmit area=3.2
B_LD6  nld5 nld6 jjmit area=3.2
B_LD7  nld6 nld7 jjmit area=3.2
B_LD8  nld7 0    jjmit area=3.2
```

- [ ] **Step 3: 运行 5 个网表**

```bash
cd /home/howard/JoSIM
for f in short 1ohm 12ohm 50ohm 8jj; do
  build/josim-cli -o test/final/interface/data/bvm_load_${f}.csv test/final/interface/test_bvm_load_${f}.cir
done
```

- [ ] **Step 4: 提取指标（含峰值）**

```bash
cd /home/howard/JoSIM
for f in short 1ohm 12ohm 50ohm 8jj; do
  python3 scripts/sfq_metrics.py test/final/interface/data/bvm_load_${f}.csv \
    "P(B_JM1|XBVM1),P(B_JM2|XBVM1)" --peaks "I(L_SL|XBVM1),V(SL1)" > test/final/interface/data/bvm_load_${f}.json
done
```

- [ ] **Step 5: 产出接口规格表（P0_LOG.md）**

每负载记录（R1 读1 与 R0 读0 分开）：

| 负载 | I(L_SL) R1 峰值@t | I(L_SL) R0 峰值@t | 宽度 | V(SL1) 峰值 | JM1 net（存储扰动） |

**期望（诚实标注）**: R1 峰值应在 68.4µA（8-JJ 链，与冻结基线一致）附近随负载变化；低阻负载可能拉低读出量（源阻抗 ~15Ω 分压）；JM1 在 R0 后应保持写入态（扰动检查）。以实测为准。

- [ ] **Step 6: 提交**

```bash
cd /home/howard/JoSIM
git add test/final/interface/ && git commit -m "feat(P0.0): BVM load sweep — interface spec (5 loads)"
```

---

### Task 4: P0.2 — DCSFQ_BVM 创建 + 电流分流标定

> **前提**: P0.1 已判定触发位置与边沿/电平性质（该判定决定后续路线，但不阻塞本任务的元件创建——起点参数由 spec §3 冻结）。

**Files:**
- Create: `circuits/interface/DCSFQ_BVM.cir`
- Create: `test/final/interface/test_dcsfq_bvm_div.cir`

- [ ] **Step 1: 创建 DCSFQ_BVM 元件**

`circuits/interface/DCSFQ_BVM.cir` = 复制 `circuits/standard/DCSFQ.cir`，**只改 4 行**（其余参数 RB/LRB/L1-L6 由 `.param` 公式自动缩放，无需手改）：

```spice
* DCSFQ_BVM — BVM readout interface cell (H7 main route)
* Source: ColdFlux DCSFQ skeleton, input stage scaled to BVM levels
* Ports: a q | Bias: internal (IB1/IB2)
* Changes vs THmitll_DCSFQ (2026-08-06, spec 2026-08-06-dcsfq-bvm-cell-design.md):
*   B1/B2: 2.25 → 0.8 (225→80µA)  — threshold ≈25µA at port
*   IB1:   275u → 100u             — ~60% bias operating point
*   RB/LRB auto-scale via formula (RB≈8.6Ω, LRB≈4.85/5.35pH)
*   B3/IB2/L1-L6 unchanged — output stays JTL-compatible (250µA)
*
.subckt THmitll_DCSFQ_BVM a q
.param Phi0=2.067833848E-15
.param B0=1
.param Ic0=0.0001
.param IcRs=100u*6.859904418
.param B0Rs=IcRs/Ic0*B0
.param Rsheet=2
.param Lsheet=1.13e-12
.param LP=0.5p
.param IC=2.5
.param LB=2p
.param BiasCoef=0.7
.param B1=0.8
.param B2=0.8
.param B3=IC
.param IB1=100u
.param IB2=B3*Ic0*BiasCoef
.param LB1=LB
.param LB2=LB
.param L1=1p
.param L2=3.9p
.param L3=0.6p
.param L4=1.1p
.param L5=4.5p
.param L6=Phi0/(4*IC*Ic0)
.param LP2=LP
.param LP3=LP
.param RB1=B0Rs/B1
.param RB2=B0Rs/B2
.param RB3=B0Rs/B3
.param LRB1=(RB1/Rsheet)*Lsheet
.param LRB2=(RB2/Rsheet)*Lsheet+LP
.param LRB3=(RB3/Rsheet)*Lsheet+LP
B1 2 3 jjmit area=B1
B2 5 6 jjmit area=B2
B3 7 8 jjmit area=B3
IB1 0 4 pwl(0 0 5p IB1)
IB2 0 9 pwl(0 0 5p IB2)
LB1 4 3 2.825E-012
LB2 9 7 2.942E-012
L1 a 1 1.672E-012
L2 1 0 3.901E-012
L3 1 2 5.953E-013
L4 3 5 1.1E-012
L5 5 7 4.542E-012
L6 7 q 2.012E-012
LP2 6 0 3.924E-013
LP3 8 0 3.841E-013
RB1 2 102 RB1
LRB1 102 3 LRB1
RB2 5 105 RB2
LRB2 105 0 LRB2
RB3 7 107 RB3
LRB3 107 0 LRB3
.ends
```

（对照 `circuits/standard/DCSFQ.cir` 逐行核对：仅 `.param B1/B2/IB1` 与 subckt 名不同。）

- [ ] **Step 2: 写分流标定测试**

`test/final/interface/test_dcsfq_bvm_div.cir`：

```spice
* P0.2 — DCSFQ_BVM input current division: I(L3)/I(L1) at port a
* 68.4µA bump (read-1 level); ratio = current reaching B1 branch
.include ../../../circuits/models/jjmit.cir
.include ../../../circuits/interface/DCSFQ_BVM.cir

.param IIN=68.4u

XDCSFQ IN1 OUT1 THmitll_DCSFQ_BVM
R_LOAD OUT1 0 10
I_IN 0 IN1 pwl(0 0 10p 0 12p IIN 40p IIN 45p 0)

.tran 0.1p 200p
.print V(OUT1) P(B1|XDCSFQ) P(B2|XDCSFQ) P(B3|XDCSFQ)
.print I(L1|XDCSFQ) I(L2|XDCSFQ) I(L3|XDCSFQ)
.end
```

- [ ] **Step 3: 运行并提取**

```bash
cd /home/howard/JoSIM
build/josim-cli -o test/final/interface/data/dcsfq_bvm_div.csv test/final/interface/test_dcsfq_bvm_div.cir
python3 scripts/sfq_metrics.py test/final/interface/data/dcsfq_bvm_div.csv \
  "P(B1|XDCSFQ),P(B2|XDCSFQ),P(B3|XDCSFQ)" --peaks "I(L1|XDCSFQ),I(L2|XDCSFQ),I(L3|XDCSFQ),V(OUT1)" > test/final/interface/data/dcsfq_bvm_div.json
```

- [ ] **Step 4: 计算分流系数并记录**

从 JSON 的 peaks 取 I(L1) 峰值（端口输入）与 I(L3) 峰值（B1 支路电流），**分流系数 = I(L3)/I(L1)**。记录到 P0_LOG.md。

**期望（诚实标注）**: L2=3.9p、L3=0.6p，高频分流应偏向 L3（小电感）→ 系数预计 0.5-0.9；实测为准。若系数 <0.3（输入大多走 L2 到地），需在 Phase 1 调整输入网络（L2/L3 比值），这正是标定的目的。

- [ ] **Step 5: 提交**

```bash
cd /home/howard/JoSIM
git add circuits/interface/ test/final/interface/ && git commit -m "feat(P0.2): DCSFQ_BVM cell (start params) + current division calibration"
```

---

### Task 5: P0.3 — 确定性验证（全量重跑）

> **规则**: 每个关键 CSV ≥2 次运行 md5 一致（HANDOVER IRON RULE 5）。

- [ ] **Step 1: 重跑关键网表**

```bash
cd /home/howard/JoSIM
# P0.1 关键点: 68.4µA bump + 68.4µA sustained
build/josim-cli -o /tmp/p03_dcsfq_bump68_r2.csv test/final/interface/test_dcsfq_behavior_bump.cir
build/josim-cli -o /tmp/p03_dcsfq_sus68_r2.csv test/final/interface/test_dcsfq_behavior_sustained.cir
# P0.0 关键点: 12Ω 与 8-JJ 负载
build/josim-cli -o /tmp/p03_bvm_12ohm_r2.csv test/final/interface/test_bvm_load_12ohm.cir
build/josim-cli -o /tmp/p03_bvm_8jj_r2.csv test/final/interface/test_bvm_load_8jj.cir
# P0.2
build/josim-cli -o /tmp/p03_dcsfq_bvm_div_r2.csv test/final/interface/test_dcsfq_bvm_div.cir
```

- [ ] **Step 2: md5 对比**

```bash
cd /home/howard/JoSIM
md5sum test/final/interface/data/test_dcsfq_behavior_bump_68u.csv /tmp/p03_dcsfq_bump68_r2.csv
md5sum test/final/interface/data/test_dcsfq_behavior_sustained_68u.csv /tmp/p03_dcsfq_sus68_r2.csv
md5sum test/final/interface/data/bvm_load_12ohm.csv /tmp/p03_bvm_12ohm_r2.csv
md5sum test/final/interface/data/bvm_load_8jj.csv /tmp/p03_bvm_8jj_r2.csv
md5sum test/final/interface/data/dcsfq_bvm_div.csv /tmp/p03_dcsfq_bvm_div_r2.csv
```

**判定**: 全部 md5 一致 → ✅ 确定性确认。任一不一致 → 停止并进入 systematic-debugging（这不应该是参数问题，而是复现性问题）。

- [ ] **Step 3: md5 表写入 P0_LOG.md**（每个 CSV 的 SHA-256 + 运行次数）

- [ ] **Step 4: 提交**

```bash
cd /home/howard/JoSIM
git add test/final/interface/ && git commit -m "test(P0.3): determinism md5 re-runs — all identical"
```

---

### Task 6: 决策门判定 + 文档同步

- [ ] **Step 1: 填写决策门判定表（P0_LOG.md → 决策）**

| 决策门 | 判据 | 实测 | 下一步 |
|---|---|---|---|
| G1 触发位置 | 首个 fast_events≥1 的 IIN | ____ | 若 ≥68.4µA：缩放输入级正确；若 ≫68.4µA：需加大缩放或重设计输入网络 |
| G2 边沿 vs 电平 | sustained 68.4/150µA net | ____ | ≈1 → 方案一继续；巨大 → 升格方案二（门控偏置） |
| G3 接口规格 | P0.0 表：R1 峰值/宽度/读1/0 裕度 | ____ | 决定 B1/B2 最终 IC（目标：阈值两侧 ≥2× 裕度） |
| G4 分流系数 | I(L3)/I(L1) | ____ | ≥0.5 → 起点参数可用；<0.3 → Phase 1 调 L2/L3 |
| G5 确定性 | md5 全一致 | ____ | ✅ 才可引用 Phase 0 结论 |

**G2 决策表（冻结，不无限迭代）**:
- 边沿触发且 net≈1 → 方案一（最小缩放）继续 → Phase 1 计划（V1-V4b）
- 电平触发/持续滑移 → **方案二（IB1 读窗口门控）**：DCSFQ_BVM 增加 IB1 门控 pwl 端口，写 Phase 1 计划
- 均无法工作 → 转 H6（修 BQ 后备路线），记录并停止

- [ ] **Step 2: 更新项目文档（带时间标注，2026-08-06 规则）**

- `memory/project-todo.md`: P0.0-P0.3 状态 🔴→🟢 或 🟡，每行标注 `(2026-08-06)`；更新日志追加带日期行；决策门结论写入 Step 5 说明列
- `memory/project-summary.md`: 头部"最后更新"日期 + §七 下一步改为 Phase 1（V1-V4b）或方案二升格
- `CHANGELOG.md`: 追加 "Phase 0 完成" 条目（做了什么/为什么/影响）
- `memory/dcsfq-bvm-design.md`: 补 P0 实测结果与最终参数（frontmatter last_updated 更新）

- [ ] **Step 3: 提交**

```bash
cd /home/howard/JoSIM
git add -A && git commit -m "docs: Phase 0 complete — gate decisions + interface spec (P0.0-P0.3)"
```

---

## 自审记录

- **Spec 覆盖**: §4 Phase 0 四实验 → Task 2/3/4/5 ✓；§2 决策门 → Task 6 G1/G2 ✓；§1 接口规格 → Task 3 ✓；§6 工程规范 → 全部任务内嵌 ✓
- **无占位符**: 所有网表含完整 SPICE；命令含确切路径；期望值均为诚实标注（实测为准）
- **类型一致性**: 列名 `P(B1|XDCSFQ)`（DCSFQ 与 DCSFQ_BVM 测试均用实例名 XDCSFQ）✓；`I(L_SL|XBVM1)` 与基线一致 ✓；include 相对路径统一 3 级 ✓
- **sed 规避**: 全部变体用 Write 创建，无 sed 生成（HANDOVER 坑）✓
