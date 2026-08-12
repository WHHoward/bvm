---
title: Claude 对 WORKFLOW-lite 的审阅意见
document_type: review
status: FOR_DISCUSSION
date: 2026-08-11
reviewed: WORKFLOW-lite.md（用户方案，2026-08-11）
related:
  - research/WORKFLOW.md
  - workflowdiscuss/archive/proposals/WORKFLOW-copilot-review-proposal.md（Copilot 提案）
  - workflowdiscuss/archive/proposals/WORKFLOW-v2-three-party-discussion-summary.md（三方讨论总结）
  - research/mailbox/from-codex/codex-20260811-142613.md（Codex 协议建议）
  - research/tasks/JH-20260811-M4-003/audits/C01/verdict.yaml（M4 审计实录）
---
# Claude 对 WORKFLOW-lite 的审阅意见

> 本文是执行者视角的审阅意见，供用户 + Codex 决策参考；不修改任何协议条款。

## 一、总体判断

**方向支持**：「轻量默认 + 风险分级 + 保留安全底线」是正确的工程权衡。但方案放弃的东西（哈希链、ACK）恰是最近两天用真实错误验证过价值的机制——需要补强五点后才能站住。

## 二、值得保留的设计

| 设计                                           | 评价                            |
| ---------------------------------------------- | ------------------------------- |
| 两级风险（NORMAL/CRITICAL）+ CRITICAL 深度复核 | ✅ 把审计预算花在科学风险上     |
| claim ceiling                                  | ✅ 成本最低、价值最高的安全边界 |
| Formal Freeze 按需升级                         | ✅ 重型协议变"按需模式"         |
| 防共识幻觉（每层最小独立证据）                 | ✅ 回应 Reviewer 独立性担忧     |
| 八条底线                                       | ✅ 可作任何协议的公约数         |
| Reviewer 抽样检查 + token 预算                 | ✅ 务实                         |

## 三、五个必须补强的问题

### 1. 放弃哈希链的代价被低估（我们刚验证过它的价值）

lite §10 说「主要威胁不是恶意篡改」——对，我们的威胁模型是**疏忽与漂移**（Codex 签发遗漏基线、Claude 误删日志、stand-in 重签越权）。**非恶意错误恰恰需要机械校验来抓**：

- M4-001 REJECTED：是「签名不可变」抓到的重签违规；
- M4-002 BLOCKED：是「基线哈希绑定」抓到的基线不符；
- 这两次都在**执行前**被抓住，代价是一次重签发。

lite 版无签名、无不可变 request，同类错误会滑到物理结论阶段才爆发，代价大得多。

**建议**：NORMAL 可以不要完整哈希链，但以下三项必须保留：

- TASK 的 Baseline commit + **执行前 HEAD 核对**（直接对应 M4-002 教训）；
- 对冻结/历史证据路径的只读保护（禁止覆盖）；
- 涉及 Formal Freeze 的任务恢复完整哈希链（复用现成 handoff.py/schema）。

### 2. 「开始执行即视为接受 TASK」——放弃 ACK 有代价

M4-002 的 BLOCKED 恰恰发生在 ACK 预检阶段（发现基线不符，省了一整轮执行）。lite 无 ACK，基线/scope 问题要等 RESULT 才暴露。

**建议**：不强制独立 ACK 文件，但 RESULT.md 开头固定 3 行「预检确认」：

```text
Preflight: baseline HEAD 核对（= TASK Baseline ？）
Preflight: allowed paths 核对（无越界意图）
Preflight: 歧义说明（若有）
```

零成本，守住 M4-002 的教训。

### 3. 风险定级是最大决策点——「看着简单」的任务可能误标 NORMAL

M4 是纯实现任务，看着就是 NORMAL——但它暴露了最多的协议问题。分级制最大的风险是**定级本身不可靠**。

**建议**：

- 定级规则保守：拿不准 → CRITICAL；
- 用户可强制升级任何任务；
- 补两条自动 CRITICAL 触发：① 协议流程首次执行 / 新协作方参与；② 任务与已冻结证据或历史基线有任何交互。

### 4. 与 josim-handoff/v1 的关系必须说清（一套协议，两种模式）

lite 说 supersede 重型流程，但 v1 的工具链（handoff.py、schema、哈希链、stand-in、mailbox）刚在 M4-003 上完整验证。两套协议并存会混乱：M5 走哪套？Formal Freeze 时还兼容 v1 工具吗？

**建议**：表述为**「一套协议、两种模式」**：

- lite = 默认模式（TASK/RESULT/REVIEW，NORMAL 走 light）；
- Formal Freeze = v1 重型模式（request/ACK/receipt/verdict + 哈希链，复用现有工具与 schema，已验证可用）。

不维护两套独立协议文档；WORKFLOW-lite 可作为 WORKFLOW.md 的「轻量默认路径」章节并入，或与之明确互引。

### 5. 文件命名映射

lite 用 TASK.md/RESULT.md/REVIEW.md，现有目录是 request.yaml/ack.yaml/receipt.yaml/verdict.yaml。§17 说「现有结构优先」但未定义映射。

**建议**：明确等价关系——TASK.md ≡ request.yaml（语义等价物）；走 lite 用 TASK.md，走 Formal Freeze 用 request.yaml（机器校验）。避免同一任务目录两套命名。

## 四、与 Codex 建议的共识点

读 codex-20260811-142613 后，双方一致：

1. M4 已完成，不能作 DRAFT 试点（试点候选：M12 纯工程 / M5 纯计量实现部分）；
2. 新增 review 记录需要 schema 与机械校验（Codex 建议独立 evidence-review 记录 R01，绑定 request/ACK/receipt 哈希）；
3. 路线、物理 Gate、指标冻结、论文主张、证据冲突、单位/窗口/收敛争议，Codex 必须亲自从 raw 复核，不能只读 review 摘要；
4. 「独立」= 未参与实现 + 只读 + 固定快照复核；共享文件系统不提供身份/命令历史证明。

分歧点：Codex 认为应新增独立 evidence-review 记录（R01）并绑定哈希；我此前建议「不新增文件类型、复用 audits/ 结构」。折中：**lite 模式用 REVIEW.md（无哈希链），Formal Freeze 模式用 R01 记录（带哈希链）**——按模式取舍，避免一刀切。

## 五、试点建议

| 任务                           | 类型               | 建议模式                     | 验证点                    |
| ------------------------------ | ------------------ | ---------------------------- | ------------------------- |
| M12（josim-plot2 绘图修复）    | 纯工程、无物理语义 | lite NORMAL                  | 轻量流程全链              |
| M5（事件窗口）的纯计量实现部分 | 实现层             | lite NORMAL                  | 与后续 CRITICAL 复用      |
| M5 的物理判定部分              | 物理语义           | CRITICAL（或 Formal Freeze） | 升级路径 + Codex 深度复核 |

一次并行验证「一套协议两种模式」的切换，成本最低。

## 六、结论

骨架正确，补强五点（执行前基线核对、RESULT 预检行、保守定级、一套协议两种模式、命名映射）后，可在「便宜」与「抓得住错误」之间站住。八条底线作为协议公约数保留。

决定权在用户 + Codex；本文件不构成任何协议修订。
