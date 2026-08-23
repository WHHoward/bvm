# PAPER-SL-Q3 — L1 Routing Closure 报告

## 结论等级

主 verdict：**`ROUTING_GAIN_WITH_BJL1_SUBTHRESHOLD`**

本 Exploration 使用 accepted PAPER-SL-Q2 40-uA replay 作为 source-isolated QB fixture；没有连接 physical BVM/JSL，也没有接 JTL。基线和单点都使用同一 0.0125 ps / 170 ps source deck；唯一电路变更是 native QB 的 `L1=3.91 pH -> 4.50 pH`。phase/area 事件判断使用同一 JJ、同一 monotonic segment、直接 V(BJJ) 和 CSV 实际时间。

## 事件计数摘要

表格中的 `main/post` 是 `[94,130) ps` 与 `[140,170) ps` 内满足 phase/area 一致性的完整 event units；它不是 derivative/peak 计数。

| case | baseline BJs | baseline BJL1 | baseline BJL2 | L1=4.50 BJs | L1=4.50 BJL1 | L1=4.50 BJL2 |
|---|---:|---:|---:|---:|---:|---:|
| paper-j1-logical1-read0-control | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| paper-j0-logical0-read0-control | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| paper-j0-logical0-read | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| paper-j1-logical1-read | 14 / 0 | 0 / 0 | 0 / 0 | 14 / 0 | 0 / 0 | 0 / 0 |

## Continuous phase / same-JJ voltage-area

下表是每个 case 主 `[94,130) ps` 中与 dominant BJs window 配对的最大 monotonic segment；它用于 routing comparison，不把 total phase range 当作 event。

| case | JJ | baseline segment (ps) | baseline Δturn | baseline area (Φ0) | perturbed segment (ps) | perturbed Δturn | perturbed area (Φ0) | phase/area aligned | complete event |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| paper-j1-logical1-read0-control | BJs | 95.3875–96.7 | 0.000180388 | 0.000180427 | 95.3875–96.7 | 0.000180388 | 0.000180427 | yes | no |
| paper-j1-logical1-read0-control | BJL1 | 94–94.9 | -7.21768e-05 | -7.21952e-05 | 94–94.9125 | -7.67604e-05 | -7.67848e-05 | yes | no |
| paper-j1-logical1-read0-control | BJL2 | 94.325–95.4 | -2.5051e-05 | -2.50475e-05 | 94.3375–95.425 | -2.44462e-05 | -2.44477e-05 | yes | no |
| paper-j0-logical0-read0-control | BJs | 95.3875–96.7 | -0.000180388 | -0.000180427 | 95.3875–96.7 | -0.000180388 | -0.000180427 | yes | no |
| paper-j0-logical0-read0-control | BJL1 | 94–94.8875 | 7.21768e-05 | 7.22008e-05 | 94–94.9125 | 7.67445e-05 | 7.67842e-05 | yes | no |
| paper-j0-logical0-read0-control | BJL2 | 94.3125–95.4 | 2.50669e-05 | 2.50616e-05 | 94.35–95.4375 | 2.44303e-05 | 2.44261e-05 | yes | no |
| paper-j0-logical0-read | BJs | 106.487–107.7 | 0.0236757 | 0.0236817 | 106.487–107.7 | 0.0236757 | 0.0236817 | yes | no |
| paper-j0-logical0-read | BJL1 | 108.162–109.312 | 0.0193068 | 0.0193122 | 108.175–109.325 | 0.0199779 | 0.0199835 | yes | no |
| paper-j0-logical0-read | BJL2 | 108.625–109.812 | 0.00662115 | 0.00662284 | 108.65–109.837 | 0.00643323 | 0.00643489 | yes | no |
| paper-j1-logical1-read | BJs | 102.55–120.263 | 14.0921 | 14.0921 | 102.55–120.263 | 14.0921 | 14.0921 | yes | yes |
| paper-j1-logical1-read | BJL1 | 102.525–106.875 | 0.815414 | 0.815445 | 102.5–106.837 | 0.82107 | 0.821102 | yes | no |
| paper-j1-logical1-read | BJL2 | 100.262–107.425 | 0.944323 | 0.944333 | 100.3–107.4 | 0.950537 | 0.950548 | yes | no |

## BJs→BJL1 node2 routing

node2 KCL 为 `I(BJs)=I(L1)+I(BJL1)+I(RJ1)`。`F_local` 与 `F_L1` 是配对 BJL1 segment 内 signed current-area 的派生分流指标；KCL residual 用 dominant BJs interval 计算。

| case | baseline F_local | L1=4.50 F_local | ΔF_local | baseline F_L1 | L1=4.50 F_L1 | ΔF_L1 | baseline node2 KCL RMS (uA) | perturbed node2 KCL RMS (uA) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| paper-j1-logical1-read0-control | ill-conditioned | ill-conditioned | ill-conditioned | ill-conditioned | ill-conditioned | ill-conditioned | 4.09019e-06 | 4.42541e-06 |
| paper-j0-logical0-read0-control | ill-conditioned | ill-conditioned | ill-conditioned | ill-conditioned | ill-conditioned | ill-conditioned | 4.03467e-06 | 3.87214e-06 |
| paper-j0-logical0-read | ill-conditioned | ill-conditioned | ill-conditioned | ill-conditioned | ill-conditioned | ill-conditioned | 3.80723e-06 | 4.26936e-06 |
| paper-j1-logical1-read | 0.21866 | 0.224945 | 0.00628481 | 0.78134 | 0.775055 | -0.0062848 | 3.82119e-06 | 3.88815e-06 |

配对窗口 signed current-area（单位 µA·ps）如下；它直接显示 node2 分流的分子/分母，READ=0 control 的近零 BJs signed area 不用于计算有意义的 fraction。

| case | baseline ∫BJs | L1=4.50 ∫BJs | baseline ∫BJL1 | L1=4.50 ∫BJL1 | baseline ∫RJ1 | L1=4.50 ∫RJ1 | baseline ∫L1 | L1=4.50 ∫L1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| paper-j1-logical1-read0-control | -0.0062748 | -0.00627722 | 15.533 | 15.3846 | -0.00452387 | -0.00481146 | -15.5348 | -15.3861 |
| paper-j0-logical0-read0-control | 0.00626818 | 0.00627722 | 15.3136 | 15.381 | 0.00452422 | 0.00481142 | -15.3118 | -15.3795 |
| paper-j0-logical0-read | 0.759008 | 0.771841 | 19.1975 | 18.7508 | 1.21013 | 1.2522 | -19.6487 | -19.2312 |
| paper-j1-logical1-read | 220.477 | 221.5 | -2.88744 | -1.62633 | 51.0971 | 51.4516 | 172.268 | 171.674 |

### Read/control-subtracted RMS

`δI(t)=I_read(t)-I_READ0_control(t)`，仅在 `[94,130) ps` 逐点相减；这是同一 source fixture 下的 routing diagnostic，不是事件判据。

| set | baseline RMS δBJs (uA) | L1=4.50 RMS δBJs | baseline RMS δlocal (uA) | L1=4.50 RMS δlocal | baseline G_local | L1=4.50 G_local | baseline RMS δL1 | L1=4.50 RMS δL1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| logical1_read_minus_read0_control | 27.0892 | 27.0892 | 13.956 | 14.2648 | 0.515185 | 0.526585 | 24.8732 | 24.837 |
| logical0_read_minus_read0_control | 1.31576 | 1.31576 | 1.19291 | 1.23255 | 0.906627 | 0.936753 | 1.01325 | 0.984863 |

说明：`RMS(local)` 是先将 `δI(BJL1)+δI(RJ1)` 逐点相加后再求 RMS，不是两个 RMS 的相加；完整 waveform、比值和 signed area 也保存在 `metrics.json` 的 `control_subtracted` 字段中。

## Settled / post behavior

各 case 的 post-window phase p2p、branch current ranges、完整 segment 列表和 phase/area consistency 保存在 `metrics.json`。本报告只把 post-window 中满足同一-JJ phase/area 条件的 segment 计入 event summary；未满足者保留为 activity，不称 event。

## Observed

- 四个单点 raw 均生成且 exit code 为 0；首跑 logical1 READ=0 control 没有 startup/free-running 或完整 phase/area-consistent transition，因此按预注册停止条件完成全部 matched cases。
- 具体 BJL1/BJL2 的 phase、同段 voltage area、KCL 和 read1/read0/control event count 见上表和 `metrics.json`；任何 sub-turn excursion 均不被写成 switching event。
- 本 replay fixture 不包含 canonical BVM 的 `SL/N6/I(L_SL)/JM/JS` 列，因此本轮不能独立证明 physical BVM source/back-action guard；这不是“guard 通过”，而是 replay scope 的已知边界。

## Derived

- `L1=4.50 pH` 的效果以 signed branch split、control-subtracted waveform 和 same-JJ phase/area 三组量共同判断；不能以 `I/Ic`、电压峰值或 total phase range 单独判定。READ=0 control 的 signed-area fraction 因分母接近零而标为 ill-conditioned，不参与 read1 routing gain 的解释。
- 如果 `F_local`/control-subtracted local routing 提高但 BJL1 仍没有完整同段 transition，最强结论只能是 routing gain with subthreshold BJL1，不能推断 threshold 已闭合。

## Inference

本单点只用于裁决 L1 routing hypothesis。在当前 scope 内，不能把一个 bounded local response升级为 downstream SFQ delivery；也不能从单点失败宣称所有 L1/load-line 方向不可能。

## Unknown

- 没有 physical BVM→12JSL→QB 接入；source/back-action guard 仍需后续具有 BVM 列的实验才能验证。
- 本轮未做 L1 sweep、convergence rerun 或 BJL1/BJL2 ratio tuning；单点结果不定义连续参数窗口。

## Stop rule / disposition

本 checkpoint 后不追加 L1 sweep，不改变 BJL1/BJL2 AREA、central bias、L2、RB/RJ1/RJ2，不连接 physical BVM/JSL/QB 或 JTL。若 routing gain 但 BJL1 仍 subthreshold，关闭本轮 L1 单点并保留 bounded routing conclusion。

## Provenance

- preregistration：`PREREGISTRATION.md`；
- Stage-A：`analysis/ANALYTIC_PRECHECK.md`；
- modified fixture：`inputs/l1-4p5/`；
- source deck identity/hash：`inputs/deck-hashes.json`；
- raw/log/hash manifest：`manifest.yaml`、`sha256sums.txt`；
- phase/area helper dependency：accepted `test/exploration/paper-sl-q3-pre-20260824/analysis/analyze_q3_pre.py`。
