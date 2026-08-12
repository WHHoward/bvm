---
title: JoSIM × BVM 研究流程与 Batch 协作机制整合修改提案
document_type: discussion_proposal
status: DISCUSSION_DRAFT
date: 2026-08-12
authority: advisory_only
intended_reviewers:
  - Codex
  - Claude Code
  - GitHub Copilot
project: WHHoward/bvm
---

# JoSIM × BVM 研究流程与 Batch 协作机制整合修改提案

> **用途**：供 Codex / Claude Code / GitHub Copilot 三方讨论。  
> **状态**：讨论稿，不修改当前 active protocol，不授权任何科研任务。  
> **目标**：把 WORKFLOW-lite 2.0 Batch Extension 的最终讨论结果，与 2026-08-11 晚间形成的科研方法改进方案合并为一套更统一的项目演进计划。
>
> 核心原则：
>
> 1. **不通过降低科学审计强度来省成本，只通过降低重复上下文、机械复核、无效往返和不必要的高阶模型使用来省成本。**
> 2. **协作流程服务于科研方法，而不是让科研方法服从协作流程。**
> 3. **下一阶段最大的风险，是参数 provenance、模型/reconstruction 不确定性、探索与确认混用，以及用已校准的尺子精确优化一个尚未被定义清楚的参考系统。**
> 4. **Phase −1 的成果必须保留；进入 BQ v4 / DCSFQ_BVM 之前，需要增加 Reference Reconstruction + Source/Receiver Characterization 层。**
> 5. **Batch 机制先做窄 Pilot，不能一次把全部自动路由、verify-batch、Decision Cache 等升级为权威机制。**

---

# 1. 当前背景与问题定义

截至 2026-08-12：

- M4 已完成：修正 raw phase rad → turns，停止把 activity samples 称为 event；
- M5 已完成：pre/activity/post window、显式方向、zero-input control、activity clustering 已实现并通过 review；
- M6 已完成：same-JJ `P/V`、same direction、same sampled endpoints、actual-time integration 的 phase–voltage-area cross-check 已获得 FROZEN 可验证证据；
- M7–M11 尚未完成；
- BQ v4 与 DCSFQ_BVM 仍被 Phase −1 阻塞；
- W5 文献空白系统检索尚未完成；
- WORKFLOW-lite 2.0 已经过 M12/M5/M6 的真实 Pilot；
- Batch Extension + Cost Optimization 已完成多方审阅，但仍是待协议化方案。

当前需要解决两个系统性问题：

## 1.1 科研方法问题

现有流程仍偏向：

```text
Measurement repair
  ↓
BQ v4 / DCSFQ_BVM
  ↓
System Gate
```

但现在已经确认：

- published BVM 与本项目 reconstruction 不完全等价；
- published BVM-modified QB 参数公开不足；
- original BQ 与 BVM-modified QB 不是同一对象；
- BVM source behavior 与 receiver operating behavior 必须独立表征；
- 如果直接在 reconstruction 上调参，可能“非常精确地优化了错误参考对象”。

因此需要插入：

```text
Reference Provenance
Reference Reconstruction
BVM Source Characterization
Receiver Characterization
Unified Interface Benchmark
```

## 1.2 协作/成本问题

当前单任务闭环的优点是审计强，但可能出现：

- Codex 重复读取大量机械 evidence；
- M5 类实现缺陷需要多轮 Codex 接触；
- mailbox / receipt / review 产生较多上下文；
- FROZEN 因合同设计错误而要求科学上无新增信息的重跑；
- 高价值模型被用于机械验证；
- 相邻小任务重复构造相同上下文。

Batch Extension 的方向正确，但必须防止：

- batch 内错误污染下游；
- PRE-REVIEW 与 FORMAL REVIEW 共享 framing；
- Semantic Lock 多份复制后漂移；
- Audit Packet 变成 executor narrative；
- “lowest sufficient assurance” 被误用于科学 Gate；
- 减少 mailbox chatter 后 status 不可发现。

---

# 2. 提议的双轴架构

## 2.1 科研阶段轴（Study Phase）

```yaml
study_phase:
  EXPLORATORY
  CALIBRATION
  CONFIRMATORY
```

### EXPLORATORY
允许根据结果调整下一组实验、Debug、bounded sweep、形成 hypothesis。  
限制：不能直接成为 final Gate / paper-critical final number，不能事后补票成为 CONFIRMATORY。

### CALIBRATION
用于 measurement method、metric regression、timestep convergence、tolerance establishment。典型任务：M6/M7/M8/M9。

### CONFIRMATORY
用于 final interface Gate、route decision、final margin、paper-critical claim。  
要求 hypothesis / input / metric / window / control / threshold / parameter domain 在 run 前冻结，并使用 FROZEN + fresh-context independent review。

## 2.2 协作保证轴（Assurance Axis）

继续使用：

```yaml
risk:
  NORMAL
  CRITICAL

evidence_mode:
  LITE
  FROZEN
```

组合成：

```text
Study Phase × Risk × Evidence Mode
```

示例：

| Task | Study Phase | Risk | Evidence |
|---|---|---|---|
| 普通脚本重构 | EXPLORATORY | NORMAL | LITE |
| M7 synthetic tests | CALIBRATION | CRITICAL | LITE |
| M8 decisive convergence | CALIBRATION | CRITICAL | FROZEN |
| M9 MetricSpec freeze | CALIBRATION | CRITICAL | FROZEN |
| BQ 参数探索 | EXPLORATORY | NORMAL/CRITICAL | LITE |
| final interface Gate | CONFIRMATORY | CRITICAL | FROZEN |

---

# 3. 研究主线改为七阶段结构

```text
Stage A  Measurement Calibration
         M7 → M8 → M9
              │
              ├───────────────┐
              │               │
Stage B       │          Literature / Provenance
Reference     │          W5 + Author Inquiry
Reconstruction│               │
              └───────┬───────┘
                      ↓
Stage C  BVM Source Characterization
                      ↓
Stage D  Receiver Characterization
        Published-QB Reconstruction / canonical BQ / canonical DCSFQ
                      ↓
Stage E  Unified Interface Benchmark
        Published-QB-like / BQ v4 / DCSFQ_BVM
                      ↓
Stage F  Margin / Robustness / Held-out Validation
                      ↓
Stage G  JTL / T1 / End-to-End CONFIRMATORY FROZEN
                      ↓
                    Paper
```

---

# 4. Stage A：修改 M7 / M8 / M9

## 4.1 M7 拆成三类验证

### M7A — Mathematical Unit Tests
真正拥有数学 ground truth：

- synthetic phase step；
- synthetic zero trace；
- synthetic two-transition trace；
- synthetic voltage pulse with known area；
- sign reversal；
- boundary-window behavior。

目标：验证公式、单位、window、cluster semantics。  
Evidence：`CRITICAL + LITE`

### M7B — Canonical Circuit Validation
使用独立、已充分理解的标准 SFQ/JTL case，例如 JoSIM canonical JTL。  
目标：验证 metric 在真实 Josephson transient circuit 上正确。  
Evidence：`CRITICAL + LITE`

### M7C — Historical Regression Characterization
使用 DCSFQ 300 µA、BQ v4 六周期与 preserved raw data。  
目标：检查新 pipeline 是否稳定复现人工重算数字。  
禁止：把 M7C 当作 DCSFQ/BQ 本身物理正确的 ground truth。  
Evidence：`CRITICAL + LITE`

## 4.2 M8 改成真正的 convergence procedure

最低起点：

```text
0.1 ps → 0.05 ps → 0.025 ps
```

但 completion criterion 应是：

> successive refinement 后，预注册的关键 observables 达到稳定；若 0.025 ps 尚未稳定，则继续 refinement。

建议观测：

- phase turns；
- voltage-area turns；
- phase-area residual；
- event timing；
- pulse width；
- downstream count（如适用）。

M8 decisive evidence：`CALIBRATION + CRITICAL + FROZEN`

## 4.3 M9 拆成 Measurement Spec 与 Interface Gate

### `METRIC_SPEC_V2.md`
只冻结“怎么测”：

- phase normalization；
- same-JJ P/V mapping；
- windows；
- control subtraction；
- clustering；
- voltage-area integration；
- sign convention；
- numerical tolerance；
- timestep convergence rule。

### `INTERFACE_GATE_V1.md`
在 Reference Reconstruction / Source Characterization 后冻结“什么叫接口成功”：

- read-0 → 0；
- read-1 → exactly 1；
- JTL reception / propagation；
- BVM state disturbance；
- bias/load/parameter margin；
- repeat-read；
- false/multi-trigger policy。

原则：**测量尺与产品验收标准彻底分离。**

---

# 5. Stage B：W5 与 Parameter Provenance 前移

W5 不应继续只在“论文文档阶段”。

## W5A — Prior-art Boundary
记录：

- query；
- database；
- date；
- closest prior art；
- already does；
- does not report；
- allowed novelty wording。

W5 完成前禁止使用“first / no prior work / literature blank confirmed”。

## W5B — Reproduction Provenance

建议新增：

`docs/research/REFERENCE_PROVENANCE.md`

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

至少审计：

- BVM topology / Ic / L / JM1 shunt / JJ model / testbench；
- published modified-QB topology / Ic/L/R/bias/load；
- original BQ；
- project BQ v2/v4；
- canonical DCSFQ / DCSFQ_BVM。

## W5C — Author Inquiry

向 BVM 作者询问：

- modified QB exact netlist；
- QB parameters；
- JM1 shunt；
- exact JoSIM `.model`；
- source/load testbench；
- bias/timestep。

作者信息标 `[AUTHOR_PROVIDED]`，不自动等同 `[PUBLISHED]`。

---

# 6. Reference Reconstruction Level

以后不只写 reproduced / not reproduced：

```text
R0 = Topology Reconstruction
R1 = Published Nominal-Parameter Reconstruction
R2 = Behavioral Reproduction
R3 = Full Reproducibility
```

至少记录：

- BVM；
- original BQ；
- published BVM-modified QB；
- canonical DCSFQ；
- JTL；
- T1。

参数缺失时必须明确 `R0 / partial-R1`，不能把项目参数冒充论文参数。

---

# 7. Stage C：BVM Source Characterization

在 BQ v4 / DCSFQ_BVM 优化前，先建立：

`docs/research/BVM_SOURCE_SPEC_V1.md`

至少包含：

### read-0 envelope
- peak current；
- width；
- ringing；
- baseline；
- source-load dependence。

### read-1 envelope
- peak current；
- width；
- timing；
- repeatability；
- load dependence。

### state disturbance
- local drift；
- repeat-read；
- destructive boundary。

### effective source characterization
允许 multi-load Thevenin/Norton-like fit，但只能表述为：

> measured-range effective characterization

不能表述成固定、普适“BVM 内阻”。

---

# 8. Stage D：Receiver Characterization

先分别建立：

## Published-QB / canonical BQ Receiver Map
## Canonical DCSFQ Receiver Map

统一输出分类：

```text
NO_TRIGGER
ONE_EVENT
MULTI_EVENT
UNSTABLE
```

变量：

- input stimulus；
- bias；
- load；
- Ic；
- shunt；
- relevant L。

目的：

> 先知道 receiver feasible envelope，再谈 BVM compatibility。

---

# 9. JJ / Loop Physical Preflight 正式化

## JJ Preflight

| JJ | Role | Ic | RN | R0 | C | Rsh | Reff | βc estimate | provenance |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|

βc 只作为 design preflight，不作为 full transient verdict。

## Loop Preflight

记录：

- loop path；
- L；
- relevant Ic；
- chosen βL convention；
- expected storage / circulating-current role；
- intended switching / non-switching JJ。

必须写清 βL convention。

---

# 10. Stage E：Unified Interface Benchmark

Phase −1 + Source/Receiver characterization 完成后，再比较：

- Candidate A：Published-topology-compatible QB reconstruction
- Candidate B：BQ v4
- Candidate C：DCSFQ_BVM

统一：

- same BVM source；
- same JJ model；
- same source/load；
- same timestep policy；
- same MetricSpec；
- same Interface Gate；
- same downstream JTL；
- same variation policy。

核心指标：

- read-0 false trigger；
- read-1 one-event；
- multi-event boundary；
- JTL stage-1 / stage-2；
- BVM state disturbance；
- bias/load/parameter margin；
- timestep stability；
- latency；
- JJ/component count。

---

# 11. Candidate Route 启动边界

与 Batch 最终方案保持一致：

> **Route C / D 正式候选参数执行继续 BLOCKED UNTIL M11。**

M11 前允许：

- literature / provenance / author inquiry；
- canonical cell study；
- read-only topology anatomy；
- JJ/loop audit；
- BVM source characterization（前提是 measurement definition 已允许）；
- receiver baseline characterization；
- benchmark design。

M11 前不允许：

- 把新 BQ v4 / DCSFQ_BVM 参数结果升级为 route verdict；
- 用 exploratory route run 形成 final scientific evidence。

---

# 12. Stage F：从“找成功点”改为“找 Operating Region”

区分：

## Mechanism Experiment
单变量：Rsh / one Ic / one L / bias / load。  
目的：识别因果机制。

## Optimization Experiment
在机制理解后使用 bounded grid / fractional factorial / Latin hypercube / 必要时 Bayesian optimization。

目标：

> 找宽的 `ONE_EVENT` operating region，而不是一个偶然成功点。

建议形成：

```text
Ibias × Iinput
Ibias × load
Ic scale × load
```

区域分类：

```text
NO_TRIGGER
ONE_EVENT
MULTI_EVENT
STATE_DISTURB
UNSTABLE
```

---

# 13. Held-out Validation

不能用同一批 waveform：

```text
调参
+
证明 robust
```

建议划分：

### Calibration Set
用于 tuning / mechanism。

### Validation Set
包含未参与调参的：

- load；
- waveform；
- bias；
- state；
- process sample。

final candidate 必须在 held-out condition 上确认。

---

# 14. Robustness 四层递进

```text
L1 Nominal feasibility
  ↓
L2 One-factor sensitivity
  ↓
L3 Multi-factor operating region
  ↓
L4 Process variation / Monte Carlo
```

不要对未成熟 topology 过早做高成本 Monte Carlo。

---

# 15. Negative Result Policy

有效 negative result 必须声明：

- model；
- source envelope；
- load；
- parameter domain；
- metric；
- convergence；
- stopping criterion；
- tested space。

允许：

> Under model X, source envelope Y, load Z and predeclared parameter domain D, no robust single-event operating region satisfying Gate G was identified.

禁止有限 sweep 推成：

> This topology can never work.

---

# 16. Batch Extension：最小正式结构

第一版只引入：

```text
research/tasks/<BATCH-ID>/
├── BATCH.md
├── BATCH-MANIFEST.*
├── subtasks/
│   ├── <subtask-id>/
│   │   ├── SEMANTIC-LOCK.yaml
│   │   ├── RESULT.md
│   │   └── REVIEW.md / LEDGER entries
│   └── ...
└── attempts/
    └── Axx/
        ├── batch RESULT
        ├── FORMAL REVIEW
        └── generated AUDIT-PACKET
```

`SUBTASK_READY` 只能表示 batch-internal readiness，不能 close todo、建立 physical conclusion、成为 paper evidence 或 freeze metric。

若已被 downstream 使用的 subtask 后来被重新质疑：

> **立即停止 dependency chain 并升级 Codex。**

---

# 17. 每个 Subtask 只有一份 Canonical Semantic Lock

`SEMANTIC-LOCK.yaml` 记录：

- windows；
- directions；
- thresholds；
- controls；
- formulas；
- output schema；
- parameter envelope；
- metric version；
- claim ceiling。

其他文件只引用 lock hash，不复制 scientific semantics。

### FROZEN
immutable。

### LITE
semantic change → 显式 revision + new snapshot，不覆盖旧 lock。

---

# 18. PRE-REVIEW 与 FORMAL REVIEW 分离

```text
Claude Execute
    ↓
Copilot PRE-REVIEW
    ↓
Claude Repair
    ↓
Stable Delivery Snapshot
    ↓
Fresh-context FORMAL REVIEW
    ↓
Codex Final Audit
```

PRE-REVIEW 的关键 finding 写入 append-only `LEDGER`。

---

# 19. Fresh-context FORMAL REVIEW 初始 Blind to Ledger

### Phase 1 — Blind Review
先只看：

- Batch Contract；
- Semantic Lock；
- delivery snapshot；
- machine-generated evidence index；
- raw evidence。

先独立形成 falsification hypotheses。

### Phase 2 — Compare Ledger
之后再读取：

- PRE-REVIEW finding；
- repair history；
- known issues。

目的：避免 fresh context 继续继承 executor framing。

---

# 20. Audit Packet 必须机器生成

来源：

- Git metadata；
- snapshot；
- manifests；
- hashes；
- logs；
- RESULT/REVIEW headers；
- declared evidence。

禁止以 executor narrative 作为 factual source。

Packet mismatch：

> provenance / artifact-integrity problem

不是 physical FAIL。

raw evidence 始终直接可访问。

---

# 21. FROZEN Verifier：Input / Mutable / Output 三段式

M6-001 已经证明当前 FROZEN 合同容易把 authorized mutable file 和 frozen input 混淆。

建议：

## INPUT MANIFEST
冻结：

- simulator binary；
- model closure；
- input netlist；
- controls；
- metric spec；
- analysis code revision；
- semantic lock。

## MUTABLE DELIVERY BINDING
记录：

```text
authorized path
pre-image hash
post-image hash
```

## OUTPUT MANIFEST
绑定：

- raw CSV；
- stdout/stderr；
- generated metrics；
- RESULT；
- receipt；
- audit packet。

这样避免科学上无新增信息、只为修合同而重跑。

---

# 22. Scientific Provenance 与 Workflow Provenance 分离

FROZEN 科学核心 hash：

- simulator；
- model；
- netlist；
- source/control；
- metric implementation；
- metric spec；
- raw data。

AGENTS / WORKFLOW / skills / HANDOVER / todo 通常只需 Git commit reference。

原则：

> “为什么允许做”与“数字怎么产生”使用不同 provenance 层。

---

# 23. Deterministic Sampling 边界

如非 final batch 使用 deterministic sampling：

- seed 必须在 Batch Contract 签发时固定；
- 可由 contract hash 派生；
- 不得由 delivery commit 派生。

Sampling 永不替代：

- final physical Gate；
- metric freeze；
- route decision；
- paper-critical claim；
- convergence raw review；
- independent recomputation。

---

# 24. Scientific ADR 生命周期

```text
PROPOSED
  ↓
CODEX_AUDITED
  ↓
USER_ADOPTED
  ↓
SUPERSEDED
```

Codex audit 不自动：

- freeze metric；
- adopt route；
- authorize paper claim。

建议用户角色称为：

> **Final Scientific Decision Owner**

而不是把“科学 authority”理解为物理真理由角色决定。

---

# 25. Lowest Sufficient Assurance 只用于机械层

正式措辞建议：

> **Use the lowest-cost mechanical assurance tier that still satisfies the task's predeclared risk and evidence mode.**

可降低：

- discovery；
- routine checks；
- formatting；
- manifest generation；
- repetitive regression；
- evidence indexing。

不可降低：

- CRITICAL/FROZEN raw evidence；
- convergence；
- semantic freeze；
- independent recomputation；
- final Gate；
- route decision；
- paper claim。

---

# 26. Batch 状态必须可发现

可以减少 mailbox chatter，但至少保留机器可读状态：

```text
ISSUED
RUNNING
BLOCKED
SUBTASK_READY
BATCH_READY
FORMAL_REVIEW
CODEX_AUDIT
CLOSED
```

至少 task issuance、BLOCKED、BATCH_READY、scientific-Gate readiness 必须 discoverable。

---

# 27. 第一个真实 Batch Extension Pilot

建议：

```text
Batch B
├── M7A
├── M7B
└── M7C
```

M8 与该 Batch 可以**合并 Codex 审计会话**，但不强行共用 evidence contract：

- M7：CRITICAL + LITE；
- M8 decisive convergence：CRITICAL + FROZEN；
- M9：独立 CRITICAL + FROZEN；
- M9 永不 batch-internal close；
- M11 永不 batch-internal close；
- final system Gate 永不由 sampling / SUBTASK_READY 代替。

---

# 28. Pilot 实施顺序

## P0 — 第一阶段
1. Batch fact layer；
2. append-only manifest / ledger；
3. fresh-context blind formal review；
4. minimal canonical Semantic Lock；
5. read-only generated Audit Packet prototype。

## P1 — 一个真实 Batch Pilot 后
如果证明：

- context reconstruction 减少；
- Codex 仍能发现关键问题；
- raw evidence 可追；
- failed attempts 没有被隐藏；

再考虑：

- `verify-batch`；
- Decision Cache；
- complexity scoring；
- automatic routing；
- deeper sampling automation。

禁止未经 Pilot 就让新自动化成为科研 authority。

---

# 29. 文档体系简化

Pilot 结束后建议统一三层当前权威：

```text
AGENTS.md
  = repository-wide invariants

research/WORKFLOW.md
  = canonical collaboration protocol
  + Batch Extension
  + FROZEN backend

memory/project-todo.md
  = current research dependency/state
```

其他 consensus / proposal / review / old workflow version 归档为设计历史，不再作为默认必读。

`HANDOVER.md` 缩短为：

- trusted current state；
- blockers；
- immediate next actions；
- superseded warnings。

---

# 30. 历史文档不机械重写

建议调整 W3：

不要把所有旧日志正文改写成今天的理解。

改为：

- 保留历史；
- `SUPERSEDED` banner；
- central correction table；
- machine-readable `metrics_v2`；
- 新 paper evidence chain 只引用 current accepted evidence。

---

# 31. AI 角色

## Terra
Planner / batch contract / normal final audit / semantic risk。

## Sol XHigh
只处理：
- M9；
- M11；
- major route decision；
- difficult physical ambiguity；
- paper-critical claim；
- expensive-to-reverse architecture。

## Luna
- discovery；
- evidence indexing；
- mechanical checks；
- repetitive regression；
- audit packet consistency。

## Claude Code + DeepSeek Flash
- implementation；
- experiment execution；
- bounded sweep；
- test/script；
- preflight；
- RESULT；
- repair loop。

## Copilot
- PRE-REVIEW；
- adversarial local review；
- contradiction finding；
- independent second look。

---

# 32. Reviewer Independence 分成两种

```yaml
execution_independence:
  INDEPENDENT | CO_EXECUTED

cognitive_independence:
  FRESH_CONTEXT | CONTINUITY
```

### Execution independence
是否修改过 execution artifacts。

### Cognitive independence
是否参与 task planning / PRE-REVIEW / prior mechanism discussion。

final milestone review 优先 `FRESH_CONTEXT`。

---

# 33. AI 物理主张纪律

任何 Agent 提出：

- “该 shunt 会保持过阻尼”
- “BJL1 是根因”
- “该参数证明 receiver 不可行”

必须附：

```text
MODEL
FORMULA
NUMERICAL SUBSTITUTION
UNITS
ASSUMPTIONS
FALSIFICATION TEST
```

否则默认：

`HYPOTHESIS`

---

# 34. 推荐新增文件

## 第一优先级

```text
docs/research/REFERENCE_PROVENANCE.md
SEMANTIC-LOCK.yaml
Batch fact layer
generated Audit Packet prototype
scripts/jj_audit.py
```

## 第二优先级

```text
docs/research/REPRODUCTION_LEVELS.md
docs/research/BVM_SOURCE_SPEC_V1.md
docs/research/INTERFACE_GATE_V1.md
docs/research/INTERFACE_BENCHMARK.md
docs/research/W5_LITERATURE_MATRIX.md
scripts/source_envelope.py
```

## 后续

```text
scripts/loop_audit.py
scripts/interface_margin.py
verify-batch
Decision Cache
automatic routing
```

避免一次建立过多新流程。

---

# 35. Todo 依赖建议

建议研究依赖变成：

```text
M7A/B/C
  ↓
M8
  ↓
M9 METRIC_SPEC freeze
  ↓
M10 historical recomputation
  ↓
Measurement Calibration Baseline
  ↓
Reference Reconstruction
  +
BVM Source / Receiver Characterization
  ↓
INTERFACE_GATE_V1 freeze
  ↓
M11 Scientific Reconstruction Baseline
  ↓
BQ / DCSFQ candidate routes
```

需要三方讨论：

> M11 是否拆成：
>
> - `M11A Measurement Calibration Baseline`
> - `M11B Scientific Reconstruction Baseline`
>
> 还是保留 M11 一个编号、增加两个 sub-gate。

---

# 36. 需要三方重点讨论的依赖冲突

Batch 最终方案要求：

> Route C/D BLOCKED UNTIL M11。

科研方法要求：

> Reference Reconstruction / Source Characterization 应早于 candidate tuning。

建议边界：

### M11 前允许
- W5；
- provenance；
- author inquiry；
- canonical cell characterization；
- BVM source characterization；
- receiver baseline characterization；
- JJ/loop audit；
- benchmark design。

### M11 后允许
- BQ v4 candidate parameter exploration；
- DCSFQ_BVM candidate parameter exploration；
- route comparison；
- optimization；
- route verdict。

请三方判断：

> 这个边界是否能同时保持 Batch 科学防线，又避免 Phase −1 变成长期研究阻塞。

---

# 37. 十条不可妥协原则

1. Measurement definition 与 Interface success Gate 分开。
2. Exploratory 结果不能事后补票成为 Confirmatory。
3. Published / Inferred / Designed / Tuned 参数永不混写。
4. local JJ evidence 不能直接升级成 downstream/system evidence。
5. M8 convergence 不能只看 PASS label 稳定。
6. M9/M11/final Gate 不允许 batch-internal closure。
7. Fresh-context reviewer 先 blind review，再看 Ledger。
8. Semantic Lock 单一来源，不多处复制科研语义。
9. 省成本只能省机械保障，不能省 CRITICAL/FROZEN 科学证据。
10. topology failure 只有在 bounded model/parameter domain 下才形成 negative scientific result。

---

# 38. 给 Codex 的讨论问题

1. 是否同意 `Study Phase × Risk × Evidence Mode` 三维语义而不新增重型流程？
2. M7A/B/C + M8 的 batch/audit 边界怎样设计最合理？
3. M9 是否应只冻结 measurement semantics？
4. `INTERFACE_GATE_V1` 应在哪个时间点冻结？
5. FROZEN input/mutable/output manifest 怎样修改才能彻底避免 M6-001 类缺陷？
6. 何时正式结束 WORKFLOW-lite Pilot 并同步权威文件？
7. M11 是否需要拆 Measurement Baseline / Scientific Reconstruction Baseline？

# 39. 给 Claude Code 的讨论问题

1. Batch fact layer / Semantic Lock / Ledger 的最小实现是什么？
2. 如何自动生成 narrow Audit Packet 而不复制 narrative？
3. `jj_audit.py` 哪些字段能可靠机械解析，哪些必须人工 role annotation？
4. BVM Source Spec 怎样用最少实验得到有效 envelope？
5. 当前执行成本主要浪费在 context、重复 read、review、run 还是文档？
6. 如何保证 PRE-REVIEW repair 不隐藏真实 failed attempts？

# 40. 给 Copilot 的讨论问题

1. Blind formal review 的最小 evidence set 是什么？
2. 如何防止 M7 historical regression 形成 circular validation？
3. `SEMANTIC-LOCK.yaml` 还缺哪些容易漂移的科研语义？
4. 如何审计 parameter provenance？
5. 如何审查 bounded negative result 是否偷换成 universal impossibility？
6. Batch 内哪些错误最可能污染下游但又最容易被 PRE-REVIEW 漏掉？

---

# 41. 推荐决策顺序

## Decision 1 — Research Method
先确定：

- M7 split；
- M8 convergence；
- M9 MetricSpec-only；
- W5/provenance early；
- Reference Reconstruction；
- Source/Receiver characterization；
- Interface Gate separation。

## Decision 2 — Batch Minimal Extension
确定：

- Batch fact layer；
- Semantic Lock；
- Ledger；
- blind Formal Review；
- Audit Packet。

## Decision 3 — FROZEN Repair
确定：

- input manifest；
- mutable delivery binding；
- output manifest。

## Decision 4 — Pilot
使用：

```text
M7A/B/C
+
M8 audit session
```

作为首个真实 Batch Extension Pilot。

## Decision 5 — Protocol Consolidation
Pilot 成功后：

- WORKFLOW-lite → canonical WORKFLOW；
- 同步 AGENTS / CLAUDE_EXECUTOR；
- discussion docs 归档；
- 再考虑 verify-batch / Decision Cache / automatic routing。

---

# 42. 推荐的近期执行顺序

```text
现在
│
├─ 三方审阅本提案
│
├─ W5A/B/C 开始
│   ├─ literature matrix
│   ├─ provenance
│   └─ author inquiry
│
├─ WORKFLOW-lite Pilot Exit Review
│
├─ Batch P0 最小实现
│   ├─ fact layer
│   ├─ semantic lock
│   ├─ blind review
│   └─ audit packet prototype
│
├─ M7A/B/C
│
├─ M8 FROZEN convergence
│
├─ M9 METRIC_SPEC freeze
│
├─ M10 historical recomputation
│
├─ Measurement Calibration Baseline
│
├─ Reference Reconstruction
├─ BVM Source Characterization
├─ Receiver Characterization
│
├─ Freeze INTERFACE_GATE_V1
│
├─ M11 Scientific Reconstruction Baseline
│
├─ BQ / DCSFQ routes
│
├─ operating-region study
├─ held-out validation
├─ process variation
│
├─ JTL / T1
│
└─ CONFIRMATORY FROZEN paper evidence
```

---

# 43. 结论

本提案不建议推翻 WORKFLOW-lite，也不建议放松 Phase −1。

建议做的是：

> **让 Phase −1 之后的科研路线真正转向 model-driven、reproducible、falsifiable computational research；让 Batch Extension 专门减少机械开销，而不进入 scientific semantics 的裁决层。**

项目下一阶段应该从：

```text
“怎样更快让 AI 多跑一些实验”
```

转成：

```text
“怎样保证每一次大规模实验都在回答一个已经定义清楚、可证伪、参数来源明确的问题”
```

如果最终：

```text
BQ v4 FAIL
DCSFQ_BVM FAIL
```

仍然可以形成：

- published reconstruction boundary；
- BVM source specification；
- receiver compatibility map；
- operating-region analysis；
- bounded negative result；
- next-generation interface requirements。

如果其中一条路线成功，则目标应是：

> **在统一 MetricSpec、统一 Source/Load、统一 JTL Gate、统一 variation policy 下，经 held-out validation 和 CONFIRMATORY FROZEN evidence 支持的 robust BVM→SFQ interface。**

这应成为后续科研与协作的共同目标。
