- **2026-08-09 审计警告**：JoSIM `P()` 是 raw rad；旧 `sfq_metrics.py` 的 SFQ/`fast_events` 口径失效。除本索引明确标为当前有效的文件外，所有 2026-08-06 及更早的接口结论先按历史材料处理。
- **状态图例**: 🟢 当前有效 | 🕰 历史/被替代（保留参考）| 📚 参考/工具 | 🔄 进行中
- **目录结构（2026-08-09 整理）**：根目录 = 活跃文件；`history/` = 研究历程；`archives/` = 归档研究记录（不常用，保留参考）。跨模型交接先读 `docs/HANDOVER.md` + `history/research-history.md`。

## 活跃（根目录）
- 🟢 [项目主任务清单](project-todo.md) — Phase −1 计量与双基线（M4–M11、M12 已验收）；候选路线/接口 Gate 仍待独立授权（状态追踪唯一权威，2026-08-13）
- 🟢 [项目综合总结](project-summary.md) — Phase −1 状态快照
- 🟢 [项目结构](project-structure.md) — 目录、证据层级与工作流入口（2026-08-09）
- 🟢 [Skill 使用规范](skill-usage.md) — `.agents/skills` canonical 结构、最小触发与 Claude 兼容规则

## 研究历程（history/）
- 🟢 [研究历程时间线](history/research-history.md) — 2026-07-12 至今完整历程：阶段、实验、结论演变、转折点；跨会话/跨模型第一手历史权威（2026-08-09）

## 归档（archives/，历史或参考，不常用）
- 🕰 [GPT 项目审计](archives/guidance-from-gpt.md) — 旧 Step 0-5 框架；相位/事件与路线结论已被 08-09 审计取代
- 🕰 [DCSFQ_BVM 设计](archives/dcsfq-bvm-design.md) — 起点网表仍存在；45–55µA 目标和 Phase 1 判据已失效
- 🕰 [Phase 1 执行计划](archives/phase1-bvm-bq-coupling-plan.md) — 旧 BVM→BQ 双路线计划，已被 Step 0-4 + H7 替代
- 🕰 [BVM→BQ 耦合问题](archives/bvm-bq-coupling.md) — 早期阻抗匹配分析（~25% 传递），已被实验记录+证据链替代
- 🕰 [BVM→BQ 耦合实验记录](archives/bvm-bq-coupling-experiments.md) — 原始实验索引可追溯；SFQ 数、v4 和排除结论待重算
- 🕰 [PIM 路线图设计](archives/pim-roadmap-design.md) — PoC→PIM 顶层方向仍有效；Phase 1 双路线细节过时
- 🕰 [BQ v4 修改方案](archives/bq-v4-modification-plan.md) — 旧判定已失效；110/130/150µA 完整 Gate 待重验
- 📚 [K 元件变压器分析](archives/k-element-transformer-analysis.md) — 历史参数分析；"根因"机制未经当前口径单变量对照冻结
- 📚 [ColdFlux 标准元件库](archives/coldflux-library.md) — 35 个网表与 jjmit 参数索引；旧"已验证"级别待数值断言和负载回归
- 📚 [SFQ 脉冲物理](archives/sfq-physics.md) — 背景参考；固定脉宽/旧相位计数口径不得代替审计后指南
- 📚 [测试方法论](archives/test-methodology.md) — 测试结构参考；事件指标以 Phase −1 新规格为准
- 📚 [JJ 模型参数演变](archives/jj-model-parameters.md) — V0 (0.25mV) vs ColdFlux (1.6mV) 的模型时代索引
- 📚 [T1 全加器](archives/t1-full-adder.md) — 11 结网表参考；实现映射和完整时序功能待验证
- 📚 [论文方向分析](archives/paper-directions-analysis.md) — 四个论文方向创新性/可行性评估，竞争格局
- 📚 [元件参考](archives/component-reference.md) — 元件参数速查

## 仓库文档（docs/，活跃）
- 🟢 [项目完全理解指南](../docs/guide/project-guide.md) — 当前物理、源码、实验和路线口径
- 🟢 [审计后交接](../docs/HANDOVER.md) — 当前执行状态与下一步（新会话第一读）
- 🕰 [原理深讲（deep-dive）](../docs/guide/deep-dive.md) — 已被证据审计取代，正文仅历史草稿（顶部有警告）
- **信任与建议（2026-08-10）**：用户信任我并欢迎主动建议；保持"大胆推进 + 严谨标准"平衡，物理结论仍等审计。[详情](feedback-trust-and-advice.md)
- **commit/通知三级模型（2026-08-15）**：L0 默认不提交不通知；L1 自检后直接 atomic commit + 简报用户 + 批量汇总 INFO；L2 须用户授权或有效 Codex contract，超范围立即停止。[详情](feedback-notify-changes.md)
