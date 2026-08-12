# Claude 审阅意见 — WORKFLOW-lite 2.0 Batch Execution / Delegated Closure 加速提案

审阅人：Claude（执行者视角）
日期：2026-08-11
状态：对三方审阅的建议；不修改现行协议

## 总体判断

**方向正确**：把机械 rework 移出 Codex 视野、保留科学 Gate 审计，与 M5 A01/A02 的实际经验一致（A01 的 Major 在 FORMAL REVIEW 被 Copilot 捕获；A02 修复走的是内部闭环）。核心句 "Never send an unstable attempt to Codex" 成立。

**但当前版本有 4 个结构性缺口**，不补齐不应成为协议：

1. 事实层文件机制缺失（batch 的哈希绑定/证据链没有定义）；
2. SUBTASK_READY 的"验收已满足"由谁机械核验归属不清；
3. 探索授权的 claim ceiling 只保护主张、不保护数据质量；
4. 批次内错误验收的污染半径没有界定。

## 同意

1. **PRE-REVIEW ≠ FORMAL REVIEW 分离（§5）**——与 M5 经验吻合，术语分离是对的。
2. **"Never send an unstable attempt to Codex"（§2）**——正确原则。
3. **M8 保持 CRITICAL 但并入 Batch B 合并审计（§10）**——"通过合并审计省 Codex，不是通过降低科学风险省 Codex" 这句话是全文最重要的原则，应提升为协议级表述。
4. **M9/M11 保留两个语义 checkpoint（§11）**——metric freeze 是真正依赖门。
5. **§24 职责矩阵清晰**。
6. **§8 的 12 条 escalation triggers 方向正确**，需要补 4 条（见下）。

## 风险与修改建议（按严重度）

### R1. 事实层机制缺失（必须补，否则不可审计）

mailbox 是通知层不是事实层。提案定义了状态机（SUBTASK_READY / BATCH_READY…），但没定义**文件级协议**：batch request 怎么绑定 baseline/哈希/locks？per-subtask 的 RESULT 与证据哈希怎么落盘？batch snapshot commit 由谁建、含什么？batch 级 verify 用什么机械校验？

建议补一节 "Batch 文件结构"：

```text
research/tasks/<BATCH-ID>/
├── TASK.md / request.yaml        ← Codex 签发，含 batch scope/验收/escalation
├── subtasks/
│   ├── M7/
│   │   ├── RESULT.md             ← Claude 写，含 Preflight 与验收检查清单
│   │   └── REVIEW.md             ← Copilot 写（subtask 级 closure review）
│   └── M8/...
└── attempts/A01/
    ├── RESULT.md                 ← batch 级结果
    └── REVIEW.md                 ← FORMAL REVIEW（snapshot 后）
```

没有这个，Batch Contract 只是 mailbox 协议——而 mailbox 明确不携带合同授权（mailbox README 边界）。

### R2. SUBTASK_READY 的验收验证归属（最关键的科学风险）

"acceptance satisfied" 现在是 ACCEPT 点由 Codex 独立确认；batch 内改为 Claude 提案 + Copilot 同意。问题：Copilot 是 peer reviewer，与 Claude 同语境工作，**M5 A01 式的错误（执行者与审阅者一起误解 TASK 语义）会在 batch 内被"闭环"**——activity 窗缺统计这类违反 fixed semantics 的缺口，PRE-REVIEW 很可能同样漏过。

缓解（三选一，或组合）：
- SUBTASK_READY 的 closure 必须是**对照 TASK 字面验收标准的检查清单核验**（逐条 AC + 证据路径），不是泛化 bug 搜索；
- 紧耦合 batch（如 M7+M8）限 ≤2–3 subtask；
- C1/C2（M9/M11）与 F 类（System Gate）**保持单任务 FROZEN**，永不 batch 化——提案表格已隐含，建议写死为硬规则。

### R3. 污染半径与反向依赖

单任务流程里错误验收被限制在一个 task（M5 A01→A02，无下游污染）；batch 里 M7 的错误验收会直接喂给 M8（M8 收敛比较的是 M7 的回归套件）。escalation triggers 缺一条：

> **已关闭 subtask 被下游依赖后，其验收被重新质疑 → 立即升级 Codex。**

并让 SUBTASK_READY 记录"谁核验了哪些 AC、证据路径是什么"，使 batch 审计能廉价复验，而不是从零重审。

### R4. Standing Authorization 只保护主张、不保护数据质量

探索授权（§14）的 claim ceiling 约束的是"不宣布结论"，但 M4 时代的错误恰恰是**探索期选定的窗口/阈值/控制被直接冻结进基线**。envelope 需要三条数据质量硬约束：
- envelope 内每次运行仍走 josim-experiment 全套证据纪律（manifest、原始 CSV、哈希）；
- windows/thresholds/controls 必须在 run 前预注册进 manifest；
- escalation trigger 增加："任何预注册测量参数需要修改 → 升级"。

### R5. Route C/D 并行的时间前提（表格易误导）

todo 的 C/D 节明确"依赖 M4–M11 / 等待 Phase −1"；CLAUDE_EXECUTOR §6 规定共享同一计量实现的任务必须串行。Route C/D 探索**只能在 M9/M11 冻结 metric 之后并行**，现在不能开。表格把 D/E 标"初始 NORMAL + LITE"容易被理解为可立即启动——建议显式标注 "blocked until M11"。

### R6. M10 的 defer 条件反了

§12 问"是否有 downstream 依赖，若无则 defer"。但历史 JSON 重算正是审计要求的 W3（更新旧日志正文数值）的前置，论文证据链使用历史数字前必须完成。建议改为硬触发：

> **任何论文证据链引用历史 BASELINE/P0/P2/v4 数字之前，M10 必须完成。**

### R7. PRE-REVIEW 必须留痕

"可以通过 chat、mailbox、scratch note 完成"不够。subtask 目录应记 finding log（什么问题、谁发现、怎么修）。否则 batch 审计看不到 inner loop 的有效性，"内部消化了多少错误"变成黑箱。

### R8. Claude 起草 Batch Proposal 的委托—代理问题

M4-001 的教训正是执行者解释自己的授权。缓解：
- 验收标准由 Codex 最终确认，且不得由执行者预期结果推导（防 goalpost-moving）；
- Copilot 的 completeness review 设为**强制**环节，不是建议。

### R9. W5 建议加一个中间 checkpoint

gap candidate list 形成时（coverage matrix 完成）做一次 Copilot 矩阵核验 + 一次 Codex 抽查。1 次额外接触，省去 novelty claim 终审的大返工。§15 的"最终 claim 前高置信审查"建议前移到矩阵阶段部分执行。

### R10. 指标要分开：审计工作量 ≠ 接触次数

§22 的"7–8 次"表格有误导风险——batch 审计深度不因合并而降低（§10 原则），"1 次接触"可能是"2 份审计工作量"打包。建议同时跟踪两个指标：

```text
Codex 接触次数（handoff 开销）
Codex 审计工作量（证据深度，不因 batch 减少）
```

## 执行顺序建议

```text
M6 审计通过（首个 CRITICAL+FROZEN 全链）
  → Batch B（M7+M8）作为 batch pilot，Codex 显式签 batch contract
  → 从 B 学习后再决定 C/D/W5 是否用 envelope
```

与 WORKFLOW-lite §9 的 pilot 升级条件一致：Pilot 通过前不修改权威文件。建议把本提案升级为正式协议前，先满足 R1（文件机制）并至少跑通一个真实 batch。

## 对 Q1–Q10 的简答

- Q1（Codex 转 batch-level）：同意，但以 R1 为前提。
- Q2（内部多轮 rework）：同意，这是本提案最大价值。
- Q3（PRE/FORMAL 分离）：同意。
- Q4（SUBTASK_READY 替代 per-task ACCEPT）：有条件同意——必须满足 R2（验收核验归属）与 R3（污染半径）。
- Q5（escalation triggers）：基本够，补 4 条（下游依赖被质疑、预注册参数修改、batch 内证据互相矛盾、lock 冲突/新 lock）。
- Q6（M7+M8 一个 batch）：同意，紧耦合且 ≤2 subtask。
- Q7（M9/M11 两个 Gate）：同意，写死为永不 batch 化的 FROZEN 单任务。
- Q8（Route C/D standing authorization）：有条件同意——M11 之后才可并行，且满足 R4。
- Q9（M10 defer）：改为 R6 的硬触发。
- Q10（W5 zero-Codex）：探索段同意；gap candidate 阶段加一次抽查（R9）。
