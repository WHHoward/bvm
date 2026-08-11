---
title: WORKFLOW-lite — 三方科研协作协议
version: 1.0
status: FINAL
date: 2026-08-11
supersedes_for_default_use:
  - josim-handoff/v1 的重型日常审计流程
design_goal: 用最小流程成本保持研究可追溯、可复核、不过度主张
---

# WORKFLOW-lite — 三方科研协作协议

## 0. 一句话版本

```text
Codex 定义任务与风险等级
    → Claude 实现并提交 RESULT
    → Copilot Reviewer 做证据层复核
    → Codex 按风险等级做轻量或深度最终审查
    → 用户对研究路线、指标冻结和论文级主张保留最终决定权
```

本协议的目标不是构建“AI 审计系统”，而是让 AI **可靠地推进研究**。

核心原则：

> **普通任务保持轻量；关键科学任务升级审查。**
>
> **代码协作主要靠 Git；只有最终科研证据冻结时才使用 SHA-256。**
>
> **Copilot 负责 evidence-level redundancy；Codex 负责 decision-level redundancy。**

---

# 1. 适用范围

本协议适用于仓库中的研究、仿真、计量、绘图、测试、数据分析与论文证据准备任务。

适合的典型任务包括：

- JoSIM / 超导电路仿真；
- SFQ / JTL / 相位与电压面积相关计量；
- measurement / event-window 实现；
- CLI、脚本、测试与绘图工具；
- raw CSV / derived data / figure 的生成与验证；
- 研究 Gate 与论文主张前的证据准备。

本协议默认假设：

1. 用户、Codex、Claude、Copilot 在同一个受控 Git 仓库内协作；
2. 主要风险是 **AI 犯错、越界、误读证据或过度主张**；
3. 主要威胁不是恶意伪造历史或对抗性篡改。

因此，不为普通任务维护复杂的 request/ACK/receipt/review/verdict 哈希链。

---

# 2. 四个角色

## 2.1 用户 — Final Authority

用户拥有以下最终决定权：

- 研究路线改变；
- 核心 metric 定义或冻结；
- physical Gate 的最终采用；
- 论文级 scientific claim；
- 是否接受重大风险或偏离；
- 是否进入更严格的证据冻结模式。

用户不需要参与每一个机械检查。

---

## 2.2 Codex — Planner + Final Auditor

Codex 负责两件事：

### A. 任务前：Planner

Codex 创建或确认 `TASK.md`，明确：

- 目标；
- 风险等级；
- Git baseline；
- allowed paths；
- acceptance criteria；
- stop conditions；
- claim ceiling；
- 所需 evidence。

### B. 任务后：Final Auditor

Codex 根据风险等级进行最终审查：

- `NORMAL`：阅读 TASK / RESULT / REVIEW，抽查关键 diff 或证据；
- `CRITICAL`：必须亲自检查关键 raw evidence、metric semantics 和科学含义。

Codex 拥有：

```text
ACCEPT
REWORK
BLOCKED
```

的最终任务处置权。

涉及研究路线、metric freeze、physical Gate 或论文主张时，Codex 的意见仍需服从用户的最终决定。

---

## 2.3 Claude — Executor

Claude 是实现者。

Claude 应：

- 只在 `allowed_paths` 内修改；
- 按 `acceptance criteria` 实现与测试；
- 保存必要 raw evidence；
- 不把“程序执行成功”自动解释为“物理结论成立”；
- 完成后写 `RESULT.md`。

Claude 不应：

- 自行扩大任务范围；
- 为了让测试通过而修改合同含义；
- 覆盖原始科研产物；
- 擅自冻结 metric；
- 擅自宣布超出 `claim_ceiling` 的结论。

遇到停止条件时，立即返回 `BLOCKED`，而不是自行绕过。

---

## 2.4 Copilot Reviewer — Evidence Reviewer / Peer Reviewer

Copilot 使用仓库中的：

```text
.github/agents/reviewer.agent.md
```

作为 `reviewer` Agent。

Reviewer 的职责是：

> **检查 Claude 的交付是否由代码、测试和证据支持。**

Reviewer 主要检查：

1. scope；
2. acceptance criteria；
3. 测试与运行证据；
4. raw evidence 抽查 / 独立重算；
5. claim ceiling；
6. 明显异常、矛盾或遗漏。

Reviewer **不是第二个 Codex**。

Reviewer 不负责：

- 重新规划研究；
- 修改实现来“顺手修好”问题；
- 决定研究路线；
- 冻结 metric；
- 给出最终 physical verdict；
- 批准论文级 claim；
- 代替 Codex 做最终审计。

Reviewer 对实现保持只读；唯一允许写入的是任务目录中的：

```text
REVIEW.md
```

---

# 3. 风险等级：只保留两级

所有任务必须标记为：

```text
NORMAL
```

或：

```text
CRITICAL
```

不再维护复杂的多级审计状态。

---

## 3.1 NORMAL

典型任务：

- 绘图布局；
- CLI 修复；
- 文档；
- 测试补充；
- 纯代码重构；
- 非科学语义的工程修复；
- 不改变 metric 含义的辅助脚本。

流程：

```text
Codex TASK
    ↓
Claude RESULT
    ↓
Copilot REVIEW
    ↓
Codex light review
    ↓
ACCEPT / REWORK / BLOCKED
```

Codex 通常无需重复运行 Reviewer 已经完成的全部机械检查。

---

## 3.2 CRITICAL

只要任务影响下列任一项，就属于 `CRITICAL`：

- physical Gate；
- SFQ / JTL / 相位传播等物理判断；
- metric 定义；
- measurement semantics；
- event/window/unit 的定义；
- solver / convergence 争议；
- raw evidence 与结论存在冲突；
- metric freeze；
- 研究路线改变；
- 论文图表的关键数值；
- 论文级 scientific claim；
- 任何可能让后续研究建立在错误结论上的关键节点。

流程仍然保持相同：

```text
Codex TASK
    ↓
Claude RESULT
    ↓
Copilot REVIEW
    ↓
Codex deep review from raw evidence
    ↓
ACCEPT / REWORK / BLOCKED
```

区别只在于 **Codex 的审查深度**，而不是增加更多协议文件。

---

# 4. 最小任务文件

一个任务通常只需要三个文件：

```text
tasks/<TASK-ID>/
├── TASK.md
├── RESULT.md
└── REVIEW.md
```

如果项目已有自己的任务目录，例如：

```text
research/tasks/<TASK-ID>/
```

继续使用现有目录即可。

不要求为了协议重新组织整个仓库。

---

# 5. TASK.md — Codex 的任务合同

`TASK.md` 是唯一必须在执行前冻结语义的文件。

推荐模板：

```markdown
# TASK <TASK-ID>

Risk: NORMAL | CRITICAL
Baseline: <git commit>

## Goal
本任务要完成什么。

## Allowed paths
- path/a/**
- path/b/**

## Acceptance criteria
- [ ] 条件 1
- [ ] 条件 2
- [ ] 条件 3

## Required evidence
- 需要保留的测试输出、raw CSV、figure 或关键数值。

## Stop conditions
遇到以下情况停止并报告 BLOCKED：
- baseline 明显不匹配；
- metric / unit / window 定义存在歧义；
- 必须修改 allowed paths 之外文件；
- 连续两次因同一根因失败；
- 发现会改变研究结论的未预期异常。

## Claim ceiling
本任务允许得出的最强结论。

例如：
Implementation verified only.
No physical conclusion allowed.
```

---

# 6. RESULT.md — Claude 的执行报告

Claude 不需要额外 ACK 文件。

开始执行即视为接受当前 TASK。

推荐模板：

```markdown
# RESULT <TASK-ID>

Status: DONE | BLOCKED

## Summary
完成了什么。

## Changes
- 修改文件与主要变化。

## Verification
- command: ...
  result: PASS / FAIL
- command: ...
  result: PASS / FAIL

## Evidence
- raw evidence 路径；
- 代表性 case；
- 关键数字；
- 必要时给出生成方式。

## Changed files
- path/a
- path/b

## Limitations / anomalies
- 已知限制；
- 未解释异常；
- 未完成项。

## Claim
本次结果实际支持的结论。
必须位于 TASK 的 claim ceiling 内。
```

不要把整份大日志复制进 `RESULT.md`。

推荐写：

```text
command + exit/result + artifact/log path + 关键摘要
```

完整日志保存在文件中。

---

# 7. REVIEW.md — Copilot Reviewer 的证据复核

Reviewer 只做 **证据层复核**。

推荐格式：

```markdown
# REVIEW <TASK-ID>

Review disposition: PASS | REWORK | BLOCKED
Recommended risk: NORMAL | CRITICAL

## Scope
PASS / FAIL
- 是否越过 allowed paths。

## Acceptance criteria
- [x] ...
- [ ] ...

## Independent checks
- 抽查了什么；
- 是否从 raw evidence 独立重算；
- 结果是否与 RESULT 一致。

## Claim ceiling
PASS / FAIL
- Claude 的 claim 是否越界。

## Concerns
- 矛盾；
- 缺失证据；
- 可疑结果；
- 无法复现的项目。

## Codex focus
仅列 Codex 最值得进一步检查的 0–5 个点。
不要重复整个 review。
```

Reviewer 的 `PASS` 表示：

> 在本次 review scope 内，交付物与证据自洽，且没有发现需要返工的问题。

它**不等于**：

```text
physical PASS
scientific truth
metric frozen
paper claim approved
```

---

# 8. Reviewer 应该检查多少？

## 8.1 NORMAL

默认采用抽样而非全量重做：

- scope：全量检查；
- acceptance criteria：逐条检查；
- tests：检查声明并按必要性复跑关键命令；
- raw evidence：抽查 1–2 个代表性 case；
- claim ceiling：全量检查；
- diff：重点看实际修改文件，不重读无关文件。

如果没有异常，停止扩展检查。

---

## 8.2 CRITICAL

Reviewer 应更深入检查 evidence，但仍然不代替 Codex：

- scope：全量；
- acceptance：逐条；
- 关键 tests：复跑；
- 关键 raw evidence：独立重算；
- 单位、窗口、输入/输出映射：检查；
- control case：至少检查一个；
- anomaly：主动寻找；
- claim ceiling：严格检查。

然后给 Codex 一个短的：

```text
Codex focus
```

让 Codex 把推理预算集中到真正的科学风险上。

---

# 9. Codex 的最终审查规则

## 9.1 NORMAL — light review

当：

```text
RESULT = DONE
REVIEW = PASS
```

且没有异常时，Codex 通常只需：

1. 阅读 TASK；
2. 阅读 RESULT；
3. 阅读 REVIEW；
4. 检查关键 diff；
5. 抽查 Reviewer 最重要的一项证据；
6. 决定 ACCEPT / REWORK / BLOCKED。

不要求重新：

- 跑全部测试；
- 重算所有 case；
- 逐个检查所有 artifact；
- 重新完成 Reviewer 的机械复核。

---

## 9.2 CRITICAL — deep review

Codex 必须亲自检查：

- 关键 raw evidence；
- metric / unit / window semantics；
- control case；
- 关键 numerical result；
- evidence 与 claim 的逻辑关系；
- physical interpretation；
- 是否允许推进到下一研究 Gate。

以下事项不能只依赖 Reviewer 摘要：

- physical Gate；
- metric freeze；
- SFQ/JTL 核心结论；
- 路线改变；
- 论文主张；
- 证据冲突；
- numerical convergence / unit / window 争议。

---

# 10. Git 与 SHA-256 策略

## 10.1 日常代码追踪：Git 即可

任务开始记录：

```text
Baseline: <git commit>
```

主要依赖：

```text
git status
git diff
git log
git show
```

回答：

- 从哪个版本开始；
- 改了哪些文件；
- 是否越界；
- 当前代码状态是什么。

普通任务不再维护：

- request SHA；
- ACK SHA；
- RESULT SHA；
- REVIEW SHA；
- verdict SHA；
- 多层 hash binding。

---

## 10.2 SHA-256 只用于“冻结科研证据”

当一个 artifact 将用于：

- final physical Gate；
- metric freeze；
- 论文核心数字；
- 论文 figure；
- 最终可复现数据集；
- 用户或 Codex 明确要求长期冻结；

才建议记录 SHA-256。

例如：

```text
evidence/final-gate.csv
evidence/final-gate.csv.sha256
```

原则：

> **代码历史用 Git；最终科研证据冻结用 SHA-256。**

SHA-256 是完整性标记，不是“谁执行了某条命令”的身份证明。

---

# 11. Claim Ceiling — 必须保留

`claim_ceiling` 是本协议中成本最低、价值最高的安全边界之一。

示例：

### 工程任务

```text
Claim ceiling:
Implementation verified only.
No physical conclusion allowed.
```

### measurement 任务

```text
Claim ceiling:
May report measurement outputs and controls.
May not freeze the metric or change the research route.
```

### Critical scientific task

```text
Claim ceiling:
May evaluate evidence for the stated physical Gate.
Final adoption remains with Codex/User.
```

任何角色都不得静默突破 claim ceiling。

---

# 12. Stop Conditions — 防止 AI 自行扩大范围

满足以下任一条件应停止：

1. baseline 与 TASK 明显不匹配；
2. allowed paths 与实际需要冲突；
3. acceptance criteria 自相矛盾或无法解释；
4. metric / unit / window 定义存在实质歧义；
5. 连续两次因同一根因失败；
6. 为“让结果通过”必须改变任务定义；
7. 发现可能改变研究结论的重大异常；
8. raw evidence 缺失或不可读取；
9. 需要覆盖、删除或重写已有关键科研证据。

停止后：

```text
Status: BLOCKED
```

并说明：

```text
what happened
why it blocks the task
minimum decision/change needed
```

不要自行扩大 scope。

---

# 13. 状态机

不再维护复杂状态机。

只使用：

```text
TODO
  ↓
RUNNING
  ↓
REVIEW
  ├─ ACCEPTED
  ├─ REWORK
  └─ BLOCKED
```

如果 `REWORK`：

- 更新现有 RESULT / REVIEW 或保留简短 revision note；
- 不强制创建复杂的 A01/A02/R01/C01 树；
- 若任务已经进入论文证据冻结阶段，可由 Codex 临时升级为 Formal Freeze。

---

# 14. Formal Freeze — 只在真正需要时升级

默认关闭。

只有当以下情况出现时启用：

- publication-grade evidence；
- metric freeze；
- final Gate；
- 严重 evidence conflict；
- 用户明确要求；
- Codex 认为未来需要严格证明“当时使用的是哪一份 artifact”。

启用后可增加：

- artifact SHA-256；
- frozen snapshot；
- 明确的 raw → derived → figure 映射；
- 更完整的 audit note。

重要的是：

> Formal Freeze 是按需升级，不是所有任务的默认成本。

---

# 15. Token / 上下文预算原则

所有角色必须遵循：

## 不做

- 不复制整份日志；
- 不复制整份 diff；
- 不在每个文件里重复 TASK；
- 不重复机械检查结果；
- 不为普通任务输出长篇审计叙事；
- 不为了“完整”而读取与任务无关的文件。

## 要做

- 用路径引用 raw artifact；
- 报告命令 + 结果 + 关键摘要；
- Reviewer 先抽样，有异常才扩展；
- Codex 优先阅读 `Codex focus`；
- NORMAL 保持短；
- CRITICAL 把 token 花在 raw evidence 与科学语义上。

---

# 16. 三方不允许形成“共识幻觉”

下游角色不能因为上游角色说 PASS 就自动 PASS。

### Claude

必须基于执行结果写 RESULT。

### Reviewer

不得仅检查：

```text
“Claude 说测试过了”
```

而应按风险抽查实际命令、diff 或 raw evidence。

### Codex

CRITICAL 任务不得仅因为：

```text
Reviewer = PASS
```

就接受科学结论。

原则：

> **每一层都必须有自己的最小独立证据来源。**

但独立检查不等于全量重复。

---

# 17. 推荐目录

```text
.github/
└── agents/
    └── reviewer.agent.md

research/
├── WORKFLOW-lite.md
├── tasks/
│   ├── M5/
│   │   ├── TASK.md
│   │   ├── RESULT.md
│   │   └── REVIEW.md
│   └── M12/
│       ├── TASK.md
│       ├── RESULT.md
│       └── REVIEW.md
└── evidence/
```

如果现有仓库结构不同，以现有结构优先。

---

# 18. 最终职责矩阵

| 工作 | Claude | Copilot Reviewer | Codex | 用户 |
|---|---:|---:|---:|---:|
| 实现代码 | ✅ | ❌ | 通常 ❌ | ❌ |
| 修改任务目标 | ❌ | ❌ | 建议/签发 | 最终权 |
| 检查 scope | 自检 | ✅ | 抽查 | — |
| 跑测试 | ✅ | 关键项复跑 | NORMAL 抽查 / CRITICAL 复核 | — |
| raw evidence 抽查 | 提供 | ✅ | CRITICAL 必须 | — |
| 独立重算关键数字 | 可自检 | ✅ | CRITICAL 必须检查关键项 | — |
| claim ceiling | 遵守 | ✅ | ✅ | 可提升/限制 |
| physical verdict | 不越权 | ❌ | 评估 | 最终采用权 |
| metric freeze | ❌ | ❌ | 建议 | 最终采用权 |
| 论文级 claim | ❌ | ❌ | 审查 | 最终采用权 |
| 写 REVIEW.md | ❌ | ✅ | ❌ | — |

---

# 19. 默认工作口令

## 给 Codex

```text
按照 WORKFLOW-lite 创建下一项 TASK，标记 NORMAL 或 CRITICAL。
```

## 给 Claude

```text
执行 TASK.md。严格遵守 allowed paths、stop conditions 和 claim ceiling。
完成后写 RESULT.md；遇到阻塞写 BLOCKED，不自行扩大 scope。
```

## 给 Copilot

选择 `reviewer` Agent，然后：

```text
Review this task under WORKFLOW-lite.
Read TASK.md and RESULT.md, inspect the actual diff/evidence,
perform the minimum independent checks required by the task risk,
and write REVIEW.md only.
```

## 给 Codex 最终审查

```text
Review TASK.md, RESULT.md and REVIEW.md under WORKFLOW-lite.
For NORMAL use light review.
For CRITICAL independently inspect the critical raw evidence and scientific semantics.
Return ACCEPT, REWORK or BLOCKED.
```

---

# 20. 协议底线

无论以后怎么简化，都保留以下底线：

```text
1. 任务目标必须明确。
2. Claude 的写入范围必须明确。
3. acceptance criteria 必须明确。
4. stop conditions 必须明确。
5. claim ceiling 必须明确。
6. Reviewer 必须做最低限度的独立证据检查。
7. CRITICAL 科学任务必须由 Codex 从 raw evidence 深度复核。
8. 用户保留路线、metric freeze、physical Gate 和论文主张的最终决定权。
```

只要这八条还在，流程就可以继续保持轻量。
