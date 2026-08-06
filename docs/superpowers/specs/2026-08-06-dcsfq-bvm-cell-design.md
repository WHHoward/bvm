# DCSFQ_BVM 元件设计 — BVM 慢读出电流 → 受控 SFQ 接口

> **状态**: 设计已获用户批准 (2026-08-06) | 下一步: writing-plans 实施计划
> **路线**: H7 主攻方向 (GPT 审计 §九.4/§十.5) — 基于 ColdFlux DCSFQ 骨架的缩放读出比较器
> **前置证据**: [证据链](../../paper/bvm-bq-interface-evidence-chain.md) (8 轮排除) + [BASELINE.md](../../../test/final/single_bvm_qb/BASELINE.md) (冻结口径)

## 1. 背景与问题定义

BVM 读"1"在 SL 端给出 ~68.4µA、30-40ps 的慢衰减电流；读"0"给出 ~1.4µA。
**目标**（GPT §十.5 冻结口径）: 读"1" → 恰好 1 个被下游 JTL 接收的 SFQ；读"0" → 0 个且无误触发。

现有 BQ 经 8 轮实验系统性排除（证据链 §4），冻结根因：

1. **BJs 裸结无外部阻尼**（βc≈5.4 欠阻尼）→ 任何过驱动 ≥1.4×IC 即电压态滑移
2. **电流源注入 = 通量泵** → 滑移量窗口依赖（602-829 SFQ/300ps），无离散性
3. **输出级驱动不足** → ~100µA < ColdFlux JTL 阈值 250µA，下游 JTL 收到 0
4. **v4 IC 顺序修正副作用** → 输出传递路径死亡（输出比 v2 差 5.5×）

## 2. 设计决策记录（2026-08-06，用户拍板）

| # | 决策 | 选择 | 保留备选 |
|---|------|------|---------|
| D1 | 新元件 vs 修改 BQ | **新元件**（基于 DCSFQ 骨架） | H6: 修 BQ（BJs 加阻尼+偏置+输出级 JTL 化）— DCSFQ_BVM 失败后启用 |
| D2 | 输入级设计 | **方案一: 最小缩放**（B1/B2→80µA，无门控） | 方案二: +读使能门控（IB1 读窗口 pwl）；方案三: 双端口时钟式（违背 YAGNI） |
| D3 | 输出级 | **B3=250µA 冻结不动**（JTL 兼容） | — |

**P0.1 决策门**（不无限迭代）:

- 现有 DCSFQ **边沿触发**（输入上升沿 → 1 SFQ，持续输入不连续触发）→ 方案一继续
- **电平触发滑移**（持续输入 → 连续相位累积）→ 升格方案二（门控偏置）

## 3. 元件拓扑与参数

### 拓扑

```
a ─ L1(1.67p) ─ node1 ─ L3(0.6p) ─ B1(80µA) ─ L4(1.1p) ─ B2(80µA) ─ L5(4.5p) ─ B3(250µA) ─ L6 ─ q
                  │                                            │
                  L2(3.9p) 到地                                IB2=175µA (70%×B3, 不变)
IB1≈100µA ─ LB1 ─ node3 ─(B1/B2 支路间分流)
```

### 参数表

| 参数 | 原 DCSFQ | DCSFQ_BVM | 依据 |
|---|---|---|---|
| B1/B2 area | 2.25 (225µA) | **0.8 (80µA)** | 触发阈值 ≈25µA；读1 68.4µA → 2.8× 裕度，读0 1.4µA → 远离阈值 |
| IB1 | 275µA | **≈100µA** | 按 80/225 比例缩放，保持 ~60-70% 工作点（P0.2 后微调） |
| RB1/RB2 | 3.05Ω | **≈8.6Ω** | RB = 6.86/area 公式（6.8599/0.8 = 8.57Ω） |
| LRB1 | 1.72pH | **≈4.85pH** | (RB/Rsheet)·Lsheet 公式 |
| LRB2 | 2.22pH | **≈5.35pH** | (RB/Rsheet)·Lsheet + LP 公式 |
| B3 / IB2 / L1-L6 / LB1 / LB2 | — | **全部不变** | 输出级与输入网络保持标准 ColdFlux 配方 |

参数在 Phase 0（P0.2 电流分流标定）后按实测微调；**B3、L6、IB2 冻结不动**。

## 4. Phase 0 诊断实验（先测行为，再定稿参数）

| # | 内容 | 判定 → 下一步 |
|---|---|---|
| P0.1 | 现有 `circuits/standard/DCSFQ.cir` 跑输入形态：单次 pwl 68µA/30-40ps 凸包 + 阈值扫描 0-150µA | 边沿触发 → 方案一继续；电平触发滑移 → 升格方案二 |
| P0.2 | DCSFQ_BVM 电流分流标定：I(B1 支路) vs I(端口 a) | 定"端口输入 ↔ B1 实际电流"换算系数，冻结最终参数 |
| P0.3 | 确定性：每次运行 ≥2 次，md5 一致 | 全流程标准动作 |

P0.1 直接使用现有标准件——零设计成本回答"思路是否成立"。

## 5. 验证链（元件定稿后）

| 阶段 | 内容 | Gate |
|---|---|---|
| V1 | 无输入偏置稳定性（IB1/IB2 建立） | net≈0、fast_events=0 |
| V2 | 阈值判别：输入凸包扫描 0/1.4/20/40/68.4/100µA | 读1 水平恰好 1 SFQ；读0 水平 0；判别裕度记录在案 |
| V3 | 输出级 → Load JTL | JTL B1 收到 ≥1（读1）/ 0（读0） |
| V4 | BVM 级联（替换基线网表 [test_bvm_bq_baseline.cir](../../../test/final/single_bvm_qb/test_bvm_bq_baseline.cir) 中的 BQ） | R1 读出 → JTL 恰好 1 SFQ；R0 → 0 无误触发；≥2 次 md5 一致 |
| V4b | A/B 对照：去掉 8-JJ 负载链 | 回答负载链是否额外障碍（GPT §九.2 最小化负载扫描） |

**最终 Gate**（GPT §十.5）: 读1 → 恰好 1 个被 JTL 接收的 SFQ；读0 → 0 且无误触发；可复现。

## 6. 工程规范（冻结铁律）

- 新文件: `circuits/interface/DCSFQ_BVM.cir`，subckt 名 `THmitll_DCSFQ_BVM`（沿用 ColdFlux THmitll_ 前缀）；**不改标准库原文件** `circuits/standard/DCSFQ.cir`
- 测试: `test/final/interface/` + `data/`；相对 include 路径 3/4 级
- **全部用单次 `pwl` 脉冲**，禁周期 `pulse()`（GPT §十.3）
- 指标一律 `scripts/sfq_metrics.py`，原始 CSV 提交到 `test/final/interface/data/`，禁 /tmp
- 记录分 观察/机理/假设 三分类（GPT §六）
- 仿真用 `build/josim-cli`（v2.7.2837d13），禁 /usr/local/bin 版本

## 7. 相关文件

- 证据链: `docs/paper/bvm-bq-interface-evidence-chain.md`
- 基线: `test/final/single_bvm_qb/BASELINE.md`
- 审计: `memory/GuidanceFromGpt.md` §九.4/§十
- 原元件: `circuits/standard/DCSFQ.cir`
- v4 失败记录: `docs/superpowers/plans/2026-08-06-bq-v4.md`
