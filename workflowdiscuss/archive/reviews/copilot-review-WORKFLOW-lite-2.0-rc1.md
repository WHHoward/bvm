# Copilot 对 WORKFLOW-lite 2.0-rc1 的最终审阅意见

> 审阅人：Copilot（Reviewer 角色）
> 审阅对象：`workflowdiscuss/archive/old-versions/WORKFLOW-lite-2.0-rc1.md`（v2.0-rc1，PILOT）
> 日期：2026-08-11
> 状态：供用户/Codex 参考，非协议文件，不修改任何协议条款

---

## 1. 总体判断：目前最好的一版，强烈支持

v2.0-rc1 几乎把 Copilot 对 v1.0 的 7 条意见与 Codex 在 mailbox 中提出的 verify-task 语义问题全部吸收，且实现得比预期更干净。

最核心的进化是 **「一套协议，两种证据模式」（LITE / FROZEN）**：把「简化日常」和「冻结关键证据」从互相妥协变成分层共存——这是真正的设计突破。

**可以直接进入 Pilot，不需要再大改。**

---

## 2. v1.0 七条意见 → v2.0-rc1 落实情况（全部解决）

| Copilot v1.0 意见 | v2.0-rc1 对应 | 评价 |
|---|---|---|
| ① TASK.md 冻结机制 | §3 Git commit 密封 + 显式 revision | ✅ 完美解决，成本为零 |
| ② 四维结果分离显式化 | §8–11 RESULT 四字段 + 明确不等号 | ✅ 比 v1 更彻底 |
| ③ todo/HANDOVER 更新权 | §26 仅 Codex ACCEPT 后更新 | ✅ |
| ④ 风险等级纠偏机制 | §19–21 Reviewer 建议 + §20「拿不准就 CRITICAL」+ §21 必须记录原因 | ✅ 超出预期 |
| ⑤ 与旧协议/工具共存 | §1 / §24.3 / §35 / §36「两种证据模式」 | ✅ 最优雅的解法 |
| ⑥ REVIEW.md 模板不一致 | §18 统一格式 | ✅ |
| ⑦ 小项 | §7 attempts 保留 / §27 四态区分 / §37 不搬迁数据 | ✅ |

此外：
- **verify-task 历史语义问题**（Codex mailbox 第 7 点）→ 由 §31（execution snapshot vs current drift）解决；
- **M4-002 的 BLOCKED 教训** → 由 §5 Preflight（Observed HEAD ≠ baseline → BLOCKED）接住；
- **§32「Reviewer Prompt 不是文件系统 ACL」**的诚实定位与降级规则，是全文档里最清醒的一句话。

---

## 3. 剩余意见（按重要性排序，均不大）

### 3.1 LITE → FROZEN 的中途迁移规则还差半句话（最值得补）

§33 Pilot 3 暗示了迁移，§36 说「不要在同一个 attempt 同时维护两套语义重复文件」，但缺少明确的迁移契约。

**建议补充**：

> FROZEN 必须在物理判定/论文数据**产生之前**由 Codex 显式发起并重签为 v1 合同；LITE 阶段产物只能作为 FROZEN 合同的只读输入，**不自动获得 FROZEN 效力**。

否则「做着做着发现该冻结」时，双方会纠结旧 attempt 算什么。

### 3.2 REVIEW.md 缺 `Recommended evidence mode` 字段（与两维度模型不对称）

文档反复强调两个独立维度（Risk + Evidence mode），但 REVIEW.md 只有 `Recommended risk`。

**建议**：在 §18 头部对称加一行：

```text
Recommended evidence mode: LITE | FROZEN
```

让 Reviewer 在证据链有隐患但拿不准是否冻结时能明确表态，而不是只能拐弯说 CRITICAL。

### 3.3 证据模式也加一条「拿不准就 FROZEN」

§20 有「拿不准就 CRITICAL」，但证据模式没有对称规则。

**建议**：加一句——*有疑问时证据模式按 FROZEN 处理，由 Codex 决定。* 防止 LITE 模式下漏冻结。

### 3.4 补一句：mailbox 与科研 skills 在 LITE 模式仍然适用

§35 说明了协议关系，但没提两件日常工具：

- **mailbox**：LITE 任务间非正式沟通仍需要；
- **josim-experiment / josim-evidence-audit** 等科研技能：它们是物理层技能，与协作层协议正交。

**建议**：加一句交叉引用，避免误读成「换了协议就不再用旧技能」。

### 3.5 §32 的只读验证给一个具体抓手

「Reviewer 只写 REVIEW.md」在 Pilot 里怎么机械验证？

**建议**：Pilot 评价时检查 `git status`——审查前后 diff 应只有 attempt 内新增的 `REVIEW.md`。把它作为 §34 的一条 Pilot 指标（如「Reviewer 只读性：git status 确认无实现文件改动」）。

### 3.6 关于协议长度——可接受，可选做速查表

§38 说「复杂度放在发现错误的能力而不是手续」。协议 43 节看似长，但每节是短清单；NORMAL+LITE 的实际单任务成本只有 4 个文件 + 一个 Git commit，符合「轻量默认」。

**可选**：把 §0 + §40 矩阵 + §41 底线做成一张一页速查表，但非必须。

---

## 4. 结论

- **可以直接进入 Pilot**；
- 硬性建议只有 **3.1（迁移规则）**；
- 3.2、3.3 是 5 分钟的小对称修正；
- 3.4、3.5、3.6 是可选增强；
- Pilot 1（M12，NORMAL+LITE）设计合理；Copilot 作为 Reviewer 角色，届时将按 §32 实际验证约束是否真的成立。

---

## 5. 下一步建议

1. 决定是否将 3.1–3.3 并入 rc1（由用户/Codex 决定）；
2. 按 §33 启动 Pilot 1（M12）；
3. Pilot 按 §34 指标评估后，再决定 rc1 → 2.0 FINAL。
