---
name: project-todo
description: JoSIM 项目主任务清单 — 所有工作项的状态追踪，每次会话开始/结束时更新
metadata:
  type: project
  node_type: memory
  last_updated: 2026-07-17
---

# JoSIM 项目主任务清单

> **规则**: 每次会话开始时检查进度，完成或新增项目时更新。状态: 🔴未开始 🟡进行中 🟢已完成 ⏸️暂停

---

## 一、Paper A: BVM→BQ 接口设计

| # | 任务 | 状态 | 产出 | 备注 |
|---|------|------|------|------|
| T1 | BVM→BQ 级联基线测试 | 🟢 | 量化失配数据 (68µA→BJs慢滑移1SFQ) | 2026-07-17 完成 |
| T2 | 低 IC BQ 子电路设计 | 🟢 | 3 版本, 全部失败 (L_J矛盾) | 放弃此路线 |
| T3 | K 元件变压器 (n=2/2.5/3) | 🟢 | 全部失败 (SFQ时间尺度耦合太弱) | 放弃此路线 |
| T4 | 论文原始 BQ 测试 | 🟢 | JS=133µA 也失败 (阈值不匹配) | 参考价值 |
| T5 | BQ 量化能力测试 | 🟢 | 70-170µA 扫参, 恒定3.1SFQ输出 | 不满足可变SFQ要求 |
| T6 | 元件可视化 + 参考手册 | 🟢 | 18 HTML + component-reference.md | 完成 |
| ~~T6-T8~~ | ~~旧计划~~ | ⏸️ | — | 路线调整中 |

**当前状态**: 单 BVM cell 无法驱动任何 IC>50µA 接收器。等待量化器重设计。

**下一步**: 实现并测试 BQ v4 (BJL1 IC反转方案, 见 [[bq-v4-modification-plan]])

---

## 七、BQ 量化器重设计

| # | 任务 | 状态 | 说明 |
|---|------|------|------|
| Q1 | BQ v4 方案设计 | 🟢 | 已完成 → memory/bq-v4-modification-plan.md |
| Q2 | 创建 bq_cell_v4.cir | 🔴 | BJL1 IC 36→90µA, BJL2 54→70µA |
| Q3 | BQ v4 独立测试 (SFQ注入+电流扫参) | 🔴 | 验证线性量化 |
| Q4 | BQ v4 + BVM 级联测试 | 🔴 | 验证单cell可触发 |

---

## 二、Paper A: 论文撰写与投稿

| # | 任务 | 状态 | 依赖 |
|---|------|------|------|
| P1 | ARS ars-plan 论文大纲 | 🔴 | T1-T7 完成 |
| P2 | ARS academic-paper 初稿 | 🔴 | P1 |
| P3 | ARS ars-reviewer 内部审稿 | 🔴 | P2 |
| P4 | 修改定稿 | 🔴 | P3 |
| P5 | 投 arXiv | 🔴 | P4 |
| P6 | 投 Supercond. Sci. Technol. | 🔴 | P5 |

---

## 三、Paper B: BVM 乘法器可扩展性与鲁棒性

| # | 任务 | 状态 | 依赖 |
|---|------|------|------|
| B1 | T1 全加器完整真值表验证 | 🔴 | Paper A Phase 1 |
| B2 | T1 时序窗口扫描 | 🔴 | B1 |
| B3 | 4×4 BVM 乘法器仿真 | 🔴 | Paper A Phase 1 |
| B4 | Preload vs Direct-input 比较 | 🔴 | B3 |
| B5 | 规模扩展分析 (4×4→8×8) | 🔴 | B3 |
| B6 | T1 参数鲁棒性扫描 | 🔴 | B2 |

---

## 四、标准元件库

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| S1 | OR2 仿真测试 | 🔴 | 最后未测的逻辑门 |
| S2 | XNOR 仿真测试 | 🔴 | 19 JJ，最复杂 |
| S3 | BUFF 仿真测试 | 🔴 | 基础缓冲器 |
| S4 | 注册所有标准元件到 ctest | 🔴 | CMakeLists.txt |
| S5 | .gitignore 添加 *.html | 🔴 | 30MB 瘦身 |

---

## 五、基础设施

| # | 任务 | 状态 | 备注 |
|---|------|------|------|
| I1 | 清理 settings.json 过期权限 | 🔴 | 180+ 条规则 |
| I2 | 删除 library_josim/ 或合并 | 🔴 | 与 circuits/standard/ 重复 |
| I3 | 创建 test/standard/README.md | 🔴 | 真值表+测试状态一览 |
| I4 | 标准化 .gitignore | 🔴 | *.html, /tmp, *.csv |

---

## 六、长期方向（Phase 3-5）

| # | 任务 | 状态 | 依赖 |
|---|------|------|------|
| L1 | 4×1 BVM 阵列 | 🔴 | Paper A 完成 |
| L2 | 4×4 BVM 阵列 | 🔴 | L1 |
| L3 | 全链路 PoC (BVM→BQ→逻辑→T1) | 🔴 | L1 + Paper A |
| L4 | SFQ 流水线研究 | 🔴 | — |
| L5 | PIM 指令集设计 | 🔴 | L3 |

---

## 更新日志

| 日期 | 变更 |
|------|------|
| 2026-07-13 | 初始创建，基于 PIM 路线图 + Phase 1 计划 |
