---
title: JoSIM × BVM 最终研究流程与协作方案
document_type: final_proposal
status: FINAL_FOR_BLOCKER_REVIEW
date: 2026-08-12
authority: advisory_until_user_adoption
project: WHHoward/bvm
intended_reviewers:
  - Codex
  - Claude Code
  - GitHub Copilot
---

# JoSIM × BVM 最终研究流程与协作方案

> **用途**：作为 Codex / Claude Code / GitHub Copilot 的最终 blocker-only 审阅稿。  
> **当前状态**：不直接修改 active protocol；通过最后一次 blocker-only review 后，由用户决定是否采纳并进入实施。  
> **当前项目事实**：Phase −1 的 M4、M5、M6 已完成；M6 已获得有效 FROZEN 审计并 `ACCEPTED`。M7–M11 尚未完成；BQ v4 与 DCSFQ_BVM 的正式路线判定继续阻塞。
>
> 本方案的最终目标不是增加更多流程，而是：
>
> **科研方法更严格，日常协作更轻。**
>
> 即：
>
> - 绝大多数机械/实现任务使用最低成本且足够的保证；
> - 少数真正决定物理结论、路线与论文主张的 Gate 使用最严格证据；
> - 不再让合同、mailbox、重复审阅和上下文重建占据主要科研成本。

---

# Decision A — 引入 Study Phase，但不增加新的重型工作流

所有科研任务增加一个认识论标签：

```yaml
study_phase:
  EXPLORATORY
  CALIBRATION
  CONFIRMATORY
```

## A1. EXPLORATORY

用途：

- Debug；
- mechanism hypothesis；
- bounded parameter sweep；
- topology anatomy；
- 下一步实验设计。

允许根据结果调整下一次实验。

限制：

- 不能直接成为 final Gate；
- 不能事后补票升级为 CONFIRMATORY；
- 不能直接成为 paper-critical final number；
- 产生的参数若后续采用，必须保留 `[TUNED] / [INFERRED] / [DESIGNED]` provenance。

## A2. CALIBRATION

用途：

- measurement method；
- regression；
- convergence；
- tolerance；
- baseline reconstruction。

典型任务：

```text
M6 / M7 / M8 / M9 / M10 / M11A
```

## A3. CONFIRMATORY

用途：

- final interface Gate；
- route verdict；
- final margin；
- paper-critical claim。

要求在运行前冻结：

- hypothesis；
- model；
- parameter domain；
- source/load；
- metric；
- windows；
- controls；
- thresholds；
- validation set；
- stopping rule。

必须使用：

```text
CRITICAL + FROZEN
+
fresh-context independent review
```

阶段转换不自动继承证据权威。

至少：

```text
EXPLORATORY → CONFIRMATORY
```

必须留下 decision record，并由 Codex 审计、用户采纳。

---

# Decision B — Phase −1 最终依赖链固定为 M7A/B/C → M8 → M9 → M10 → M11

保持现有 M 编号，避免 provenance churn。

---

## B1. M7 拆成 M7A / M7B / M7C

### M7A — Mathematical Unit Tests

真正的 mathematical ground truth：

- synthetic zero trace；
- known phase step；
- known two-transition trace；
- known voltage-area pulse；
- sign reversal；
- boundary/window edge cases。

它只能证明：

> metric 的公式、单位、window、cluster 和 sign 实现正确。

不能证明：

> 真实 BQ/DCSFQ/BVM 物理正确。

Evidence：

```text
CALIBRATION
CRITICAL + LITE
```

---

### M7B — Canonical Circuit Validation

使用独立、已充分理解的 canonical Josephson/SFQ case，例如 JoSIM JTL。

它只能证明：

> measurement pipeline 在真实 Josephson transient circuit 上行为正确。

不能证明：

> BQ v4 或 DCSFQ_BVM candidate 成功。

Evidence：

```text
CALIBRATION
CRITICAL + LITE
```

---

### M7C — Historical Regression Characterization

使用 preserved raw data，例如：

- DCSFQ 300 µA；
- BQ v4 六周期；
- 已人工重算历史结果。

**M7C 的 expected values 必须来自独立人工/raw 重算冻结值。**

禁止：

```text
production analyzer
→ 生成 expected
→ 同一个 production analyzer
→ 验证 expected
```

M7C 只能证明：

> 新 pipeline 没有再次误读历史 raw data。

不能证明：

> 历史设计或历史物理解释就是 ground truth。

Evidence：

```text
CALIBRATION
CRITICAL + LITE
```

---

## B2. M8 改成“有界 convergence procedure”

`0.1 → 0.05 → 0.025 ps` 只是起点，不是完成定义。

M8 必须在运行前预注册：

```yaml
initial_dt:
refinement_ratio:
max_refinement_levels:
observables:
comparison_windows:
alignment_or_interpolation_policy:
stability_tolerance:
stop_rule:
```

至少检查：

- phase turns；
- voltage-area turns；
- phase-area residual；
- event timing；
- pulse width；
- downstream count（如适用）。

### 成功条件

相邻 refinement 的预注册关键量满足稳定带宽。

### 未收敛条件

达到最大 refinement depth 仍不稳定：

```text
INCONCLUSIVE
```

禁止无限 refinement。

Evidence：

```text
CALIBRATION
CRITICAL + FROZEN
```

---

## B3. M9 只冻结 `METRIC_SPEC_V2.md`

M9 回答：

> **怎么测？**

包括：

- raw rad → turns；
- same-JJ P/V mapping；
- direction/sign；
- window semantics；
- control subtraction；
- activity clustering；
- phase wrap/unwrap policy；
- actual-time voltage integration；
- numerical tolerance；
- convergence rule；
- CSV/output schema。

M9 不回答：

> 什么结果算一个好的 BVM interface。

也就是说：

```text
METRIC_SPEC_V2
≠
INTERFACE_GATE_V1
```

Evidence：

```text
CALIBRATION
CRITICAL + FROZEN
```

---

## B4. M10 保持原职责

M10：

- 重建 `metrics_v2`；
- 生成 audit tables；
- 保留旧文件；
- 不机械改写历史 narrative。

旧研究文档采用：

```text
原文保留
+
SUPERSEDED banner
+
central correction table
+
metrics_v2 machine-readable output
```

不删除错误历史。

---

## B5. M11 保留单编号，但设两个子门

### M11A — Measurement Calibration Baseline

要求：

- M4–M10 完整；
- MetricSpec frozen；
- tests；
- raw data；
- controls；
- convergence；
- historical recomputation；
- evidence provenance。

### M11B — Scientific Reconstruction Baseline

要求：

- reference provenance；
- reproduction level；
- BVM reconstruction state；
- published-QB reconstruction state；
- canonical receiver baselines；
- source/receiver characterization 状态；
- UNKNOWN / INFERRED 参数明确。

只有：

```text
M11A PASS
+
M11B PASS
```

后，才能启动 BQ v4 / DCSFQ_BVM 的正式 candidate tuning 与 route verdict。

---

# Decision C — 在候选调参前增加 Reference / Source / Receiver 三层

这是 Phase −1 之后最重要的科研方法修改。

---

## C1. W5 前移，并拆成三个子部分

### W5A — Prior-art Boundary

记录：

- database；
- query；
- date；
- closest prior art；
- already does；
- does not report；
- allowed novelty wording。

W5A 未完成前禁止使用：

```text
first
no prior work
literature blank confirmed
```

---

### W5B — Reference Provenance

现在即可启动。

新增：

```text
docs/research/REFERENCE_PROVENANCE.md
```

统一标签：

```text
[PUBLISHED]
[AUTHOR_PROVIDED]
[DERIVED]
[INFERRED]
[DESIGNED]
[TUNED]
[UNKNOWN]
```

至少覆盖：

- BVM；
- published modified QB；
- original BQ；
- project BQ v2/v4；
- canonical DCSFQ；
- DCSFQ_BVM；
- JJ model；
- external shunt；
- testbench；
- source/load；
- bias；
- timestep。

---

### W5C — Author Inquiry

作者联系是可选外部行动，发送前必须由用户明确授权。

询问：

- modified QB exact netlist；
- QB parameters；
- JM1 shunt；
- exact JoSIM `.model`；
- source/load testbench；
- bias/timestep。

收到的信息：

```text
[AUTHOR_PROVIDED]
```

不自动等同：

```text
[PUBLISHED]
```

必须 time-box：

```text
发送
→ 一次 follow-up
→ 到预设期限仍无充分回复
→ 继续项目
```

回退状态：

```text
R0 / partial-R1
+
UNKNOWN list
```

不能无限等待作者。

---

## C2. Reproduction Level

统一使用：

```text
R0 = Topology Reconstruction
R1 = Published Nominal-Parameter Reconstruction
R2 = Behavioral Reproduction
R3 = Independent Full Reproduction
```

R3 定义为：

> 在预先声明的 model closure、testbench、parameter provenance、numerical settings 与 observation tolerance 下，满足全部 reproduction criteria 的独立复现。

任何 `[UNKNOWN] / [INFERRED]` 参数不会因为后续调参自动变成“论文参数”。

---

## C3. M9 后即可启动 Source / Receiver Characterization

为防止 Phase −1 变成长期阻塞：

```text
M9 METRIC_SPEC frozen
```

之后即可开始：

- W5；
- provenance；
- canonical cell characterization；
- BVM source characterization；
- receiver baseline characterization；
- benchmark design。

但正式 BQ v4 / DCSFQ_BVM candidate tuning 仍等待 M11A+B。

---

## C4. BVM Source Spec

建立：

```text
docs/research/BVM_SOURCE_SPEC_V1.md
```

它必须**引用 `METRIC_SPEC_V2`**，不能重新定义：

- windows；
- direction；
- integration；
- cluster；
- event semantics。

至少表征：

### read-0
- peak；
- width；
- ringing；
- load dependence。

### read-1
- peak；
- width；
- timing；
- repeatability；
- load dependence。

### state disturbance
- read drift；
- repeat-read；
- destructive boundary。

Thevenin/Norton 只能表述为：

> tested-range effective characterization

不能写成普适固定 BVM 内阻。

---

## C5. Receiver Characterization

分别建立：

- published-topology-compatible QB reconstruction；
- canonical/original BQ；
- canonical DCSFQ。

统一分类：

```text
NO_TRIGGER
ONE_EVENT
MULTI_EVENT
UNSTABLE
```

先得到 receiver feasible envelope，再讨论 BVM compatibility。

---

## C6. `INTERFACE_GATE_V1` 独立于 M9

在：

```text
Reference Reconstruction
+
BVM source envelope
+
receiver feasible envelope
```

有事实层之后，冻结：

```text
INTERFACE_GATE_V1
```

它回答：

> **什么结果算一个成功接口？**

至少包括：

- read-0 → 0；
- read-1 → exactly 1；
- JTL stage-1 reception；
- JTL stage-2 propagation；
- BVM state preservation；
- repeat-read；
- false-trigger boundary；
- multi-trigger boundary；
- minimum bias/load/parameter margin。

---

## C7. Held-out validation 在调参前冻结

在 candidate calibration/tuning 开始前锁定：

```yaml
calibration_set:
validation_set:
```

Validation set 包含未用于调参的：

- load；
- waveform；
- bias；
- state；
- process sample。

调参后不得替换 validation case。

---

## C8. Candidate 的目标从“成功点”改成“Operating Region”

正式比较：

- Published-QB-like reconstruction；
- BQ v4；
- DCSFQ_BVM。

统一：

- same BVM source；
- same model；
- same load policy；
- same MetricSpec；
- same Interface Gate；
- same JTL；
- same variation policy。

目标不是：

> 找一个成功参数点。

而是：

> 找一个宽、稳定、可验证的 `ONE_EVENT` region。

研究顺序：

```text
Nominal feasibility
↓
One-factor sensitivity
↓
Multi-factor operating region
↓
Held-out validation
↓
Process variation / Monte Carlo
```

---

## C9. Negative Result 必须有边界

只有声明以下内容后，失败才可能构成 scientific negative result：

- model；
- source envelope；
- load；
- parameter domain；
- metric；
- convergence；
- stopping criterion；
- tested space。

允许：

> Under model X, source envelope Y, load Z and parameter domain D, no robust operating region satisfying Gate G was identified.

禁止：

> This topology can never work.

---

# Decision D — FROZEN v1.1 是当前唯一优先协议修复

M6-001 已经真实证明：

> authorized mutable output 与 frozen input 混为一个 hash set 会制造无科学新增信息的 rework。

因此优先升级 FROZEN verifier，而不是先实现完整 Batch。

---

## D1. INPUT MANIFEST

绑定真正决定科学结果的不可变输入：

- simulator binary；
- model closure；
- input netlist；
- controls；
- MetricSpec / Semantic Lock；
- analysis implementation revision；
- source/load definition。

---

## D2. MUTABLE BINDING

对允许修改的交付物记录：

```yaml
path:
pre_image_hash:
post_image_hash:
authorization:
```

验证：

> 改动恰好属于授权集合。

---

## D3. OUTPUT MANIFEST

绑定：

- raw CSV；
- stdout/stderr；
- generated metrics；
- RESULT；
- receipt；
- evidence index。

---

## D4. Workflow Provenance 与 Scientific Provenance 分开

Scientific hash 核心关注：

- binary；
- model；
- netlist；
- source/control；
- metric implementation；
- metric spec；
- raw data。

以下通常只记录 Git commit reference：

- AGENTS；
- WORKFLOW；
- skills；
- HANDOVER；
- todo。

目的：

> “为什么允许这样做”与“这个数字怎么产生”不再使用同一 provenance 机制。

---

# Decision E — Batch 只实现 P0 最小 Pilot

M12/M5/M6 已验证的是 Lite/FROZEN 单任务流程，不代表 Batch Extension 已通过真实 Pilot。

因此第一阶段 Batch 只实现五项：

```text
1. Batch fact layer
2. canonical SEMANTIC-LOCK.yaml
3. append-only LEDGER
4. fresh-context blind FORMAL REVIEW
5. machine-generated read-only AUDIT-PACKET
```

明确延期：

- verify-batch；
- Decision Cache；
- complexity scoring；
- automatic routing；
-复杂 sampling automation。

---

## E1. 最小 Batch 结构

```text
research/tasks/<BATCH-ID>/
├── BATCH.md
├── BATCH-MANIFEST
├── subtasks/
│   └── <id>/
│       ├── SEMANTIC-LOCK.yaml
│       ├── RESULT.md
│       └── LEDGER.md
└── attempts/
    └── Axx/
        ├── FORMAL-REVIEW.md
        └── AUDIT-PACKET
```

---

## E2. `SUBTASK_READY` 只是内部状态

不能：

- close todo；
-建立 physical conclusion；
- freeze metric；
- become paper evidence；
- establish authority outside batch。

下游必须记录：

- upstream Semantic Lock hash；
- upstream snapshot；
- assumed inputs/premises。

若上游后来被质疑：

```text
STOP dependency chain
→ escalate Codex
```

---

## E3. Semantic Lock 是科研语义唯一来源

每 subtask 只有一份：

```text
SEMANTIC-LOCK.yaml
```

至少记录：

- windows；
- sign/direction；
- controls；
- thresholds；
- formulas；
- output schema；
- phase wrap policy；
- timestep/solver；
- P/V endpoint mapping；
- integration rule；
- run-ID policy；
- parameter envelope；
- frozen vs variable fields；
- claim ceiling。

其他文件只引用其 hash。

---

## E4. PRE-REVIEW 与 FORMAL REVIEW 分开

```text
Claude Execute
↓
Copilot PRE-REVIEW
↓
Claude repair
↓
stable snapshot
↓
fresh-context FORMAL REVIEW
↓
Codex final audit
```

PRE-REVIEW 的实质 finding 必须追加到 LEDGER，不能隐藏 failed attempts。

---

## E5. Fresh Formal Review 先 Blind，后看 Ledger

### Blind phase
只看：

- Contract；
- Semantic Lock；
- snapshot；
- machine evidence index；
- raw evidence；
- RESULT header。

先独立形成 falsification hypotheses。

### Compare phase
再看：

- LEDGER；
- internal repair；
- known findings。

避免 fresh context 被旧 framing 锚定。

---

## E6. Audit Packet 必须机器生成

来源：

- Git metadata；
- manifests；
- hashes；
- exit codes；
- RESULT/REVIEW headers；
- declared evidence；
- AC mapping。

不得以 executor narrative 作为事实来源。

Packet mismatch：

```text
provenance / artifact-integrity problem
```

不是：

```text
physical FAIL
```

---

# Decision F — 最终采用“三层任务模型”：80% 轻，20% 重

这是流程简化的核心。

协议中按**能力等级**定义角色，不永久绑定具体型号。

---

## Tier 1 — Routine

适用：

- file discovery；
- plotting；
- format；
-普通测试；
- manifest/hash；
- evidence indexing；
- `jj_audit.py`；
-非科学语义代码维护。

目标状态：

```text
NORMAL + LITE
```

尽量由低成本执行/验证能力完成。

不需要最高能力审计。

---

## Tier 2 — Scientific Implementation

适用：

- M7 implementation；
- source characterization implementation；
- receiver mapping；
- bounded exploratory sweep；
-复杂 debugging。

流程：

```text
Controller defines scope once
↓
Executor + PRE-REVIEW internal loop
↓
stable snapshot
↓
one final audit
```

典型：

```text
CRITICAL + LITE
```

或按任务需要 FROZEN。

---

## Tier 3 — Scientific Gate

只用于：

- M8 decisive convergence；
- M9 MetricSpec freeze；
- M11A/B；
- Interface Gate freeze；
- route verdict；
- final margin；
- paper-critical claim。

流程：

```text
pre-registration
+
CRITICAL + FROZEN
+
fresh-context review
+
high-capability final audit
+
user adoption
```

---

## F1. 协议写能力层，不写死模型名

协议使用：

```text
highest-capability reviewer
daily controller / complex reviewer
low-cost verifier
executor
independent reviewer
```

当前实际环境可以映射为现有可用模型/工具，但模型名称放在 runtime/config，而不是 scientific protocol。

这样模型更新不要求重写科研协议。

---

# 迁移计划

不能一次把全部方案写进 active protocol。

---

## Step 0 — 最后一次 Blocker-only Review

把本文件交给：

- Codex；
- Claude Code；
- Copilot。

要求他们：

> **只报告会阻止实施的 blocker，不重新讨论已经三方一致的总体方向。**

输出格式：

```text
BLOCKER
MINOR
NO_BLOCKER
```

如果没有 blocker，用户决定 `USER_ADOPTED`。

---

## Step 1 — 立即采用“无工具成本”的科研规则

先修改研究计划/ADR，不实现复杂工具：

- Study Phase 标签；
- M7A/B/C；
- M8 bounded convergence；
- M9 = MetricSpec only；
- W5B provenance；
- R0–R3；
- held-out pre-registration rule；
- M11 双子门。

这是第一批正式决策。

---

## Step 2 — W5B 立即开始，W5A 可并行

优先创建：

```text
REFERENCE_PROVENANCE.md
W5_LITERATURE_MATRIX.md
```

W5C 作者联系等用户明确授权后再发送。

---

## Step 3 — 修 FROZEN v1.1

优先于完整 Batch。

实现：

```text
INPUT MANIFEST
MUTABLE BINDING
OUTPUT MANIFEST
```

用已有 M6-001 / M6-002 作为 regression cases。

验收目标：

> M6-001 类型的 authorized mutable file 不再导致 verifier 误判，同时真正 frozen input drift 仍能被捕获。

---

## Step 4 — 实现 Batch P0

只实现：

- fact layer；
- Semantic Lock；
- Ledger；
- blind review；
- Audit Packet prototype。

不实现其他 backlog。

---

## Step 5 — 首个真实 Batch Pilot：M7A/B/C

M7A/B/C：

```text
CALIBRATION
CRITICAL + LITE
```

Claude + Copilot 内部修复，稳定后 FORMAL REVIEW。

记录：

- internal findings count；
- escaped findings count；
- Codex context reconstruction time；
- audit depth；
- false positive；
- evidence loss；
- process friction。

---

## Step 6 — M8 单独 FROZEN，但与 M7 合并审计会话

M8：

```text
CALIBRATION
CRITICAL + FROZEN
```

合同独立。

可以和 M7 在同一次 Codex 审计会话连续处理，以减少上下文重建。

---

## Step 7 — M9 / M10 / M11

顺序固定：

```text
M9
METRIC_SPEC freeze
↓
M10
metrics_v2 reconstruction
↓
M11A
Measurement Calibration Baseline
↓
M11B
Scientific Reconstruction Baseline
```

在 M9 后，W5 / source / receiver characterization 可以并行推进。

---

## Step 8 — 冻结 Interface Gate + Validation Set

在 candidate tuning 之前冻结：

```text
INTERFACE_GATE_V1
+
calibration_set
+
held_out_validation_set
```

---

## Step 9 — 才开始 BQ v4 / DCSFQ_BVM 正式候选路线

研究顺序：

```text
Nominal feasibility
↓
mechanism experiment
↓
bounded optimization
↓
operating region
↓
held-out validation
↓
process variation
↓
JTL/T1
↓
CONFIRMATORY FROZEN
```

---

# Batch Pilot 的通过标准

Batch P0 只有在以下条件全部满足后，才允许升级为正式协议组成部分：

1. `SEMANTIC-LOCK` 没有 silent drift；
2. failed/reworked attempts 可发现，不被 PRE-REVIEW 隐藏；
3. fresh reviewer 能在不看 Ledger 的情况下独立构造有效 falsification hypotheses；
4. Audit Packet 与 raw evidence 一致；
5. downstream dependency invalidation 能正确停止；
6. Codex context reconstruction 明显减少；
7. Codex 科学审计深度没有下降；
8. 没有 evidence/provenance loss；
9. 至少一个真实 defect 被 PRE/FORMAL review 捕获，或证明该机制对现有错误模式有效；
10. 实际总摩擦低于旧单任务全链。

如果不满足：

> 保留研究方法改进，但 Batch Extension 不升级为正式流程。

---

# 明确延期的事项

以下全部进入 backlog，不作为当前实施前提：

```text
verify-batch
Decision Cache
complexity scoring
automatic model routing
automatic scientific decision
deep sampling automation
loop_audit full automation
interface_margin full automation
large Monte Carlo framework
```

原则：

> **先证明需要，再自动化。**

---

# 当前立即行动清单

用户现在只需要做以下事情：

```text
1. 把本文件发给 Codex / Claude / Copilot 做 blocker-only review
2. 若无 blocker，明确 USER_ADOPTED
3. 先让 Codex 更新研究计划/ADR，不立刻签发 M7
4. 启动 W5B REFERENCE_PROVENANCE
5. 启动 FROZEN v1.1 设计与 regression
6. 实现 Batch P0 最小机制
7. 准备 M7A/B/C Batch Pilot
8. 用户决定恢复科研执行后，再正式签发 M7
```

---

# 最终科研依赖图

```text
                          W5A Literature
                          W5B Provenance
                          W5C Author Inquiry
                               │
                               │
M7A ─┐                         │
M7B ─┼→ M8 → M9 → M10 → M11A │
M7C ─┘             │           │
                   │           │
                   ├→ BVM Source Characterization
                   ├→ Receiver Characterization
                   └→ Reference Reconstruction
                               │
                               └────→ M11B
                                       │
                                       ▼
                            Freeze INTERFACE_GATE_V1
                            Freeze held-out validation
                                       │
                       ┌───────────────┼───────────────┐
                       ▼               ▼               ▼
                Published-QB-like     BQ v4       DCSFQ_BVM
                       └───────────────┼───────────────┘
                                       ▼
                              Operating Region
                                       ▼
                              Held-out Validation
                                       ▼
                               Process Variation
                                       ▼
                                  JTL / T1
                                       ▼
                           CONFIRMATORY FROZEN
                                       ▼
                                     Paper
```

---

# 最终原则

这个项目后续不再以：

> “怎样让 AI 更快地产生更多仿真”

作为优化目标。

真正目标是：

> **用尽可能轻的协作成本，让每一次昂贵仿真都回答一个已经定义清楚、参数来源明确、可证伪、可复现的问题。**

最终系统应当达到：

```text
日常工作：
轻量、快速、低成本

科研校准：
严格但有界

科学 Gate：
少量、独立、FROZEN、可审计
```

如果 BQ v4 / DCSFQ_BVM 最终成功，则形成 robust BVM→SFQ interface。

如果二者最终失败，只要已经建立：

- reference reconstruction boundary；
- source/receiver envelope；
- bounded parameter domain；
- convergence；
- unified Gate；
- held-out validation；
- failure mechanism / compatibility boundary；

仍然可以形成有效的 bounded scientific result，而不是“试了很多参数没成功”。

这就是本项目最终应采用的研究方法与协作方向。
