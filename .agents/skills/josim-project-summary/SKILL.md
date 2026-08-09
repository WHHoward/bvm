---
name: josim-project-summary
description: Produce or persist evidence-backed JoSIM/BVM project summaries, handovers, knowledge snapshots, and change history. Use when the user asks to summarize, archive, update project memory, record material changes, or prepare a handoff; a read-only status request must not mutate files, and cleanup or deletion requires separate explicit authorization.
---

# JoSIM 项目总结

## 证据层级

按下列方向汇总，不让上层文档替代原始证据：

```text
网表、include、原始 CSV、manifest、求解日志
  → 版本化指标与 Gate 结果
  → 单次实验分析/实验日志
  → memory/project-todo.md
  → memory/project-summary.md 与 docs/HANDOVER.md
  → CHANGELOG.md
```

## 只读总结

当用户只问状态或总结时：

1. 读取 `docs/HANDOVER.md`、`memory/project-todo.md` 和相关事实层产物。
2. 将内容分为“已观察”“解释性推断”“未知/待验证”“下一 Gate”。
3. 给出可点击证据路径，不修改任何文件。

## 持久化总结

用户要求记录、归档或交接，或者当前实现确实产生了需要保存的重大变化时：

1. 先核验产物、测试和工作树，保留用户的既有修改。
2. 对 `research/tasks/` 交付，先核验 request/ACK/receipt/audit 绑定；只有 `ACCEPTED` 审计才能上推为项目事实。
3. 先更新对应实验事实层；不要从上层摘要反向生成原始事实。
4. 按完成标准更新 `memory/project-todo.md`，不得把不确定结果标为完成。
5. 仅在项目状态或路线确有变化时更新 `memory/project-summary.md` 和 `docs/HANDOVER.md`。
6. 新增知识文件时才更新 `memory/MEMORY.md`；不要批量触碰无关 memory 文件。
7. 在 `CHANGELOG.md` 顶部追加一个带当前日期的材料性变更条目；避免为同一工作重复追加。
8. 运行文档/脚本的相关验证和 `git diff --check`。

## 写作规则

- 每个数字写明单位、数据来源、窗口/对照和指标版本。
- 将源码/网表事实、论文原文、项目仿真、推断和待验证明确区分。
- 对失效结论添加 `superseded` 入口并链接替代结果；保留历史证据。
- 负面结论限定模型、激励、负载、参数范围和指标版本，不写成普遍不可能。
- 仿真证据不得写成硬件实测。
- **时间标注（2026-08-06 起强制，用户要求）**：修改任何项目文档（todo/summary/memory/CHANGELOG）时，在修改处标注日期（YYYY-MM-DD），并同步更新 frontmatter `last_updated`；避免多会话交替修改造成状态混乱。

## 清理边界

普通总结不得删除任何文件。即使文件可重新生成，也只能在用户明确要求清理后列出精确目标、依据和可恢复性，再单独执行。原始网表、CSV、manifest、失败实验和历史审计证据默认不得删除。

## 输出

列出更新过的文件、证据层级、完成的验证、保留的不确定性和下一 Gate。若只读，明确说明未写入仓库。
