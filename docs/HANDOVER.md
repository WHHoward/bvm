# JoSIM 项目交接文档

> **用途**: 会话交接。新会话开始后先读本文件 + `memory/project-todo.md`，即可零上下文接手。
> **版本**: 2026-08-06 | 上一会话终点: commit `ea87445`（Step 3 决策 D 完成）
> **本文档要回答**: 项目是什么、做到哪了、哪些结论已冻结、下一步做什么、有哪些坑。

---

## 0. 新会话第一步

```bash
cd /home/howard/JoSIM
git log --oneline -5          # 确认当前状态
build/josim-cli --version     # 必须是 v2.7.2837d13（冻结二进制，见 §8.1）
```
然后读：
1. `memory/project-todo.md` — 主任务清单（状态追踪的唯一权威）
2. `docs/paper/bvm-bq-interface-evidence-chain.md` — 8 轮实验证据链（论文素材）
3. `test/final/single_bvm_qb/BASELINE.md` — 冻结基线定义
4. `memory/GuidanceFromGpt.md` — 外部审计结论（Step 0-4 框架来源）

---

## 1. 项目是什么

**JoSIM** = 超导电子学 SPICE 语法电路仿真器（C++17, KLU 求解器）。本项目用它仿真基于 **ColdFlux RSFQ** 设计方法的超导数字电路。

**最终目标**: 构建「存储(BVM) → 量化/缓冲(BQ) → 逻辑(标准元件) → 运算(T1 全加器)」的完整仿真流水线 + 发表论文。

**当前论文方向（Paper A）**: **BVM→BQ 接口设计** —— BVM 的慢读出电流（~68µA、30-40ps）能否触发 BQ 产生离散可控 SFQ 输出。文献空白已确认（Karamuftuoglu SUST 2024 + arXiv:2507.04648 只说 "threshold matched"，不提阻抗）。

---

## 2. 当前状态快照（2026-08-06）

| 项目 | 状态 |
|------|------|
| Step 0 基线冻结（矛盾解决 + 指标脚本 + 确定性验证） | 🟢 完成（commit f4c78ba） |
| Step 1 BQ v4 独立验证 | ❌ **Gate 未通过**（commit 95b70f6） |
| Step 2 BVM→BQ v4 级联 | 🔴 阻塞（Step 1 未过） |
| Step 3 路线决策（用户选 D: 先整理论文证据链） | 🟢 完成（commit ea87445） |
| Step 4 备用接口方案 H6-H10 | 🟡 保留为后备（H7 已转 Step 5） |
| **Step 5 DCSFQ_BVM 新元件（H7 主路线）** | 🟡 **Phase 0 完成**（P0.0-P0.3）→ Phase 1（V1-V4b） |
| 标准元件库（8 个核心元件） | 🟢 全部验证通过 |
| 论文写作 | 🔴 待 DCSFQ_BVM 正结果后动笔（推荐） |

**一句话**: BVM→BQ 直接耦合路线经 8 轮实验系统性排除；H7/DCSFQ_BVM 新元件 Phase 0 完成——接口规格实测（I_peak 43.9-97.8µA、Zth≈40Ω、FWHM ~10ps）、现有 DCSFQ 边沿触发、分流 0.285（需调输入网络）；下一步是 Phase 1（V1-V4b 验证链，含 L2/L3 调整与极性验证）。Phase 0 数据与决策门见 `test/final/interface/P0_LOG.md`。

---

## 3. 冻结的物理结论（8/6 起不可动摇，引用时需注明来源）

1. **BJs 任何过驱动即滑移**: 70µA (1.4×IC) 即进入电压态滑移；基线 68.4µA 同样。从未出现干净单翻转。
2. **βc 不变量**: jjmit 所有结固有 βc≈5.44（βc = 2π·Ic0·rn²·cap/Φ₀，与 area 无关）。标准 JTL 能干净翻转是因为**外部 RB+LRB 阻尼网络 + 70% 偏置**；BQ 的 BJs 两者皆无 → 欠阻尼振铃/滑移。**这是 BQ 与标准单元行为差异的关键结构原因。**
3. **电流源注入 = 通量泵**: 理想电流源在结翻转后持续泵入磁通，滑移量由驱动水平与窗口决定（602-829 SFQ/300ps），与离散 SFQ 计数无对应关系。
4. **L_J 矛盾（数学成立）**: L_J = Φ₀/(2π·IC)。IC 50→20µA → L_J 6.6→16.5pH → 输入总电感 +133% → SL 电流传递 68.4→33.6µA (-51%)。**降低 IC 的方案自相矛盾**，低 IC 路线放弃。
5. **K 元件变压器失效**: L_PRI 在 500GHz 下 Z≈6.3Ω 分流、M≈3.6pH 对 30ps 脉冲耦合能量不足、L_SEC 感抗 Z≈25Ω。**K 元件适合 MHz-GHz 连续波，不适合 ps 级脉冲瞬时能量传递。**
6. **v2 的"成功"是滑移输出**: v2 的 1035µV/"190 SFQ" 记录本质是电压态滑移驱动，不是离散 SFQ——连标准 JTL 都推不动（JTL 收到 0）。v4 更差 5.5×（Vpk=186µV）。
7. **BVM 写入是多涡旋态**: JM1 在 jjmit 下 settle +5.93 SFQ（多翻转），"1 状态"不是单涡旋——影响任何依赖"单涡旋读出"的接口设计。
8. **确定性**: 固定步长仿真完全确定，md5 验证是标准做法。

---

## 4. 关键资产索引

### 代码 / 电路
| 文件 | 内容 |
|------|------|
| `circuits/qb/bq_cell.cir` | BQ v2（BJs=50µA, BJL1=36µA, BJL2=54µA） |
| `circuits/qb/bq_cell_v4.cir` | BQ v4（IC 顺序 BJs<BJL2<BJL1: 50/70/90µA, RJ1=56Ω, RJ2=36Ω, L0=2.5pH） |
| `circuits/standard/JTL.cir` | THmitll_JTL（B1=B2=2.5→IC=250µA, RB≈2.74Ω+LRB≈2.05p 阻尼网络, 偏置 350µA）— **H6 的参考模板** |
| `circuits/standard/` | ColdFlux 35 元件库（INDEX.md 索引） |
| `scripts/sfq_metrics.py` | **冻结指标脚本**: net_delta / max_excursion / total_variation / fast_events / max_dPdt，JSON 输出 |
| `build/josim-cli` | 冻结二进制 v2.7.2837d13（唯一可用版本） |

### 测试 / 数据
| 文件 | 内容 |
|------|------|
| `test/final/single_bvm_qb/BASELINE.md` | 冻结基线定义（指标口径 + commit hash + SHA-256） |
| `test/final/single_bvm_qb/EXPERIMENT_LOG.md` | 全部实验日志（实验 1-6） |
| `test/final/qb/data/bq_v4_*.csv` | v4 全部原始 CSV（md5 验证，确定性） |
| `test/final/qb/test_bq_v4_*.cir` | v4 测试网表（bias/sfq/sweep/diag） |

### 文档
| 文件 | 内容 |
|------|------|
| `docs/paper/bvm-bq-interface-evidence-chain.md` | **论文证据链**（8 轮 + 排除表 + 章节映射）— 论文写作的骨架 |
| `docs/superpowers/plans/2026-08-06-bq-v4.md` | Step 1 完整计划 + 执行结果 |
| `CHANGELOG.md` | 变更历史 |
| `memory/` | 知识库（18 文件）— `project-todo.md` 是任务权威，`GuidanceFromGpt.md` 是审计源 |

---

## 5. 下一步：Phase 1（V1-V4b 验证链，DCSFQ_BVM 主路线）

**Phase 0 已完成**（2026-08-06，实现经双审查）: 接口规格实测、边沿触发确认、分流标定、确定性 5/5。完整决策门 G1-G5 与数据见 `test/final/interface/P0_LOG.md`（分册 P0_LOG_P00-P03）。

**Phase 1 要点（spec 修订 2 + P0_LOG.md §3-4）**:
1. V1 偏置稳定 → **V2 阈值判别扫描（含 L2/L3 输入网络调整变体 + B1/B2 下调候选，阈值目标 45-55µA）** → V3 JTL 接收 → V4 BVM 级联（**极性验证**）→ V4b 去负载链对照
2. 起点元件: `circuits/interface/DCSFQ_BVM.cir`（B1/B2=0.8, IB1=100µA）；测试台: `test/final/interface/test_dcsfq_bvm_div.cir` 模式（相对 include 3 级 `../../../`，data/ 下 4 级）
3. **最终 Gate**（GPT §十.5）: 读1 → 恰好 1 个被 JTL 接收的 SFQ；读0 → 0 且无误触发

**如果 Phase 1 失败**: 按 spec 决策表——V2 扫描设 bound，失败升格方案二（IB1 读窗口门控）或转 H6 后备——**不要擅自改参数无限迭代**（GPT 审计教训：决策表而非"试到成功"）。

**并行可做**（独立项，GPT §十.6）: BVM 多涡旋读写一致性验证；论文 §3-§6 草稿（数据已齐，不阻塞）。

---

## 6. 指标口径（冻结，不可改）

| 指标 | 定义 |
|------|------|
| net_delta_sfq | (相位末值 - 初始值)/2π 的净值 |
| fast_events | \|ΔP\| > 0.3 SFQ 每 0.1ps 采样的事件数（**离散 SFQ 判据**） |
| 电压态滑移 | net 巨大（数百 SFQ）、窗口依赖、fast_events=0 或不可控 |
| 离散 SFQ | fast_events>0 且 net 小、可控 |

**关键区分**: 电压态滑移 ≠ 离散 SFQ。论文的核心叙事就是基于这个区分。

---

## 7. 项目规则（IRON RULES）

1. **🚨 任何 Bash/Write/Edit 前必须读 `.claude/skills/skill-router.md`** 并输出 `[skill-router] Task: ... Skills: ...` 行（CLAUDE.md 强制）
2. **仿真必须用 `build/josim-cli`**（v2.7.2837d13）。`/usr/local/bin/josim-cli` 是更旧版本，**禁用**
3. **原始 CSV 必须保存到 `test/final/*/data/` 并提交**——存 /tmp 会丢（7/13-7/17 实验数据全部丢失的教训，BASELINE.md §5）
4. **所有指标用 `scripts/sfq_metrics.py` 口径**，禁止人工读图计数
5. **每个结论可复现**: 至少 2 次运行 md5 一致
6. **Skill 纪律**: 实现→writing-plans/TDD，调试→systematic-debugging，声称完成→verification-before-completion，C++→ecc:cpp-review
7. **会话开始/结束** 更新 `memory/project-todo.md`（todo-manager skill）

---

## 8. 已知坑（都踩过，别重踩）

| 坑 | 说明 |
|----|------|
| 两个 josim-cli | `build/josim-cli` (v2.7.2837d13) vs `/usr/local/bin` (v2.7.02a34ee) — 结果不同，必须用前者 |
| CSV 列名大写 | JoSIM 输出 `P(BJS|XBQ)`，不是 `P(BJs|XBQ)`——Python KeyError 的常见来源 |
| 相对 include 路径 | 基于 .cir 文件位置解析。`test/final/qb/` 下需要 `../../../`（3 级），`test/final/qb/data/` 下需要 `../../../../`（4 级）。**不要放到 /tmp 跑**（会解析失败） |
| `pulse()` 周期陷阱 | `pulse(0 1.5m 10p 1p 1p 2p 50p)` 的 50p 是**周期**（每 50ps 重复），不是单次脉冲。要单次用 `pwl(...)` |
| 变体生成用 sed 会删 .print 行 | 含 `P(B1|XJTL)` 等括号的 .print 行会被 sed 正则误伤 → 空 CSV → JSON 解析错误。生成变体后必须检查 .print 行还在 |
| 相位计数误读 | 滑移的 net 值巨大（600+），别把"相位前进"当成"SFQ 翻转"。看 fast_events |
| 模型时代混用 | 7/12 commit 916ac09 之前是 V0 模型（0.25mV），之后是 jjmit（1.6mV）。老记录（0.94 SFQ 等）不可直接引用 |

---

## 9. 论文状态（Paper A）

- **叙事**: "首次系统表征 BVM→BQ 接口 + 失效机制根因分析（βc 不变量、阻尼网络差异、通量泵）+ 负向设计准则 + 方案空间评估"
- **§3-§6 数据已齐**（证据链文档），**§7 正向方案待 H6/H7 结果**
- **推荐**: 先 H6/H7 任一正结果再动笔（正结果增强论文说服力）
- 竞争格局 / 方向评估见 `memory/paper-directions-analysis.md`；ARS 工具链可全程辅助写作

---

*交接完成。祝新会话顺利——从 §0 开始。*
