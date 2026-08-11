# RESULT M5-LITE-PILOT-001 / A02

execution_status: COMPLETED
executor_artifact_assessment: VALID
proposed_physical_verdict: NOT_APPLICABLE

## Preflight
<最先写入的不可变块，不得回填重写；错误用追加 correction note>

Task revision commit: 6498d3607cf1fb12c00b79c118bd72d9046a8baf（不可变 TASK）
Execution baseline commit: f83a9361df8d28d4fe556af9efa1a6d26254d50e（Codex 授权，见 attempts/A01/CODEX-AUDIT.md；A02 基线 ≠ TASK revision 的已记录理由：基线 = 首个包含 A01 review/audit 记录的 commit，仅增加使 rework 可开始的记录）
Observed HEAD: f83a9361df8d28d4fe556af9efa1a6d26254d50e
Branch/worktree: claude/M5-LITE-PILOT-001 / /home/howard/JoSIM-m5-lite
Git status:
  (clean — `git status --porcelain=v1 --untracked-files=all` 输出为空)
Allowed paths: understood（scripts/sfq_metrics_v2.py、test/metrics/test_sfq_metrics_v2_m5.py、research/tasks/M5-LITE-PILOT-001/attempts/**、research/mailbox/from-claude/** 仅通知；A01 已封存，不修改）
Risk: CRITICAL
Evidence mode: LITE
Claim ceiling: understood（同 A01：仅实现与确定性回归；冻结 CSV 重放是算术检查；不建立任何物理主张；LITE 不得追溯为 FROZEN）
Frozen input hashes: 7 个未修改冻结输入交付前重新校验（bump_0/300u CSV+CIR、DCSFQ.cir、jjmit.cir、test_sfq_metrics_v2.py）；sfq_metrics_v2.py 为交付物，哈希随 A01/A02 变更
Bump netlist diff: `.param IIN` 参数位于第 6 行（A02 更正 A01 的"第 3 行"表述——A01 中该数字来自去注释/去空行后的 diff 行号；A02 以 grep 行号 6 为准）
CSV structure: 各 2000 行 = 1 表头 + 1999 数据行（A02 更正 A01 的"各 2000 行"表述）
REWORK 原因（Codex/Copilot Major，CODEX-AUDIT.md）：activity 窗缺完整统计；activity 0/1 样本未拒绝，违反 TASK fixed semantics/AC2
Ambiguity: none
Preflight result: PASS

## Summary

A02 修复 REWORK Major 缺口，全部要求满足：

1. **activity 窗完整统计**：pre/activity/post 三个窗口在 signal 与 `zero_input_control` 命名空间均输出完整未舍入统计块（requested bounds、selected first/last time、sample_count、mean_rad、min/max/p2p_rad）；聚类与窗统计分离（`activity_clusters` 列表 + `over_threshold_sample_count` 独立字段），聚类不携带任何事件语义；
2. **activity <2 样本拒绝**：`_window_stats` 现对 activity 窗同样生效——0 样本与 1 样本均触发 ValueError（CLI 返回码 2），与 pre/post 一致；
3. **409 样本断言**：冻结重放测试断言 signal 与 control 的 activity `sample_count == 409`，并断言 activity 统计块九个字段齐备；
4. **A01 非材料更正**（不重写 A01 历史）：IIN 参数位于第 6 行；CSV 为 1999 数据行 + 1 表头。

## Changes

- `scripts/sfq_metrics_v2.py`（A02 增量 +35/−21）：`_activity_clusters` 改为返回 `(clusters, over_threshold_sample_count)` 元组；`namespace()` 现对 pre/activity/post 均调用 `_window_stats`（activity <2 样本由此拒绝），列结构变为 `{direction, pre, activity, post, activity_clusters, over_threshold_sample_count, delta_rad}`；`windowed_analyze` docstring 更新。
- `test/metrics/test_sfq_metrics_v2_m5.py`（25 → 29 测试）：适配新列结构；新增 `test_activity_window_zero_samples_rejected`、`test_activity_window_one_sample_rejected`（1 样本用例用精确二进制窗口上界 2.0625 = 2+1/16，0.1 网格上仅 t=2.0 落入）、`test_activity_window_stats_complete`（首性原理：60 样本、均值 272.5/60 = 4.541666666666667）、`test_activity_stats_separate_from_clustering`（统计块内无聚类字段）；冻结重放测试新增 409 断言与统计字段断言。

## Verification

| command | result |
|---|---|
| `python3 test/metrics/test_sfq_metrics_v2_m5.py` | PASS — 29/29 |
| `python3 test/metrics/test_sfq_metrics_v2.py`（M4 回归） | PASS — 15/15，未改动 |
| 冻结 CSV 重放（300u signal − 0u control，固定 plan） | PASS — turns 误差 ≤1.6e-14 rad；pre/activity/post = 30/409/900；聚类 signal 1/0/1、control 0/0/0 |
| 冻结输入哈希复验（交付前） | PASS — 7 个未修改冻结输入全部匹配 |
| scope 检查（A02 基线 f83a9361 vs worktree） | PASS — 仅允许路径有改动 |

AC6 重放关键数值（TASK 冻结期望 vs A02 实现输出）：

| 列 | 期望 turns（TASK） | 实际 turns | 误差 (rad) |
|---|---|---|---|
| P(B1\|XDCSFQ) | 0.999999982941839 | 0.9999999829418391 | 6.98e-16 |
| P(B2\|XDCSFQ) | 1.00000006251931 | 1.0000000625193106 | 4.19e-15 |
| P(B3\|XDCSFQ) | 1.00000001477283 | 1.0000000147728276 | 1.53e-14 |

选定样本：pre 30 / activity 409 / post 900（signal 与 control 一致）；0.3 rad 阈值下信号聚类数 B1/B2/B3 = 1/0/1、控制 = 0/0/0（与 TASK 一致）。

## Evidence

- `research/tasks/M5-LITE-PILOT-001/attempts/A02/plan.json` — 87eb68d13ce98331d3fd5229ae0409f8a564d5490272420a642d23b018999857（与 A01 冻结 plan 逐字节一致）
- `research/tasks/M5-LITE-PILOT-001/attempts/A02/output.json` — 43b1508880010411dfd9a034971c33953967a4f6547c5e58a7604d1e3fb94b0c
- `research/tasks/M5-LITE-PILOT-001/attempts/A02/logs/unit-tests.log` — a180b0d88e39500a60ea0ca6d9b5ebd8b517352f02c5ac14bc614aa797242b11（29 M5 + 15 M4 全量）
- `research/tasks/M5-LITE-PILOT-001/attempts/A02/logs/replay.log` — ce2bca22016bfade0a10921045811152f0a7d84320af5911c4764eaee6334dcc
- `research/tasks/M5-LITE-PILOT-001/attempts/A02/logs/hashes.log` — 5c5f096ddc950c0af89fa36bfc3aabee650b12204d324ae5f801da20400c8331
- `research/tasks/M5-LITE-PILOT-001/attempts/A02/logs/scope-diff.log` — 623eb7bdbdaf375922edd1f973bff7abf8a49412936992960480569cd9053ed1
- A01 审计记录（REWORK 依据，不修改）：`attempts/A01/CODEX-AUDIT.md`、`attempts/A01/REVIEW.md`

## Changed files

- `scripts/sfq_metrics_v2.py`（修改，允许路径内；A01 快照之上增量）
- `test/metrics/test_sfq_metrics_v2_m5.py`（修改，允许路径内）
- `research/tasks/M5-LITE-PILOT-001/attempts/A02/**`（证据文件）

## Limitations / anomalies

- A01 非材料表述更正（Codex 要求，A01 历史不改写）：bump netlist 的 `.param IIN` 在第 6 行（A01 记"第 3 行"系去注释/空行后的 diff 行号）；CSV 为 1999 数据行 + 1 表头（A01 记"各 2000 行"为含表头总行数）。
- 方向向量同 A01：`P(B1|XDCSFQ)=-1, P(B2|XDCSFQ)=+1, P(B3|XDCSFQ)=+1`，由 TASK AC6 冻结常数唯一确定，是声明输入而非从观测符号推断。
- 阈值 0.3 rad 仍为描述性/未冻结（`threshold_status: descriptive_unfrozen`），由 M9 冻结。
- 未运行 JoSIM、未修改/重跑历史数据、未做 M6 电压积分、未实现 M7–M11 任何部分。

## Claim

REWORK 要求全部满足：pre/activity/post 三窗完整未舍入统计在 signal 与 control 命名空间齐备，聚类与统计分离且无事件语义；activity 0/1 样本均拒绝（CLI 非零）；冻结重放 409 断言通过。既有 M4 15 测试与 M5 全部行为保持。AC6 冻结 CSV 重放以 ≤1.6e-14 rad 精度复现 TASK 常数，聚类 1/0/1 与 0/0/0 复现——算术检查，聚类数不是物理事件数。本结果不建立任何 SFQ 事件、下游/JTL 接收、闭环 fluxoid、电路 Gate、冻结容差、路线对比或论文主张；LITE 证据不得追溯为 FROZEN。M6–M11 均未实现，见 TASK Explicit remainder。

---

## Delivery snapshot（RESULT 完成后由授权 owner 追加）

Delivery snapshot commit: 4c4975ac0f982dc7488fe1975d20109fdd0f38ab
Snapshot owner: CODEX
Snapshot scope check: PASS
