---
name: josim-todo-manager
description: Inspect or update the JoSIM/BVM master task list using current evidence and completion criteria. Use for project progress, dependencies, next unblocked work, task completion, reprioritization, or edits to `memory/project-todo.md`; status questions are read-only unless the user requests changes or the current work actually changes task evidence.
---

# JoSIM 任务管理

## 权威来源

- 任务与完成标准：`memory/project-todo.md`
- 当前执行状态与事故边界：`docs/HANDOVER.md`
- 完成证据：原始网表/CSV/manifest、版本化指标、Gate 结果和对应实验日志

不得在本 skill 中硬编码当前路线、截止日期、分类或优先级；每次从上述文件读取。

## 查看状态

1. 读取任务表头、状态说明、依赖和相关完成标准。
2. 统计各状态，但把表格中的说明文字与真正任务行分开。
3. 找出第一个依赖已满足的高优先级任务；若依赖未写明，从 Gate 顺序推断时明确标成推断。
4. 报告当前阶段、下一项、阻塞条件和证据路径。
5. 不因“查看进度”“接下来做什么”而修改仓库。

## 更新任务

仅在用户明确要求更新，或本轮实际产出改变了完成证据时编辑：

1. 对照该任务的“完成标准”，逐项核验可追溯产物。
2. 只有全部满足时标为完成；计划、讨论、只读审计和 `INCONCLUSIVE` 结果都不算完成。
3. 若工作由 `research/tasks/` 交接执行，只有对应 audit disposition 为 `ACCEPTED` 且完成标准确实满足，才上推任务状态；receipt 中的 `COMPLETED` 本身不够。
4. 进行中的工作标为进行中；外部依赖或被取代路线才标为暂停，并写明原因。
5. 使用当前日期更新任务行和 `last_updated`；按现有格式追加一条简短更新记录（若文件有该区域）。
6. 不重排或重写无关任务，不虚构工时、截止日期或依赖。

## 完成证据最低要求

实验任务通常需要：唯一 run ID、输入网表和 include 闭包、原始 CSV、JoSIM/脚本/规格版本、匹配对照、结果判定和验证日志。若任务完成标准要求收敛或系统 Gate，单次波形或哈希重复不能替代它。

## 输出

给出状态变化前后、满足的完成标准、证据链接、仍未满足的条件和下一项。没有修改时明确写“本次只读，未更新任务表”。
