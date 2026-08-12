---
title: Claude 对 WORKFLOW-lite 2.0-rc1 的最终意见
document_type: review
status: FOR_DISCUSSION
date: 2026-08-11
reviewed: workflowdiscuss/archive/old-versions/WORKFLOW-lite-2.0-rc1.md（用户方案，2026-08-11）
supersedes: claude-review-workflow-lite.md（1.0 审阅意见，同目录）
related:
  - research/WORKFLOW.md
  - workflowdiscuss/archive/proposals/WORKFLOW-copilot-review-proposal.md
  - workflowdiscuss/archive/proposals/WORKFLOW-v2-three-party-discussion-summary.md
  - research/mailbox/from-codex/codex-20260811-142613.md
  - research/tasks/JH-20260811-M4-003/audits/C01/verdict.yaml
---

# Claude 对 WORKFLOW-lite 2.0-rc1 的最终意见

> 执行者视角的最终审阅。**结论先行：2.0-rc1 可以进入 PILOT**，附四个增量点。

## 一、总体判断

2.0-rc1 是高质量修订：上一轮审阅的五点意见全部吸收，Codex 的 verify-task 语义拆分建议也纳入。骨架完整（两维度 × 两模式 + Preflight + 强 Reviewer + 十条底线），工程权衡诚实（把复杂度花在发现错误上，而非手续上）。

## 二、吸收确认

| 意见来源 | 2.0 的落实 |
|---|---|
| Claude：一套协议两种模式 | §0「LITE / FROZEN」+ §35 迁移关系（v1 = FROZEN 后端） |
| Claude：保留执行前基线核对 | §5 Preflight（HEAD ≠ Baseline → BLOCKED，直接对应 M4-002 教训） |
| Claude：RESULT 预检行（替代 ACK） | §9 模板 Preflight 块，不增加文件数 |
| Claude：保守风险定级 | §20 八条自动 CRITICAL + 用户强制升级 + §21 降级必须记录理由 |
| Claude：文件命名映射 | §36（TASK.md ≈ LITE / request.yaml ≈ FROZEN，禁止同一 attempt 双维护） |
| Claude：试点修正 | §33 三层 Pilot（M12 / M5 实现 / M5 物理） |
| Codex：verify-task 语义拆分 | §31（execution snapshot verification vs current drift check） |
| Codex：review 需独立记录 + 绑定 | §18 REVIEW.md 完整格式 + §8 四维语义保留 |

## 三、增量意见（四条）

### 1. 认知修正：NORMAL+LITE 并没有真正放弃哈希链——Git 本身就是

§24 说 NORMAL 不维护 hash chain，严格说**不准确**：Git 的 blob 本身就是 SHA-1/SHA-256 内容寻址，commit 链就是不可变哈希链。LITE 实际放弃的只有两样：

1. 未提交工作树的篡改检测（M4-002 的 request.yaml 覆盖场景）；
2. 逐文件字节级绑定记录。

而这两样恰好被 **TASK 纳入 Git commit（§3）+ Preflight 基线核对（§5）** 基本覆盖。

**建议**：§24 点明「Git = 轻量哈希链（blob/commit 级）；FROZEN = 文件级哈希链（工作树级）」——论证更诚实，也让 Codex 放心 NORMAL 不是"无防篡改"。

### 2. Skill 资产必须复用，不能平行建设（最重要）

§13 的 `superconducting-simulation-review` 与项目**现有** `josim-evidence-audit`（相位/电压面积/事件审计规则，经 M4 与单位事故验证）**功能重叠**。平行建一套，两套物理审计规则必然漂移——这正是我们刚用教训建立的体系，不能再造一套。

**建议**：
- `.github/skills/superconducting-simulation-review/SKILL.md` 只做**包装/引用**（指向 `.agents/skills/josim-evidence-audit/` + `references/phase-evidence-contract.md`），不复制规则；
- `numerical-science-review` 复用 `josim-experiment` 的纪律（不可覆盖 raw、manifest、run ID）；
- **7 个 skill 不一次全建**：先建 3 个核心（adversarial-review、numerical-science-review、superconducting-simulation-review 包装件），Pilot 验证后再按需补。

### 3. LITE → FROZEN 中途切换路径要明确

§19 允许 Codex 决定"进入 FROZEN"，但未说明已完成的 LITE attempt 如何处理。

**建议**：升级时——LITE attempt **原样保留**（历史记录），创建新 attempt 走 FROZEN 流程（request/ACK/receipt + 哈希链），Codex 将已有成果快速封存进新合同；两套文件不混在同一 attempt（§36 已禁止）。这样切换有明确路径，且历史可追溯。

### 4. 两个小确认

- §1.3 组合表补一句「**NORMAL 任务永不要求 FROZEN**」——组合语义无歧义；
- §32 的 Reviewer 权限验证（Prompt ≠ ACL）建议作为 **Pilot 0**：不依赖任务，纯验证 Copilot 能否识别 `.github/agents/reviewer.agent.md`、发现 skills、只写当前 attempt 的 REVIEW.md、不污染 worktree。验证过了再让 M12 正式依赖 Reviewer，否则 Pilot 1 结论会被"环境未搭好"污染。

## 四、试点确认

| Pilot | 组合 | 验证点 | 状态 |
|---|---|---|---|
| 0 | — | Reviewer 权限/环境验证 | 建议新增（前置） |
| 1 | M12，NORMAL + LITE | TASK freeze / Preflight / attempt / Reviewer / light audit | ✅ 合适 |
| 2 | M5 计量实现，CRITICAL + LITE | numerical review / control / critical Reviewer / Codex raw audit | ✅ 合适 |
| 3 | M5 物理解释 / M6，CRITICAL + FROZEN | Lite→FROZEN 切换 / v1 后端 / physical interpretation | ✅ 合适 |

Pilot 评价指标（§34 八项）完整，建议加第 9 项：「skill 复用度——Reviewer 是否实际调用 josim-evidence-audit 而非平行推理」。

## 五、结论

**2.0-rc1 可进入 PILOT。** 四个增量点（Git 即哈希链、skill 复用防漂移、升级路径明确、Pilot 0 前置）不阻塞试点，但建议在 Pilot 1 开始前落实第 2、4 点（skill 复用 + Pilot 0），第 1、3 点可在 Pilot 期间并入。

决定权在用户 + Codex；本文件不构成协议修订。
