# Claude 审阅意见 — Batch Extension 最终建议与第三方成本优化

审阅人：Claude（执行者视角）
日期：2026-08-11
对象：`workflowdiscuss/WORKFLOW-lite-2.0-batch-extension-and-cost-optimization.md`
状态：对三方审阅的建议；不修改现行协议

## 总体判断

**Part I 已吸收我上一轮的主要意见**（事实层、SUBTASK_READY 降权、污染半径、探索数据纪律、M10 硬规则、LEDGER、W5 检查点、审计指标分离），并补上了关键一句 **"Do not hide unstable attempts from Codex"**——这比"Never send unstable"更完整，我完全同意。**Part I 可以进入正式扩展草案**。

**Part II 的 A–O 方向多数正确，但有两个结构性细化必须先定**：(1) B/C 的 audit packet 必须"审计时生成"而非"交付时由执行者写"；(2) §15 的 B1/B2 拆分意味着 batch 内证据模式必须同质——B1 (M7, LITE) 与 B2 (M8, FROZEN) 是两个合同，只能合并审计会话，不能合并成同一个 batch 合同。

## Part I — 同意与三处细化

同意：§3 事实层、§5 manifest 是索引不是大日志、§6 LEDGER 最小留痕、§7 SUBTASK_READY 降权与四维语义、§8 污染半径硬触发、§9 绝对边界 + "Implementation repair is delegated; scientific semantics are not"、§12 involvement disclosure、§13 探索数据纪律、§14 Route C/D = BLOCKED UNTIL M11、§15 B1/B2 拆分、§16 双 Gate、§17 M10 硬规则、§19 强制对抗性 completeness review、§21 双指标。

细化：

1. **§9 的边界清单应与 §27 的 Semantic Lock 合并为同一机制**。"什么算科学语义变化"靠 prompt + 清单判断会反复争议（M5 A02 改输出 schema 算 bug 修复还是 metric 定义变化？）。机械版本：**锁文件列出具体冻结项（window 数值、threshold 值、公式、列命名、输出 schema），锁内项变化 = 升级；锁外项 = 自由修复**。清单作为 prompt 兜底，锁文件作为裁定依据。

2. **§10 FORMAL REVIEW "重新验证 PRE-REVIEW 曾发现的问题类型"**——赞成，这是 bug-class 回归，成本低收益高。建议在 REVIEW.md 模板中显式留字段（`pre_review_finding_classes_rechecked: [...]`），否则容易被跳过。

3. **§11 的"二者之一"对终局 Gate 应升级为"两者都要"**：metric freeze（M9）与 physical Gate 必须 Fresh-context Reviewer **且** Codex independent raw recomputation。实现类 CRITICAL+FROZEN（如 M6）维持"至少一个"。

## Part II — 逐项表态

| 项 | 判断 | 要点 |
|---|---|---|
| A Fresh-context FORMAL reviewer | ✅ 同意 | 我们只有一位 Copilot，Session A/B 是真实 fresh context；对 CRITICAL batch 设为默认。§11 的 caution（非不同组织审计）已如实声明 |
| B/C 机器生成 Audit Packet | ✅ 同意，**但有一处关键修正** | 见下 |
| D/E Scientific Decision Record | ✅ 有条件同意 | 见下 |
| F/G Semantic Lock | ✅ 同意 | 与现有机制是同一家族：request 的 windows/directions/threshold + 冻结输入哈希 + M6 的 plan.json 已经是雏形。Batch 级锁 = 各 subtask 锁的并集，脚本校验 |
| H deterministic sampling | ✅ 同意 | 补充边界：sampling 只决定"深读哪些证据集"，**验收标准本身仍逐条机械+审阅核验**，不可抽样 |
| I Exception-only queue | ✅ 同意 | 注意 mailbox 仍是 append-only 通知层；queue 是分类/过滤（`[BATCH-READY]`/`[ESCALATE]`/`[GATE]` 前缀即可），不是会丢消息的隔离区 |
| J Batch Audit Window | ✅ 同意 | 与 M9/M11 同会话双 record 同一思路；每个 batch 独立 decision 是硬条件 |
| K Batch Complexity Score | ✅ 同意 | 按文档说的做 checklist 即可，不要数学化 |
| L Reviewer Lessons | ⚠️ 有条件同意 | 见下 |
| M verify-batch 机械先审 | ✅ 同意，长期最有价值 | 增量演进：现有 handoff.py verify-task 就是种子；先加 semantic-lock 等值校验 + audit-packet 生成，不 gold-plate |
| N fail-fast preflight | ✅ 同意 | 就是现行协议实践（ACK 前机械预检），建议直接引用现有流程而非另立机制 |
| O 三级成本 / lowest sufficient tier | ✅ 同意 | 注意"sufficient"由任务声明的 Risk/Mode 定义，不是"能过的最小层" |

### B/C 的关键修正：Audit Packet 必须"审计时生成"

交付时由执行者写 packet，即使字段机械生成，`codex_focus` 这类判断字段仍会被执行者视角污染（自己挑重点 ≈ cherry-pick 的软版本）。建议：

```text
packet = f(receipt.yaml, BATCH-MANIFEST, git diff metadata, ledger 头部)
生成时机 = Codex 审计开始时（或 audit 工具内）
生成者 = 脚本（如 verify-batch 的一部分）
```

packet 是**派生视图**，不是新的平行格式——协议记录仍是 receipt.yaml（schema 校验、哈希绑定），packet 只是它的渲染。这样 packet 永不漂移、执行者无法挑选。

### D/E 的条件

- SDR 只记录**会被反复重新争论**的裁决（unit/window/sign/event 语义），不记录一次性决定——避免文档增殖；
- SDR 必须挂 `valid_for` 的 spec 版本：M9 冻结后 METRIC_SPEC_V2 是唯一权威，SDR 里与它冲突的条目自动失效（文档已有 invalidate_if，补充"spec freeze 自动失效"条款）；
- SDR 由 Codex/User 裁决，Claude 最多起草，且 draft 不进事实层（mailbox 或 discussion 即可）。

### L 的条件

- RL 只存可泛化的 failure pattern（带示例），任务结论不固化；
- 加载进 review prompt 必须 opt-in，防止锚定 reviewer；
- 一条 RL 被后续 review 反证后必须显式退役（加 `retired_by`），否则 lessons 会变成累积偏见。

## 新发现的三处缺口

### G1. Batch 内证据模式必须同质（§15 的直接推论）

B1 (M7, LITE) 与 B2 (M8, FROZEN) 证据模式不同，按 WORKFLOW-lite §2，FROZEN 走 v1 后端（request/ACK/receipt 链）。一个 batch 合同不能同时挂两种模式。正确表述：

```text
B1 = M7，LITE batch pilot（新文件结构）
B2 = M8，独立 FROZEN v1 任务（其 decisive evidence 预注册为 M9 输入）
B1/B2 可在同一 Codex 审计会话连续审（Audit Window），但合同独立
```

文档 §15 的语义对，但"B2 是 batch 还是任务"要写清楚，否则实现时会混淆。

### G2. BATCH-MANIFEST 必须机械维护

append-only 索引如果由 Claude 手写，会漂移（漏条目、选择性记录）。建议：manifest 追加由脚本完成（从 LEDGER/RESULT 头部读取字段），Claude 只提供 finding_summary 的人类字段。与 verify-batch 工具一并实现。

### G3. 启动时序要写死

扩展草案应显式声明 pilot 条件：

```text
前置：M6 审计 ACCEPT（首个 CRITICAL+FROZEN 全链闭环）
Pilot：B1（M7）LITE batch，Codex 显式签 BATCH.md
记录：§21 双指标（touchpoints / audit workload）+ §37 的 pilot 观察
之后：再决定 B2 与 C/D/W5 的机制
```

否则会出现"M6 还在审计、batch 扩展先跑起来"的并轨混乱——M6 本身是验证现行协议时序的锚点。

## T1–T8 简答

- T1（CRITICAL batch 默认 fresh-context FORMAL）：✅ 同意，设为默认。
- T2（机器生成 audit packet 作首屏）：✅ 同意，但按 B/C 修正——审计时生成、派生视图、执行者不写判断字段。
- T3（SDR）：✅ 有条件——见 D/E 三条。
- T4（SEMANTIC-LOCK）：✅ 同意，与 §9 合并为同一机制（锁文件裁定），脚本校验。
- T5（commit-seeded deterministic sampling）：✅ 同意，且 AC 逐条核验不可抽样。
- T6（exception-only queue）：✅ 同意，前缀分类即可，mailbox 仍 append-only。
- T7（Batch Audit Window）：✅ 同意，独立 decision 是硬条件。
- T8（verify-batch）：✅ 同意长期实现；从 verify-task 增量演进，先做 lock 校验 + packet 生成。

## 结论

Part I 可以定稿为正式扩展草案；Part II 按 P0 四项进 pilot，P1/P2 按批次迭代。**先决条件**：G1（模式同质）、G2（manifest 机械维护）、G3（M6 审计通过后再启动 B1 pilot）。
