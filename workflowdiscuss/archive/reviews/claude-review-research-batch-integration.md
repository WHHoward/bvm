# Claude 审阅意见 — 研究流程与 Batch 协作整合修改提案

审阅人：Claude（执行者视角）
日期：2026-08-12
对象：`workflowdiscuss/archive/proposals/JOSIM_BVM_研究流程与Batch协作整合修改提案.md`
状态：对三方审阅的建议；不修改现行协议，不授权科研任务

## 总体判断

这是三份提案中最好的一份。决定性改进是 **Study Phase 轴（EXPLORATORY / CALIBRATION / CONFIRMATORY）**——它把协作机制挂到了科研方法之下，直接针对本项目最深的失败模式（M4 时代探索期窗口/阈值选择被冻结进基线）。§41 的决策顺序（科研方法 → Batch 最小扩展 → FROZEN 修复 → Pilot → 协议合并）正确，我支持按此顺序推进。

**§21 的 FROZEN 三段式（input manifest / mutable delivery binding / output manifest）是本提案最高价值的协议修复**——它精确对应 M6-001 的 REWORK 根因（scope manifest 同时绑定并授权修改交付物）。M6-002 用"mutable deliverable 不入 scope manifest"的简单替代解决了同一问题；三段式是更一般的形式，建议落实为 handoff.py 的 schema 扩展（v1.1）。

## 强同意（简要）

1. **METRIC_SPEC_V2 与 INTERFACE_GATE_V1 分离**（§4.3）——"测量尺"与"产品验收标准"分离，纠正了项目一贯的概念混淆；
2. **M7A/B/C 拆分**（§4.1）——数学 ground truth / canonical circuit / historical regression 三类验证分开，M7C 明确"不是电路物理正确的 ground truth"，防 circular validation；
3. **Reference Reconstruction + provenance 标签**（§5/§6）——[PUBLISHED]/[AUTHOR_PROVIDED]/[DERIVED]/[INFERRED] 等标签与 R0–R3 层级是"不要精确定优错误参考对象"的正确工具；
4. **Blind FORMAL REVIEW 两阶段**（§19）——先盲审形成 falsification hypotheses，再看 ledger，正确回应 anchoring 问题；
5. **Operating Region 取代成功点**（§12）+ **Held-out Validation**（§13）+ **Robustness 四层**（§14）——方法正确；
6. **§23 抽样 seed 在合同签发时固定**——比"delivery commit 派生"更干净（连 delivery 时点都无法影响）；
7. **§33 AI 物理主张纪律**——MODEL/FORMULA/NUMERICAL SUBSTITUTION/UNITS/ASSUMPTIONS/FALSIFICATION TEST，与项目 law/measured/inferred 传统一致；
8. **十条不可妥协原则**——可作协议级表述。

## 需要修正或补充

### R1. §31 角色表引入了现有协议中不存在的实体（必须澄清）

Terra / Sol XHigh / Luna 是当前协议中从未出现的名称。如果它们是用户实际可用的模型层，请明确映射到真实工具（否则协议文档引用虚构角色会造成"谁做什么"的歧义）；如果只是设想，请把该节标注为 future-looking，不进入协议正文。目前三方都实际存在的只有：Codex、Claude Code、Copilot（+ 用户）。"Sol XHigh 只处理 M9/M11"这类职责描述在被确认前不能写进协议。

### R2. M8 的"稳定"判据必须 run 前预声明

§4.2 说"若 0.025 ps 尚未稳定，则继续 refinement"——但"稳定"的数值定义（关键可观测量在相邻步长间的允许偏差带）必须在收敛协议中**事先**声明，否则"稳定"是事后目标移动（M9 防的是同一风险在容差层面，M8 需在收敛判据层面防）。建议：M8 的 convergence protocol 在运行前冻结稳定性带宽，与 §23 seed 同纪律。

### R3. Held-out 验证集必须在调参前声明

§13 方向正确，但要显式补一条：**验证集（load/waveform/bias/state/process sample）在 calibration 运行开始前声明并锁定**，否则 held-out 是事后划分，与"seed 在签发时固定"同理。

### R4. 阶段转换本身是科学决定，需明确裁决与记录

EXPLORATORY → CALIBRATION → CONFIRMATORY 的转换由谁裁决、如何记录？按角色共识，这是 Codex 审计 + User 采纳（与 SDR 生命周期一致）。建议：每次阶段转换写一条 decision record（至少 EXPLORATORY→CONFIRMATORY 必须），转换前不自动继承前一阶段证据的权威性。

### R5. M 编号保持稳定，不重编号

todo/历史/mailbox 引用都锚定在 M7/M8/M9/M10/M11 编号上，重编号会产生 provenance churn。建议：**M7 下挂 M7A/B/C 子项；M11 保留单编号、设两个子门**（M11A Measurement Calibration Baseline / M11B Scientific Reconstruction Baseline，回答 §35 的开放问题）。M9 拆分同理：METRIC_SPEC_V2 是 M9 的产物，INTERFACE_GATE_V1 是独立新任务（建议编号 G0 或并入 Stage F 前置）。

### R6. FROZEN 三段式 verifier 的落地方式

建议：扩展 handoff.py schema 为 v1.1——request 增加 `input_manifest`（不可变输入哈希，含语义参数如 plan.json 的 windows/directions/thresholds）、`mutable_binding`（授权路径 + pre/post image 哈希）、`output_manifest`（raw/分析产物绑定）。verify-task 对三段分别校验：frozen inputs 匹配、mutable 变更恰为授权集合且 post-image 与声明一致、outputs 完整。同时记录 M6-002 的简单替代方案（mutable deliverable 不入 scope-files.sha256）作为轻量选项——两种都写进协议，任务按需选择。

### R7. 背景状态行需修正

§1 说"M6 已完成"——实际状态：M6-001 A01 因 scope manifest 双路径问题 REWORK（产物归档为候选），M6-002（FROZEN 复现）A01 已交付、最终 verify-task VERIFIED，**待 Codex 审计**。建议按实际状态改写，否则作为"背景事实"会误导后续引用。

### R8. W5C Author Inquiry 需要时间盒与回退路径

作者询问结果标 [AUTHOR_PROVIDED] 正确，但要加：询问发出/答复的日期记录；若无答复或答复不充分，**回退到 R0/partial-R1 + 显式 UNKNOWN 清单**继续，不能无限等待。询问本身零 Codex 成本，建议现在就开始。

### R9. 讨论问题太多（36 个），建议收敛

§38–40 共 36 个问题，全部回答会稀释决策。建议每方只回答归属自己的 5–7 个核心问题（如 Claude 答 §39 的 6 个），其余标记 "defer to pilot"（pilot 中回答比讨论中回答便宜且真实）。

### R10. BVM_SOURCE_SPEC 的测量语义必须与 METRIC_SPEC 同尺

Stage C 的 source characterization 使用的窗口/方向/积分/聚类语义必须直接引用 METRIC_SPEC_V2（ruler 唯一性），不能在 source spec 中另行定义测量语义。文件层级上 BVM_SOURCE_SPEC 是 METRIC_SPEC 的消费方，不是平行定义。

## 对 §36 依赖冲突的判断

同意"Reference Reconstruction / Source Characterization 早于 candidate tuning"。补充一点使边界更可操作：

```text
M9（METRIC_SPEC 冻结）后即可启动：
  W5 / provenance / author inquiry / canonical cell /
  BVM source characterization / receiver baseline characterization

M11 只锁：
  candidate 参数路线（BQ v4 / DCSFQ_BVM 的调参与 route verdict）
```

这样 Phase −1 不会成为研究阻塞（characterization 不等 M11），同时 candidate tuning 的科学防线保持。

## 对 §35 M11 拆分问题的建议

**M11 保留单编号 + 双子门**（M11A Measurement Calibration Baseline / M11B Scientific Reconstruction Baseline）。理由：measurement baseline（尺子与重算基线）与 reconstruction baseline（参考对象与 provenance 状态）是两个不同对象，但共享同一编号利于 todo 历史连续性。

## 回答 §39（给 Claude 的问题）

1. **Batch fact layer 最小实现**：BATCH.md（授权边界）+ 每 subtask 的 RESULT.md/LEDGER.md + 机器追加的 BATCH-MANIFEST；不加 schema 重担——先用现有 receipt.yaml 模式平移到 subtask 级。
2. **Audit Packet 机器生成**：`packet = f(receipt.yaml, manifests, git metadata)`，在审计时由脚本渲染（不在交付时由执行者写）；codex_focus 字段从"有 rework 的 subtask + Major findings + 边界用例"推导，不手写。
3. **jj_audit.py 可机械解析字段**：网表 .param（Ic/area/L/R）、.model 行、subckt 拓扑边、JJ 元件名与节点对——可解析；**role annotation（[PUBLISHED]/[TUNED]/[INFERRED]）必须人工/来源声明**，机器只能校验格式与一致性，不能判定来源真实性。
4. **BVM Source Spec 最少实验**：read-0/read-1 各 2–3 个负载点的单一 pwl 激励 + 现有 P2 数据复用；重点是**声明测量语义（窗口/方向/积分）来自 METRIC_SPEC**，而不是实验数量。
5. **当前执行成本浪费点**（实测）：M6-001/002 的 receipt-verify 哈希定点摩擦、verify-task 对 read+write 路径的机械误报、以及每次任务的上下文重建——三个都是 Tier 0 工具问题，不是模型问题。
6. **PRE-REVIEW 不隐藏失败**：LEDGER append-only + 机器计数（attempts/state 转换）已足够；关键是 Codex 审计时能看到"内部消化了多少"的统计（failures caught internally vs escaped），LEDGER 结构要为此设计。

## 结论

本提案应成为三方的整合基线：**Decision 1（科研方法）** 采纳 Study Phase + 七阶段 + M7A/B/C + M9 拆分 + provenance 前移；**Decision 3（FROZEN 三段式）** 是当前最高价值修复，建议先于 Batch pilot 落地（它修复的是现行 FROZEN 合同的真实缺陷，不依赖 batch 机制）。W5A/B/C 现在就可以零 Codex 启动。M7A/B/C + M8 审计会话作为首个 batch pilot（§27）合理。

前置确认：R1（角色实体）、R2（M8 判据预声明）、R3（held-out 预声明）、R7（M6 状态修正）。
