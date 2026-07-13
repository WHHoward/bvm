---
name: project-todo
description: JoSIM 项目主任务清单 — 所有工作项的状态追踪，每次会话开始/结束时更新
metadata:
  type: project
  node_type: memory
  last_updated: 2026-07-13
---

# JoSIM 项目主任务清单

> **规则**: 每次会话开始时检查进度，完成或新增项目时更新。状态: 🔴未开始 🟡进行中 🟢已完成 ⏸️暂停

---

## 一、Paper A: BVM→BQ 接口设计

| # | 任务 | 状态 | 产出 | 预计工时 |
|---|------|------|------|---------|
| T1 | BVM→BQ 级联基线测试 | 🔴 | 量化失配数据 | 1.5h |
| T2 | 低 IC BQ 子电路设计 | 🔴 | `bq_cell_lowic.cir` | 2h |
| T3 | 低 IC 参数扫描 | 🔴 | 触发窗口图表 | 2h |
| T4 | K 元件变压器设计 | 🔴 | `tx_k_element.cir` | 2h |
| T5 | 变压器参数扫描 | 🔴 | n-k 热力图 | 2h |
| T6 | 双方案对比分析 | 🔴 | 6指标对比表+雷达图 | 1.5h |
| T7 | 扰动鲁棒性测试 | 🔴 | 工作窗口边界 | 2h |
| T8 | 论文初稿 (ARS skills) | 🔴 | arXiv 预印本 | 4h |

**Phase 1 总计**: ~17h | **Gate**: arXiv 预印本提交

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
