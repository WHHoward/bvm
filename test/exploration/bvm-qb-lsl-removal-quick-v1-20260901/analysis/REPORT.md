# BVM_QB_LSL_REMOVAL_QUICK_V1 分析报告

## Scope and provenance

本报告只分析一个新 candidate raw：13 ps / 12×320 / logical1_read。
BASELINE 是父矩阵已存在且 hash、模型、solver、metric spec 均匹配的 physical raw；
grounded-JSL source 与 ideal replay QB 是只读 reference。第一次 runner 后处理因
`I(Lin|XBQ)` 大小写错误而失败，但 solver return code=0 且 raw QA 有效；该失败及
raw 已保留，修正分析没有重跑第二个 science case。

| case | meaning | samples | time (ps) | raw hash prefix |
|---|---|---:|---:|---|
| grounded_source | grounded-JSL source reference | 13599 | [0, 169.988] | b92056235a06 |
| ideal_replay_qb | ideal replay QB | 13599 | [0, 169.988] | be7e0403586b |
| baseline_physical | baseline physical QB | 13599 | [0, 169.988] | 9aecc3f62614 |
| candidate_lsl_removed | LSL-removed candidate | 13599 | [0, 169.988] | d31cdfdddcf5 |

父 baseline reuse checks：`PASS`。canonical BVM、JJ model、QB model、solver
v2.7.2837d13 和 `METRIC_SPEC_V2.md` hash 均与父矩阵 manifest 一致。

## Fixed windows

| Window | interval (ps) | samples | interpretation |
|---|---:|---:|---|
| W2_pre_read_idle | [80, 90) | 800 | pre-READ idle / stored-state safety |
| W3_read | [95, 110) | 1200 | READ dynamic mismatch |
| W4_post_read_observation | [110, 130) | 1600 | post-READ observation |

W3 `[95,110)` ps 是 READ waveform diagnostic window；它不作为 BJL2 strict-event
activity cutoff。strict-event 使用独立、预先固定的窗口：

| Strict window | interval (ps) | interpretation |
|---|---:|---|
| READ diagnostic | [95,110) | waveform comparison only |
| activity | [95,115) | include complete READ-associated monotonic segment |
| post | [115,130) | post/retrap boundedness observation |
| post tail | [125,130) | fixed tail boundedness check |

ideal replay、baseline physical 和 candidate 使用完全相同的 strict-event windows；
strict label 仍是 local phase/area compatibility diagnostic，不是 SFQ count 或 system Gate。

## Pre-READ BVM state safety

| BVM phase | baseline W2 median | candidate W2 median | baseline→candidate W2 max diff (turns) |
|---|---:|---:|---:|
| `P(B_JM1|XBVM1)` | 0.940776 | 0.940776 | 9.5493e-07 |
| `P(B_JM2|XBVM1)` | 0.0504915 | 0.0504912 | 1.6393e-06 |
| `P(B_JS1|XBVM1)` | 0.0424946 | 0.0424951 | 1.32894e-05 |
| `P(B_JS2|XBVM1)` | -0.0424923 | -0.0424945 | 9.67662e-06 |

W2 BVM phase max difference = `1.32894e-05 turns`；
source-current max difference = `0.000800136 uA`；
pre-READ safety rule result = `True`。

## Source/JSL direction

### W3 `I(B_LD1)` waveform diagnostics

| condition | positive peak (uA) | peak time (ps) | positive area (uA*ps) | negative area (uA*ps) | signed area (uA*ps) | RMS (uA) |
|---|---:|---:|---:|---:|---:|---:|
| grounded-JSL source reference | 79.0668 | 104.237 | 713.088 | 0 | 713.088 | 50.6141 |
| baseline physical QB | 68.1454 | 103.762 | 471.94 | -7.81556 | 464.125 | 36.8867 |
| LSL-removed candidate | 67.7227 | 103.737 | 468.548 | -7.8428 | 460.705 | 36.6896 |

baseline→candidate W3 `I(B_LD1)` max pointwise difference = `6.32347 uA`；
candidate-vs-grounded W3 RMS distance reduction = `-0.288176%`。
positive/negative/signed area are current-time waveform diagnostics, not SFQ quantities。

### W3 BVM JS1/JS2 trajectory

| signal | baseline p2p / endpoint Δ | candidate p2p / endpoint Δ | baseline→candidate max diff (turns) |
|---|---:|---:|---:|
| `P(B_JS1|XBVM1)` | 5.27707 / -5.26947 | 5.30338 / -5.29571 | 0.0344921 |
| `P(B_JS2|XBVM1)` | 5.81751 / -5.81751 | 5.84021 / -5.84021 | 0.0227082 |
| `P(B_JM2|XBVM1)` | 0.406177 / 0.137179 | 0.406396 / 0.139545 | 0.002366 |

Source-to-grounded W3 RMS distance reduction（正值表示 candidate 更靠近 grounded reference）：

| source signal | baseline RMS distance | candidate RMS distance | reduction |
|---|---:|---:|---:|
| `I(B_LD1)` | 28.4735 | 28.5555 | -0.288176% |
| `I(B_LD12)` | 28.4735 | 28.5555 | -0.288176% |
| `I(L_PSL|XBVM1)` | 28.4735 | 28.5555 | -0.288176% |
| `V(SL1)` | 0.895583 | 0.892945 | 0.294592% |

candidate 没有 `L_SL` 支路，因此不伪造 `I(L_SL|XBVM1)`；candidate 使用
`V(SL1)` 和 `I(L_PSL|XBVM1)` 等价的 source-port/support probes。

## QB internal trajectory against ideal replay

### W2 pre-READ

| QB signal | baseline stat | candidate stat | baseline→candidate max diff | ideal→baseline RMS | ideal→candidate RMS |
|---|---:|---:|---:|---:|---:|
| `P(BJS|XBQ)` | median=7.65076e-07, p2p=0.000162021 turns | median=1.2868e-06, p2p=0.000163457 turns | 2.43679e-06 turns | 9.34969e-05 | 9.45925e-05 |
| `P(BJL1|XBQ)` | median=0.0689931, p2p=0.000111138 turns | median=0.0689926, p2p=0.000115324 turns | 2.96028e-06 turns | 8.08878e-05 | 8.24551e-05 |
| `P(BJL2|XBQ)` | median=0.0599999, p2p=3.51414e-05 turns | median=0.06, p2p=3.64783e-05 turns | 1.01859e-06 turns | 2.75862e-05 | 2.81161e-05 |
| `I(LIN|XBQ)` | mean=-0.00064046, p2p=0.0277605, RMS=0.00712757, max=0.0144479 uA | mean=-0.000670506, p2p=0.0288183, RMS=0.0074081, max=0.0150018 uA | 0.000800136 uA | 0.0213712 | 0.0217861 |
| `I(L1|XBQ)` | mean=-15.1217, p2p=0.03018, RMS=15.1217, max=15.1361 uA | mean=-15.1218, p2p=0.03131, RMS=15.1218, max=15.1366 uA | 0.0008 uA | 0.0215392 | 0.0219567 |
| `I(L2|XBQ)` | mean=19.8783, p2p=0.03018, RMS=19.8783, max=19.8941 uA | mean=19.8782, p2p=0.03131, RMS=19.8782, max=19.8947 uA | 0.0008 uA | 0.0215392 | 0.0219567 |
| `I(RB|XBQ)` | mean=35, p2p=0, RMS=35, max=35 uA | mean=35, p2p=0, RMS=35, max=35 uA | 0 uA | 0 | 0 |

### W3 READ

| QB signal | baseline stat | candidate stat | baseline→candidate max diff | ideal→baseline RMS | ideal→candidate RMS | reduction |
|---|---:|---:|---:|---:|---:|---:|
| `P(BJS|XBQ)` | median=0.22447, p2p=2.77658 turns | median=0.226803, p2p=2.80051 turns | 0.0613319 turns | 2.2452 | 2.22563 | 0.871821% |
| `P(BJL1|XBQ)` | median=0.213024, p2p=0.278799 turns | median=0.212562, p2p=0.281123 turns | 0.0158775 turns | 0.519117 | 0.521443 | -0.448068% |
| `P(BJL2|XBQ)` | median=0.124762, p2p=0.133621 turns | median=0.124872, p2p=0.1346 turns | 0.00676105 turns | 0.43001 | 0.431587 | -0.366914% |
| `I(LIN|XBQ)` | mean=30.9447, p2p=78.5275, RMS=36.8867, max=68.1454 uA | mean=30.717, p2p=77.7329, RMS=36.6896, max=67.7227 uA | 6.32347 uA | 28.4735 | 28.5555 | -0.288176% |
| `I(L1|XBQ)` | mean=1.60251, p2p=47.2152, RMS=12.9793, max=24.327 uA | mean=1.45673, p2p=46.7786, RMS=12.9582, max=24.3049 uA | 2.96844 uA | 28.3754 | 28.7001 | -1.14401% |
| `I(L2|XBQ)` | mean=36.6025, p2p=47.2152, RMS=38.8025, max=59.327 uA | mean=36.4567, p2p=46.7786, RMS=38.6638, max=59.3049 uA | 2.96844 uA | 28.3754 | 28.7001 | -1.14401% |
| `I(RB|XBQ)` | mean=35, p2p=0, RMS=35, max=35 uA | mean=35, p2p=0, RMS=35, max=35 uA | 0 uA | 0 | 0 | n/a% |

## BJL2 strict local diagnostic

使用 shared `bvmtools.sfq`；同一 `P(BJL2|XBQ)`/`V(BJL2|XBQ)`、同一方向、
同一实际 CSV 时间网格和 task-local frozen compatibility arithmetic。以下不是
系统事件计数或 Formal PASS：

| case | classification | largest segment phase (turns) | area (Phi0) | residual (turns) | complete segments | post bounded |
|---|---|---:|---:|---:|---:|---|
| ideal replay QB | CLEAN_ONE_SFQ_CANDIDATE | 1.01603 | 1.01604 | -7.91154e-06 | 1 | True |
| baseline physical QB | SUBTHRESHOLD | -0.122128 | -0.122131 | 3.23871e-06 | 0 | True |
| LSL-removed candidate | SUBTHRESHOLD | -0.121208 | -0.121212 | 4.20732e-06 | 0 | True |

## Directional outcome

Outcome: `QUICK_NO_EFFECT`；physical disposition: `INCONCLUSIVE`；
Human gate: `USER_REVIEWED`；next step authorized: `false`；next action: `STOP`。

source signals meeting the pre-registered ≥20% RMS reduction: `[]`；
QB signals meeting it: `[]`；
worsened primary signals: `[]`。
若各层方向冲突，本 QUICK 不强行升级为 promising 或 root-cause claim。

## Limitations

- 只有一个 candidate condition；无 logical0/no-read/control/timestep ladder/sweep。
- W4 是 post-READ observation，不自动等价于无限时间 retrap 或最终稳定。
- phase turns、voltage area 和 current-time area 均不能单独证明下游 SFQ delivery。
- 本轮不更新 HANDOVER、project-todo 或 paper-level claim。

## Artifacts

- `RESULT_BRIEF.md`：面向人工审核的关键结论。
- `plots/RESULT_OVERVIEW.html`：唯一 compact classic overview，含 JS1/JS2、BJS、L1、BJL1、BJL2。
- `analysis/metrics.json`：所有固定窗统计、距离和 strict-local 详情。
- `analysis/provenance.json`：candidate/baseline raw、模型、solver、spec 和失败尝试记录。

`QUICK_PROMISING/QUICK_NO_EFFECT/QUICK_OPPOSITE/QUICK_AMBIGUOUS` 仅为本任务方向性 Quick 分类；不自动 Promotion。