# Copilot 对 WORKFLOW-lite 的审阅意见

> 审阅人：Copilot（Reviewer 角色）
> 审阅对象：`WORKFLOW-lite.md`（v1.0，FINAL）及配套 `.github/agents/reviewer.agent.md`
> 日期：2026-08-11
> 状态：供用户/Codex 参考，非协议文件，不修改任何协议条款

---

## 1. 总体判断：方向对，我支持，且比 Copilot 此前的提案更好

`WORKFLOW-lite` 精准解决了此前讨论中识别的核心问题——**不是「复杂」，而是「不分级」**。核心设计值得肯定：

- **NORMAL / CRITICAL 只改 Codex 审查深度，不增加协议文件**（§3）——把成本挂在风险上而不是流程上，是最优雅的一点；
- **日常代码追踪用 Git，只有冻结科研证据才用 SHA-256**（§10）——成本分配正确；
- **§16「不允许共识幻觉」**——每一层都必须有自己的最小独立证据来源，是整套协议里最有价值的一条，直接杜绝「上游说 PASS 下游就跟着 PASS」的连锁故障；
- **`claim_ceiling` 保留**，且明确任何角色不得静默突破（§11）；
- **Formal Freeze 是按需升级而非默认成本**（§14）；
- 配套的 `.github/agents/reviewer.agent.md` 质量很高：证伪思维（"什么样的隐藏错误会让它看起来对而实际错"）、十几种隐藏错误探查机制（no-op / constant-output / wrong-branch / stale-artifact / overclaim 等）、PASS 前自检清单、`Codex focus` 聚焦转交。

**§20 的八条底线完全同意，一条都不该砍。**

---

## 2. 需要补强的点（按重要性排序）

### 2.1 TASK.md 的「不可变」缺少显式机制（最需要补）

`TASK.md` 是唯一执行前冻结语义的文件，但文档没写用什么防止静默修改（旧协议的 SHA-256 密封就是这个作用）。

**建议**：加一行——*Codex 签发时 commit `TASK.md`；TASK 的修订由 Codex 显式标注 revision，Claude 永不修改 `TASK.md`。* Git 就是密封，成本为零。

### 2.2 四维结果分离被隐式化，建议在 lite 正文显式一句

旧协议的四维分离（执行完成 / 产物有效 / 物理判定 / 审计接受）在 lite 里靠 `claim_ceiling` + reviewer 的 overclaim challenge 保留着，但正文没显式写。**相位单位事故的根源恰恰是「测试过了 = 物理对了」的混淆。**

**建议**：在 §2.3 Claude 职责里补一句：*「程序执行成功」≠「产物有效」≠「物理结论成立」，三者分开报告。*（reviewer.agent.md §6.9 已写，但协议正文没有。）

### 2.3 todo / HANDOVER 的更新权未显式写

旧协议有一条真正重要的控制：*只有审计 ACCEPTED 后 Codex 才能更新 todo/HANDOVER，Claude 不得自证完成。* lite 的责任矩阵没有这一条。

**建议**：补进 §18 责任矩阵或 §2.2 Codex 职责。

### 2.4 风险等级的纠偏机制

Codex 定 NORMAL/CRITICAL，但存在低估风险。REVIEW.md 模板已有 `Recommended risk` 字段（好）。

**建议**：加一条默认规则——*有疑问时按 CRITICAL 处理；Reviewer 或用户建议升级时，Codex 若坚持 NORMAL 需说明理由。*

### 2.5 与旧协议/工具的迁移与共存需要一节明确

frontmatter 说 supersedes josim-handoff/v1，但仓库里 `handoff.py`、`josim-handoff` skill、`request.sha256` 结构都还在。

**建议**：加一节「迁移与共存」——新任务默认走 lite；已归档的 M4-001/002/003 保持原样；`handoff.py` 保留、仅在 Formal Freeze 时启用；避免两套协议并行产生「该听谁的」。

### 2.6 ⚠️ 一个具体的不一致：两份 REVIEW.md 模板字段不同

`WORKFLOW-lite.md` §7 的模板（Scope / Acceptance / Independent checks / Claim ceiling / Concerns / Codex focus）和 `reviewer.agent.md` §17 的模板（多了 Evidence confidence / Residual risk / Hidden-error probes / Findings Critical/Major/Minor / Residual uncertainty）**字段不一致**，实际执行时会产生歧义。

**建议**：以 `reviewer.agent.md` §17 为准（更完整），lite §7 保留简版示意并注明「完整格式见 reviewer.agent.md §17」。

### 2.7 小项

- **状态机图**：`REVIEW → ACCEPTED` 可能被误读为 Reviewer 给 ACCEPTED。建议加注：ACCEPT 只能由 Codex 给出，Reviewer 只提 REWORK/BLOCKED 建议。
- **REWORK 的 revision 语义**：「更新现有 REVIEW.md」会丢失「审查者当时看到什么」。建议：每次 revision 必须 commit（Git 可恢复）或追加 revision note。
- **§17 目录**：推荐 `research/evidence/`，但仓库现有实验证据在 `test/final/<route>/runs/<run-id>/`（josim-experiment 规定），建议引用现有位置而非新建目录。

---

## 3. 结论

- 这套方案**可以落地**，§20 八条底线之外只有一个硬性建议（2.1 TASK.md 冻结机制）和几个小的补强；
- **2.6（模板不一致）是当下最该先修的实际问题**；
- 其余为可选项，可按用户/Codex 判断取舍。

---

## 4. 下一步建议

1. 先统一 `WORKFLOW-lite.md` §7 与 `reviewer.agent.md` §17 的 REVIEW.md 模板一致性；
2. 将 2.1–2.5 的补强写成 diff 草案供用户/Codex 审阅（正式并入由 Codex 负责）；
3. 选定试点任务（M12 或 M5 纯计量部分）验证 lite 流程。
