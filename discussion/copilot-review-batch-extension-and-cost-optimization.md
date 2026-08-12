# Copilot 对 WORKFLOW-lite 2.0 Batch Extension / 成本优化综合文档的审阅意见

> 审阅人：Copilot（Reviewer 角色）
> 审阅对象：`workflowdiscuss/WORKFLOW-lite-2.0-batch-extension-and-cost-optimization.md`
> 日期：2026-08-11
> 状态：三方审阅意见之一；不修改协议、不授权任务

---

## 1. 总体判断

综合文档质量很高。Copilot 上一轮意见（R1–R8）已基本被吸收，Part II 有多个真正有价值的增量。**Part I 可直接进入扩展草稿；Part II 的 P0 四项建议采纳，但需按三点加固。**

---

## 2. Part I（收敛部分）：上轮意见吸收情况

| Copilot 上轮建议 | 收敛文档 | 评价 |
|---|---|---|
| R1 PRE-REVIEW 锚定 | §10 + §11/§12 `review_mode: CONTINUITY/FRESH_CONTEXT` + involvement disclosure | ✅ 比原建议更进一步，含披露机制 |
| R2 内部闭环留痕 | §5 BATCH-MANIFEST + §6 LEDGER | ✅ manifest 是索引不是大日志，定位正确 |
| R3 SUBTASK_READY 降权 | §7 显式四维语义 + "no authority outside the current Batch" | ✅ |
| R4 Standing Auth 数据纪律 | §13 "claim ceiling may be relaxed; evidence discipline is not" | ✅ 精华句 |
| R5 proposal 对抗性审查 | §19 mandatory adversarial completeness review | ✅ |
| R6/R7/R8 | §16/§17/§18 | ✅ |

### 新增且特别认可的条款

- **§8 下游污染半径规则**：已下游依赖的 READY 被重新质疑 → 立即停链升级。补上了 batch 模式最危险的隐性风险。
- **§9 inner loop 绝对边界**："Implementation repair is delegated; scientific semantics are not"，可/不可静默修改清单清晰。
- **§15 修正**：M8 关键收敛证据若喂给 M9，必须提前 FROZEN（B2），不能事后追溯。比最初"M7+M8 一个 LITE batch"更严谨，同意。
- **§14 Route C/D 阻塞至 M11**：exploration 不绕过项目依赖，正确。

---

## 3. Part II（第三方优化）评估

### 3.1 最高度支持的三项

- **A. 双 Reviewer 上下文**（PRE-REVIEWER ≠ FORMAL REVIEWER）：解决锚定问题的最划算机制，几乎零 Codex 成本。文档正确声明"仍非不同组织的独立审计"，只是认知上下文上的 second pair of eyes。
- **F/G. Semantic Lock**：把"inner loop 不得静默改科学输入"机械化，典型"用便宜确定性检查替代昂贵模型审查"。CRITICAL+LITE 也能用、不等于 FROZEN，中间层设计正确。
- **M. Machine-first review（verify-batch）**：scope/hash/manifest/semantic-lock/缺失证据/重复 run ID 下沉 Tier 0，长期最值得投入的方向。

### 3.2 三个必须警惕的点（Copilot 增量意见）

**⚠️ 1. 最大系统性风险：一切优化都倾向让"索引/缓存/总结"替代"证据"。**
文档对 Audit Packet 说了"packet 是 index/cache 不是证据"，但该边界须扩展到**所有优化**（SDR、Lessons、packet、manifest）。建议加硬规则：

> 任何降低 Codex 读取量的优化，不得降低 Codex 可验证量；packet 必须始终含 raw 路径+哈希，Codex 保留打开任意 raw 文件的权利。

**⚠️ 2. SDR / Decision Cache 是高风险高收益项，比 packet 更危险。**
2026-08-09 单位事故本质上就是"被缓存的错误决定"（rad 当 SFQ）传播很久。SDR 若缓存错误语义会在多个 batch 静默传播。建议 SDR 强制三要素：

- (a) 每条 SDR 必须记录**证据依据**（不只是决定本身）；
- (b) invalidation 触发后**必须重新推导**，不能"悄悄替换"；
- (c) SDR 是**缓存不是权威**——与 mailbox 同理，底层证据仍是事实来源。

**⚠️ 3. Tier 0 工具本身需要被验证。**
B/C/F/M/N 依赖脚本（build-audit-packet.py、verify-batch、semantic-lock 检查）。**一个坏了但说 PASS 的机械验证器，比没有更糟**（虚假的确定性保证）。建议 verify-batch 上线前先有它自己的测试（如故意放坏 scope 验证能抓住），并纳入回归。

### 3.3 补充意见

- **I. Exception-only Codex Queue**：同意，但路由必须**规则化**（按 §8 escalation triggers 机械匹配），不能靠 Claude/Copilot 判断"值不值得打扰 Codex"——否则执行者有"显得高效"而压住问题的动机。
- **L. Reviewer Lessons**：同意只记可泛化 failure pattern（如 RL-001 activity-window gap），但要有版本可被 superseded，且不得变成"B2 cluster=0 所以无事件"这类结论性偏见。
- **H. 确定性抽样**：同意仅用于非 final Gate 审计；final Gate / metric freeze 仍完整审 raw（文档已声明）。
- **Pilot 建议**：M7/M8 batch pilot 应实测 §21 两类指标（touchpoints vs audit workload），并给 Semantic Lock 加"故意改参数能否被抓住"的测试用例——机制本身也要有 control。

---

## 4. T1–T8 回答

| | 回答 |
|---|---|
| T1 CRITICAL 双上下文 | ✅ 同意 |
| T2 机器生成 Audit Packet | ✅ 同意（硬边界：packet=索引≠证据） |
| T3 Scientific Decision Records | ⚠️ 有条件同意（证据依据 + 强制失效重推 + 缓存非权威） |
| T4 Semantic Lock | ✅ 同意 |
| T5 哈希种子确定性抽样 | ✅ 同意（非 final Gate 场景） |
| T6 Exception-only Queue | ✅ 同意（规则化路由） |
| T7 Batch Audit Window | ✅ 同意（独立记录） |
| T8 verify-batch Tier 0 | ✅ 同意（工具自身需验证） |

---

## 5. 结论与落地建议

- **Part I 可直接进入扩展草稿**，无需再改；
- **Part II P0 四项建议采纳**，按三点加固：index≠evidence 全局边界、SDR 三要素、Tier 0 工具自测；
- 落地顺序：**先建 Semantic Lock + verify-batch 最小版**（解锁 F/M/N 且成本最低）→ 再上 Audit Packet 与双 Reviewer 上下文 → 最后 SDR/Lessons。
