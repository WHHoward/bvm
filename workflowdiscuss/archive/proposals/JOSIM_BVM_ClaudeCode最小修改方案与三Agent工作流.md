# JoSIM × BVM：Claude Code 最小修改方案与三 Agent 实际工作流

> **用途**：交给 Claude Code 读取并据此实施项目的最低必要修改，同时作为用户日常使用 Codex / Claude Code / Copilot 的操作手册。  
> **原则**：停止继续设计工作流；只保留提高科学严谨性的规则，协作流程尽量简化，立即恢复科研推进。  
> **当前状态**：M4 / M5 / M6 已完成；M6 已获得有效 FROZEN 审计并 `ACCEPTED`。M7–M11 未完成。BQ v4 / DCSFQ_BVM 的正式路线判定继续等待 Phase −1 完成。  
> **重要边界**：本文件不要求实现完整 Batch P0、verify-batch、Decision Cache、自动路由或其它工作流自动化。它们全部降为 backlog，不能阻塞科研。

---

# 1. Claude Code 的总体任务

Claude Code 现在不要继续扩展协作协议。

本轮只做两类事情：

1. **把已经达成共识的科研方法规则同步到最低必要的项目文件；**
2. **准备并执行下一科研任务 M7。**

目标不是让仓库拥有“最完整的 AI 工作流”，而是：

> **让 Claude 能持续快速执行，Copilot 能低成本发现错误，Codex 只在真正需要计划和科学审计时介入。**

---

# 2. 明确不做的事情

以下全部暂时不实现，不得作为 M7 的前置条件：

```text
完整 Batch P0
verify-batch
Decision Cache
complexity scoring
automatic routing
复杂 Audit Packet 系统
自动 Scientific ADR 系统
大规模工作流重构
FROZEN v1.1 schema 大改
```

FROZEN v1.1 的 `input / mutable / output manifest` 是合理 future improvement，但当前继续使用 M6-002 已验证可工作的 FROZEN 模式即可。

未来若再次出现显著合同摩擦，再单独处理。

---

# 3. 现在只保留六条科研规则

## 3.1 Study Phase

每个科研任务声明：

```yaml
study_phase: EXPLORATORY | CALIBRATION | CONFIRMATORY
```

### EXPLORATORY

允许：

- Debug；
- parameter sweep；
- topology anatomy；
- mechanism hypothesis；
- 根据结果改变下一组实验。

限制：

- 不直接成为 final Gate；
- 不直接成为 paper-critical evidence；
- 不能事后把普通 exploratory run 改名成 confirmatory。

### CALIBRATION

用于：

- metric；
- regression；
- convergence；
- baseline；
- measurement tolerance。

当前：

```text
M7 / M8 / M9 / M10 / M11A
```

属于这一层。

### CONFIRMATORY

只用于：

- route verdict；
- final Interface Gate；
- final margin；
- paper-critical result。

Confirmatory run 之前必须冻结关键变量与判据。

---

## 3.2 M7 拆成 M7A / M7B / M7C

M7 保持一个主编号，不重新编号历史 todo。

### M7A — Mathematical Unit Tests

使用真正 mathematical ground truth：

- zero trace；
- known `+2π` phase transition；
- known `−2π` phase transition；
- two known transitions；
- known voltage-area pulse；
- sign reversal；
- window-boundary case。

目标：

> 验证公式、单位、sign、window、cluster、integration。

不能证明任何 BQ / DCSFQ / BVM candidate 的物理正确性。

---

### M7B — Canonical Circuit Validation

使用独立、已充分理解的 canonical Josephson/SFQ circuit，例如官方/标准 JTL。

目标：

> 验证 measurement pipeline 在真实 Josephson transient 上正确。

不能证明 BQ v4 / DCSFQ_BVM 成功。

---

### M7C — Historical Regression

使用：

- DCSFQ 300 µA；
- BQ v4 六周期；
- preserved historical raw CSV。

Expected values 必须来自：

> **独立人工/raw 重算后预注册的 frozen constants。**

禁止：

```text
production analyzer → 生成 expected
production analyzer → 再验证 expected
```

M7C 只能证明：

> 新 pipeline 没有重新误读旧数据。

---

## 3.3 M8 是有界 convergence，不是固定三点

起点：

```text
0.1 ps
0.05 ps
0.025 ps
```

运行前必须定义：

```yaml
initial_dt:
refinement_ratio:
max_refinement_levels:
observables:
comparison_windows:
stability_tolerance:
stop_rule:
```

关键 observables 至少包括：

- phase turns；
- voltage-area turns；
- phase-area residual；
- event timing；
- pulse width；
- downstream count（若适用）。

达到稳定带宽：

```text
PASS
```

到最大 refinement depth 仍不稳定：

```text
INCONCLUSIVE
```

不得无限缩 timestep。

---

## 3.4 M9 只冻结“怎么测”

M9 产物：

```text
METRIC_SPEC_V2.md
```

只定义：

- phase normalization；
- P/V same-JJ mapping；
- direction/sign；
- windows；
- zero-input control；
- activity clustering；
- voltage-area integration；
- numerical tolerance；
- convergence rule；
- output schema。

M9 **不定义**：

> 什么样的 BVM→SFQ interface 才叫成功。

后者以后单独：

```text
INTERFACE_GATE_V1.md
```

---

## 3.5 Parameter Provenance + R0–R3

建立：

```text
docs/research/REFERENCE_PROVENANCE.md
```

参数统一标记：

```text
[PUBLISHED]
[AUTHOR_PROVIDED]
[DERIVED]
[INFERRED]
[DESIGNED]
[TUNED]
[UNKNOWN]
```

禁止：

> `[INFERRED] / [DESIGNED] / [TUNED]` 参数在后续总结中逐渐被写成 paper parameter。

Reference circuit 使用：

```text
R0 = Topology Reconstruction
R1 = Published Nominal-Parameter Reconstruction
R2 = Behavioral Reproduction
R3 = Independent Full Reproduction
```

R3 必须在预先声明的：

- model closure；
- testbench；
- parameter provenance；
- numerical settings；
- observation tolerance

下满足全部 reproduction criteria。

---

## 3.6 Source / Receiver / Interface Gate 必须分层

M9 完成后可以并行开始：

```text
Reference Reconstruction
BVM Source Characterization
Receiver Characterization
W5 Literature / Provenance
```

但 BQ v4 / DCSFQ_BVM 的**正式 candidate tuning 和 route verdict**继续等待 M11。

最终顺序：

```text
METRIC_SPEC
    ↓
Reference / Source / Receiver
    ↓
INTERFACE_GATE_V1
    ↓
Candidate tuning
    ↓
Operating region
    ↓
Held-out validation
    ↓
Process variation
    ↓
JTL / T1
    ↓
CONFIRMATORY FROZEN
```

---

# 4. M11 保持一个编号，但有两个子门

不要把历史 todo 重编号。

```text
M11
├── M11A Measurement Calibration Baseline
└── M11B Scientific Reconstruction Baseline
```

只有：

```text
M11A PASS
+
M11B PASS
```

M11 才能标绿。

---

# 5. Claude Code 当前最低必要修改

Claude Code 应优先检查当前项目文件，然后只修改最低必要内容。

建议修改对象：

```text
memory/project-todo.md
docs/HANDOVER.md            # 只做最低状态同步
必要的 research task/ADR
```

不要机械更新所有历史 summary。

---

## 5.1 `project-todo.md`

最低修改：

### M7

从单项改为：

```text
M7
├── M7A Mathematical Unit Tests
├── M7B Canonical Circuit Validation
└── M7C Historical Regression
```

### M8

完成标准改为：

> 预注册 observables / tolerance / max refinement depth / stopping rule 的有界 convergence procedure。

### M9

明确：

> 只冻结 `METRIC_SPEC_V2`。

### M11

改为：

```text
M11A Measurement Calibration Baseline
M11B Scientific Reconstruction Baseline
```

并写明：

> 两个子门都通过后 M11 才完成。

### W5

拆分或注明：

```text
W5A Literature Boundary
W5B Reference Provenance
W5C Author Inquiry
```

W5B 可与 M7 并行。

---

# 6. 当前立即科研任务

## 主线

```text
M7
```

## 并行支线

```text
W5B / REFERENCE_PROVENANCE
```

不要先实施新 Batch system。

不要先大改 workflow。

不要先做 BQ v4 / DCSFQ_BVM 新参数路线。

---

# 7. 三个 Agent 的角色：实际怎么用

用户只需要记住：

```text
Codex = 想清楚“做什么”和“结论能不能成立”
Claude = 把事情做出来
Copilot = 在交给 Codex 之前尽量找错
```

---

# 8. Claude Code：默认主力执行者

Claude Code 是项目日常工作的默认入口。

适合：

- 写代码；
- 改 netlist；
- 写 tests；
- 跑 JoSIM；
- 做 bounded sweep；
- 生成 raw evidence；
- 写 analysis script；
- 整理 provenance；
- 写 RESULT；
- 修普通 bug；
- 做文档最低同步。

原则：

> 如果任务已经定义清楚，不需要每一步再问 Codex。

Claude 可以在授权 scope 内持续推进，直到：

- task 完成；
- 遇到 stop condition；
- 需要改变 scientific semantics；
- 需要扩大 scope；
- 发现原假设可能错误。

---

# 9. Copilot：低成本的第一道 Review

Copilot 不负责调度整个项目，也不做最终 scientific verdict。

适合：

- review Claude 的 diff；
- 找测试盲区；
- 找 shared-helper oracle；
- 查 sign / unit / window；
- 查 stale artifact；
- 查 overclaim；
- 查 boundary case；
- 查 provenance 缺失；
- review script / tests；
- 做 PRE-REVIEW。

推荐日常模式：

```text
Claude 实现
↓
Copilot review
↓
Claude 修复
```

大部分 implementation 问题应该在这里解决。

---

# 10. Codex：不要日常驻场

Codex 不应该用来：

- 普通 grep；
- 普通代码补全；
- 跑重复测试；
- 每改一行就 review；
- 每个小失败都重新签任务。

Codex 只在下面几类情况介入。

---

## 10.1 Codex 调度：什么时候需要

### 情况 A：开始一个新的“科研问题”

例如：

- M7；
- M8；
- BVM Source Characterization；
- published QB reconstruction；
- BQ v4 candidate study；
- DCSFQ_BVM study。

让 Codex 做：

- objective；
- research question；
- scope；
- acceptance criteria；
- stop conditions；
- claim ceiling。

然后把任务交 Claude。

---

### 情况 B：需要改变科研语义

例如要改：

- metric formula；
- threshold；
- window；
- direction convention；
- control；
- source definition；
- Interface Gate；
- parameter domain；
- route。

停止 Claude 当前执行。

让 Codex 重新判断/修订。

---

### 情况 C：出现互相竞争的物理解释

例如：

```text
BQ 没输出
```

可能是：

- damping；
- source/load mismatch；
- bias；
- loop state；
- numerical issue。

这时让 Codex 做 hypothesis decomposition / experiment design。

不要让 Claude 无限试参数。

---

# 11. Codex Review：什么时候必须做

并不是所有任务都必须 Codex review。

## 必须 Codex review

### Scientific Gate

- M8 convergence；
- M9 MetricSpec freeze；
- M11 baseline；
- `INTERFACE_GATE_V1`；
- route verdict；
- bounded negative result；
- final margin；
- paper-critical result。

### Scientific semantics changed

例如：

- 新 metric；
- 新 control；
- 新 physical interpretation；
- 新 candidate architecture。

### Claude / Copilot 出现冲突

如果：

```text
Claude: PASS
Copilot: Major concern
```

让 Codex 裁决。

---

## 不需要 Codex review

通常：

- formatting；
- plotting；
- path；
-普通 unit tests；
- README；
- provenance table 填写；
-机械 metadata；
-简单 parser；
-小型非科学 bug。

Claude + Copilot 就可以完成。

---

# 12. 最简工作流：Routine

适用：

- 普通代码；
- 文档；
- plot；
- parser；
- mechanical checks。

```text
你
↓
Claude
↓
测试
↓
必要时 Copilot
↓
完成
```

**不叫 Codex。**

---

# 13. 最简工作流：Scientific Implementation

适用：

- M7；
- Source Characterization；
- Receiver Characterization；
- bounded exploratory sweep。

```text
你
↓
Codex
  定义一次任务
↓
Claude
  实现 + 实验
↓
Copilot
  PRE-REVIEW
↓
Claude
  修复
↓
Codex
  一次 final audit
↓
完成
```

核心：

> Codex 一头一尾，中间不驻场。

---

# 14. 最简工作流：Scientific Gate

适用：

- M8；
- M9；
- M11；
- Interface Gate；
- route verdict；
- paper result。

```text
你
↓
Codex
  预注册任务 / Gate
↓
Claude
  FROZEN execution
↓
Copilot / fresh reviewer
  独立证伪式 review
↓
Codex
  深度 final audit
↓
你
  采用 / 拒绝科学结论
```

这时才值得花高成本 review。

---

# 15. 什么时候应该停下 Claude，而不是继续让它跑

遇到以下情况：

```text
同根因连续两轮失败
需要不停增加新变量
需要扩大参数域
测试结果与物理预期矛盾
metric / window / control 需要改变
模型 provenance 不清楚
出现两个合理但冲突的物理解释
```

Claude 应停止 trial-and-error。

然后：

```text
→ Codex 做重新分解
```

---

# 16. 什么时候用 Copilot，而不是 Codex

优先 Copilot：

- “Claude 的代码有没有 bug？”
- “test 是否太弱？”
- “有没有漏边界？”
- “sign / window 有没有错？”
- “这个修改是否与 TASK 一致？”
- “有没有 overclaim？”

优先 Codex：

- “我们接下来应该研究什么？”
- “这个 failure 说明什么？”
- “哪个实验能区分两个机制？”
- “这个 Gate 是否足够？”
- “这个证据能不能支持论文结论？”
- “路线是否应该切换？”

---

# 17. 用户每天最推荐的使用模式

## 开始新科研阶段时

找 Codex：

```text
“根据 project-todo 和当前 evidence，为下一项 Mx 签一个边界清楚的任务。
只定义 objective / acceptance / stop conditions / claim ceiling。
不要执行。”
```

---

## 然后交 Claude

```text
“执行 Codex 刚签发的任务。
在授权 scope 内自行推进，不要每一步向我确认。
遇到 scientific semantics / scope / stop condition 才停。”
```

---

## Claude 完成后找 Copilot

```text
“只做 adversarial PRE-REVIEW。
重点检查 unit/sign/window/oracle/boundary/stale artifact/provenance/overclaim。
不要重新设计任务。”
```

---

## 有问题

交回 Claude：

```text
“按 Copilot findings 修复。
不要扩大 scientific scope。
修复后重新运行必要 tests/evidence。”
```

---

## 稳定以后

再找 Codex：

```text
“对稳定 delivery 做 final audit。
不要重新实现；独立检查 raw evidence 与 acceptance。
给 ACCEPT / REWORK / BLOCKED。”
```

---

# 18. 什么情况下可以完全跳过 Codex

例如：

```text
修画图
改路径
普通测试
整理 README
生成 provenance table
写 netlist parser
jj_audit.py 的非物理 parser 部分
整理实验目录
```

直接：

```text
Claude → Copilot（可选）→ 完成
```

---

# 19. 什么情况下不要跳过 Codex

```text
metric definition
convergence
baseline freeze
physical interpretation
candidate architecture
route decision
Interface Gate
paper claim
bounded negative result
```

这些必须至少：

```text
Codex planning
+
Codex final review
```

---

# 20. 关于最高能力模型

科学协议不绑定具体型号。

但实际使用可以遵循：

```text
普通调度 / 日常 audit
→ 日常高能力 controller

极关键科学 Gate / 重大架构 / paper claim
→ 当前可用最高能力 reviewer

机械 discovery / indexing / regression
→ 低成本 verifier
```

也就是说：

> 高能力模型用在“改变结论会很贵”的地方，而不是“执行时间很长”的地方。

---

# 21. 当前项目的推荐执行顺序

```text
现在
│
├── 最低必要 todo/研究规则同步
│
├── M7 task 由 Codex 定义
│
├── Claude 执行 M7A/B/C
│
├── Copilot PRE-REVIEW
│
├── Claude 修复
│
├── Codex final M7 audit
│
│
├── 同时：W5B / REFERENCE_PROVENANCE
│
▼
M8 bounded FROZEN convergence
│
▼
M9 METRIC_SPEC_V2
│
├── Reference Reconstruction
├── BVM Source Characterization
├── Receiver Characterization
├── W5
│
▼
M10
│
▼
M11A + M11B
│
▼
INTERFACE_GATE_V1 + held-out set
│
▼
Published-QB-like / BQ v4 / DCSFQ_BVM
│
▼
Operating Region
│
▼
Held-out Validation
│
▼
Variation
│
▼
JTL / T1
│
▼
CONFIRMATORY FROZEN
│
▼
Paper
```

---

# 22. 给 Claude Code 的当前指令

可以直接复制：

> 工作流设计讨论现在结束。
>
> 本项目接下来以“简化协作流程、提高科学严谨性、快速恢复科研”为原则。
>
> 请不要实施完整 Batch P0、verify-batch、Decision Cache、automatic routing 或其它非关键工作流自动化，也不要让 FROZEN v1.1 阻塞当前科研。
>
> 先读取当前 `AGENTS.md`、`memory/project-todo.md`、`docs/HANDOVER.md` 和当前 workflow。
>
> 然后只做最低必要研究计划同步：
>
> 1. 保持 M7 编号，下设 M7A mathematical / M7B canonical JTL / M7C historical regression；
> 2. M8 改为有界、预注册 stopping rule 的 timestep convergence；
> 3. M9 只冻结 `METRIC_SPEC_V2`；
> 4. M11 保持一个编号，下设 M11A Measurement Calibration Baseline / M11B Scientific Reconstruction Baseline，二者都通过才标绿；
> 5. W5 明确 literature / provenance / optional author inquiry；
> 6. 引入 EXPLORATORY / CALIBRATION / CONFIRMATORY 研究阶段语义；
> 7. 加入 parameter provenance 与 R0–R3 reproduction 原则。
>
> 不要机械重写历史日志，不要启动 BQ v4 / DCSFQ_BVM 新参数路线。
>
> 完成最低必要同步后停止，等待 Codex 签发 M7。
>
> W5B / `REFERENCE_PROVENANCE.md` 可以作为独立 documentation/provenance 工作并行准备，但不得自行升级 scientific state。

---

# 23. 给 Codex 的当前指令

可以直接复制：

> 工作流讨论结束，恢复研究。
>
> 请按当前 project-todo 与已接受 M4–M6 evidence，签发一个普通 M7 科研实现任务。
>
> M7 保持一个编号，下设：
>
> - M7A mathematical ground truth；
> - M7B canonical JTL validation；
> - M7C historical regression。
>
> M7C oracle 必须来自独立人工/raw 重算预注册值，不允许 production analyzer 自证。
>
> 当前不实施 Batch Extension，不要求 FROZEN v1.1，不启动 M8+。
>
> 请只定义 objective、scope、acceptance、stop conditions、claim ceiling，并交给 Claude 执行。

---

# 24. 给 Copilot 的当前指令

可以直接复制：

> 当 Claude 完成 M7 implementation 后，只做 adversarial PRE-REVIEW。
>
> 不重新设计 M7。
>
> 优先检查：
>
> - oracle independence；
> - unit；
> - rad/turn；
> - sign/direction；
> - window；
> - boundary；
> - activity vs event；
> - same-JJ P/V；
> - stale historical artifacts；
> - production/helper shared bug；
> - M7C circular validation；
> - overclaim。
>
> 给出 Major / Minor findings，并指出是否应交回 Claude 修复。
>
> 不给最终 physical verdict，不更新 todo。

---

# 25. 最后原则

今后每次不要先问：

> “这个任务应该走哪套复杂流程？”

先问：

> **“这个任务到底是什么性质？”**

如果只是实现：

```text
Claude
```

如果需要找代码错误：

```text
Copilot
```

如果涉及研究问题、物理语义或最终结论：

```text
Codex
```

因此日常最常见的节奏应当是：

```text
Codex 定方向一次
→ Claude 连续推进
→ Copilot 找错
→ Claude 修
→ Codex 收尾一次
```

而不是：

```text
每一步都 Codex
→ 每一步都合同
→ 每一步都审计
```

只有真正的 Scientific Gate 才使用重型流程。

**这套协作方式的目标是：让 AI 体系把时间花在研究问题本身，而不是研究如何管理 AI。**
