---
title: WORKFLOW-lite 2.0 — 三方科研协作协议
version: 2.0-rc1
status: PILOT
date: 2026-08-11
mode_model:
  - LITE
  - FROZEN
risk_model:
  - NORMAL
  - CRITICAL
design_goal: 轻量默认、关键任务升级、强 Reviewer、最小机械防线、保留科研可追溯性
---

# WORKFLOW-lite 2.0

## 0. 核心定位

`WORKFLOW-lite 2.0` 是本仓库的**轻量默认协作界面**。

它不试图把每一个任务都变成完整审计流程，而是采用：

```text
风险分级 + 轻量预检 + 强 Reviewer + 按需证据冻结
```

整体流程：

```text
Codex 定义 TASK
    ↓
Claude Preflight + 执行
    ↓
RESULT
    ↓
Copilot Reviewer + Skills
    ↓
REVIEW
    ↓
Codex 按风险等级最终审查
    ↓
ACCEPT / REWORK / BLOCKED
```

对于真正需要长期冻结和严格可追溯的关键科研证据：

```text
WORKFLOW-lite
    ↓
Formal Freeze
    ↓
josim-handoff/v1 重型冻结后端
```

因此，本协议不是和旧协议竞争，而是：

> **一套协议，两种证据模式。**

---

# 1. 两个维度，而不是一串复杂状态

本协议只使用两个彼此独立的维度：

## 1.1 风险等级

```text
NORMAL
CRITICAL
```

表示任务本身的科学/工程风险。

---

## 1.2 证据模式

```text
LITE
FROZEN
```

表示本次任务使用多严格的证据冻结机制。

---

## 1.3 常见组合

### NORMAL + LITE

默认工程任务。

例如：

- 绘图；
- CLI；
- 文档；
- 纯代码重构；
- 普通测试修复；
- 非科学语义工具；
- 不改变 metric 含义的辅助代码。

---

### CRITICAL + LITE

关键实现/计量任务，但尚未进入最终科研冻结。

例如：

- measurement implementation；
- event/window；
- numerical integration；
- units；
- threshold/tolerance；
- solver/timestep sensitivity；
- SFQ event detector；
- 可能影响科学解释的计量逻辑。

---

### CRITICAL + FROZEN

真正用于：

- final physical Gate；
- metric freeze；
- 研究路线关键切换；
- 论文核心数据；
- 论文 figure；
- paper-level claim；
- 严重 evidence conflict；
- 用户或 Codex 明确要求的长期冻结。

此模式调用已有 `josim-handoff/v1` 工具链与哈希冻结机制。

---

# 2. 四个角色

## 2.1 用户 — Final Authority

用户拥有以下最终决定权：

- 研究路线；
- metric freeze；
- physical Gate；
- paper-level scientific claim；
- 是否升级为 CRITICAL；
- 是否进入 FROZEN；
- 是否接受重大偏离或风险。

用户可以：

```text
强制将任何任务升级为 CRITICAL
```

用户不需要参与每一项机械验证。

---

## 2.2 Codex — Planner + Final Auditor

Codex 负责：

### 任务前

创建或确认 `TASK.md`：

- Risk；
- Evidence mode；
- Baseline；
- Goal；
- Allowed paths；
- Acceptance criteria；
- Required evidence；
- Stop conditions；
- Claim ceiling。

### 任务后

根据风险等级最终审查：

```text
NORMAL
→ light audit

CRITICAL
→ deep audit from raw evidence
```

Codex 拥有最终任务处置权：

```text
ACCEPT
REWORK
BLOCKED
```

但研究路线、metric freeze、physical Gate 和论文级主张仍由用户最终决定。

---

## 2.3 Claude — Executor

Claude 是执行者。

Claude 应：

- 在执行前完成 Preflight；
- 只在 allowed paths 内修改；
- 完成 acceptance criteria；
- 保存必要证据；
- 不覆盖冻结科研证据；
- 报告异常；
- 在 attempt 目录中写 `RESULT.md`；
- 遵守 claim ceiling。

Claude 不得：

- 修改 `TASK.md`；
- 自行扩大 scope；
- 自行重新定义 metric；
- 自行降低风险等级；
- 自行更新 todo/HANDOVER 为“完成”；
- 自行冻结 metric；
- 自行宣布最终 physical Gate；
- 自行批准论文级 claim。

---

## 2.4 Copilot Reviewer — Evidence Reviewer

Copilot 使用：

```text
.github/agents/reviewer.agent.md
```

以及：

```text
.github/skills/*/SKILL.md
```

进行证据层 peer review。

Reviewer 的职责：

> **尝试证伪 Claude 的最强 bounded claim，并寻找测试、实现、数值与证据链中的隐蔽错误。**

Reviewer 重点检查：

- scope；
- semantic diff；
- tests；
- hidden test gaps；
- raw evidence；
- numerical correctness；
- evidence provenance；
- reproducibility；
- claim ceiling；
- JoSIM/SFQ/JTL 专项问题。

Reviewer 不是最终裁判。

Reviewer 不得：

- 修改实现；
- 修改 TASK；
- 修改 RESULT；
- 修改 raw evidence；
- 决定研究路线；
- 冻结 metric；
- 给最终 physical verdict；
- ACCEPT 任务。

Reviewer 只能给：

```text
PASS
REWORK
BLOCKED
```

作为**review disposition**。

最终 ACCEPT 只能由 Codex 给出。

---

# 3. TASK.md 的冻结机制

`TASK.md` 是唯一必须在执行前固定语义的任务合同。

不再默认使用 TASK SHA-256。

默认冻结机制：

> **Codex 签发 TASK 后，将 TASK.md 纳入 Git commit。**

因此：

```text
Git commit = 轻量 TASK 密封
```

规则：

1. Claude 永不修改 `TASK.md`；
2. Reviewer 永不修改 `TASK.md`；
3. TASK 需要修改时，由 Codex 创建显式 revision；
4. revision 必须通过新的 Git commit 固化；
5. 不允许“悄悄修改 TASK 后继续执行”。

如果 TASK 发生实质变化：

```text
重新 Preflight
```

---

# 4. TASK.md 最小模板

```markdown
# TASK <TASK-ID>

Risk: NORMAL | CRITICAL
Evidence mode: LITE | FROZEN
Baseline: <git commit>

## Goal
本任务要完成什么。

## Allowed paths
- path/a/**
- path/b/**

## Acceptance criteria
- [ ] 条件 1
- [ ] 条件 2
- [ ] 条件 3

## Required evidence
- 测试；
- raw CSV；
- control；
- representative cases；
- figure；
- 其他必要证据。

## Stop conditions
遇到以下情况停止并报告 BLOCKED：
- baseline 不匹配；
- scope 冲突；
- metric / unit / window 定义歧义；
- 必须修改 allowed paths 之外文件；
- 连续两次同根因失败；
- 发现可能改变研究结论的未预期异常；
- 需要覆盖冻结/历史证据；
- required evidence 不可获得。

## Claim ceiling
允许得出的最强结论。

例如：
Implementation verified only.
No final physical conclusion allowed.
```

---

# 5. Preflight — 用轻量预检替代独立 ACK

不再要求单独 `ACK.yaml`。

但 Claude 在首次写入任何实现文件前必须完成 Preflight。

Preflight 至少检查：

```text
TASK baseline
Observed HEAD
branch / worktree
git status
allowed paths
risk
evidence mode
claim ceiling
ambiguities
```

推荐格式：

```markdown
## Preflight

Task baseline: d4e91d3
Observed HEAD: d4e91d3
Branch/worktree: ...
Git status: clean / expected
Allowed paths: understood
Risk: NORMAL
Evidence mode: LITE
Ambiguity: none
Preflight result: PASS
```

如果：

```text
Observed HEAD != TASK Baseline
```

并且 TASK 没有明确允许该漂移：

```text
Preflight result: BLOCKED
```

Claude 不得继续执行。

---

# 6. Preflight 的目的

Preflight 不是为了增加文件。

它只负责在真正执行前抓住：

- 错 baseline；
- 错 worktree；
- 未提交的污染；
- scope 冲突；
- TASK 歧义；
- 风险误解；
- frozen evidence 冲突。

它保留旧协议 ACK 最有价值的部分，但移除 ACK 文件、ACK hash 与 ACK schema。

---

# 7. Attempt 历史

不再覆盖历史 RESULT / REVIEW。

推荐目录：

```text
research/tasks/<TASK-ID>/
├── TASK.md
└── attempts/
    ├── A01/
    │   ├── RESULT.md
    │   └── REVIEW.md
    ├── A02/
    │   ├── RESULT.md
    │   └── REVIEW.md
    └── ...
```

原则：

> **历史交付与历史审查必须可恢复。**

如果 A01 被 Reviewer 打回：

```text
A01 保留
→ Claude 创建 A02
→ Reviewer 审查 A02
```

不要求：

- attempt SHA；
- RESULT SHA；
- REVIEW SHA；

除非进入 FROZEN。

---

# 8. RESULT.md — 保留四维科研语义

RESULT 不再只有简单的：

```text
DONE
```

必须显式区分：

```yaml
execution_status: COMPLETED | BLOCKED | DEVIATED
artifact_status: VALID | INVALID | NOT_AUDITED
proposed_physical_verdict: PASS | FAIL | INCONCLUSIVE | NOT_APPLICABLE
```

注意：

```text
execution_status
≠ artifact_status
≠ physical verdict
≠ final audit acceptance
```

因此：

> **程序执行成功 ≠ 产物有效 ≠ 物理结论成立 ≠ Codex 接受。**

---

# 9. RESULT.md 推荐模板

```markdown
# RESULT <TASK-ID> / A01

execution_status: COMPLETED
artifact_status: VALID
proposed_physical_verdict: NOT_APPLICABLE

## Preflight
Task baseline: ...
Observed HEAD: ...
Branch/worktree: ...
Git status: ...
Allowed paths: ...
Risk: ...
Evidence mode: ...
Ambiguity: ...
Preflight result: PASS

## Summary
完成了什么。

## Changes
- ...

## Verification
- command → PASS / FAIL
- command → PASS / FAIL

## Evidence
- raw evidence path
- representative case
- control
- key numeric outputs

## Changed files
- ...

## Limitations / anomalies
- ...

## Claim
实际结果支持的结论。

必须位于 TASK claim ceiling 内。
```

---

# 10. artifact_status 的含义

## VALID

产物：

- 可读取；
- 与本次执行一致；
- 格式有效；
- evidence chain 没有发现明显断裂。

不表示最终科学结论一定成立。

---

## INVALID

例如：

- CSV 损坏；
- artifact 来自错误 run；
- 参数不匹配；
- 输出缺失；
- stale artifact；
- figure 与 raw 不一致；
- 关键证据不可重现。

---

## NOT_AUDITED

Claude 尚不能合理判断产物是否有效，或任务被提前 BLOCKED。

---

# 11. proposed_physical_verdict

Claude 可以在 TASK 明确允许时提出：

```text
PASS
FAIL
INCONCLUSIVE
```

但它只是：

```text
proposed_physical_verdict
```

不是最终 physical Gate。

Reviewer 不得把：

```text
proposed_physical_verdict
```

升级为最终结论。

Codex/User 保留最终权。

---

# 12. Reviewer 的完整审查模型

Reviewer 使用：

```text
Contradiction-first review
```

即：

> 先问“什么隐蔽错误会让结果看起来对、实际错？”

而不是：

> “我怎样证明 Claude 是对的？”

Reviewer 的完整能力由 Agent + Skills 组成。

---

# 13. Reviewer Skill Pack

推荐至少保留：

```text
adversarial-review
semantic-diff-review
test-gap-analysis
numerical-science-review
evidence-provenance-review
reproducibility-review
superconducting-simulation-review
```

---

## 13.1 adversarial-review

重点发现：

- no-op implementation；
- constant-output；
- wrong branch；
- silent fallback；
- hidden state；
- stale output；
- partial success overclaim。

---

## 13.2 semantic-diff-review

检查：

```text
changed code
→ callers
→ consumers
→ CLI
→ data contracts
→ downstream analysis
```

重点抓：

- 单位变化；
- 默认值变化；
- 参数语义变化；
- shape/schema 变化；
- 下游未同步。

---

## 13.3 test-gap-analysis

重点问：

> 错误实现有没有可能也通过这些测试？

检查：

- test oracle；
- branch reachability；
- negative/control；
- boundary；
- threshold；
- tolerance；
- fixture overfitting；
- shared helper 同错；
- flaky state。

---

## 13.4 numerical-science-review

检查：

- units；
- sign；
- integration；
- sampling interval；
- nonuniform spacing；
- window；
- threshold；
- tolerance；
- NaN/Inf；
- precision；
- convergence；
- sensitivity。

---

## 13.5 evidence-provenance-review

追踪：

```text
TASK
→ code/config
→ execution
→ raw
→ derived
→ metric
→ figure
→ RESULT claim
```

重点发现：

- stale artifact；
- wrong run；
- wrong parameter；
- wrong source data；
- figure/data mismatch。

---

## 13.6 reproducibility-review

检查：

- random seeds；
- working directory；
- environment variables；
- cache；
- ordering；
- hidden global state；
- dependency/version assumptions。

---

## 13.7 superconducting-simulation-review

针对 JoSIM / Josephson / SFQ / JTL：

- phase vs voltage-area cross-check；
- `Δφ/(2π)`；
- phase wrap / unwrap；
- sign / orientation；
- activity vs event；
- local vs downstream；
- zero-input control；
- event window；
- startup transient；
- duplicate counting；
- timestep sensitivity；
- solver sensitivity；
- claim strength。

---

# 14. Reviewer 的渐进审查阶梯

Reviewer 不应一开始就重做所有工作。

使用：

```text
Stage 0
TASK / Contract

↓
Stage 1
Git / Diff / Execution path

↓
Stage 2
Hidden-bug hypotheses

↓
Stage 3
Independent evidence triangulation
```

如果没有异常：

```text
停止扩展
```

如果发现可疑信号：

```text
调用相关 Skill 深挖
```

---

# 15. NORMAL Reviewer 最低要求

至少：

1. 完整 scope 检查；
2. 检查 actual diff；
3. 逐条 acceptance criteria；
4. 构造 3–5 个 plausible hidden-error hypotheses；
5. 检查最危险的几个；
6. 可执行/数值 claim 至少一个独立检查；
7. claim ceiling。

NORMAL 不要求研究级全量审计。

---

# 16. CRITICAL Reviewer 最低要求

除 NORMAL 外，还必须尽量完成：

1. critical tests 复跑；
2. 至少一个 negative/control；
3. 至少一个 boundary/sensitivity 检查；
4. critical raw evidence；
5. numerical independent cross-check；
6. unit/sign/window 检查；
7. evidence provenance；
8. stale/cache 检查；
9. anomaly 搜索；
10. Codex focus。

Reviewer 仍然不代替 Codex。

---

# 17. Reviewer 不允许形成共识幻觉

Reviewer 不得：

```text
Claude RESULT = PASS
→ 所以 REVIEW = PASS
```

必须拥有自己的最小独立证据来源。

例如：

```text
Claude:
Δφ/(2π) = 1.002

Reviewer:
从 raw CSV 独立计算
→ 1.0018
→ 一致
```

而不是只检查 RESULT 里有没有写 `1.002`。

---

# 18. REVIEW.md 完整格式

协议正文与 Reviewer Agent 统一使用以下格式：

```markdown
# REVIEW <TASK-ID> / A01

Review disposition: PASS | REWORK | BLOCKED
Recommended risk: NORMAL | CRITICAL
Evidence confidence: HIGH | MEDIUM | LOW
Residual risk: LOW | MEDIUM | HIGH

## Scope
PASS | FAIL | UNKNOWN

Evidence:
- ...

## Acceptance criteria
- [x] Criterion — PASS — evidence
- [ ] Criterion — FAIL — evidence

## Independent checks
- check → result
- check → result

## Hidden-error probes
- hypothesis/probe → result
- hypothesis/probe → result

## Claim ceiling
PASS | FAIL | AMBIGUOUS

## Findings

### Critical
- None.

### Major
- None.

### Minor
- None.

## Residual uncertainty
- ...

## Codex focus
1. ...
2. ...
```

---

# 19. Reviewer 风险升级规则

Reviewer 可以：

```text
Recommended risk: CRITICAL
```

但不得自己修改 TASK。

如果 Reviewer 发现：

- unit；
- window；
- physical interpretation；
- solver/timestep；
- raw evidence；
- control；
- metric semantics；

存在重大问题，应：

```text
REWORK / BLOCKED
+
Recommended risk: CRITICAL
```

然后由 Codex决定：

```text
升级 / 保持 / 重签 / 进入 FROZEN
```

---

# 20. “拿不准就 CRITICAL”

风险分级采用保守原则：

```text
有实质疑问
→ CRITICAL
```

以下情况自动触发 CRITICAL：

1. 新协作机制首次试点；
2. 新 Agent / Reviewer / Skill 首次用于真实任务；
3. 与 frozen evidence 交互；
4. 与历史 baseline 关键证据交互；
5. metric / unit / window / threshold 变化；
6. physical interpretation；
7. solver/timestep/convergence；
8. paper-critical evidence。

用户可随时强制升级。

---

# 21. 如果 Reviewer 建议升级但 Codex 保持 NORMAL

Codex 必须简单记录：

```text
Reviewer recommended CRITICAL.
Codex decision: keep NORMAL.
Reason: ...
```

不允许静默忽略风险升级建议。

---

# 22. Codex NORMAL final audit

当：

```text
RESULT 完整
REVIEW = PASS
无高风险 finding
```

Codex 通常只需：

1. 阅读 TASK；
2. 阅读 RESULT；
3. 阅读 REVIEW；
4. 检查关键 diff；
5. 抽查 Reviewer 最重要的一项证据；
6. 检查 risk recommendation；
7. 给出：

```text
ACCEPT
REWORK
BLOCKED
```

Codex 不需要重跑全部 Reviewer 工作。

---

# 23. Codex CRITICAL final audit

即使：

```text
REVIEW = PASS
```

以下任务 Codex仍必须亲自回到 raw evidence：

- physical Gate；
- SFQ/JTL/phase propagation；
- metric definition/freeze；
- research route；
- paper-level claim；
- units；
- endpoints；
- direction；
- window；
- timestep；
- convergence；
- evidence conflict；
- FAIL；
- INCONCLUSIVE；
- INVALID；
- frozen input drift。

Codex 至少检查：

- critical raw evidence；
- metric semantics；
- unit/sign/window；
- control；
- critical numerical result；
- evidence → claim 逻辑；
- physical interpretation。

---

# 24. Git 与 SHA-256

## 24.1 NORMAL + LITE

默认只用 Git：

```text
Baseline commit
git status
git diff
git log
git show
```

不维护：

- request SHA；
- RESULT SHA；
- REVIEW SHA；
- verdict SHA；
- hash chain。

---

## 24.2 CRITICAL + LITE

仍不恢复完整 hash chain。

但关键科研输入/输出应记录：

```text
path
SHA-256
```

例如：

```text
raw/run-17.csv
SHA-256: ...
```

目的：

> 确定 Codex/Reviewer 审的是哪一份关键数据。

不是为了证明谁执行了命令。

---

## 24.3 CRITICAL + FROZEN

进入：

```text
josim-handoff/v1
```

恢复已有：

- request；
- ACK；
- receipt；
- audit/verdict；
- frozen snapshot；
- hash binding；
- append-only evidence。

不重新发明另一套 Formal Freeze 协议。

---

# 25. frozen evidence 保护

任何 frozen / historical evidence：

- 不允许覆盖；
- 不允许“重新生成到同一路径”；
- 不允许修改原始内容；
- 新 run 使用新路径；
- 必要时记录 SHA-256。

如果验证需要重跑：

```text
生成到新的 run / temp / ignored path
```

而不是覆盖旧证据。

---

# 26. todo / HANDOVER 更新权

只有 Codex 给出：

```text
ACCEPT
```

之后，才能将任务状态更新为完成。

Claude 不得：

```text
执行完
→ 自己把 todo 标绿
```

Reviewer 也不得：

```text
REVIEW PASS
→ 自己把 HANDOVER 更新为完成
```

推荐：

```text
Codex ACCEPT
→ 更新 todo/HANDOVER
```

---

# 27. ACCEPT / REVIEW PASS / physical PASS 的区别

严格区分：

```text
Reviewer PASS
=
证据复核在 review scope 内通过

Codex ACCEPT
=
本次任务交付被最终采纳

physical PASS
=
TASK 定义的物理条件满足

User adoption
=
用户决定将其作为研究路线/metric/paper 结论采用
```

四者不能互相替代。

---

# 28. REWORK

Reviewer 或 Codex发现问题：

```text
A01
↓
REWORK
↓
A02
```

不覆盖 A01。

REWORK 必须具体：

```text
observed discrepancy
why it matters
minimum reproducible evidence
required correction/reverification
```

---

# 29. BLOCKED

出现：

- baseline mismatch；
- TASK ambiguity；
- scope conflict；
- missing raw evidence；
- destructive verification required；
- metric/window/unit materially ambiguous；
- frozen evidence conflict；
- repository state 无法可靠归因；

返回：

```text
BLOCKED
```

不允许靠猜测继续。

---

# 30. 重复同根因失败

如果连续两个 attempt 因同一根因失败：

```text
Repeated root cause
```

暂停继续尝试。

升级给：

```text
Codex / User
```

避免 AI 无限 trial-and-error。

---

# 31. verify-task 的语义拆分

历史任务验证必须区分：

## execution snapshot verification

回答：

> Claude 当时是否在正确 baseline / input 上执行？

---

## current drift check

回答：

> 当前仓库相对于当时又发生了什么变化？

这两个不能共用：

```text
历史任务失效
```

这一结论。

正常更新 todo/HANDOVER 不应让已 ACCEPT 的历史任务被误判为无效。

---

# 32. Reviewer Agent 的权限验证

重要：

> Reviewer Prompt 不是文件系统 ACL。

因此正式依赖 Reviewer 之前，必须通过真实 Pilot 验证：

1. Copilot 是否识别 `.github/agents/reviewer.agent.md`；
2. Skills 是否可发现；
3. Reviewer 是否只写当前 attempt 的 `REVIEW.md`；
4. verification command 是否污染 worktree；
5. 是否会修改实现；
6. 是否会错误扩大 scope。

如果约束在真实环境中无效：

```text
Reviewer 降级为只读建议角色
```

不得视为协议层正式审查。

---

# 33. 推荐 Pilot

当前版本状态：

```text
PILOT
```

不立即宣称全面替代旧协议。

---

## Pilot 1 — M12

```text
Risk: NORMAL
Evidence mode: LITE
```

验证：

- TASK freeze；
- Preflight；
- attempt；
- Reviewer Agent；
- Skills；
- NORMAL Codex light audit。

---

## Pilot 2 — M5 计量实现部分

建议：

```text
Risk: CRITICAL
Evidence mode: LITE
```

验证：

- numerical review；
- raw evidence；
- event/window；
- control；
- critical Reviewer；
- Codex raw audit。

---

## Pilot 3 — M5 物理解释 / M6

```text
Risk: CRITICAL
Evidence mode: FROZEN
```

验证：

- Lite → Formal Freeze；
- josim-handoff/v1 backend；
- physical interpretation；
- final evidence freezing。

---

# 34. Pilot 评价指标

每个 Pilot 记录：

```text
1. Reviewer 是否发现 Claude 未发现的问题？
2. Reviewer findings 是否被 Codex 确认？
3. false positives 多不多？
4. NORMAL token/流程成本是否下降？
5. CRITICAL 科学审查是否仍可靠？
6. Preflight 是否成功捕获 baseline/scope 问题？
7. Agent/Skills 是否按设计工作？
8. Codex 是否明显减少机械复核？
```

Pilot 结束后再决定是否：

```text
2.0-rc1
→ 2.0 FINAL
```

---

# 35. 与现有协议/工具的迁移关系

在 Pilot 期间：

```text
WORKFLOW-lite 2.0
=
新任务的默认协作界面

josim-handoff/v1
=
CRITICAL/FROZEN 的证据冻结后端
+
现有已归档任务的权威历史协议
```

旧任务如：

```text
M4-001
M4-002
M4-003
```

保持原样。

不重写历史。

---

# 36. 文件命名映射

## LITE

```text
TASK.md
attempts/Axx/RESULT.md
attempts/Axx/REVIEW.md
```

---

## FROZEN

使用 `josim-handoff/v1` 的：

```text
request
ACK
receipt
audit/verdict
hash chain
```

因此：

```text
TASK.md
≈ LITE 模式的任务合同

request.yaml
≈ FROZEN 模式的机器校验合同
```

不要在同一个 attempt 中同时维护两套语义重复文件。

---

# 37. 推荐目录

```text
.github/
├── agents/
│   └── reviewer.agent.md
└── skills/
    ├── adversarial-review/
    │   └── SKILL.md
    ├── semantic-diff-review/
    │   └── SKILL.md
    ├── test-gap-analysis/
    │   └── SKILL.md
    ├── numerical-science-review/
    │   └── SKILL.md
    ├── evidence-provenance-review/
    │   └── SKILL.md
    ├── reproducibility-review/
    │   └── SKILL.md
    └── superconducting-simulation-review/
        └── SKILL.md

research/
├── WORKFLOW-lite.md
└── tasks/
    └── <TASK-ID>/
        ├── TASK.md
        └── attempts/
            ├── A01/
            │   ├── RESULT.md
            │   └── REVIEW.md
            └── A02/
                ├── RESULT.md
                └── REVIEW.md
```

已有 evidence 目录结构优先。

不要仅为了协议重新搬迁现有科研数据。

---

# 38. Token / 上下文预算原则

本协议强调：

> **复杂度优先放在发现错误的能力，而不是手续。**

---

## 不做

- NORMAL 任务完整 hash chain；
- 每次复制大日志；
- 每次复制完整 diff；
- Reviewer 全量重做 Claude；
- Codex 全量重做 Reviewer；
- 不相关仓库历史扫描；
- 为了“完整”输出长审计作文。

---

## 要做

- Git 记录 baseline；
- Preflight 抓低成本错误；
- Reviewer 先构造隐藏错误假设；
- Skill 按任务相关性调用；
- raw evidence 用路径引用；
- numerical claim 做独立 cross-check；
- NORMAL 抽样；
- CRITICAL 深查；
- FROZEN 才恢复完整证据冻结。

---

# 39. 三方最小独立证据

## Claude

基于实际执行写 RESULT。

---

## Reviewer

至少一个独立证据来源。

---

## Codex NORMAL

至少抽查一个关键事实。

---

## Codex CRITICAL

必须直接读取关键 raw evidence。

---

# 40. 最终职责矩阵

| 工作 | Claude | Copilot Reviewer | Codex | 用户 |
|---|---:|---:|---:|---:|
| 创建 TASK | ❌ | ❌ | ✅ | 可要求 |
| 修改 TASK | ❌ | ❌ | ✅ | 最终权 |
| Preflight | ✅ | 检查 | 抽查 | — |
| 实现代码 | ✅ | ❌ | 通常 ❌ | ❌ |
| scope 自检 | ✅ | ✅ | 抽查 | — |
| 跑测试 | ✅ | 关键项复跑 | 按风险 | — |
| hidden-bug probing | 自检可做 | ✅ | 按风险 | — |
| raw evidence | 提供 | 检查 | CRITICAL 必须 | — |
| numerical cross-check | 可做 | ✅ | CRITICAL 必须关键项 | — |
| claim ceiling | 遵守 | ✅ | ✅ | 可提升 |
| Recommended risk | ❌ | ✅ | 决定 | 可强制升级 |
| physical verdict | 仅 proposed | ❌ | 审查 | 最终采用 |
| metric freeze | ❌ | ❌ | 建议 | 最终采用 |
| paper claim | ❌ | ❌ | 审查 | 最终采用 |
| REVIEW.md | ❌ | ✅ | ❌ | — |
| ACCEPT | ❌ | ❌ | ✅ | 最终科研采用 |
| todo/HANDOVER 完成更新 | ❌ | ❌ | ✅ after ACCEPT | 可决定 |
| Formal Freeze | ❌ | 建议风险 | ✅ 发起 | 可强制 |

---

# 41. 最小底线

无论未来如何修改，本协议至少保留：

```text
1. 任务目标明确。
2. 写入范围明确。
3. acceptance criteria 明确。
4. stop conditions 明确。
5. claim ceiling 明确。
6. 执行前 baseline 可核对。
7. TASK 不允许静默修改。
8. Reviewer 有最小独立证据。
9. Critical 科学任务由 Codex 从 raw evidence 深度复核。
10. 用户保留路线、metric freeze、physical Gate 和论文主张最终权。
```

---

# 42. 默认工作口令

## 给 Codex

```text
Create the next task under WORKFLOW-lite 2.0.
Set Risk and Evidence mode conservatively.
Commit TASK.md before delegation.
```

---

## 给 Claude

```text
Execute the current TASK under WORKFLOW-lite 2.0.
Perform Preflight before any implementation write.
Respect allowed paths, stop conditions and claim ceiling.
Write the result under a new attempt directory.
Do not modify TASK.md or update todo/HANDOVER as completed.
```

---

## 给 Copilot Reviewer

选择 `reviewer` Agent：

```text
Review the latest attempt under WORKFLOW-lite 2.0.

Read TASK before RESULT.
Inspect the actual diff and evidence.
Use the relevant review skills.
Generate plausible hidden-error hypotheses and test the highest-risk ones.
For executable/numerical claims, perform independent checks.
For CRITICAL work, inspect raw evidence and provide Codex focus.

Write only the attempt-local REVIEW.md.
Do not modify implementation, TASK, RESULT, or raw evidence.
```

---

## 给 Codex 最终审查

```text
Audit the latest attempt under WORKFLOW-lite 2.0.

For NORMAL:
use light audit and do not repeat all Reviewer checks.

For CRITICAL:
independently inspect critical raw evidence, units, windows, controls,
numerical semantics and physical interpretation.

Return ACCEPT, REWORK or BLOCKED.
Only after ACCEPT may todo/HANDOVER be marked completed.
```

---

# 43. 核心设计原则

最后只需要记住四句话：

> **轻量默认，不等于取消预检。**

> **强 Reviewer，不等于第二个 Codex。**

> **关键数据冻结，不等于所有文件都做 hash chain。**

> **把复杂度花在发现真实错误上，而不是花在手续上。**
