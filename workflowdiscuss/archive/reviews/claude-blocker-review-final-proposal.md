# Claude Blocker-only Review — 最终研究流程与协作方案

审阅人：Claude（执行者视角）
日期：2026-08-12
对象：`workflowdiscuss/archive/proposals/JOSIM_BVM_最终研究流程与协作方案.md`
格式：BLOCKER / MINOR / NO_BLOCKER（按要求只找阻止实施的问题，不做第四轮流程设计）

## 事实核验（审阅前置）

文档"当前项目事实"声明"M6 已获得有效 FROZEN 审计并 ACCEPTED"——**已核实为真**：
`codex-20260812-173816`（M6-002 A01 已 ACCEPT，按用户指令暂停派发后续任务），M6-002 worktree 的 `audits/C01/` 存在。背景事实准确。

## BLOCKER

**无。**

逐项核验：

- **依赖图一致性**：M7A/B/C → M8 → M9 → M10 → M11A；characterization 自 M9 分支 → M11B → INTERFACE_GATE_V1 → candidates。与正文 B/C/Step 7–9 无矛盾。
- **A3 CONFIRMATORY 冻结清单**（hypothesis/model/parameter domain/source-load/metric/windows/controls/thresholds/validation set/stopping rule）与 C7（held-out 调参前冻结）、C8（operating region）一致。
- **W5C 回退路径**：无答复 → R0/partial-R1 + UNKNOWN list；与 M11B 通过条件（"UNKNOWN / INFERRED 参数明确"即可 PASS）兼容，不会死锁等待作者。
- **FROZEN v1.1 可行性**：input/mutable/output 三段式有 M6-001（mutable deliverable 混入 frozen manifest → 误判）与 M6-002（mutable 不入 manifest → 通过）两组现成回归样例，验收目标（mutable 不误判 + 真 frozen drift 仍捕获）可测试。
- **Batch P0 五项** + 明确延期清单（verify-batch/Decision Cache/routing 等入 backlog）消除了前几轮的重型机制风险。
- **Decision F 能力层写法**解决了角色实体歧义（前稿的 Terra/Sol XHigh/Luna 已移除，模型名入 runtime/config 而非协议）。
- **SUBTASK_READY 降权**、Semantic Lock 单一来源、blind review 两阶段、Audit Packet 机器生成——与已三方收敛的 Batch Extension 一致。

## MINOR

1. **B2/B3 的 Evidence 行与 Tier 3 审查要求不一致**
   M8/M9 的 Evidence 只标 `CALIBRATION + CRITICAL + FROZEN`，未引用 Decision F Tier 3 的 fresh-context review + high-capability final audit + user adoption；A2（CALIBRATION）也未写 fresh-context 要求。实施时可能产生"M8/M9 到底要不要 fresh review"的歧义。建议：B2/B3 的 Evidence 行补 Tier 3 审查要求引用。

2. **Batch Pilot 通过标准 #9 的"或"分支未预定义**
   "至少一个真实 defect 被捕获，**或**证明该机制对现有错误模式有效"——自然发现 defect 是随机的；若 pilot 期间未自然发现，回退分支的判定会现场发挥。建议：pilot 开始前写死回退协议（如注入一个 M5-A01 类已知缺陷做 seeded review）。

3. **FROZEN v1.1 的实施授权未写**
   Step 3 需改 handoff.py/schema（input/mutable/output manifest），文档未写由谁实现、走什么授权路径。按现行角色，schema 属 Codex 域。建议：明确"Codex 定义 v1.1 schema，Claude 实现，M6-001/002 作回归验证"的分工，否则 Step 3 在角色归属上卡住。

4. **SEMANTIC-LOCK.yaml 与 FROZEN request.yaml 的双来源未写**
   E3 称 lock 是科研语义唯一来源；但 M8（FROZEN，Step 6）的 request.yaml + plan.json 也是语义来源。LITE batch（M7）无冲突；M8 需明确"FROZEN 任务以 request.yaml 为权威、lock 是其摘要"（或相反），否则出现两个权威。

5. **M7C 的"冻结 expected values"需先正式化**
   文档要求 M7C expected 来自"独立人工/raw 重算冻结值"；但当前 HANDOVER 人工重算表明确标注"不能称为新的自动冻结基线"。M7C 实施前需把人工重算值正式预注册为 frozen constants（M5 AC6 已有此模式），否则 M7C 会在"expected 未冻结"上卡住。可执行细节，非 blocker。

6. **WORKFLOW-lite 仍是 PILOT 状态**
   本方案（FROZEN v1.1 + Batch P0）经用户采纳后即生效，但 WORKFLOW-lite §9 的 pilot→final 条件（2–3 个真实任务 + 指标评估）未走完。建议：采纳决议中显式写"用户采纳 = 授权 v1.1 与 Batch P0 在 pilot 协议上叠加"，避免双轨权威歧义。

## NO_BLOCKER

方案可实施。当前阻塞链是**执行时序**而非方案本身：M6-002 已 ACCEPT（按用户指令暂停派发）；待用户决定恢复科研执行后，按 Step 0（采纳）→ Step 1（科研规则）→ Step 2（W5B）→ Step 3（FROZEN v1.1）→ Step 4（Batch P0）→ Step 5（M7A/B/C pilot）推进即可。
