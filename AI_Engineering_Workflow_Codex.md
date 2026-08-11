# AI Engineering Workflow
## Codex Work 模式下的 Sol + Terra + Luna + Claude Code 协作规范

> Version: 1.0  
> Purpose: 在保证项目工程质量的前提下，尽可能减少高成本模型的 Token、Credits 和上下文消耗。  
> Primary Orchestrator: Codex  
> Primary Implementation Agent: Claude Code

> **JoSIM × BVM 项目适配（2026-08-11）**：本文提供通用的成本与角色分工建议；本仓库中任务授权、物理计量和研究结论的权威顺序是 `AGENTS.md` → `memory/project-todo.md` → `docs/HANDOVER.md` → 已签发的 `research/tasks/<task-id>/request.yaml` → `research/WORKFLOW.md`。因此不使用本文建议的 `.ai/tasks/` 目录，也不以“测试通过”替代 JoSIM 原始证据、收敛检查或 Codex 审计。运行环境未提供文中某个模型时，按职责层级选择可用的较低成本模型或确定性工具，不虚构模型能力。

---

## 1. 核心目标

本开发环境采用多模型分工，而不是让单一模型承担整个软件生命周期。

基本原则：

> **让最便宜、最合适的工具完成任务，并且只在确实需要时升级模型。**

推荐职责：

```text
GPT-5.6 Sol
    │
    ├── Architecture
    ├── Design
    ├── Technical Direction
    ├── Critical Decisions
    └── Final / Milestone Review

GPT-5.6 Terra
    │
    └── Codex Controller / Daily Orchestrator

Claude Code
    │
    ├── Implementation
    ├── Refactoring
    ├── Bug Fixing
    └── Feature Development

GPT-5.6 Luna
    │
    ├── QA
    ├── Testing
    ├── Diff Review
    ├── Regression Analysis
    └── Acceptance Verification
```

任何 Agent 都不应该无理由越过自己的职责边界。

---

## 2. Codex 日常默认模型

Codex 日常主线程推荐使用：

```text
Model:
GPT-5.6 Terra

Reasoning:
Medium
```

Terra 是整个系统中的：

```text
Controller
Coordinator
Task Router
State Manager
```

而不是主要程序员。

Codex 主线程主要负责：

- 理解当前任务状态
- 阅读项目计划
- 判断下一步应该做什么
- 选择正确的执行 Agent
- 创建任务
- 调用 Claude Code
- 调用 Luna
- 判断是否需要升级到 Sol
- 更新任务状态
- 管理开发流程

不要让 Codex 主线程承担大量实现代码工作。

---

## 3. Reasoning 使用原则

任何模型都应该：

> 使用能够可靠完成当前任务的最低 Reasoning Level。

推荐规则：

```text
简单明确任务
        ↓
Light / Low

普通开发任务
        ↓
Medium

复杂问题
        ↓
High

非常困难的问题
        ↓
Extra High / xhigh

极端困难且价值非常高的问题
        ↓
Max
```

不要因为模型支持 Extra High 或 Max 就默认使用。

---

## 4. GPT-5.6 Terra —— Codex Controller

### 默认设置

```text
GPT-5.6 Terra
Reasoning: Medium
```

适用于：

- 项目状态判断
- Task 路由
- Git 状态理解
- 读取 PLAN
- 读取任务描述
- 调度其他 Agent
- 整理任务
- 创建简短 Prompt
- 判断测试是否通过
- 管理开发流程

### Terra High 使用条件

只有以下情况可以升级为：

```text
Terra
High
```

例如：

- 多模块之间存在依赖
- 当前任务状态难以判断
- 多个 Agent 的结果互相冲突
- 需要复杂任务拆分
- 普通调度无法判断下一步

任务结束后，应恢复：

```text
Terra Medium
```

---

## 5. GPT-5.6 Sol —— Architect / Technical Lead

Sol 是项目中技术决策权最高的 Agent。

但 Sol 不应该是工作量最大的 Agent。

理想状态：

```text
工作量：

Claude Code   ████████████████████
Luna          ████
Terra         ███
Sol           █
```

而决策权：

```text
Sol           ████████████████████
Terra         ███████████
Luna          █████
Claude Code   ███
```

### Sol 的职责

#### Requirements

- 复杂需求分析
- 模糊需求澄清
- 发现需求矛盾
- 定义系统边界

#### Architecture

- 系统架构
- 模块划分
- 数据模型
- API 设计
- 公共接口
- 数据库架构
- 核心抽象
- 状态模型

#### Technical Direction

- 技术选型
- 长期技术路线
- 重大重构
- 性能策略
- 安全策略

#### Review

- Architecture Review
- Milestone Review
- Release Review
- Critical Change Review

### Sol 默认不应该做什么

Sol 不应该用于：

- 写普通 CRUD
- 修改普通 UI
- 修改普通函数
- lint
- 格式化
- 跑普通测试
- 修简单 Bug
- 写普通单元测试
- 看普通测试日志
- 重复阅读整个代码仓库
- 做机械性 Diff Review
- 更新普通文档
- 重复解释已经记录过的设计

这些工作应该交给：

```text
Claude Code
Luna
Terra
Deterministic Tools
```

### Sol 推理级别

默认：

```text
Sol
Extra High
```

适合：

- 初始架构
- 重大设计
- 架构冲突
- 核心设计 Review
- 重大重构
- 复杂技术决策

只有极少情况可以使用：

```text
Sol
Max
```

例如：

- 极困难跨系统问题
- 高风险架构决策
- 多个方案长期影响巨大
- xhigh 无法可靠解决的问题

不要日常使用 Max。

---

## 6. Claude Code —— Primary Implementation Agent

Claude Code 是项目的主要执行者。

负责：

- 编写 Production Code
- Feature Implementation
- Bug Fix
- Refactoring
- 添加测试
- 修改配置
- 修改构建文件
- 实现 API
- 实现数据库访问
- 实现业务逻辑
- 前端实现
- 后端实现
- 性能优化实施

原则：

> Architect 决定 What 和 Why。  
> Claude Code 决定具体 How，并完成实现。

### Claude Code 不应该自行修改核心架构

以下情况 Claude Code 必须停止实现：

- 需要改变公共 API
- 需要改变数据库 Schema
- 需要改变核心数据模型
- 需要改变模块边界
- 发现架构存在明显问题
- Acceptance Criteria 与设计冲突
- 发现需求无法按当前架构完成

处理流程：

```text
Claude Code
      ↓
发现架构问题
      ↓
停止扩大修改
      ↓
生成 Handoff
      ↓
Codex Controller
      ↓
Sol Architect
```

Sol 给出新的设计决策后再继续实现。

---

## 7. Codex 与 Claude Code 的边界

Claude Code 属于外部 Implementation Agent。

如果当前环境已经配置：

```text
Claude Code CLI
Claude Code Tool
Wrapper Script
MCP
或其他可靠调用方式
```

Codex 应优先通过该机制调用 Claude Code。

如果当前环境无法直接调用 Claude Code：

Codex 不应该偷偷把 Implementation Agent 的全部工作接管。

应生成：

```text
.ai/tasks/TASK-XXX.md
```

作为 Claude Code 的完整任务包。

任务包应能独立交给 Claude Code 执行。

---

## 8. GPT-5.6 Luna —— QA / Verification

Luna 是默认 QA Agent。

主要负责：

- Diff Review
- Acceptance Verification
- Test Failure Analysis
- Regression Detection
- Boundary Condition Analysis
- Error Handling Review
- Missing Test Detection
- Implementation Verification

### Luna 推理级别

默认：

```text
Luna
Medium
```

用于：

- 普通 Diff
- 测试结果分析
- Acceptance Criteria 检查
- 普通 Bug Review
- 单模块检查

升级：

```text
Luna
High
```

用于：

- 复杂业务逻辑
- 多模块行为
- 并发
- 状态机
- 生命周期
- 数据一致性
- Regression

只有极少情况：

```text
Luna
Extra High
```

用于：

- 非常隐蔽的 Bug
- 跨多个子系统
- High 无法解释的失败
- Critical correctness issue
- 高风险安全问题

不要默认使用 Luna Extra High。

### Luna 默认 Read Only

Luna 原则上应该：

```text
READ ONLY
```

它应该发现问题，而不是修改 Production Code。

流程：

```text
Luna
 ↓
发现问题
 ↓
生成 Finding
 ↓
Claude Code
 ↓
修复
```

这样可以避免 Reviewer 自己修改自己刚刚 Review 的代码，造成角色混乱。

---

## 9. Deterministic Tools 优先

在调用任何 AI 之前，首先考虑：

> 能不能由确定性工具完成？

推荐优先级：

```text
1. Deterministic Tool
2. Luna
3. Claude Code
4. Terra
5. Sol
```

例如：

```text
pytest
npm test
pnpm test
cargo test
go test
ctest

eslint
ruff
mypy
pyright

tsc
cargo check
go vet

compiler
formatter
static analyzer
CI
```

如果：

```text
TEST PASS
```

不要让多个模型重新分析一遍测试日志。

如果：

```text
TEST FAIL
```

再调用 Luna 分析。

---

## 10. 标准 Bug 流程

```text
TEST
 │
 ├──── PASS
 │       ↓
 │     VERIFY
 │
 └──── FAIL
         ↓
       Luna
         ↓
   Analyze Failure
         ↓
      Claude
         ↓
       Fix
         ↓
       TEST
```

---

## 11. 两次失败升级规则

非常重要：

> Claude Code 对同一个 Root Cause 连续修复两次仍失败时，停止继续试错。

流程：

```text
Claude Attempt #1
       ↓
     FAIL
       ↓
Claude Attempt #2
       ↓
     FAIL
       ↓
     STOP
       ↓
Luna Root Cause Analysis
       ↓
如果是架构问题
       ↓
Sol
```

原因：

连续失败可能意味着：

- 架构错误
- API 理解错误
- 状态模型错误
- Requirement 冲突
- 数据模型错误
- 根因判断错误

此时继续让 Coding Agent 重试通常只会浪费 Token。

---

## 12. Feature 标准开发生命周期

每一个较大的 Feature 应该遵循：

```text
REQUEST
   ↓
SPEC
   ↓
ARCHITECTURE
   ↓
PLAN
   ↓
TASK
   ↓
IMPLEMENT
   ↓
TEST
   ↓
VERIFY
   ↓
FIX
   ↓
VERIFY
   ↓
COMPLETE
```

不要：

```text
模糊需求
   ↓
直接开始写代码
```

---

## 13. Sol 的标准调用时机

Sol 只应该在 Gate 上出现。

### Gate A — Architecture

```text
New Major Feature
        ↓
Sol
        ↓
Architecture
```

### Gate B — Architecture Conflict

```text
Implementation
      ↓
Architecture Problem
      ↓
Sol
```

### Gate C — Milestone Review

```text
Several Tasks Complete
        ↓
Sol
        ↓
Milestone Review
```

---

## 14. Sol 调用预算思想

普通 Feature：

```text
Sol Call #1
Architecture

Sol Call #2
Optional Architecture Escalation

Sol Call #3
Final / Milestone Review
```

理想情况下：

```text
1～3 次 Sol
```

即可完成一个较大的 Feature。

不要：

```text
每完成一个文件
↓
问 Sol

每修改一个函数
↓
问 Sol

每一次 Test
↓
问 Sol
```

---

## 15. Project Memory

为了减少所有 Agent 重复理解整个仓库，应建立项目长期记忆文件。

推荐：

```text
docs/

ARCHITECTURE.md
PLAN.md
DECISIONS.md
ACCEPTANCE.md
```

### ARCHITECTURE.md

记录：

- 系统整体结构
- 模块职责
- 数据流
- 核心接口
- 数据模型
- 技术栈
- Architectural Constraints

Sol 第一次可以全面理解项目。

之后优先读取：

```text
ARCHITECTURE.md
```

而不是重新扫描整个仓库。

### DECISIONS.md

所有重要架构决策应该记录：

```text
Decision ID
Date
Problem
Options
Decision
Reason
Consequences
```

Agent 不应该反复重新讨论已经确定的问题。

### PLAN.md

PLAN 应包含：

```text
Feature
Goal
Architecture
Milestones
Tasks
Dependencies
Risks
Acceptance Criteria
```

Claude Code 不需要重新设计整个 Feature。

只需要执行对应 Task。

---

## 16. Task System

推荐目录：

```text
.ai/
├── tasks/
├── handoffs/
└── reports/
```

Task：

```text
.ai/tasks/TASK-001.md
```

### Task 格式

```markdown
# TASK-XXX

## Objective

清晰说明需要完成什么。

## Context

只列出完成任务必须了解的信息。

## Relevant Files

相关文件和目录。

## Scope

允许修改什么。

## Out of Scope

不允许修改什么。

## Constraints

必须遵守的限制。

## Acceptance Criteria

明确什么条件意味着任务完成。

## Required Tests

必须执行哪些测试。

## Architecture References

关联的 Architecture / Decision ID。
```

### Task 必须足够小

一个良好的 Task 应该：

- 一个 Agent 能独立理解
- 一个 Agent 能独立完成
- 有清晰 Done Definition
- 可以独立验证
- 不需要重新阅读整个 Repo

如果 Task 太大：

```text
TASK
 ↓
拆分
 ↓
TASK-A
TASK-B
TASK-C
```

---

## 17. Claude Code Handoff

Claude Code 完成任务后不要输出巨大总结。

只生成短 Handoff：

```markdown
# TASK-XXX HANDOFF

Status:
COMPLETE / BLOCKED

Files Changed:
- file1
- file2

Implemented:
- ...

Tests Added:
- ...

Commands Run:
- ...

Validation:
PASS / FAIL

Commit:
<commit>

Concerns:
- ...

Architecture Impact:
NONE / POSSIBLE / CONFIRMED
```

---

## 18. 禁止 Agent 之间传递完整聊天记录

不要：

```text
Sol 输出 20k tokens
        ↓
Claude 读 20k
        ↓
Luna 读 20k
        ↓
Terra 再读 20k
```

Agent 之间应该通过：

```text
Git Diff
Task File
Architecture File
Decision File
Handoff
Test Result
```

交流。

---

## 19. Git 是主要事实来源

Implementation 完成后：

Reviewer 应优先查看：

```text
git diff
```

而不是 Claude Code 的聊天记录。

代码本身：

```text
Source of Truth
```

Handoff：

```text
Summary
```

---

## 20. 测试日志 Token 控制

不要把完整日志直接发送给模型。

例如：

```text
10,000 lines test.log
```

应该先：

```text
grep error
grep failed
tail
```

或者保存：

```text
.ai/reports/test.log
```

给 Agent：

```text
Failure summary
Relevant lines
Log path
```

只有确实需要时才读取完整日志。

---

## 21. Context Budget Policy

每一次 Agent 调用都应该问：

> 这个 Agent 真正需要知道什么？

优先提供：

```text
Task
Relevant Diff
Relevant Files
Architecture Summary
Acceptance Criteria
Relevant Error
```

避免：

```text
Entire Repository
Entire Chat History
Entire CI Log
Entire Documentation
```

---

## 22. Progressive Context Loading

使用：

```text
Level 1
Task Summary

↓ 不够

Level 2
Relevant Files

↓ 不够

Level 3
Relevant Module

↓ 不够

Level 4
Broader Repository Context
```

不要一开始直接使用 Level 4。

---

## 23. QA 输出格式

Luna 应只输出 actionable findings。

格式：

```text
Severity:
BLOCKER / HIGH / MEDIUM / LOW

Location:
file / symbol

Problem:
...

Evidence:
...

Expected:
...

Suggested Direction:
...
```

如果没有阻塞问题：

```text
VERIFIED
```

不要为了“看起来认真”而制造无意义问题。

---

## 24. Review Priority

Review 优先级：

```text
Correctness
Security
Data Integrity
Regression
Error Handling
Boundary Conditions
Concurrency
Performance
Maintainability
Style
```

纯 Style 问题优先级最低。

---

## 25. Architecture Escalation Conditions

满足以下任意条件：

```text
Public API Change
Database Schema Change
Core Data Model Change
Cross-module Architecture Change
Security Boundary Change
Concurrency Model Change
Persistent State Change
Major Dependency Change
```

必须考虑升级 Sol。

### 不需要 Sol 的情况

以下情况默认不调用 Sol：

```text
rename
format
lint
simple test
simple bug
small refactor
documentation typo
UI copy
small CSS adjustment
routine CRUD
test fixture
mock
simple configuration
```

---

## 26. 日常 Codex 决策树

Codex Controller 对每个请求执行：

```text
收到任务
   ↓
任务是否明确？
   │
 ┌─┴───────────┐
 │             │
是             否
 │             │
 ↓             ↓
是否需要架构？  Sol
 │
 ┌─┴────────────┐
 │              │
否              是
 │              │
 ↓              ↓
Task           Sol
 │              │
 ↓              ↓
Claude        Plan
 │              │
 ↓              ↓
Test          Task
 │
 ↓
Pass?
 │
 ├─ No → Luna → Claude
 │
 └─ Yes
      ↓
    Luna
      ↓
Verified?
 │
 ├─ No → Claude
 │
 └─ Yes
      ↓
   Complete
```

---

## 27. Codex 不应该过度代理

Codex Controller 不应该因为：

```text
“我自己也能写”
```

就接管 Claude Code 的职责。

必须尊重 Role Boundary。

Codex 主要目标不是：

```text
自己完成最多工作
```

而是：

```text
让整个系统以最低成本正确完成工作。
```

---

## 28. 模型选择总表

| Task | Model | Reasoning |
|---|---|---|
| 日常 Codex Controller | Terra | Medium |
| 简单调度 | Terra | Light |
| 复杂调度 | Terra | High |
| Architecture | Sol | Extra High |
| Major Design | Sol | Extra High |
| Critical Review | Sol | Extra High |
| Extreme Architecture Problem | Sol | Max |
| Routine QA | Luna | Medium |
| Diff Review | Luna | Medium |
| Complex QA | Luna | High |
| Regression Analysis | Luna | High |
| Extreme Verification | Luna | Extra High |
| Implementation | Claude Code | External |
| Bug Fix | Claude Code | External |
| Refactoring | Claude Code | External |

---

## 29. Token 优化优先级

当目标是减少 Token / Credits 时：

第一优先：

```text
避免重复工作
```

第二优先：

```text
减少 Context
```

第三优先：

```text
降低 Reasoning
```

第四优先：

```text
选择更便宜模型
```

第五优先：

```text
减少 Agent 次数
```

真正最大的 Token 浪费通常来自：

```text
重复读代码
重复读日志
重复解释需求
多个 Agent 重做同一个分析
无意义的 Review Loop
过大的 Task
```

---

## 30. 禁止无限 Review Loop

最多执行：

```text
Implementation
↓
Verification
↓
Fix
↓
Verification
```

如果多次循环仍无法解决：

```text
STOP
↓
Root Cause Analysis
```

而不是无限：

```text
Claude
Luna
Claude
Luna
Claude
Luna
...
```

---

## 31. Parallelism Policy

只有真正互不依赖的任务才并行。

可以：

```text
Task A ─ Claude
Task B ─ Claude
Task C ─ Luna Analysis
```

不能：

```text
三个 Agent
同时修改同一个核心模块
```

并行不是免费的。

更多 Agent 意味着：

- 更多上下文
- 更多 Token
- 更多 Merge 成本
- 更多冲突风险

默认保持最低必要并行度。

---

## 32. Completion Definition

一个 Task 只有满足以下条件才算完成：

- Implementation 完成
- Acceptance Criteria 满足
- Relevant Tests Pass
- Static Checks Pass
- 没有 Blocker
- 没有重大 Regression
- Luna Verification 通过

普通 Task 不需要 Sol Review。

---

## 33. Milestone Definition

一个 Milestone 完成后，可以让 Sol 进行一次 Review。

输入应尽可能只包含：

```text
Architecture
Relevant Decisions
Milestone Summary
git diff / commit range
Test Summary
Known Risks
```

不要自动把整个项目重新塞给 Sol。

---

## 34. 最终执行原则

Codex 必须始终遵守：

> Do not use the smartest model when a cheaper model is sufficient.

> Do not use AI when a deterministic tool is sufficient.

> Do not reread information that has already been persisted.

> Do not make one Agent rediscover work already completed by another Agent.

> Do not send full repository context when targeted context is sufficient.

> Do not call Sol for routine implementation.

> Do not use Extra High reasoning by default.

> Do not let Claude Code redefine architecture silently.

> Do not allow Luna to become the implementation agent.

> Use Git, Tasks, Architecture documents and concise Handoffs as the communication layer between Agents.

---

## 35. Default Operating Configuration

正常项目状态建议为：

```text
CODEX CONTROLLER

Model:
GPT-5.6 Terra

Reasoning:
Medium
```

Architecture escalation：

```text
GPT-5.6 Sol
Extra High
```

QA：

```text
GPT-5.6 Luna
Medium
```

Implementation：

```text
Claude Code
```

除非任务复杂度提供了明确理由，否则保持上述配置。

---

## 36. Core Philosophy

该系统不是为了最大化：

```text
AI intelligence used per task
```

而是最大化：

```text
Engineering Quality
───────────────────
Token + Credit Cost
```

Sol 应该完成最少、但决策价值最高的工作。

Claude Code 应承担绝大多数实现工作。

Luna 应承担高频验证和 QA。

Terra 应协调整个开发系统。

确定性工具应完成所有不需要 AI 推理的工作。

最终架构：

```text
                 SOL
            Technical Lead
                  │
                  ▼
              TERRA
         Codex Controller
                  │
       ┌──────────┴──────────┐
       ▼                     ▼
 CLAUDE CODE               LUNA
Implementation          Verification
       │                     │
       └──────────┬──────────┘
                  ▼
             Tests / Git
                  │
                  ▼
              Complete
```

---

## 37. Instruction to Codex

When this document is present, treat it as the project's AI execution policy.

For every new request:

1. Identify the task type.
2. Determine whether architecture work is required.
3. Select the cheapest sufficient model or deterministic tool.
4. Create a bounded task.
5. Delegate implementation to Claude Code when available.
6. Run deterministic validation.
7. Use Luna only when reasoning-based verification is useful.
8. Escalate architectural problems to Sol.
9. Persist important decisions.
10. Keep Agent handoffs concise.
11. Avoid repeated repository exploration.
12. Stop unnecessary Agent loops.
13. Optimize for engineering correctness per unit of model usage.

When uncertain between two models:

> Start with the cheaper option unless failure would create significant risk.

When uncertain whether Sol is required:

> Do not invoke Sol unless a real architecture, ambiguity, risk, or high-value decision exists.

When uncertain whether another review is necessary:

> Prefer deterministic tests and explicit acceptance criteria over another AI review.

The goal is not to use every available Agent.

The goal is to complete the project correctly with the minimum necessary model expenditure.
