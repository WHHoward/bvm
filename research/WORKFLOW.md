---
title: JoSIM × BVM 双代理研究工作流
document_type: workflow
protocol: josim-handoff/v1
status: active
last_updated: 2026-08-11
---

# JoSIM × BVM 双代理研究工作流

本文定义项目中“用户作最终裁决、Codex 负责任务设计与独立审计、Claude Code 负责受约束执行”的协作协议。目标不是让代理彼此转述结论，而是让每一步都有冻结输入、明确权限、不可变回执和可复核的原始证据。

这是一份**协作与溯源规范**，不是物理计量规范。它不定义 SFQ 阈值、相位容差或系统 Gate。Phase −1 计量基线（M4–M11）已验收，`METRIC_SPEC_V2.md` 已冻结（FROZEN）；本工作流仍不宣布任何物理 Gate——Gate 主张必须来自独立证据审计。

## 1. 一句话模型

```text
用户给出研究方向和最终授权
        ↓
Codex 把下一项工作冻结成带哈希的任务合同
        ↓
Claude 先 ACK，再在限定路径内实现/运行并交付 receipt
        ↓
Codex 从合同、diff、原始数据开始独立审计
        ↓
用户对路线改变、指标冻结和论文主张作最终裁决
```

核心原则是：**执行完成不等于数据有效，数据有效不等于物理通过，物理失败也不等于执行失败。**

## 2. 权威来源与冲突处理

每次任务都必须绑定以下来源，而不是只依赖聊天上下文：

1. `AGENTS.md`：全仓库不可违反的计量、实验和读写边界；
2. `memory/project-todo.md`：研究阶段、依赖关系和完成标准的任务权威；
3. `docs/HANDOVER.md`：当前可信状态、已知事故和行动顺序；
4. 已签名的 `research/tasks/<task-id>/request.yaml`：本次执行的目标、权限和交付物；
5. 任务列出的相关 skill：具体实验、证据审计或文档流程。

任务合同只能在上述边界内缩小本次范围，不能放宽 `AGENTS.md`，也不能把 todo 中未完成的 Gate 写成已完成。发现冲突时，Claude 必须停止并以 `BLOCKED` 回执；只有用户或 Codex 重新签发合同后才能继续。

聊天指令若改变已签名合同，不视为口头修订。必须签发新的 task request，并用新 request 的 `supersedes: {task_id, revision}` 指向旧合同。旧 `request.yaml` 和签名保持字节级不变；它的逻辑状态由替代合同推导为 `SUPERSEDED`。

## 3. 角色、职责与独立性

| 角色 | 主要职责 | 不应自行做的事 |
|---|---|---|
| 用户（研究负责人） | 决定研究方向；批准路线切换、指标冻结、论文级主张和重大范围扩展 | 不需要手工核对每个 CSV 样本或每条命令 |
| Codex（指挥/审计者） | 拆解 todo、设计可证伪任务、冻结合同、安排依赖与并行、独立复算、出审计裁决、同步上层状态 | 在未披露的情况下替 Claude 修改核心实现或原始实验产物 |
| Claude Code（执行者） | 做预检与 ACK；严格按合同改代码/网表、运行实验和测试；保存原始证据；提交 execution receipt | 修改合同或审计结论；自行扩大权限；把自己的解释写成最终 Gate |
| CI/脚本（机械判定器） | 校验 schema、哈希、路径范围、测试和确定性规则 | 代替物理审计或因果解释 |

### 3.1 独立审计边界

Codex 应保持“未实现、只审计”的角色分离。如果 Codex 为解除阻塞而修改了本次任务的核心代码、网表或原始产物，必须在审计中记录：

```yaml
independence:
  mode: CO_EXECUTOR
  codex_modified_execution_artifacts: true
  reviewer: <后续独立复核者>
```

这时不能再把同一轮 Codex 审计称为独立复核，应由 Claude 反向复核，或安排第三方/后续独立审计。只运行只读校验、独立计算或新增审计文件，不算参与实现。

### 3.2 模型路由与升级（2026-08-11；2026-08-18 调整）

按**角色层级**分派工作，不把某个特定模型名称写入合同；运行环境决定核心、工程审阅和机械检查层各自映射到的模型。

本项目的默认模型路由为：

| 默认配置 | 职责 |
|---|---|
| **Sol XHigh** | 架构、电路/计量方向、合同设计、物理解释与最终审计裁决 |
| **Luna XHigh** | Codex 日常 root controller：checkin、mailbox、routine planning、依赖/状态调度、routine receipt triage、Claude orchestration、已定义路线的任务推进 |
| **Terra Medium** | controller escalation：长上下文状态调和、历史/约束一致性 review、路线连续性 review |
| **Luna Low/Medium/High** | 大量低成本、只读的 specialist agents（scout/explorer/docs/tester/verifier） |
| **Terra High** | 复杂工程 review、debugging、相互矛盾的执行证据与根因分析 |
| **Claude Code + 配置的 DeepSeek** | implementation、simulation、testing、execution、evidence packaging |

> **Running as the root controller does not grant Luna scientific authority.**

当前编排接口不接受直接 `spawn_agent(model="gpt-5.6-luna")`，但项目级 `.codex/agents/*.toml` 的**命名 custom agent** 可以固定路由到 Luna；调用时选择 `josim_scout`、`josim_explorer`、`josim_docs_researcher`、`josim_tester` 或 `josim_verifier` 等角色。controller 状态/上下文歧义时调用 `josim_controller_review`（Terra Medium，只读）。若某环境未注册这些命名角色，先使用确定性工具，必要的低风险只读检查可回退到 Terra Low/Medium，但不得把这类回退当作最终物理审计。`plan_mode_reasoning_effort = "max"` 未启用：本地 Codex schema/help 无法确认该字段受支持（`PLAN_MODE_MAX_NOT_CONFIGURED`），Plan Mode 继承 `model_reasoning_effort = "xhigh"`。

当前编排接口不接受直接 `spawn_agent(model="gpt-5.6-luna")`，但项目级 `.codex/agents/*.toml` 的**命名 custom agent** 可以固定路由到 Luna；调用时选择 `josim_scout`、`josim_explorer`、`josim_docs_researcher`、`josim_tester` 或 `josim_verifier` 等角色。若某环境未注册这些命名角色，先使用确定性工具，必要的低风险只读检查可回退到 Terra Low/Medium，但不得把这类回退当作最终物理审计。

| 层级 | 可承担的工作 | 不可承担的工作 |
|---|---|---|
| 核心审阅层 | 路线与电路设计、任务合同、指标/容差冻结、物理解释、audit disposition、论文主张 | — |
| 工程审阅层 | 代码/网表预审、独立重算、测试设计、风险清单 | 最终物理 Gate、合同签发或审计接受 |
| 机械检查层 | schema/哈希/路径、lint、单元测试、CSV 完整性、日志索引和链接检查 | 用自然语言总结替代原始证据，或作任何路线/物理判断 |

机械检查层每次必须返回输入版本、命令、退出码、产物路径、哈希和未知项；核心审阅层只在发现失败、单位/端点歧义、权限扩张、冻结输入漂移、收敛问题或物理含义时升级处理。高推理预算只用于这些不可机械化的判断。

### 3.3 质量优先的能力、失败升级与上下文策略（2026-08-11）

按**最低足够能力**处理工作，推荐顺序为：

```text
确定性工具（schema、hash、diff、lint、unit test）
  → 低成本只读检查（日志摘要、范围/回归检查）
  → Claude 的受约束实现或实验
  → Codex 工程审阅
  → 核心审阅层的高推理设计/物理/审计判断
```

- **质量高于 token 节省。**这里的“最小”指避免无关重复，不是限制理解深度：跨模块设计、计量单位、实验因果、异常结果、审计与路线决策应主动读取足以消除关键歧义的完整上下文、原始日志和相邻证据；不能用摘要替代必须核对的源码、网表、CSV 或失败记录。
- 任务合同和 mailbox 默认给出目标、边界、验收、相关文件、命令/日志路径和失败摘录，便于定位；当执行者或审阅者需要更多上下文时，应直接读取所引用的完整文件/日志，并在 ACK、receipt 或审计中说明扩展阅读的原因和范围。原始日志始终保留，绝不为了节省上下文而截断或丢弃。
- 测试通过时，先记录命令、退出码、版本和证据路径；若任务风险低且验收充分，无需重复解释。测试失败、存在警告、结果矛盾或涉及物理含义时，应读取足够的完整日志和输入上下文后再判断，不能仅凭 `tail` 或单行失败摘要下结论。
- Claude 对**同一根因**至多作两次受合同约束的修复尝试。第二次仍失败，或发现公共接口、计量语义、实验设计、物理解释、冻结输入或合同验收冲突时，停止扩大修改：在 receipt/邮件中给出最小复现、已尝试动作、证据路径和根因假设，交回 Codex 重新设计或升级审阅。
- 低成本审阅可以发现并报告问题，但不能签发合同、修改物理 Gate 或接受自己的实现；模型具体名称由运行环境配置决定，不写入科学结论或合同真值。

### 3.4 mailbox：简短沟通，不替代合同（2026-08-11）

双方每次会话开始、处理任务前和任务出现 `BLOCKED`/`DEVIATED`/待审计交付时，都在**源仓库**运行：

```bash
python3 research/mailbox/scripts/mailbox.py list
```

Codex 签发任务后必须向 Claude 发送一条关联 `related_task` 的邮件，至少列出执行 worktree、request 路径、ACK 前置条件、最关键的停止条件和下一次汇报点。Claude 的普通进度/阻塞邮件应保持简短：状态、改动/证据路径、已运行命令及退出码、一个明确问题或请求。mailbox 只传递意图与索引；签发、ACK、receipt、audit、上推 todo/HANDOVER 仍只在任务合同文件中生效。

## 4. 文件所有权

默认所有权如下。合同可以进一步缩小 Claude 的写入范围，但不能由 Claude 自行扩大。

| 文件或目录 | 写入者 | 规则 |
|---|---|---|
| `research/tasks/<id>/request.yaml`、`request.sha256` | Codex | 签发后不可原地修改 |
| `research/tasks/<id>/baseline/` | Codex | 发行时冻结 HEAD、dirty 快照和范围哈希 |
| `research/tasks/<id>/attempts/<attempt>/ack.yaml` | Claude | 任何实现或实验前写；写后不可覆盖 |
| `research/tasks/<id>/attempts/<attempt>/receipt.yaml` | Claude | 记录实际动作和产物；需要修正时使用新 attempt |
| 任务授权的代码、网表和测试路径 | Claude | 只可写 `scope.write_paths` |
| `test/final/<route>/runs/<run-id>/` 等运行目录 | Claude | 每次新建唯一 run ID；原始数据 append-only |
| `research/tasks/<id>/audits/<audit>/verdict.yaml` | Codex | 基于原始证据独立生成；不覆盖旧审计 |
| `memory/project-todo.md`、`docs/HANDOVER.md`、`CHANGELOG.md` | Codex | 仅在审计接受并确有状态变化后更新 |
| `AGENTS.md`、冻结指标规范、论文主张 | 用户批准，Codex维护 | Claude 在普通执行任务中不得修改 |

Claude 不得修改 request、baseline、audit、todo、HANDOVER 或 CHANGELOG 来让任务“看起来通过”。需要更改这些文件时，只能在 receipt 中提出建议。

## 5. 目录与不可变记录

协调层使用下列结构：

```text
research/
├── WORKFLOW.md
├── CLAUDE_EXECUTOR.md
├── schemas/
│   ├── task-request.schema.json
│   ├── execution-ack.schema.json
│   ├── execution-receipt.schema.json
│   └── audit-verdict.schema.json
└── tasks/
    └── <task-id>/
        ├── request.yaml
        ├── request.sha256
        ├── baseline/
        │   ├── git-status.txt
        │   └── scope-files.sha256
        ├── attempts/
        │   └── A01/
        │       ├── ack.yaml
        │       ├── receipt.yaml
        │       └── ...任务要求的实现日志或索引
        └── audits/
            └── C01/
                └── verdict.yaml
```

协调层只保存合同、状态、索引和审计。大体积实验事实仍按 `josim-experiment` 保存到唯一 run 目录；receipt 引用路径与 SHA-256，不把 CSV 内容复制进协调层。

任务、attempt 和 audit 都是追加式记录：

- 合同未签发前可以处于 `DRAFT`；
- `ISSUED` 后必须有匹配的 `request.sha256`；
- 同一合同重跑使用 `A02`、`A03`，不得覆盖 `A01`；
- 合同目标、权限、验收条件或 claim ceiling 改变时，签发带新 task ID 的 request，并用 `supersedes` 指向旧 task/revision；旧合同原文和签名永不改写；
- 重审使用 `C02`，不得改写 `C01`；
- 原始或失败实验不得因结论不理想而删除、覆盖或“整理掉”。

## 6. 四个互不替代的结果维度

不要用一个 `status: pass` 混合表示不同事情。完整交接链必须分别回答四个问题：

| 维度 | 允许值 | 回答的问题 |
|---|---|---|
| `execution_status` | `COMPLETED` / `BLOCKED` / `DEVIATED` | Claude 是否完成了合同约定的动作？ |
| `artifact_status` | `VALID` / `INVALID` / `NOT_AUDITED` | 产物是否完整、可追溯并适合用来判断？ |
| `physical_verdict` | `PASS` / `FAIL` / `INCONCLUSIVE` / `NOT_APPLICABLE` | 有效证据对预注册物理主张说明什么？ |
| `audit_disposition` | `ACCEPTED` / `REWORK_REQUIRED` / `REJECTED` | Codex 是否接受这次交付，以及下一步是什么？ |

典型组合：

- `COMPLETED + VALID + PASS + ACCEPTED`：执行和证据均支持预注册主张；仍只能声称到合同的 `claim_ceiling`。
- `COMPLETED + VALID + FAIL + ACCEPTED`：实验正确完成，可信地得到负面结果。这是有效研究成果，不应要求 Claude “调到通过”。
- `COMPLETED + VALID + INCONCLUSIVE + ACCEPTED`：执行正确，但在已测条件下证据天然不足以区分解释；接受这次结果，并设计下一项最小判别实验。
- `COMPLETED + INVALID + NOT_APPLICABLE + REWORK_REQUIRED`：文件缺失、方向错误、哈希不符或数据损坏，不能据此判电路失败。
- `DEVIATED + VALID + INCONCLUSIVE + REWORK_REQUIRED`：可能保留探索价值，但偏离合同的结果不能直接完成原任务。

其中 `execution_status` 固化在 receipt；audit verdict 绑定该 receipt，并填写 `artifact_status`、`physical_verdict` 和 `audit_disposition`。四者可以位于不同的不可变文件中，但必须能沿 SHA-256 绑定链同时读出。

### 6.1 `FAIL`、`INCONCLUSIVE` 与 `INVALID`

- `FAIL` 要求数据本身有效，并且至少一个预先声明的必要条件明确不满足。
- `INCONCLUSIVE` 表示有效证据不能决定主张，例如无冻结容差、步长改变分类或结果落在事先定义的不可判区间。
- `INVALID` 描述证据载体有问题，例如缺关键列、NaN、时间轴损坏、方向/网表不匹配、输出被覆盖或来源无法追溯。它不是物理判定。

若 Claude 漏做合同明确要求的控制或测试，通常是 `REWORK_REQUIRED`，而不是把遗漏包装成已完成的 `INCONCLUSIVE`。若合同完整执行后，物理上仍存在预先允许的歧义，则可以 `ACCEPTED + INCONCLUSIVE`。

## 7. 工作流状态机

工作流状态描述记录走到哪里；它不同于上节的四维结果：

```text
BACKLOG
  → DRAFT
  → ISSUED
  → ACKED
  → RUNNING
  → DELIVERED ─→ AUDITED ─→ CLOSED
       │             ├─→ REWORK → 新 attempt
       │             └─→ REJECTED
       ├─→ BLOCKED
       └─→ DEVIATED

任一已发行合同 ─→ 新 request 的 supersedes 指针 → 逻辑 SUPERSEDED
```

状态由不可变文件推导，不维护一个容易被并发覆盖的共享 `status.yaml`。`SUPERSEDED` 也由新 request 的 `supersedes` 指针推导，绝不靠修改旧 request：

- 有已签名 request：`ISSUED`；
- 有接受任务的 ack：`ACKED`；
- 执行中但无 receipt：`RUNNING`；
- 有 receipt：`DELIVERED`、`BLOCKED` 或 `DEVIATED`；
- 有 verdict：`AUDITED`；
- verdict 为 `ACCEPTED` 且上层状态已按需同步：`CLOSED`。

## 8. 从请求到关闭的标准流程

### 8.1 Codex：从 todo 生成可证伪请求

Codex 先读取 todo 的依赖和完成标准，再把一个任务缩小为一次可以审计的合同。request 至少声明：

- 唯一 `task_id`、revision、父 todo ID 和依赖；
- 一个研究问题、目标、非目标和允许的最强主张 `claim_ceiling`；
- `read_paths`、`write_paths`、`frozen_paths` 和互斥锁；
- 基线 Git HEAD、dirty 策略、状态快照和范围文件哈希；
- 是否允许编辑、运行 JoSIM、联网、安装依赖、创建 worktree、提交、删除或覆盖；
- 必读文件、所需 skills，以及绑定规范/交接文档的路径与哈希；
- 交付物、逐条验收条件、无效条件、不可判条件和停止条件。

研究问题应能被结果反驳。例如“实现指标 v2 的单位基础，并证明合成相位台阶按 rad→圈转换”可审计；“把项目做正确”不可审计。

request 必须明确 `claim_ceiling`。实现型 M4 任务即使测试通过，也只能支持“计量代码基础满足这些单元测试”，不能提前支持 JTL 接收、系统 Gate 或论文结论。

### 8.2 Codex：签发并冻结请求

签发前：

1. 校验 request schema；
2. 捕获 HEAD、dirty 列表和本次作用域文件哈希；
3. 检查写路径与其他活动任务无冲突；
4. 把 `workflow_state` 设为 `ISSUED`；
5. 生成 `request.sha256`。

只有 `ISSUED` 且哈希匹配的请求可以执行。`DRAFT`、缺少签名或签名不符都不具备执行授权，也不得生成协议 ACK。

这里和工具命令中的“签名”指 SHA-256 内容封存与链式篡改检测，不是带私钥的数字签名，不能单独证明文件由 Codex 创建。身份与授权信任仍依赖仓库文件所有权、独立 worktree 和 Git diff/审查。

仓库工具入口为：

```bash
python3 .agents/skills/josim-handoff/scripts/handoff.py validate \
  research/tasks/<task-id>/request.yaml
python3 .agents/skills/josim-handoff/scripts/handoff.py sign-request \
  research/tasks/<task-id>/request.yaml
python3 .agents/skills/josim-handoff/scripts/handoff.py verify-task \
  research/tasks/<task-id>
```

以脚本 `--help` 和 schema 为机械事实；文档示例不能替代校验结果。

当前 `verify-task` 机械检查 schema、request 签名、已绑定合同文件、ACK/receipt/verdict 哈希链、receipt 自报 changed paths 的范围、验收项映射，以及当前仓库中自报 change/artifact/log 文件的 SHA-256。它不读取实时 HEAD/dirty 状态，不调度 locks/依赖，也不能发现 receipt 遗漏的实际 Git diff 或证明某个命令确实按记录执行。Claude 必须完成实时预检，Codex 必须从工作树和产物独立复核；命令返回 `VERIFIED` 不能单独证明执行合规或证据有效。`DRAFT` 会以非零退出码报错，而不是执行授权。

### 8.3 Claude：ACK 预检

Claude 只有在 request 已是 `ISSUED`、签名有效、且没有未确认 stand-in record 后，才进入 ACK 阶段。`DRAFT` 或 `PROVISIONAL` 都没有授权执行，也不得生成 ACK，只需在会话中报告等待 Codex 签发/确认。对于已有效签发的请求，Claude 在任何写入实现路径或运行实验之前：

1. 读取 `AGENTS.md`、request 的 `read_first`、相关 skill；
2. 校验 request schema、签名和基线绑定；
3. 检查当前 HEAD、预存 dirty 文件、依赖、工具版本和路径权限；
4. 检查 write paths、locks 是否与其他活动任务冲突；
5. 将目标、非目标和停止条件写入 `understanding`，将命令和路径分别写入 `planned_commands` 与 `expected_changed_paths`；发现的风险或不一致写入 `blockers`/`deviations`。

预检全部满足时写 `decision: ACCEPTED`；有效合同在 HEAD、dirty、依赖、工具、scope 或 lock 预检中失败时，写 `decision: BLOCKED` 和精确原因，然后停止。ACK 是 Claude 对冻结合同的确认，不是对物理结论的认可。

ACK 后发现误解不能覆盖原文件；应新增 attempt，或请求 Codex supersede 合同。

### 8.4 Claude：受约束执行

执行期间：

- 只修改 `scope.write_paths`，只读取允许的路径；
- 遵守 authorization 布尔值；未明确允许即视为禁止；
- 不使用 `git add -A`、`git reset --hard`、`git clean` 或隐式 stash；
- 不覆盖已存在的 raw CSV、netlist snapshot、manifest、日志或失败运行；
- 实验使用唯一 run ID，并按 `josim-experiment` 保存 JoSIM 版本/二进制哈希、include 闭包、时间步、方向、窗口、控制和原始输出；
- 不以图像、导数过阈值样本或旧 `scripts/sfq_metrics.py` 作为物理 Gate；
- 触发停止条件、需要新权限或必须改变合同假设时，立即停止并回执，不可自行“合理扩大范围”。

合同允许探索性诊断时，探索产物必须单独标记，不得混入验收证据。

Codex 签发任务时必须把 Claude 要写入的 attempt 目录、命令日志和 receipt 路径纳入 `scope.write_paths`；若遗漏，Claude 不得把协议文件当作隐含例外，应返回 `BLOCKED`。

### 8.5 Claude：提交 execution receipt

receipt 记录**实际发生了什么**，而不是计划发生什么。至少包括：

- request 与 ACK 的哈希、attempt ID 和 receipt 创建时间；
- `execution_status` 及阻塞/偏离原因；
- 实际执行的命令、退出码和重要 stderr/warning；
- 所有执行产物的 changed paths、新增 run ID、产物路径和 SHA-256；ACK 已由 `ack_sha256` 绑定，当前 receipt 不能自哈希，所以这两个协议封装文件不列入 `changes[]`；
- 测试名称、结果、未运行项及原因；
- 逐条 acceptance evidence 映射；
- Claude 的 `observations`、`interpretations`、`unknowns` 和**提议的**物理判定；
- 尚未解决的风险，记录在 `limitations`、`deviations` 或 `blockers`。

**多 attempt 聚合（2026-08-17，MAINT-003）**：同一 task 的多个 attempt 各自保留不可变 canonical receipt（`attempts/<id>/receipt.yaml`）。`verify-task` 对必需 deliverable 覆盖和 request acceptance-ID 覆盖做 **task-wide union** 校验：各 receipt 可分别承载各自交付的子集，只要所有 canonical receipt 的并集覆盖全部必需 deliverable 与全部 acceptance ID 即通过；每个 receipt 自身的哈希链、scope 和 artifact 校验保持不变，duplicate/unknown ID 仍逐 receipt 报错。RECEIPT 角色 deliverable 通常写成 glob（如 `attempts/**/receipt.yaml`），任一 canonical receipt 匹配即满足并集。单 attempt 任务与旧行为完全一致（并集 = 该 receipt）。002 的 A01/A02 单路径 D3 冲突（`attempts/A01/receipt.yaml` 无法由 A02 receipt 满足）为历史协议缺陷，不再重复；新 request 应使用 glob。

**Evidence bundle = 声明条目（2026-08-17，MAINT-007）**：PRE-receipt evidence bundle 是 **multi-entry** manifest，权威是**声明的条目**（role 可多条），最终 receipt 永不包含在内。目录展开只是枚举声明条目的构建便利，**不声称递归文件系统完备性**。CRITICAL/FROZEN 工作的完备性定义为：冻结期望证据/run-artifact 矩阵 + 必需 artifacts/manifest/inventory 交付集比较；**绝不**用"目录下所有 regular 文件"定义完备性。

Claude 可以提议 `PASS/FAIL/INCONCLUSIVE`，但不能给出最终审计裁决，也不能更新 todo/HANDOVER 证明自己已完成。

### 8.6 Codex：按固定顺序独立审计

为避免被执行者叙事锚定，Codex 应按下列顺序审计：

1. **合同和溯源**：request/ACK/receipt schema、哈希链、HEAD、依赖和权限；
2. **范围和实现**：changed paths、diff、网表连接、端点、方向、参数和测试代码；
3. **原始产物有效性**：退出码、solver warning、CSV 表头、NaN、时间轴、终点、manifest、二进制/输入哈希；
4. **独立计算**：从 raw CSV 重算关键量，运行独立测试，检查控制和步长；
5. **科学证据**：调用 `josim-evidence-audit`，区分 Artifact/Activity/Local/Downstream/System 层级；
6. **最后才读 Claude 的解释**：核对其中哪些是观察、推断或超出 claim ceiling 的主张。

verdict 必须绑定包含 `execution_status` 的 receipt，填写其余三个结果维度，逐条裁决 acceptance，并分别记录 `accepted_claims`、`rejected_claims` 和 `next_actions`。额外的 `scope_status` 只表示合同范围合规性，不替代产物或物理判定。`REWORK_REQUIRED` 要在 `required_rework` 中指出缺少的最小动作；`REJECTED` 要指出无法通过重跑修复的合同或诚信问题。每次重审使用新的 `audit_id`（例如 `C02`），不覆盖已有 verdict。

### 8.7 Codex 与用户：关闭和同步

只有审计为 `ACCEPTED` 后，Codex 才根据真实影响更新上层状态：

- 达到 todo 完成标准时才更新 `memory/project-todo.md`；
- 当前可信状态或行动顺序变化时才更新 `docs/HANDOVER.md`；
- 材料性变化按项目规则写入 CHANGELOG；
- 路线切换、指标规范冻结和论文主张交由用户最终批准。

有效的 `FAIL` 或 `INCONCLUSIVE` 也可以关闭一次任务，但不一定完成其父 todo；Codex 应把它转化为明确的下一项判别任务，而不是篡改完成标准。

## 9. 重试、阻塞与偏离

| 情况 | 应采取的动作 |
|---|---|
| 同一合同因瞬时问题重跑 | 新建 `A02`，保留 `A01` |
| 合同目标、范围、权限或验收条件变化 | 签发新 task request，以 `supersedes` 指向旧 task/revision；旧文件保持不变 |
| 开始前缺依赖、基线不符或路径冲突 | ACK=`BLOCKED`，不执行 |
| 执行中发现需修改冻结路径或联网 | 停止，receipt=`BLOCKED` 或 `DEVIATED` |
| 已产生有用结果但偏离预注册条件 | 保留产物，receipt=`DEVIATED`，不得冒充原任务完成 |
| 电路在有效实验中未达到 Gate | `COMPLETED + VALID + FAIL`，不是阻塞 |
| 有效结果无法区分两种解释 | `INCONCLUSIVE`，设计下一项单变量判别任务 |

“遇到困难”本身不是扩大扫描、修改多个参数或改变阈值的授权。停止条件应在 request 中预注册，包括最大运行数、时间/资源预算、solver 异常、越界写入风险和分类对步长不稳定等。

## 10. Git、worktree 与 dirty 工作树

### 10.1 默认使用独立分支/worktree

执行任务优先由 Codex/用户从 `baseline.git_head` 创建约定分支 `claude/<task-id>` 和独立 worktree，再交给 Claude，使协调文档、实现和其他实验不会混在同一 diff 中。Claude 只有在 `authorization.create_worktree: true` 时才能自行创建。独立 build/output 目录必须列入该任务的 write paths/deliverables/locks；它们不是 request schema 之外的隐式字段。

创建 worktree 前，request 必须绑定可访问的 base commit。若协调层尚未提交，Codex 应先把任务保留为 `DRAFT`，或用明确的只读传递方式把已签名 request 交给 worktree；不能假装未提交文件属于 base commit。

是否允许 commit 由 request 的 authorization 决定。允许 commit 不等于允许 push、merge 或修改未授权路径。

### 10.2 dirty 工作树策略

Claude 不得用 stash/reset/clean 消除用户或其他代理的修改。request 必须选择一种策略：

- `REQUIRE_CLEAN`：任何预存改动都阻塞执行；
- `ALLOW_NONOVERLAP`：允许预存改动，但它们不得与 read/write/frozen 作用域冲突；
在 `ALLOW_NONOVERLAP` 下，Claude 必须把发行时的 `baseline/git-status.txt` 与当前状态比较；新出现的非本任务改动、作用域重叠或无法归属的文件都应阻塞。审计 diff 应相对冻结基线和 scope hashes，而不是假定 `git diff` 中所有内容都来自 Claude。

## 11. 并行执行规则

只有同时满足以下条件的任务才可并行：

1. 写路径不相交；
2. raw output/run ID 不相交；
3. build 目录不共享；
4. request 的 `locks` 不相交；
5. 两者不修改同一规范、todo、HANDOVER 或公共基线；
6. 一项任务的验收不依赖另一项尚未审计的结果。

只读相同文件通常可以并行，但双方必须绑定相同哈希。若一个任务会改变另一个任务的输入，就必须串行并重新签发后者基线。

当前 Phase −1 中，M4、M5、M6 都触及同一计量接口和语义，应串行审计；M12 若写路径、测试和 build 目录完全独立，可以与 M4 的实现并行。是否真正并行仍以各 request 的 scope 和 locks 为准。

`locks` 是签发者检查的声明式冲突键，不是操作系统锁或租约。v1 不维护可并发覆盖的中央锁文件；Codex 在签发时检查已知活动 request，Claude 检查仓库中可见合同。无法确认是否冲突时按 `BLOCKED` 处理。

## 12. 与现有项目 skills 和文档的集成

| 能力 | 负责什么 | 不负责什么 |
|---|---|---|
| `josim-handoff` | request/ACK/receipt/verdict 生命周期、schema、哈希链、路径权限和交接 | 不发明物理阈值，不替代实验和证据审计 |
| `josim-experiment` | 预注册实验、匹配控制、唯一 run、JoSIM provenance、不可变 raw 和步长检查 | 不签发任务合同，不给最终系统 Gate |
| `josim-evidence-audit` | 从原始 CSV/网表审计相位、同 JJ 电压面积、JTL 传播、状态保持和三态物理结论 | 不把可视化或执行回执当作原始证据 |
| `josim-todo-manager` | 读取依赖、完成标准和下一项未阻塞工作；审计接受后更新状态 | 不因 receipt=`COMPLETED` 自动勾选任务 |
| `josim-project-summary` | 在材料性变化后同步摘要、HANDOVER 和历史 | 不反向生成原始实验事实 |
| `docs/HANDOVER.md` | 告诉新会话当前可信事实、事故边界和优先顺序 | 不替代具体 request 或 raw run |

一次物理实验通常同时使用 `josim-handoff` 和 `josim-experiment`；Codex 审计物理主张时再使用 `josim-evidence-audit`。纯实现任务若不运行或解释 JoSIM 数据，可以只使用 handoff 与相应代码测试。

## 13. 当前落地顺序

1. 先用 schema 和校验脚本验证一个 M4 任务包的合同链；
2. M4 仍按 `memory/project-todo.md` 的完成标准执行和审计，不预设其完成；
3. 经过 2–3 个真实任务后，再评估是否需要自动生成全局任务台账；
4. 在此之前不搬迁历史实验目录，不重写旧 raw，不制造一个可并发覆盖的中央状态文件。

任何任务若仍处于 `DRAFT` 或缺少有效签名，Claude 必须等待 Codex 正式签发。工作流基础设施完成不代表任何 BQ/DCSFQ Gate 已完成；`scientific_claim_ceiling` 由审计者声明并在审计中复核，不是机械的语义子集检查。

## 14. 快速审计清单

Codex 在接受一份交付前至少确认：

- [ ] request 为 `ISSUED`，哈希链完整，未原地修改；
- [ ] ACK 发生在首次实现写入/实验运行之前；
- [ ] changed paths、权限、locks 和 dirty 策略均合规；
- [ ] 原始/失败数据没有被覆盖或删除；
- [ ] 命令、退出码、JoSIM provenance、输入闭包和产物哈希可复核；
- [ ] acceptance 每一项都有 raw evidence，不只是一段解释；
- [ ] Artifact/Activity/Local/Downstream/System 没有跨层升级；
- [ ] `INVALID`、`FAIL`、`INCONCLUSIVE` 和执行阻塞没有混用；
- [ ] 结论不超过 `claim_ceiling`；
- [ ] 只有审计接受后才同步 todo/HANDOVER，并保留未知项。

## 15. Codex 不可用时的 Claude stand-in 代理（PROVISIONAL）

**（2026-08-11，stand-in 机制 v2）**：当 Codex 因额度、停机等原因暂时不可用时，用户可明确授权 Claude Code 临时准备 DRAFT 合同、候选 baseline 与 stand-in record。签发/取代 request、上层状态同步及审计仍由 Codex（或明确指定的独立第三方）完成。本机制不改变四维结果、状态机或 schema；它只把候选准备与 Codex 背书分开，绝不把候选准备变成执行授权。

### 15.1 不变量

1. **每次 stand-in 会话都必须有用户明确授权**，且授权范围记录在 stand-in record 中；一次授权不构成永久授权。
2. 所有代理动作写入 `research/tasks/<task-id>/standin/<Sxx>/record.yaml`（schema：`standin-record.schema.json`），**不覆盖** request/audit 等既有协议文件；任何已签名 request 的合同变化一律创建新 request，并用 `supersedes` 指向旧合同。
3. stand-in 产物一律 `status: PROVISIONAL`。在 Codex 写入 `standin/<Sxx>/review.yaml` 且 verdict 为 `CONFIRMED` 之前，**不生效**：`verify-task` 必须失败，Claude 不得 ACK 或执行，也不得据此上推 todo/HANDOVER、作为物理 Gate 或视为已签发审计。
4. **stand-in 不得审计自身执行**。stand-in 期间的执行审计仍由 Codex（或明确指定的 `THIRD_PARTY`）在恢复后完成。
5. schema 不因 stand-in 放宽：`issuer.role` 仍为 `CODEX`，request 原文与签名规则不变；stand-in 身份由 record 声明。

### 15.2 可代理与不可代理

| 可代理（用户授权后） | 不可代理 |
|---|---|
| 准备 DRAFT request、baseline 清单和待 Codex 审查的 record | 审计自身的执行并出最终裁决 |
| 整理不改变事实层级的候选状态文本 | 重签、覆盖或 `--force` 修改任何 ISSUED request |
| 记录用户授权与阻断原因 | 修改 schema 以放宽校验、决定路线切换、指标冻结、论文主张 |

### 15.3 审查与转正

Codex 恢复后按固定顺序审查：先读 `standin/<Sxx>/record.yaml` 与受影响的 request/产物，再写 `standin/<Sxx>/review.yaml`（schema：`standin-review.schema.json`）：

- `CONFIRMED`：Codex 背书该 stand-in 动作，视为与 Codex 自行执行等价；
- `REWORK_REQUIRED`：动作不完整或绑定失效，Codex 在 notes 中列出最小修正；如需合同变更，创建新的 superseding request，绝不重签旧 request；
- `REJECTED`：动作不成立，Codex 以新 request（`supersedes`）或审计处置纠正，旧 record 保留。

`verify-task` 对存在未确认 record 的任务以非零退出，并报告 `STAND-IN PROVISIONAL`；只有绑定完整的 `CONFIRMED` review 才解除该阻断。机械校验始终不能替代 Codex 对工作树和产物的独立复核。

### 15.4 与其它流程的关系

- stand-in 签发后的任务仍走标准 `ISSUED → ACK → RECEIPT → AUDIT` 生命周期；ACK/receipt 的作者仍是执行者，审计仍由 Codex/THIRD_PARTY 出具。
- 若 Codex 在不可用期间恢复并发现 stand-in 改动有误，可按 §9 处置（新 attempt、`supersede` 或拒绝），不改写旧 record。
- 本机制的协议文件（record/review）不属于四维结果，不改变 §6 的四个维度语义。

## §23 v1 workflow-maintenance defaults (2026-08-17)

New CRITICAL/FROZEN L2 scientific questions default to ONE preregistered
batch containing: inputs, raw, logs, task-owned frozen analysis-spec
(`research/schemas/quantitative-analysis-spec.schema.json`), analyzer,
independent verifier (`scripts/quantitative_analysis_verifier.py`),
structured analysis, deterministic report
(`scripts/render_structured_report.py`), report-consistency result,
recursive evidence bundle (`scripts/build_evidence_bundle.py`), and
receipt.  Successor use is limited to authority/scope defects; ordinary
seal/report/hash work is not split into successors.  Optional v1 fields:
`baseline.issuer_snapshot_commit` (ACK-observed commit tree must carry
byte-identical request/signature/scope bindings) and
`scientific_claim_ceiling` (narrower science-specific audit ceiling,
never broader than the mandatory contract `claim_ceiling`; it is
auditor-declared and reviewed in the audit, not mechanically checked as a
natural-language semantic subset).  Legacy requests without v1 fields keep
the strict-HEAD behavior unchanged.
