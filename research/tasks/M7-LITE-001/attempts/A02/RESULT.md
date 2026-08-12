# RESULT M7-LITE-001 / A02

execution_status: COMPLETED
executor_artifact_assessment: VALID
proposed_physical_verdict: NOT_APPLICABLE

## Preflight
<最先写入的不可变块，不得回填重写；错误用追加 correction note>

Task revision commit: a27750bc026ca0b9afc9d3d02464008630fdc9df（不可变 TASK）
Execution baseline commit: df5027e3c0809a6a8ba958dc853409976adb02a7（Codex 授权：首个包含 A01 CODEX-AUDIT.md 的 commit；A02 基线 ≠ TASK revision 的理由与 M5/M6 同类——审计记录使 rework 可开始）
Observed HEAD: df5027e3c0809a6a8ba958dc853409976adb02a7
Branch/worktree: claude/M7-LITE-001 / /home/howard/JoSIM-m7-lite
Git status:
  (clean — `git status --porcelain=v1 --untracked-files=all` 输出为空；A01 证据已由 snapshot commits 纳入)
Allowed paths: understood（test/metrics/test_sfq_metrics_v2_m7.py、test/metrics/m7_canonical_jtl.cir、research/tasks/M7-LITE-001/attempts/**、research/mailbox/from-claude/** 仅通知；A01 保留不修改）
Risk: CRITICAL
Evidence mode: LITE
Study phase: CALIBRATION
Claim ceiling: understood（同 A01；本 A02 只补证据闭环，不重跑 JoSIM、不做收敛/容差/candidate/物理结论）
Frozen input hashes: 14 项与 A01 Preflight 一致（A01 已核 14/14 未变；本 A02 不修改任何冻结输入）
REWORK 原因（CODEX-AUDIT.md）: (1) AC3 缺 A02-local M7B analysis 产物；(2) AC5 scope-diff 不完整（仅 3 项，遗漏 RESULT/manifest/raw/inputs）
A01 M7B raw CSV（本 A02 analysis 的输入，只读引用）: runs/m7-jtl-cal-20260812-01/raw/m7-jtl-cal-20260812-01.csv，sha256 728c112ec18864a9f84a0f73e3ffedf39051b528c8e3785b5632f409190cda52
Ambiguity: none
Preflight result: PASS

## Summary

A02 补齐 A01 的证据闭环（REWORK 两项修正）：

1. **A02-local M7B analysis**（`analysis-m7b.md`）：只读引用 A01 raw CSV（SHA-256 728c112e…），声明窗口 `[6e-12, 50e-12)`，记录首/末选中实际样本（index 60 @ 6.000000e-12 s、index 498 @ 4.990000e-11 s，共 439 样本）、带符号 phase delta / area turns / residual；显式保留 no-tolerance / no-event / no-Gate 边界。数值与 Codex A01 独立复核精确一致（B1 −1.412755095155926e-04、B2 +1.412930656122136e-03 turns）。
2. **完整 scope 检查**（`logs/scope-check.log`）：在所有 A02 文件生成后执行 `git status --porcelain --untracked-files=all`，列出全部变更路径并断言均在 `attempts/**` 内。

未重跑 JoSIM、未修改 TASK/实现/历史输入/A01、未做 M8/容差/candidate/物理结论。

## Changes

- `research/tasks/M7-LITE-001/attempts/A02/RESULT.md`（新增）
- `research/tasks/M7-LITE-001/attempts/A02/analysis-m7b.md`（新增，A02-local M7B analysis）
- `research/tasks/M7-LITE-001/attempts/A02/logs/analysis-generation.log`（新增）
- `research/tasks/M7-LITE-001/attempts/A02/logs/scope-check.log`（新增）

## Verification

| command | result |
|---|---|
| A02 analysis 生成（独立初等算术，A01 raw 只读） | PASS — 残差与 Codex A01 独立复核精确一致（B1 −1.412755095155926e-4 / B2 +1.412930656122136e-3） |
| 完整 scope 检查（A02 全部文件生成后） | PASS — 全部变更路径均在 attempts/** 内，无 out-of-scope |
| A01 实现/测试文件 | 未修改（git status 无相关条目；A01 83/83 测试结果不变） |
| 冻结输入 | 未修改（A01 已核 14/14） |

A02-local M7B analysis 数值（窗口 [6e-12, 50e-12)，实际时间轴，同 JJ 直接 V/P）：

| 结 | phase_delta_rad | phase_delta_turns | area_turns | residual_turns |
|---|---:|---:|---:|---:|
| B1\|XDUT | 6.375604500000000e+00 | 1.014708971373932e+00 | 1.014850246883447e+00 | −1.412755095155926e-04 |
| B2\|XDUT | 6.341850200000001e+00 | 1.009336807678325e+00 | 1.007923877022203e+00 | +1.412930656122136e-03 |

## Evidence

- `research/tasks/M7-LITE-001/attempts/A02/analysis-m7b.md` — 719e1df1aff987124f54320b34ffdefb8107c4f967a3fbf794041254d0a2269e
- `research/tasks/M7-LITE-001/attempts/A02/logs/analysis-generation.log` — a320124b55a6f16ec0d62c3888154aa1167681c881467bf6443bc68a2fbf723e
- `research/tasks/M7-LITE-001/attempts/A02/logs/scope-check.log` — 1649bd9df29822b665bfb7623c5d06b0cbcb1c0a320ec02df0f600b7a0d24f2f
- 引用的 A01 raw：728c112ec18864a9f84a0f73e3ffedf39051b528c8e3785b5632f409190cda52（A01 冻结，只读）

## Changed files

- `research/tasks/M7-LITE-001/attempts/A02/**`（RESULT.md、analysis-m7b.md、logs/×2）——全部在允许路径内

## Limitations / anomalies

- A02 analysis 生成器的第一次迭代曾用"位置索引"代替"窗口样本索引"计算梯形面积（得到错误残差 −0.1085 turns），通过与 Codex A01 独立复核值交叉检查发现并修正；最终 analysis-m7b.md 与 Codex 值精确一致。该中间错误未保存为证据（覆盖重生成），记录于此保证透明。
- M7B 残差为管线原始值，仅报告、不判定（容差由 M9 冻结）；不构成任何物理事件/Gate。
- 未重跑 JoSIM（审计明确授权不重跑）；A01 的 raw/manifest/inputs 保持冻结引用。

## Claim

A02 满足审计 Required correction：A02-local 不可变 M7B analysis 已产生（引用 A01 raw 哈希、声明窗口、记录选中样本与带符号数值、显式 no-tolerance/no-event/no-Gate 边界）；完整 scope 检查在全部 A02 文件生成后执行并证明无 out-of-scope 变更。A01 未修改，TASK/实现/历史输入未动。仍为 CALIBRATION LITE：不建立任何物理事件数、SFQ、下游接收、fluxoid、路线结果、容差、收敛、Gate 或论文主张；LITE 不得追溯为 FROZEN。

---

## Delivery snapshot（RESULT 完成后由授权 owner 追加）

Delivery snapshot commit: f2e20ea0b2ba92b9fa4634dba29a2778833124c1
Snapshot owner: CODEX
Snapshot scope check: PASS
