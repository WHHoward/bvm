# RESULT M5-LITE-PILOT-001 / A01

execution_status: COMPLETED
executor_artifact_assessment: VALID
proposed_physical_verdict: NOT_APPLICABLE

## Preflight
<最先写入的不可变块，不得回填重写；错误用追加 correction note>

Task revision commit: 6498d3607cf1fb12c00b79c118bd72d9046a8baf
Execution baseline commit: 6498d3607cf1fb12c00b79c118bd72d9046a8baf
Observed HEAD: 6498d3607cf1fb12c00b79c118bd72d9046a8baf
Branch/worktree: claude/M5-LITE-PILOT-001 / /home/howard/JoSIM-m5-lite
Git status:
  (clean — `git status --porcelain=v1 --untracked-files=all` 输出为空)
Allowed paths: understood（scripts/sfq_metrics_v2.py、test/metrics/test_sfq_metrics_v2_m5.py、research/tasks/M5-LITE-PILOT-001/attempts/**、research/mailbox/from-claude/** 仅通知）
Risk: CRITICAL
Evidence mode: LITE
Claim ceiling: understood（仅窗口/方向/零输入控制/活动聚类实现与确定性回归；冻结 CSV 重放是算术检查，不建立任何 SFQ 事件/物理 Gate/容差/路线/论文主张；LITE 不得追溯为 FROZEN）
Frozen input hashes: 8/8 匹配（sfq_metrics_v2.py b654205a…、test_sfq_metrics_v2.py 7f0898e9…、bump_0.csv 2420b99a…、bump_300u.csv dfe20406…、bump_0.cir 0918141e…、bump_300u.cir 4c7d3df3…、DCSFQ.cir 3452106b…、jjmit.cir 19862d1f…）
Bump netlist diff: 精确为 `.param IIN=0u` vs `.param IIN=300u`（第 3 行），其余行字节一致
CSV alignment: 两 CSV 头部逐字一致（time, "V(OUT1)", "P(B1|XDCSFQ)", "P(B2|XDCSFQ)", "P(B3|XDCSFQ)"），各 2000 行
Ambiguity: none
Preflight result: PASS

## Summary

M5 在 M4 单位基础（`scripts/sfq_metrics_v2.py`，向后兼容保持）上实现了窗口化计量：

- 确定性 pre/activity/post 半开窗口 `[start_s, end_s)`（秒），校验 `pre_end <= activity_start`、`activity_end <= post_start`，每窗 ≥2 个有限样本；
- 逐窗统计：请求边界、实际选中首/末时间、样本数、未舍入算术均值（raw rad）、min/max/峰峰；
- 显式列方向（严格 ±1，绝不从观测符号推断、不取绝对值）；
- 匹配零输入控制校正：`corrected_delta_rad = direction * (signal_delta_rad - control_delta_rad)`，`corrected_delta_turns` 仅在相减后除以 2π；控制 CSV 必须头部逐字一致且时间数组逐元素相等（不插值/重采样/最近匹配）；输出保留 `signal` / `zero_input_control` / `control_corrected` 三个命名空间；
- 活动聚类：增量两端点均在活动窗内（半开）、严格 `abs(delta) > threshold`（相等不激活、不跨间隙）；聚类与过阈值样本只称 activity，绝不称事件；
- JSON measurement plan CLI：`--measurement-plan PLAN.json [--control-csv CONTROL.csv]`；M4 的 `analyze(csv, threshold_rad=...)` 与旧 CLI 行为完全不变；
- 阈值标为 `descriptive_unfrozen`（M9 才冻结）。

## Changes

- `scripts/sfq_metrics_v2.py`（+322/−2）：新增 `M5_DISCLAIMER`、`validate_plan`、`_read_phase_csv`、`_window_indices`、`_window_stats`、`_activity_clusters`、`windowed_analyze`；`main()` 增加 `--measurement-plan` / `--control-csv` 分支（失败返回码 2，stderr 输出 `error: <原因>`）。`analyze()` 与 M4 CLI 路径未动。
- `test/metrics/test_sfq_metrics_v2_m5.py`（新增，25 测试）：PlanValidationTests（8）、ControlAlignmentTests（3）、ClusteringTests（4）、ControlCorrectionTests（4）、WindowSelectionTests（1）、FrozenReplayTests（2）、TerminologyTests（1）、CliTests（2）。期望值全部为独立首性原理常数（0.25=2^-2 精确增量、5.0=10×0.5 精确爬升、TASK 冻结重放常数），不调用生产辅助函数。
- `research/tasks/M5-LITE-PILOT-001/attempts/A01/`：plan.json、output.json、logs/（unit-tests、replay、hashes、scope-diff）。

## Verification

| command | result |
|---|---|
| `python3 test/metrics/test_sfq_metrics_v2_m5.py` | PASS — 25/25 |
| `python3 test/metrics/test_sfq_metrics_v2.py`（M4 回归） | PASS — 15/15，未改动 |
| 冻结 CSV 重放（300u signal − 0u control，固定 plan） | PASS — 三列 turns 与 TASK AC6 常数误差 < 1.6e-14 rad |
| 冻结输入哈希二次校验（交付前） | PASS — 7 个未修改冻结输入全部匹配；sfq_metrics_v2.py 为新哈希（交付物本身） |
| bump netlist diff | PASS — 仅 `.param IIN` 一行 |
| scope 检查（HEAD vs worktree） | PASS — 仅允许路径有改动 |

AC6 重放关键数值（TASK 冻结期望 vs 实现输出）：

| 列 | 期望 turns（TASK） | 实际 turns | 误差 (rad) |
|---|---|---|---|
| P(B1\|XDCSFQ) | 0.999999982941839 | 0.9999999829418391 | 6.98e-16 |
| P(B2\|XDCSFQ) | 1.00000006251931 | 1.0000000625193106 | 4.19e-15 |
| P(B3\|XDCSFQ) | 1.00000001477283 | 1.0000000147728276 | 1.53e-14 |

选定样本：pre 30 / post 900（与 TASK 一致）；0.3 rad 阈值下信号聚类数 B1/B2/B3 = 1/0/1、控制 = 0/0/0（与 TASK 一致）。

## Evidence

- `research/tasks/M5-LITE-PILOT-001/attempts/A01/plan.json` — 87eb68d13ce98331d3fd5229ae0409f8a564d5490272420a642d23b018999857
- `research/tasks/M5-LITE-PILOT-001/attempts/A01/output.json` — 52dc2cd4b888b2132775a6295d87fe9444c287d6b7e1f2d686b57e91097df247
- `research/tasks/M5-LITE-PILOT-001/attempts/A01/logs/unit-tests.log` — bc5174ee8b2f5fc62107ca075892cda391774c39ed2c00fc235f76814ea73fd1
- `research/tasks/M5-LITE-PILOT-001/attempts/A01/logs/replay.log` — c744e23f1724ab7cf9b786223a71786d8d49da305f866ae81a850978acdd085b
- `research/tasks/M5-LITE-PILOT-001/attempts/A01/logs/hashes.log` — 74e480470083abed9589d867449e98ccb6d482d39626e357ed40c0fb07042dd9
- `research/tasks/M5-LITE-PILOT-001/attempts/A01/logs/scope-diff.log` — 53d10a4c6c64dfe188deda7d825f148644b83429bc28ba3bab8f7c072e21b798
- 冻结输入（未修改）：bump_0/300u CSV+CIR、DCSFQ.cir、jjmit.cir、M4 测试文件 — 哈希见 logs/hashes.log，全部与 TASK 表一致

## Changed files

- `scripts/sfq_metrics_v2.py`（修改，允许路径内）
- `test/metrics/test_sfq_metrics_v2_m5.py`（新增，允许路径内）
- `research/tasks/M5-LITE-PILOT-001/attempts/A01/**`（证据文件）

## Limitations / anomalies

- 方向向量完成过程说明：TASK AC6 冻结常数（B1/B2/B3 全部为 +2π 圈）唯一确定完整方向向量为 `P(B1|XDCSFQ)=-1, P(B2|XDCSFQ)=+1, P(B3|XDCSFQ)=+1`（TASK 示例 plan 仅给出 B1=-1）。方向是声明输入，不是从观测符号推断；AC6 冻结数值即本 LITE 合同的规范。
- 开发期发现并修复的两个缺陷均为**测试自身**问题，实现未改动：(1) 相等性测试用 0.3 步进存在浮点累积漂移（部分增量成为 0.30000000000000004），改为 0.25（2^-2）精确增量；(2) 方向反转测试误将同一信号同时作为 signal 与 control（identical → 校正恒 0），改为零控制。两者均在独立测试逻辑层修正。
- 阈值 0.3 rad 为描述性/未冻结（`threshold_status: descriptive_unfrozen`），由 M9 冻结。
- 未运行 JoSIM、未修改/重跑历史数据、未做 M6 电压积分、未实现 M7–M11 任何部分。

## Claim

M5 窗口/方向/零输入控制/活动聚类实现与确定性回归行为已验证：AC1–AC7 全部满足。冻结 CSV 重放（300u 减 0u）以 ≤1.6e-14 rad 精度复现 TASK 冻结常数，聚类 1/0/1 与 0/0/0 复现——这是对冻结 CSV 的算术检查，明确演示聚类数不是物理事件数（B2 净增一满圈但聚类为 0）。本结果不建立任何 SFQ 事件、下游/JTL 接收、闭环 fluxoid、电路 Gate、冻结容差、路线对比或论文主张；LITE 证据不得追溯为 FROZEN。M6–M11 均未实现，见 TASK Explicit remainder。

---

## Delivery snapshot（RESULT 完成后由授权 owner 追加）

Delivery snapshot commit: <commit>
Snapshot owner: <role>
Snapshot scope check: PASS
