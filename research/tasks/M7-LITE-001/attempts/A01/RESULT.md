# RESULT M7-LITE-001 / A01

execution_status: COMPLETED
executor_artifact_assessment: VALID
proposed_physical_verdict: NOT_APPLICABLE

## Preflight
<最先写入的不可变块，不得回填重写；错误用追加 correction note>

Task revision commit: a27750bc026ca0b9afc9d3d02464008630fdc9df（首个包含本 TASK.md 的 commit）
Execution baseline commit: a27750bc026ca0b9afc9d3d02464008630fdc9df
Observed HEAD: a27750bc026ca0b9afc9d3d02464008630fdc9df
Branch/worktree: claude/M7-LITE-001 / /home/howard/JoSIM-m7-lite
Git status:
  (clean — `git status --porcelain=v1 --untracked-files=all` 输出为空)
Allowed paths: understood（test/metrics/test_sfq_metrics_v2_m7.py、test/metrics/m7_canonical_jtl.cir、research/tasks/M7-LITE-001/attempts/**、research/mailbox/from-claude/** 仅通知）
Risk: CRITICAL
Evidence mode: LITE
Study phase: CALIBRATION
Claim ceiling: understood（仅 M7A/M7B/M7C 校准实现与确定性回归；不建立物理事件数、SFQ、下游接收、fluxoid、路线结果、容差、Gate 或论文主张；LITE 不得追溯为 FROZEN）
Frozen input hashes（实现前记录，交付前复验）:
  AGENTS.md 0758c3aa…
  docs/HANDOVER.md a4891c9c…
  memory/project-todo.md 9166bae6…
  scripts/sfq_metrics_v2.py 6be62ed0…（只读，不修改）
  test/metrics/test_sfq_metrics_v2.py 7f0898e9…
  test/metrics/test_sfq_metrics_v2_m5.py b4f5b805…
  test/metrics/test_sfq_metrics_v2_m6.py d18383fd…
  test/standard/test_jtl.cir 4d21cb18…
  bump_0.csv 2420b99a… / bump_300u.csv dfe20406…
  bq_v4_sweep110.csv 75fd3cb8… / test_bq_v4_sweep.cir 09b5a57f…
  circuits/models/jjmit.cir 19862d1f… / circuits/standard/JTL.cir ac02fc93…
josim-cli（主仓库只读二进制，不创建 build）: /home/howard/JoSIM/build/josim-cli，v2.7.2837d13 compiled on May 30 2026 at 20:37:57，sha256 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2
AC4 参考定义：bq_v4_sweep110.csv 时间网格存在偏移，必须按"实际时间最近行"选样本（ref=5.0 ps 行，targets=49/99/149/199/249/299 ps 最近行）；已用此方法精确复现全部 6 个常量（err=0.00）
Ambiguity: none
Preflight result: PASS

## Summary

M7 三个校准组件全部完成：

- **M7A**（`test/metrics/test_sfq_metrics_v2_m7.py` 内 18 个测试中的合成部分）：raw rad→turns 含符号、非均匀实际时间梯形积分、同 JJ P/V 方向符号、匹配控制相减、半开窗端点、严格阈值相等不激活、分离聚类不桥接、畸形/非单调输入拒绝——oracle 全部为字面常量与初等算术，不调用生产辅助函数；
- **M7B**：`test/metrics/m7_canonical_jtl.cir`（源自 `test/standard/test_jtl.cir`，diff 仅 .print 块：直接 `V(B1|XDUT)`/`V(B2|XDUT)` 与 `P(B1|XDUT)`/`P(B2|XDUT)` 同 JJ 探针，同一单输入 PWL、第二 JTL 负载、`.tran 0.1p 50p`）。唯一 run `m7-jtl-cal-20260812-01` 保存输入快照/include 闭包/二进制版本哈希/stdout-stderr/raw CSV/manifest。测试在预声明窗 `[6e-12, 50e-12)`（后偏置/运行末）用实际 CSV 时间轴独立重算相位差与梯形面积，与生产输出在浮点精度内一致（places=9），raw signed residual 如实报告（B1 −1.41e-4、B2 +1.41e-3 turns，不作接受/拒绝判定）；
- **M7C**：冻结 DCSFQ 300u−0u 匹配控制重放（窗口 6/9/50/100/190 ps、方向 −1/+1/+1、阈值 0.3）精确复现 B1/B2/B3 控制校正圈数（差异 <1e-14）、pre/activity/post=30/409/900、聚类 1/0/1 与 0/0/0；bq_v4_sweep110.csv 的 JTL-B1 相位增量按**实际时间最近行**（5 ps 参考行 + 49/99/149/199/249/299 ps 最近行）独立计算，6 个冻结常量全部精确复现（err=0.00，容差 1e-9 远满足）。

## Changes

- `test/metrics/test_sfq_metrics_v2_m7.py`（新增，18 测试）：RadToTurnsSignTests（4）、TrapezoidNonUniformTests（4）、OrientationSignTests（2）、WindowAndClusteringTests（5）、CanonicalJtlCalibrationTests（1）、HistoricalDcsfqReplayTests（1）、HistoricalBqV4RegressionTests（1）。
- `test/metrics/m7_canonical_jtl.cir`（新增）：源自 test_jtl.cir，.print 改为直接同 JJ V/P。
- `research/tasks/M7-LITE-001/attempts/A01/`：RESULT.md、logs/（tests.log、scope-diff.log）、runs/m7-jtl-cal-20260812-01/（manifest、inputs×3、raw CSV、run.log）。

## Verification

| command | result |
|---|---|
| `python3 test/metrics/test_sfq_metrics_v2_m7.py` | PASS — 18/18 |
| `python3 test/metrics/test_sfq_metrics_v2.py`（M4 回归） | PASS — 15/15，未改动 |
| `python3 test/metrics/test_sfq_metrics_v2_m5.py`（M5 回归） | PASS — 29/29，未改动 |
| `python3 test/metrics/test_sfq_metrics_v2_m6.py`（M6 回归） | PASS — 21/21，未改动 |
| M7B 运行 | PASS — exit 0，无 solver 警告；V/P 直接同 JJ 列齐备 |
| 冻结输入哈希复验（交付前） | PASS — 14/14 与 Preflight 一致 |
| scope 检查 | PASS — 仅两个允许的新文件 + attempts |

M7B raw signed residual（[6e-12,50e-12) 窗，实际时间轴，同 JJ 直接 V/P，仅报告不判定）：
| 结 | residual_turns |
|---|---|
| B1|XDUT | −1.412755e-04 |
| B2|XDUT | +1.412931e-03 |

## Evidence

- `research/tasks/M7-LITE-001/attempts/A01/logs/tests.log` — 9c6b8094f028b76b8b2e09f50bc53008669cd37b0cbfdd28b725dc9699152c91（83 测试全量）
- `research/tasks/M7-LITE-001/attempts/A01/logs/scope-diff.log` — b542b6b3919066ac452acd2af33e0273ba20334ccf4215a7b77189ec1585a2c4
- `research/tasks/M7-LITE-001/attempts/A01/runs/m7-jtl-cal-20260812-01/manifest.yaml` — 见下方清单
- `research/tasks/M7-LITE-001/attempts/A01/runs/m7-jtl-cal-20260812-01/raw/m7-jtl-cal-20260812-01.csv` — 728c112ec18864a9f84a0f73e3ffedf39051b528c8e3785b5632f409190cda52
- `research/tasks/M7-LITE-001/attempts/A01/runs/m7-jtl-cal-20260812-01/logs/run.log` — 运行日志（exit 0）
- 输入快照（runs/…/inputs/）：m7_canonical_jtl.cir d1c7e3cb…、JTL.cir ac02fc93…、jjmit.cir 19862d1f…（与冻结值一致）
- 新增文件：test_sfq_metrics_v2_m7.py 209a530b…、m7_canonical_jtl.cir d1c7e3cb…

## Changed files

- `test/metrics/test_sfq_metrics_v2_m7.py`（新增，允许路径）
- `test/metrics/m7_canonical_jtl.cir`（新增，允许路径）
- `research/tasks/M7-LITE-001/attempts/A01/**`（证据文件）

## Limitations / anomalies

- **AC4 参考定义澄清**：bq_v4_sweep110.csv 时间网格存在偏移（行号 ≠ 时间×10），必须按"实际时间最近行"选择参考样本与目标样本；用该方法 6 个常量全部精确复现（err=0.00）。测试中同时断言所选行时间距目标 <0.11 ps。
- M7B 残差（~1e-4/1e-3 turns）为管线原始值，按 TASK 要求仅报告、不判定接受性（容差由 M9 冻结）。
- M7C 的 bq_v4 常量是**周期历史相位平台回归常量**，明确不是物理事件计数，也不是 BQ 接口 Gate（TASK AC4 要求声明）。
- 未运行 M8（收敛）、未冻结任何容差、未做任何 candidate 评估。
- josim-cli 用主仓库只读二进制（未在 worktree 创建 build）。

## Claim

M7A/M7B/M7C 校准实现与确定性回归行为已验证：AC1–AC5 全部满足。生产实现与独立初等算术在浮点精度内一致；冻结历史常量（DCSFQ 控制校正、bq_v4 六点相位平台增量）精确复现。本结果不建立任何物理事件数、SFQ、下游接收、fluxoid、BVM/BQ/DCSFQ 路线结果、metric 容差、收敛结果、接口 Gate、候选判定或论文主张；LITE 证据不得追溯为 FROZEN。M8/M9/M10/M11A/B 均未启动（见 TASK Explicit remainder）。

---

## Delivery snapshot（RESULT 完成后由授权 owner 追加）

Delivery snapshot commit: 936df75af73ddaa1625e29dd65411ee50efa11b9
Snapshot owner: CODEX
Snapshot scope check: PASS
