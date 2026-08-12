# Copilot 对《JoSIM × BVM 最终研究流程与协作方案》的 Blocker-only Review

> 审阅人：Copilot（Reviewer 角色）
> 审阅对象：`workflowdiscuss/archive/proposals/JOSIM_BVM_最终研究流程与协作方案.md`
> 日期：2026-08-12
> 模式：blocker-only（只报告会阻止实施的问题，不重新讨论已三方一致的总体方向）
> 状态：三方 blocker 审阅意见之一

---

## 结论总览

```
BLOCKER: 无
MINOR:   6
NO_BLOCKER: 设计方向可进入 USER_ADOPTED 决策
```

---

## 已核实的项目事实前提（全部为真）

- M6-002 的 C01 `ACCEPTED` 存在（`research/tasks/JH-20260812-M6-002/audits/C01/verdict.yaml`）；todo 中 M6 = 🟢（2026-08-12）——提案声明"M6 已获得有效 FROZEN 审计并 ACCEPTED"属实；
- M7–M11 未完成、BQ/DCSFQ 正式路线判定阻塞——属实；
- 提案"用户决定恢复科研执行后再签发 M7"与当前暂停指令一致（Codex 已按用户指令暂停派发后续任务）；
- 依赖链（M7A/B/C → M8 → M9 → M10 → M11A/B → 候选路线）内部一致，无循环依赖：M11B 的"UNKNOWN/INFERRED 参数明确"指"显式列出"而非"解决"，故不可重构时 M11B 仍可 PASS（bounded negative 路径已定义）。

---

## BLOCKER

**无。**

---

## MINOR（均不阻止实施，每条附最小修正）

### M1. 机器生成 Audit Packet 需要机器可解析的输入契约

`E6` 要求 packet 由脚本生成，且来源含"AC mapping / declared evidence / RESULT headers"——但当前 RESULT.md 是自由 Markdown，脚本无法可靠提取 AC 映射与证据清单。若不定义契约，E6 会退化成 LLM 摘要（正是 E6 禁止的 executor narrative）。

**修正**：Batch P0 范围内加一项"RESULT/REVIEW/ledger 最小机器可读头契约"（四维字段 + AC 映射 + 证据列表，非完整 schema）；packet 只含可解析字段。

### M2. 三个新研究产物的 ownership 与完成标准未定义

`REFERENCE_PROVENANCE.md`、`BVM_SOURCE_SPEC_V1.md`、`INTERFACE_GATE_V1.md` 只列了"推荐新增文件"，无 owner、无 acceptance、无 claim ceiling。

**修正**：签发时各挂一个带 claim ceiling 的任务（Claude 起草 / Copilot 审 / Codex 收），否则会成为无主 scope 蔓延。

### M3. W5A 的外部访问与环境前提未定

W5A 需文献数据库查询。若执行环境无网络，需明确回退（仓库内已有文献/人工检索，或用户显式授权联网）。不阻塞：W5A 不在 M7A/B/C 关键路径上，且其保守默认（未完成前禁用 "first/no prior work" 措辞）本身安全。

**修正**：给 W5A 一条网络/授权回退规则。

### M4. W5B "立即开始"与当前暂停指令的边界需一句话澄清

暂停指令针对新科研任务（M7+）。W5B 属文献/溯源文档，可立即启动，但应在任务层面显式归类为 documentation 以免与暂停冲突。

**修正**：W5B 任务标注 `documentation / provenance`，非科研执行。

### M5. M11 单编号双子门与 todo 表示需要一处对齐

提案说"保持现有 M 编号避免 provenance churn"，但 todo 目前是单一 M11；M11A/B 需要 todo 结构更新。

**修正**：在 todo 中 M11 条目下增加 M11A/M11B 两个子门（保留 M11 编号），并声明这是表示层更新而非重编号。

### M6. FROZEN v1.1 的 regression cases 边界应写死为只读

Step 3 用 M6-001/M6-002 作 regression cases——M6-001 是 REWORK 历史、M6-002 已 ACCEPTED。

**修正**：明确 regression 只读引用现有 request/receipt/verdict，不重跑、不改写 M6 产物。

---

## NO_BLOCKER

设计方向（Study Phase、M7/M9/M11 结构调整、Reference/Source/Receiver 三层、FROZEN v1.1、Batch P0、三层任务模型）**可进入 USER_ADOPTED 决策**。无需第四轮重新设计。

**结论：无 BLOCKER，可以提交用户做采纳决定。六个 MINOR 是签发/实现层面的小修正，不改变方案结构与实施路径。**
