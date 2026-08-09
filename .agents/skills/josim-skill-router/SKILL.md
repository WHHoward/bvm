---
name: josim-skill-router
description: Route broad, ambiguous, or multi-part JoSIM/BVM repository work to the smallest applicable project skills. Use when deciding how to handle a task spanning experiments, phase/SFQ evidence, visualization, project status, or handover; do not use for a single obvious action already covered by one named skill.
---

# JoSIM 工作流路由

## 路由流程

1. 用一句话确定用户要得到的结果，不把“查看状态”扩大成写文件或跑实验。
2. 只有任务涉及当前路线或依赖关系时，读取 `docs/HANDOVER.md` 和 `memory/project-todo.md`。
3. 从下表选择覆盖任务所需的最小 skill 集合，并按依赖顺序使用。
4. 在开始时只说明一次所选 skill；不要在每个工具调用前重复仪式文本。

| 任务 | 使用的项目 skill |
|---|---|
| 创建、修改、运行或扫描 `.cir` 实验 | `josim-experiment` |
| 解释 `P()`、SFQ 数、相位、电压面积、JTL 接收或 Gate | `josim-evidence-audit` |
| 绘制 CSV/DAT 波形 | `josim-viz`；若还要物理判定，再加 `josim-evidence-audit` |
| 查询进度、依赖、下一项或更新任务状态 | `josim-todo-manager` |
| 生成会话总结、交接、知识快照或变更记录 | `josim-project-summary` |

## 项目级约束

- 以当前 `docs/HANDOVER.md` 和 `memory/project-todo.md` 为状态来源，不在 skill 中复制易过期的路线结论。
- 在 Phase −1 的 M4–M11 完成前，不得把 `scripts/sfq_metrics.py` 或 `scripts/run_exp.sh` 的旧 JSON 当作物理 Gate。
- 仅在当前运行时确实可用时调用外部 skill；不得把不存在的插件或命令写成强制依赖。
- 独立且文件不冲突的重任务可以并行；主代理负责证据审阅和最终判定。
- **并行 subagent 必须文件隔离（2026-08-06 起，用户要求）**：各 agent 只写自己前缀的文件，提交时只 `git add` 自己的文件（防止并行提交竞态）；派发上下文配方：HANDOVER → 相关 skill/契约 → 任务全文 → 冻结口径（相对路径、不可覆盖、禁 sed 生成变体）。
- 完成声明必须附验证结果；未知、缺证据或步长不收敛时使用“不确定”，不得挑选有利结果。

## 路由输出

简洁报告：任务、所选 skill、执行顺序，以及任何会阻止物理结论的当前 Gate。选完后继续完成任务，不要仅停在路由说明。
