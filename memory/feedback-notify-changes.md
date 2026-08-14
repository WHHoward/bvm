---
name: feedback-notify-changes
description: commit/notification 三级风险模型（L0/L1/L2）——什么直接提交、什么需授权、什么必须通知 Codex/用户
metadata:
  node_type: memory
  type: feedback
  originSessionId: 0a6c3d20-0d5b-452e-a234-939c2e31e4bd
  modified: 2026-08-14T16:11:01.028Z
---

用户要求（2026-08-14，2026-08-15 细化为三级风险模型）：commit / notification 机制按下面三级执行，**不再按"重要/不重要"主观判断**。

## L0 — EPHEMERAL / REGENERABLE

**典型**：可重新生成的 HTML、cache、临时 debug 文件、scratch 文件、非证据级临时 log、其他可从 tracked source + frozen evidence 确定性重建的产物。

**规则**：默认不 commit；generator / source 可以 commit，纯生成物通常不 commit；**不需要单独通知 Codex**。

## L1 — LOW-RISK DERIVED / MAINTENANCE

**典型**：visualization generator、PNG/SVG 图、dashboard UI/UX、README/figure index、组会排版、typo/formatting、不改变 scientific claim 的说明性文档、portability/path/CSS 等维护。

**规则**：
- 完成自检后可直接 **atomic commit**，不必每次等用户确认；
- commit 后向用户简要说明：改了什么、commit SHA、是否运行新实验、是否触碰 frozen evidence / scientific status；
- 不要每个 L1 commit 都给 Codex 单独发 mailbox；一批完成后发**一条汇总 INFO** 即可（如 `[INFO] visualization/documentation maintenance completed; commits: ...; no new simulation, no frozen evidence change, no scientific authority change`）；
- **mailbox 不要变成 Git log 的镜像**。

## L2 — SCIENTIFIC / AUTHORITY / EXPERIMENT-PROGRESSING

**包括但不限于**：新建或修改 .cir 科研实验；修改 BVM/BQ/DCSFQ/JTL 参数；新 timestep/sweep/simulation run；修改 acceptance threshold / convergence rule；修改 metric / Gate / route；新的 raw evidence；修改 frozen evidence；改变 scientific conclusion；修改项目 authority 状态；启动 receiver / Gate / candidate tuning；paper-level / hardware-level claim。

**规则**：
- 没有明确用户授权或有效 Codex-issued contract 时，**禁止自行执行或 commit**；
- 如果已有有效、ISSUED、sealed 的 Codex contract 且操作完全在 scope.write_paths 与合同范围内，则不需要每个 commit 向用户二次确认——用户授权 + Codex contract 本身就是执行边界；
- 按合同执行、测试、形成 implementation/execution commits 和 receipt；最终 scientific verdict 仍交给独立 review / Codex audit；
- 一旦发现需要超出合同、修改 metric/Gate/route/frozen evidence，**立即停止并请求授权**，不要"顺手修复"。

## Commit granularity

一个用户意图 / 一个独立语义变更 = 一个 atomic commit。例如 `viz: redesign BVM-S0 guided visualization` 可同时包含 generator、CSS、README 更新。**不要**为记录 AI 操作过程把完整工作机械拆成 add file → fix file → update README → notify mailbox → commit mailbox，除非各阶段本身有独立科研/审计意义。

## Mailbox policy（Codex）

只用于会影响以下事项的信息：scientific audit、下一步研究动作、evidence authority、blocker、contract execution、supersession、用户改变路线/目标、需要 Codex 做判断的异常。

以下**通常不需要**逐条通知 Codex：CSS/UI 调整、README typo、图的排版、visualization portability、纯组会格式修改、不改变科学含义的 derived artifact。一批低风险工作完成后发一次汇总 INFO 即可。

## User notification

- **L1**：完成并 commit 后简报即可（改动、SHA、是否新实验、是否触碰 frozen evidence / scientific status）；
- **L2**：已有授权合同则执行后简报；无授权或需扩 scope 必须先问；
- 任何 frozen evidence、scientific status、route 或 Gate 变化都必须明确告诉用户。

## 历史（被本模型取代的早期约定）

- 2026-08-14 早期："每次改动都 mailbox + 用户确认后 commit"（已被 L1 直接提交 + 汇总通知取代）；
- 2026-08-14 末："重要/不重要"主观二分 + mailbox 消息不提交（mailbox 消息保持 untracked 的惯例不变，除非用户明确要求提交）。
