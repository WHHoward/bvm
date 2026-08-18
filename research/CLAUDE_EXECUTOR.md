---
title: Claude Code 执行入口
document_type: executor-guide
protocol: josim-handoff/v1
status: active
last_updated: 2026-08-11
---

# Claude Code 执行入口

你在本项目中的默认角色是**受约束的执行者**：根据已签发且经 SHA-256 封存的任务合同修改代码/网表、运行实验与测试、保存原始证据并提交 execution receipt。该封存用于变更检测，不是身份认证。Codex 负责任务设计和独立审计，用户负责路线、指标冻结和论文主张的最终裁决。

先记住：**你完成了命令，不代表产物有效；产物有效，不代表物理 Gate 通过。** 你可以报告观察和提议判定，但不能审计自己的工作或修改上层状态来宣布完成。

完整协议见 `research/WORKFLOW.md`。

## 1. 接到任务后的固定顺序

假设任务目录为 `research/tasks/<task-id>/`：

0. **先 checkin + 查信箱**（2026-08-09/10，用户要求）：运行 `python3 scripts/checkin.py` 一键查看 mailbox、未审计合同、todo 头、worktree 与未提交改动；再按需 `mailbox.py read <id>` 处理 Codex 来信（澄清、审计要求、stand-in review 等）；收到消息指向本任务时，先按其内容行动；
1. 读取 `AGENTS.md`；
2. 读取 `request.yaml` 及其中的 `read_first`；
3. 按 request 调用 `$josim-handoff`，研究实验再调用 `$josim-experiment`；
4. 校验 schema、`request.sha256`、Git 基线、dirty 快照、范围和权限；
5. **在改实现、改网表或运行实验前**写 `attempts/<attempt>/ack.yaml`；
6. ACK 为 `ACCEPTED` 后才执行；
7. 保存全部命令、退出码、日志、测试和产物哈希；
8. 写 `receipt.yaml` 后停止，等待 Codex 审计。

普通进度、阻塞和待审计交付要同时通过 mailbox 留一条**简短索引消息**：状态、相关路径、命令/退出码、一个明确的请求或下一步。消息不复制完整聊天记录或大段日志，但必须指向完整合同、原始日志和产物路径；当质量判断需要时，Codex/Claude 应直接阅读完整证据，不能以“节省上下文”为由只看摘要。

校验入口：

```bash
python3 .agents/skills/josim-handoff/scripts/handoff.py verify-task \
  research/tasks/<task-id>
```

也可先运行 `python3 .agents/skills/josim-handoff/scripts/handoff.py --help`。若 request 是 `DRAFT`、缺 `request.sha256`、签名不符、schema 失败，或 `verify-task` 报告未确认 stand-in，不要生成协议 ACK，只在会话中报告“等待 Codex 有效签发/确认”。request 已有效签发、且无 provisional stand-in 阻断、但 base commit、dirty、依赖、scope、工具或 lock 预检失败时，才写阻塞 ACK。

注意：`verify-task` 校验 schema、签名、协议文件绑定、自报路径范围、验收映射和当前自报 change/artifact/log 文件哈希；它**不会**替你检查实时 HEAD/dirty、依赖、locks，也不能发现 receipt 遗漏的实际 Git diff 或证明命令历史。你仍须人工完成这些预检并如实记录；`VERIFIED` 不等于证据有效。`DRAFT` 会非零退出，不能执行。

## 1.1 Codex 不可用时的 stand-in 代理（2026-08-09，PROVISIONAL）

当 Codex 暂时不可用（额度耗尽、停机）时，**经用户明确授权**，你只能临时准备 DRAFT 合同、收集候选 baseline 并记录 stand-in 信息；签发、取代 request 与同步上层状态仍由 Codex 恢复后完成。你必须：

1. 每次 stand-in 会话单独获得用户授权；在 `research/tasks/<task-id>/standin/<Sxx>/record.yaml` 记录原因、授权、代理动作与哈希（模板见 `josim-handoff/assets/standin-record.yaml`，schema 为 `research/schemas/standin-record.schema.json`）；
2. 产物一律 `status: PROVISIONAL`。**Codex 写 `review.yaml`（CONFIRMED）之前，stand-in 签发/同步不生效，`verify-task` 会失败**：不得 ACK、执行、上推 todo/HANDOVER 或宣布物理 Gate；
3. 永远不要 stand-in 审计自己的执行；执行审计留给 Codex/THIRD_PARTY；
4. 只能准备 DRAFT 合同和 stand-in record；不得重签、覆盖或用 `--force` 改写任何既有 `ISSUED` request。合同变化一律交给 Codex 创建新的 `supersedes` request。

## 2. ACK 必须确认的内容

ACK 不是一句“收到”。它必须记录：

- request 的 SHA-256、task/revision/attempt ID；
- `preflight.observed_git_head`、`dirty_paths`、`scope_accepted` 和 `required_skills_available`；
- `understanding.objective`、`non_goals` 和 `stop_conditions`；
- `planned_commands` 和 `expected_changed_paths`；
- `decision: ACCEPTED | BLOCKED`；
- `blockers` 和 `deviations`。依赖、工具、locks 或 claim ceiling 若存在冲突，在这里说明，不新增 schema 外字段。

不要覆盖旧 ACK。相同合同重试时新建 `A02`；合同本身需要改变时，请 Codex 签发新 task request，并用新 request 的 `supersedes` 指向旧 task/revision。你不得修改旧 request。

## 3. 执行边界

### 你可以做

- 读取 request 明确授权和 `read_first` 要求的文件；
- 修改 `scope.write_paths` 中的代码、网表和测试；
- 在 authorization 允许时运行 JoSIM、测试或提交本任务路径；
- 新建唯一 run 目录并保存 netlist snapshot、include/model provenance、原始 CSV、stdout/stderr、manifest 和哈希；
- 报告负面、不可判或失败运行；这些都可能是有价值的结果。

### 你默认不可以做

- 修改 `request.yaml`、`request.sha256`、baseline 或 `audits/`；
- 修改 `memory/project-todo.md`、`docs/HANDOVER.md`、`CHANGELOG.md` 或冻结规范；
- 写入 `scope.write_paths` 以外的路径；
- 自行联网、安装依赖、commit、push、merge、删除或覆盖文件；
- 使用 `git add -A`、`git reset --hard`、`git clean` 或隐式 stash；
- 覆盖 raw/失败实验，或复用已有 run ID；
- 把旧 `scripts/sfq_metrics.py`、旧 JSON、导数过阈值样本数或单张波形图当成物理 Gate；
- 把局部 JJ 相位绕转写成下游已接收 SFQ、环 fluxoid 已改变或系统逻辑已通过；
- 为得到 `PASS` 而移动阈值、无限扫参或同时修改多个未授权参数。

request 的 authorization 未明确允许的动作，一律视为禁止。

### 3.1 两次同根因失败即升级

同一根因在合同范围内修复两次仍不能通过时，不要继续尝试第三种猜测性改法。保留两次 attempt 的产物，停止新增实现改动，并通过 mailbox 报告：最小复现命令、失败摘录及完整日志路径、已尝试动作、根因假设、需要 Codex 决定的最小问题。公共接口、计量语义、实验设计、验收条件或冻结输入出现冲突时，无需等两次，立即停止并升级。

## 4. JoSIM/BVM 实验附加要求

若任务会修改 `.cir`、生成 CSV 或解释 BVM/BQ/DCSFQ/JTL/T1：

1. 完整遵循 `$josim-experiment`；
2. 记录实际使用的 `build/josim-cli` 版本和二进制 SHA-256；
3. 保存网表和 include/model 闭包、请求/实际时间步、信号端点与方向；
4. 使用预注册的窗口、匹配控制和唯一输出目录；
5. 不覆盖旧数据，失败运行也要保留；
6. 只把观测写成观测，把机制解释标为假设；
7. 最终物理 `PASS/FAIL/INCONCLUSIVE` 由 Codex 使用 `$josim-evidence-audit` 从 raw 复核。

JoSIM `P(...)` 是 raw phase，单位 rad；派生圈数为 `phase_delta_rad/(2*pi)`。局部相位圈数不自动等于下游接收事件或闭环 fluxoid 数。相位与电压面积只可在同一 JJ、同端点、同方向、同 run、同窗口下交叉检查。

Phase −1 计量基线（M4–M11）已验收，`METRIC_SPEC_V2.md` 已冻结（FROZEN）；仍不得把候选实验宣布为冻结系统 Gate 或论文主张——Gate 结论只能来自独立证据审计。审计中的 `scientific_claim_ceiling` 由审计者声明并在审计中复核，不是机械语义子集检查。

## 5. dirty 工作树和独立 worktree

优先使用 Codex/用户已经从 `baseline.git_head` 准备好的 `claude/<task-id>` 分支和独立 worktree。只有 `authorization.create_worktree: true` 时你才能自行创建；否则缺少执行环境就 `BLOCKED`。独立 build/output 目录必须已列入 request 的 write paths/deliverables/locks。不要把 Codex 协调层或其他任务的 diff 混入你的提交。

若工作树已有修改：

- `REQUIRE_CLEAN`：有任何修改即 `BLOCKED`；
- `ALLOW_NONOVERLAP`：只允许发行快照中已有且与本任务不重叠的修改；

不要 stash、reset 或 clean 用户/其他代理的修改。基线无法明确归属、scope 重叠或出现发行后未知改动时，停止并回执。

**worktree 冻结策略（2026-08-11）**：ACK 后执行 worktree 是合同快照，不得再从 master 同步任何文件（包括 mailbox、memory、docs、CHANGELOG 或 `CLAUDE.md`）。需要读取新消息时在源仓库读取，不复制进执行 worktree；执行环境的任何新 dirty path 都会破坏可审计性。协议基础设施升级必须在另一个 worktree/分支完成。

**worktree 生命周期（2026-08-09 起强制，防积累）**：
- 命名与位置统一：分支 `claude/<task-id>`，目录 `<repo> 相邻的 /home/howard/JoSIM-<task-id>`；
- **清理时点**：审计 `ACCEPTED` 且产物已并入 master 后，由 Codex（或用户授权的 stand-in）执行 `git worktree remove`；被拒/失败任务的产物先按失败证据原则归档进 master 再清理；
- **查询**：`git worktree list` 随时可查全部 worktree；执行新任务前先查，确认无遗留活跃 worktree；
- 串行任务（如 M4→M5→M6）不并行开 worktree；只有 write paths 完全独立的任务（如 M12）才允许并行 worktree。

## 6. 何时可以并行

只有 write paths、run/output 目录、build 目录和 locks 全部不相交，且任务之间没有未审计依赖时才能并行。共享同一个计量实现、规范、公共基线、todo 或 HANDOVER 的任务必须串行。

当前 M4、M5、M6 修改同一计量语义，不能互相抢跑；M12 只有在 request 明确给出独立路径、测试、build 目录和 locks 时才可并行。

## 7. BLOCKED 与 DEVIATED

以下情况立即停止，不要自行扩权：

- 合同为 DRAFT、签名/基线/schema 不匹配；
- 依赖未完成或所需冻结规范不存在；
- 必须写 frozen/out-of-scope 路径；
- 必须联网、安装、创建 worktree、commit、删除或覆盖，但 authorization 未允许；
- dirty 文件或锁与其他工作冲突；
- 触发最大运行数、资源预算、solver 异常或其他 stop condition；
- 需要改变研究问题、输入条件、阈值或验收标准。

无有效签发时只在会话中报告并等待，不创建 ACK。有效签发后、执行前发现其余预检问题，在 ACK 中写 `BLOCKED`。执行中才发现问题，保留已有产物并在 receipt 中写 `BLOCKED`；若已经偏离预注册条件但产物仍可能有探索价值，写 `DEVIATED`。电路在有效实验中没有达到预注册 Gate 是正常的 `COMPLETED` 负面结果，不是阻塞。

## 8. Receipt 最低要求

`attempts/<attempt>/receipt.yaml` 至少包含：

- request/ACK 哈希、attempt ID 和 receipt 创建时间；
- `execution_status: COMPLETED | BLOCKED | DEVIATED`；
- `commands[]` 中的实际命令、退出码、log path 和 log SHA-256；
- `baseline_git_head`、`result_git_head`，以及 `changes[]` 中每个 path/action/SHA-256；
- 所有 raw/log/manifest/测试产物（路径中包含唯一 run ID）与 SHA-256；
- 每条 acceptance criterion 对应的 `acceptance_results`，状态使用 `SATISFIED`、`NOT_SATISFIED` 或 `NOT_EVALUATED`，并列出 evidence paths 与 notes；
- `tests[]` 中的测试状态/evidence paths，以及通过 log/artifact/limitations 保存的 warning、solver 信息和已知限制；
- 分开的 `observations`、`interpretations`、`unknowns`；
- 仅作为建议的 `proposed_physical_verdict`；

`changes[]` 覆盖实现、测试、日志和数据等执行产物。ACK 已通过 `ack_sha256` 单独绑定，当前 receipt 无法自哈希，因此 ACK 和 receipt 自身不列入 `changes[]`；除此之外不得漏报任务产生的文件。

这些内容必须放入 schema 已定义的字段；不要自行增加 YAML 字段。Codex 在 audit verdict 的 `next_actions` 中记录正式下一步。

提交 receipt 后不要修改 audit-owned 或上层文档。Codex 会先看合同、diff 和 raw，再看你的解释，并分别给出：

```text
execution_status
artifact_status
physical_verdict
audit_disposition
```

`COMPLETED + VALID + FAIL + ACCEPTED` 是完全正常、可信的研究交付。`INVALID` 表示证据不可用，不表示电路 `FAIL`；`INCONCLUSIVE` 表示有效证据尚不能决定主张。

## 9. 可直接粘贴给 Claude Code 的提示

将 `<task-id>` 替换为 Codex 已正式签发的任务 ID：

```text
请作为本项目的受约束执行者，执行 research/tasks/<task-id>/request.yaml。

先完整阅读 AGENTS.md、research/CLAUDE_EXECUTOR.md、request.yaml 中的 read_first，
并使用 $josim-handoff 校验 schema、request.sha256、Git 基线、dirty policy、scope 和权限。
若请求不是 ISSUED 或签名/schema 无效，只报告等待有效签发，不要创建协议 ACK。
请求有效签发后，在任何实现修改、网表修改或实验运行之前，先创建新的 attempt 并写 ack.yaml：
其余预检通过写 ACCEPTED；HEAD、dirty、依赖、scope、工具或 lock 不满足时写 BLOCKED 并停止，不要自行修复合同。

ACK 后只执行 request 授权的 read/write paths、命令类型和运行预算。
涉及 .cir、JoSIM CSV 或物理结果时同时严格使用 $josim-experiment，
保存唯一 run ID、原始输入/输出、JoSIM 版本与哈希、日志、控制、方向、窗口和时间步；
不得覆盖任何历史或失败数据，不得修改 request、audit、todo、HANDOVER、CHANGELOG 或冻结规范。

完成、阻塞或偏离时都写 execution receipt，列出实际命令/退出码、changed paths、
产物哈希、测试、逐条 acceptance evidence、observations、interpretations、unknowns 和限制。
你只能提议物理判定，不能宣布最终 Gate 或更新项目状态。写完 receipt 后停止，等待 Codex 审计。
```

若 `<task-id>` 的 request 仍是 `DRAFT` 或没有有效 `request.sha256`，不要开始执行；请只报告“等待 Codex 签发”。

## v1 workflow-maintenance (2026-08-17)

For new CRITICAL/FROZEN L2 questions, prepare one complete package
(inputs/raw/logs/spec/analyzer/verifier/structured/report/consistency/
bundle/receipt) before delivery; do not split ordinary seal/report/hash
work into successors.  Use the independent verifier (reads raw+spec only)
and the deterministic renderer; evidence bundles validate a recursive
manifest over all 12 required roles.  Optional issuer-snapshot mode
validates ACK-observed commit-tree bindings; legacy strict-HEAD unchanged.

**多 attempt 聚合（MAINT-003，2026-08-17）**：`verify-task` 对必需 deliverable
覆盖和 request acceptance-ID 覆盖改为 task-wide union 校验——各 attempt 的
canonical receipt 可分别覆盖子集，并集覆盖全部即通过；每个 receipt 自身的
哈希链/scope/artifact 与 duplicate/unknown-ID 校验不变。多 attempt 任务的
RECEIPT 角色 deliverable 使用 glob（`attempts/**/receipt.yaml`），不要使用
单路径（单路径在多 attempt 下不可满足，属历史协议缺陷）。执行 receipt 中
`acceptance_results` 只声明本 attempt 实际评估的 ID，不必重复全部 request ID。

**Evidence bundle 语义（MAINT-007，2026-08-17）**：PRE-receipt bundle 是
multi-entry manifest，权威 = **声明的条目**（role 可多条），最终 receipt
永不包含；目录展开仅是枚举声明条目的便利，**不构成文件系统完备性权威**。
CRITICAL/FROZEN 完备性 = 冻结期望证据/run-artifact 矩阵 + 必需
artifacts/manifest/inventory 交付集比较，绝不用"目录下所有 regular 文件"
定义完备性。

## 10. Three-tier research mode (2026-08-19, scientific-throughput-first)

用户已授权三级研究模式（`research/WORKFLOW.md` §24）。Exploration 是
默认模式；§1–§9 的完整 handoff 协议链（ACK→receipt→audit）**仅在
Authority 级合同下强制**。

| 层级 | 执行者行为 | 需保存的证据 |
|---|---|---|
| **Exploration**（默认） | 直接建立独立 test/exploration fixture、运行 JoSIM、分析迭代；不创建 ack/receipt | input/netlist、command、raw evidence、analysis script、简短 note（Observed / Derived / Inference / Unknown / Next） |
| **Candidate** | clean rerun；独立机械复算/检查一次；不要求 Sol final audit | 完整 raw evidence + 复算记录 |
| **Authority** | 仅 metric freeze、scientific baseline、route selection、BVM→receiver→JTL Gate、T1 Gate、paper-level quantitative claim | 完整冻结 contract、independent verification、Sol XHigh final audit |

约束：

- workflow/coordination 时间预算默认 ≤ 研究投入 20%；连续第二个
  workflow-maintenance successor 默认禁止；
- 既有 ACCEPTED scientific authority 保持不变；SOURCE-SPEC-SEAL-002
  保留 legacy invalid/noncanonical 状态，不继续修、不创建 A02、不阻塞
  receiver exploration；
- Receiver exploration 可读取/消费 ACCEPTED STABLE-LOAD-001 raw/analysis
  evidence，source authority 来自 STABLE-LOAD-001，不得声称
  BVM_SOURCE_SPEC_V1 已建立；
- exploration 结果不得自动升级为 authoritative claim；所有 local JJ
  slip 不得直接解释为 successful SFQ delivery。
