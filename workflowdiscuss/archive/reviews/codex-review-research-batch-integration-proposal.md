---
title: Codex 对“JoSIM × BVM 研究流程与 Batch 协作机制整合修改提案”的审阅意见
document_type: discussion_review
status: ADVISORY_ONLY
date: 2026-08-12
reviews: workflowdiscuss/archive/proposals/JOSIM_BVM_研究流程与Batch协作整合修改提案.md
authority: does_not_modify_active_protocol_or_research_state
---

# 审阅结论

**建议采纳提案的总体方向，但先把它作为下一阶段的设计蓝图和 Pilot 输入，不应立即改写现行协议、任务表或研究状态。**

提案最重要的改进是把两个经常被混淆的问题明确分开：

1. 计量管线是否能正确地测量和判读；
2. 被测的 BVM、BQ 或 DCSFQ_BVM 是否是有足够来源依据、且可公平比较的对象。

这与当前 Phase −1 的审计结论一致：M4–M6 已建立部分测量能力，但 M7–M11 尚未完成；因此任何 BQ v4 / DCSFQ_BVM 路线结论仍被阻塞。

## 建议作为正式采纳前提的修改

### 1. 补全 Phase −1 的依赖链

提案第 4 节把 Stage A 写作 `M7 → M8 → M9`，但当前项目的约束还包括：

```text
M7A/M7B/M7C → M8 → M9 → M10 → M11
                              ↓
                    才能启动正式候选路线判定
```

- **M10** 负责在保留旧文件的前提下重建 `metrics_v2` 及审计表；
- **M11** 才是定义、代码、原始数据、对照、容差与收敛均齐全的新基线冻结；
- 因而 M11 前的 source / receiver 工作只能是表征、解剖、基线和实验设计，不能产出 route verdict 或 final Gate。

### 2. 区分 Lite 核心流程 Pilot 与 Batch Extension Pilot

M12、M5 和 M6 提供了 Lite/FROZEN 单任务流程的经验，但**不能据此认定 Batch Extension 已完成真实 Pilot**。下列批处理部件仍应先进行窄 Pilot：

- `BATCH.md` 与批次状态发现；
- 单一 canonical Semantic Lock；
- append-only ledger；
- fresh-context blind formal review；
- 机器生成、只读的 Audit Packet。

在这些机制完成真实试用前，它们不应成为关闭 todo、冻结指标或建立物理结论的权威路径。

### 3. 保留 Reference Reconstruction 分级，但定义 R3 的验收条件

`R0–R3` 是必要的来源边界。建议将 R3 明确为：

> 在预先声明的模型闭包、测试台、参数来源、数值设置与观测容差下，满足全部复现判据的独立复现。

否则“Full Reproducibility”过于宽泛，容易被一个局部波形相似性误用。所有未公开或无法核实的参数必须保留 `[UNKNOWN]` / `[INFERRED]` 标签，不得因后续调参而变成“论文参数”。

### 4. 对 W5C（作者询问）增加外部行动授权

作者询问是合理的 provenance 补全方式，但发送邮件或其它对外联系需要用户单独授权。收到的材料应记录日期、原始出处、适用范围，并标记为 `[AUTHOR_PROVIDED]`；它可用于复现，但不会自动变成已发表、可泛化的结论。

### 5. 让 M7 的三类“通过”具有不同语义

| 子任务 | 可证明的内容 | 明确不能证明的内容 |
|---|---|---|
| M7A | 公式、单位、窗口与聚类实现 | 真实超导电路的物理正确性 |
| M7B | 已理解的 Josephson/JTL 瞬态上的测量管线行为 | BQ/DCSFQ_BVM 候选设计成功 |
| M7C | 历史原始数据的重算稳定性 | 历史设计或解释本身就是 ground truth |

尤其 M7C 只能防止新管线再次误读历史数据，不能将 DCSFQ 300 µA 或 BQ v4 的历史轨迹提升为设计正确性的证据。

### 6. 把 M8 写成“收敛规则”，而不是固定三点检查

`0.1 → 0.05 → 0.025 ps` 是合格起点。正式标准应为：若预注册关键观测未稳定，继续 refinement；同时预先规定比较窗口、信号对齐/插值方式与数值容差。否则小幅的时间平移可能被误判为不收敛，或真正的面积/相位偏差被掩盖。

### 7. 严格分离 Measurement Spec 与 Interface Gate

我支持分别建立：

- `METRIC_SPEC_V2.md`：如何测量；
- `INTERFACE_GATE_V1.md`：什么结果算接口成功。

前者应在 M9 基于校准数据冻结；后者必须等 Reference Reconstruction、BVM source envelope 与 receiver feasible envelope 有明确事实层后才冻结。这样可防止为使候选设计通过而移动测量尺或验收线。

### 8. 为 Batch 增加依赖失效传播规则

`SUBTASK_READY` 仅是 batch 内部的暂时可用状态。每个下游 subtask 应记录其所依赖的：

- 上游 Semantic Lock hash；
- 上游结果 snapshot；
- 已假定的输入与前提。

任一上游被重新质疑时，依赖链应停止并升级给 Codex，而不是继续产出看似完整的下游结论。

### 9. 模型路由按能力等级实施，不绑定某一具体型号必然可用

建议保持提案的职责分层，但把具体模型名称视为当前可用实现，而不是协议前提：

- **最高能力审计**：M9/M11、不可逆架构、路线裁决、核心物理歧义、论文关键主张；
- **日常总控/复杂审阅**：任务拆分、合同、最终审计、复杂 debugging；
- **低成本执行支撑**：发现、索引、manifest/hash、一致性检查、重复回归；
- **Claude Code**：长时间实现、实验运行、原始证据与 `RESULT` 产出；
- **Copilot**：独立反证式 evidence review。

低成本代理的输出始终是“待审计发现”，不直接推进 todo 或科学状态。

## 当前建议的状态

本提案应保持 `DISCUSSION_DRAFT`。M6 已完成且当前已暂停，不应仅因本提案而签发 M7 或新的 Batch。合适的下一步是：在用户决定恢复工作后，先将本意见与其它审阅意见收敛成一份可验证的 Batch Pilot ADR，再由 Codex 定义首个有界 Pilot 的合同。

## 事实依据

- 当前 Phase −1 完成与阻塞状态：`memory/project-todo.md`；
- 当前可信研究边界：`docs/HANDOVER.md`；
- 当前正式 FROZEN 协议：`research/WORKFLOW.md` 与 `josim-handoff/v1`；
- Lite 2.0 当前为 Pilot 设计而非自动替代现行协议：`workflowdiscuss/current-reference/WORKFLOW-lite-2.0-FINAL-IMPLEMENTATION.md`。

