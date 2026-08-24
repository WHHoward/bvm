# PAPER-SL-Q5 — L1/L2 placement analysis report

## Verdict

**Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT**。Q5 仍没有 BJL1/BJL2 complete event；本单点不升级为 downstream SFQ evidence。

Q5 直接从 accepted Q2 `inputs/40u` 构建，将 `L1=3.91p → 4.50p` 与 `L2=3.91p → 4.50p` 同时改变；Q3 仅作为 sibling comparator。所有事件判断使用同一 JJ、同一 monotonic segment 的 continuous unwrapped phase 与直接 voltage-area，未使用 `I>Ic`、voltage peak 或旧 fast-event 指标。

## Observed

- 四个 Q5 JoSIM runs 均返回 0，CSV 均为 13,599 个 data rows，stderr 为空；首个 logical1 READ=0 control 已先通过 stop gate。
- Q5 四 case 的完整 segment/event 汇总如下；`complete_event_count` 仅统计 phase/area-consistent 的 ≥1 turn segment。
- read1 的 BJs 是预期的 multi-turn source activity，因此表中 BJs 的 segment count 不等同于输出 event；本轮 local-output 判据只对 BJL1/BJL2 读取。

| case | JJ | main phase range (turn) | post phase range (turn) | complete event count | main largest segment | post largest segment |
|---|---|---:|---:|---:|---|---|
| Q5_paper-j1-logical1-read0-control | BJs | 0.000180388 | 1.02104e-05 | 0 | [95.3875, 96.7] ps; Δ=0.000180388 turn; area=0.000180427 Φ0; consistent=yes | [141.088, 142.575] ps; Δ=1.02104e-05 turn; area=1.02122e-05 Φ0; consistent=yes |
| Q5_paper-j1-logical1-read0-control | BJL1 | 8.08666e-05 | 1.30507e-06 | 0 | [94, 94.9375] ps; Δ=-8.08666e-05 turn; area=-8.08862e-05 Φ0; consistent=yes | [143.737, 144.9] ps; Δ=-1.30507e-06 turn; area=-1.29256e-06 Φ0; consistent=yes |
| Q5_paper-j1-logical1-read0-control | BJL2 | 2.36823e-05 | 3.81972e-07 | 0 | [94.375, 95.4625] ps; Δ=-2.36823e-05 turn; area=-2.36786e-05 Φ0; consistent=yes | [144.3, 145.463] ps; Δ=-3.81972e-07 turn; area=-3.68264e-07 Φ0; consistent=yes |
| Q5_paper-j0-logical0-read0-control | BJs | 0.000180388 | 1.02104e-05 | 0 | [95.3875, 96.7] ps; Δ=-0.000180388 turn; area=-0.000180427 Φ0; consistent=yes | [141.088, 142.575] ps; Δ=-1.02104e-05 turn; area=-1.02122e-05 Φ0; consistent=yes |
| Q5_paper-j0-logical0-read0-control | BJL1 | 8.08507e-05 | 1.32099e-06 | 0 | [94, 94.9375] ps; Δ=8.08507e-05 turn; area=8.08857e-05 Φ0; consistent=yes | [143.713, 144.863] ps; Δ=1.32099e-06 turn; area=1.3094e-06 Φ0; consistent=yes |
| Q5_paper-j0-logical0-read0-control | BJL2 | 2.36823e-05 | 3.81972e-07 | 0 | [94.375, 95.4625] ps; Δ=2.36823e-05 turn; area=2.36784e-05 Φ0; consistent=yes | [144.312, 145.45] ps; Δ=3.81972e-07 turn; area=3.67897e-07 Φ0; consistent=yes |
| Q5_paper-j0-logical0-read | BJs | 0.0344871 | 0.001489 | 0 | [106.487, 107.7] ps; Δ=0.0236757 turn; area=0.0236817 Φ0; consistent=yes | [140.275, 141.488] ps; Δ=-0.001489 turn; area=-0.00148939 Φ0; consistent=yes |
| Q5_paper-j0-logical0-read | BJL1 | 0.0242538 | 0.00106457 | 0 | [108.188, 109.337] ps; Δ=0.0205847 turn; area=0.0205904 Φ0; consistent=yes | [140.787, 141.863] ps; Δ=0.00106457 turn; area=0.00106492 Φ0; consistent=yes |
| Q5_paper-j0-logical0-read | BJL2 | 0.00831414 | 0.000326108 | 0 | [108.675, 109.863] ps; Δ=0.00624333 turn; area=0.00624493 Φ0; consistent=yes | [140.213, 141.3] ps; Δ=-0.000326108 turn; area=-0.000326211 Φ0; consistent=yes |
| Q5_paper-j1-logical1-read | BJs | 14.3749 | 0.242442 | 14 | [102.55, 120.263] ps; Δ=14.0921 turn; area=14.0921 Φ0; consistent=yes | [141.238, 142.825] ps; Δ=-0.242442 turn; area=-0.24248 Φ0; consistent=yes |
| Q5_paper-j1-logical1-read | BJL1 | 1.16661 | 0.0117703 | 0 | [99.7875, 105] ps; Δ=0.748868 turn; area=0.748895 Φ0; consistent=yes | [140.037, 141.137] ps; Δ=-0.0117703 turn; area=-0.0117741 Φ0; consistent=yes |
| Q5_paper-j1-logical1-read | BJL2 | 1.05879 | 0.00332825 | 0 | [100.312, 107.275] ps; Δ=0.968179 turn; area=0.968189 Φ0; consistent=yes | [140.55, 141.65] ps; Δ=-0.00332825 turn; area=-0.00332931 Φ0; consistent=yes |

## Settled post-window operating points

READ=0 post window `[140,170)` ps 的均值/范围用于比较静态工作点；不以该表的电流比值判定 event。

| case | I(BJs) mean | I(BJL1) mean | I(BJL2) mean | I(L1) mean | I(L2) mean | I(LIN) mean | I(RB) mean | I(RJ1) mean | I(RJ2) mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q5_paper-j1-logical1-read0-control | 1.0098e-08 | 17.3806 | 22.6194 | -17.3806 | 22.6194 | 1.0098e-08 | 40 | -1.46715e-07 | -6.51738e-07 |
| Q5_paper-j0-logical0-read0-control | -1.0098e-08 | 17.3806 | 22.6194 | -17.3806 | 22.6194 | -1.0098e-08 | 40 | 1.46713e-07 | 6.51737e-07 |
| Q5_paper-j0-logical0-read | -0.000930213 | 17.3818 | 22.6191 | -17.382 | 22.618 | -0.000930213 | 40 | -0.000764659 | -0.000435354 |
| Q5_paper-j1-logical1-read | -0.0180171 | 17.3781 | 22.6127 | -17.384 | 22.616 | -0.0180171 | 40 | -0.0120943 | -0.000186808 |

## Q2/Q3/Q5 read1 comparison

`F_local`/`F_L1` 是 paired dominant BJL1 interval 的 signed-area routing fractions；`G_local` 是 `[94,130)` ps 中 read1 减去 logical1 READ=0 后，local `(BJL1+RJ1)` RMS 与 BJs RMS 的比值。正负 current area 仅作波形抵消诊断。

| dataset | F_local | F_L1 | G_local | BJL1 +area | BJL1 -area | BJL1 signed | cancellation | BJL1 forward | BJL1 backward | BJL2 largest | BJL2/BJL1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q2 | 0.21866 | 0.78134 | 0.515185 | 41.4395 | -44.3269 | -2.88744 | 0.966334 | 0.815414 | -0.135229 | 0.944323 | 1.15809 |
| Q3 | 0.224945 | 0.775055 | 0.526585 | 44.0662 | -45.6925 | -1.62633 | 0.981881 | 0.82107 | -0.141668 | 0.950537 | 1.15768 |
| Q5 | 0.343485 | 0.656515 | 0.51974 | 98.0918 | -47.5521 | 50.5397 | 0.652992 | 0.748868 | -0.183874 | 0.968179 | 1.29286 |

### Major BJL1 phase segments

| dataset | positive segment | negative segment |
|---|---|---|
| Q2 | [102.525, 106.875] ps; Δ=0.815414 turn; area=0.815445 Φ0; consistent=yes | [111.35, 112.5] ps; Δ=-0.135229 turn; area=-0.135267 Φ0; consistent=yes |
| Q3 | [102.5, 106.837] ps; Δ=0.82107 turn; area=0.821102 Φ0; consistent=yes | [111.362, 112.525] ps; Δ=-0.141668 turn; area=-0.141708 Φ0; consistent=yes |
| Q5 | [99.7875, 105] ps; Δ=0.748868 turn; area=0.748895 Φ0; consistent=yes | [106.712, 108.112] ps; Δ=-0.183874 turn; area=-0.183907 Φ0; consistent=yes |

### Onset/delay/overlap

| dataset | BJs→BJL1 delay (ps) | BJs/BJL1 overlap (ps) | BJL1→BJL2 delay (ps) | BJL1/BJL2 overlap (ps) |
|---|---:|---:|---:|---:|
| Q2 | -0.025 | 4.325 | -2.2625 | 4.35 |
| Q3 | -0.05 | 4.2875 | -2.2 | 4.3375 |
| Q5 | -2.7625 | 2.45 | 0.525 | 4.6875 |

### KCL residuals

残差单位为 µA，在各 read1 dominant BJs interval 上计算：
`node2: I(BJs)-I(L1)-I(BJL1)-I(RJ1)`；`node3: I(L1)+I(RB)-I(L2)`；`node4: I(L2)-I(L0)-I(BJL2)-I(RJ2)`。

| dataset | node2 max/RMS | node3 max/RMS | node4 max/RMS |
|---|---:|---:|---:|
| Q2 | 1e-05/3.82119e-06 | 5e-05/7.11273e-06 | 5.5e-05/8.37259e-06 |
| Q3 | 1e-05/3.88815e-06 | 5e-05/6.70528e-06 | 5e-05/7.86912e-06 |
| Q5 | 1e-05/3.88902e-06 | 5e-05/7.62503e-06 | 5e-05/8.64642e-06 |

## Derived

- Q5 的 `F_local=0.34348517` 高于 Q3 `0.22494524`，且明显高于 Q4 `0.077782092`；BJL1 forward phase `0.74886825` 高于 Q4 `0.57597983`，但仍低于 Q3 `0.82107048`。这是 proximal routing 的部分恢复，不是完整恢复。
- Q5 BJL2 largest phase `0.96817867`，接近 Q4 `0.96540202`；其 BJL2 phase interaction 为 `-0.0034377627`，接近零，未显示 BJL2 端的正向 nonlinear interaction。
- Q5 BJL1 current areas 为正 `98.091813`、负 `-47.552139`、signed `50.539674` µA·ps；相对 Q4，正向 current transfer 显著增强，但 largest monotonic phase 仍为 sub-turn。
- Q5 的 BJs→BJL1 overlap 为 `2.45` ps，BJL1→BJL2 overlap 为 `4.6875` ps；Q5 的 BJL1→BJL2 delay 变为 `0.525` ps，区别于 Q2/Q3/Q4 的负 delay。
- Q5 所有 output event claims 仍须满足 continuous monotonic phase、同段 voltage area 和 bounded post；BJs 的 14-turn source activity不计作 downstream event。

## Inference

本轮归类为 **Q5_COMPLEMENTARY_DOWNSTREAM_PRESERVED_PARTIAL_L1_RECOVERY_NO_EVENT**。Q5 部分恢复了 L1/proximal routing，并保留了 Q4 的 BJL2 activity，但没有产生完整 BJL2 event；BJL2 phase interaction 近零，不能声称存在足以量化的正向 L1×L2 nonlinear gain。该结果支持“部分互补但尚未量化闭合”的解释。
## Unknown

- 本轮只测试一个 Q5 point；即使看到 routing 方向，也不证明整个 L1/L2 family 的普遍机制。
- local JJ phase transition 不等同于 downstream SFQ delivery；本轮没有接 JTL。
- 没有进行新的 timestep/convergence 或额外 placement/bias/AREA/RJ 点。

## Stop boundary

本 checkpoint 完成后停止，不运行 Q6，不连接 physical BVM→12JSL→QB，不接 JTL，也不追加参数点。

## Provenance

运行、source fixture、模型和 raw hash 见 `logs/`、`reference/`、`inputs/deck-hashes.json` 与 `sha256sums.txt`。

## Q2/Q3/Q4/Q5 factorial read1 summary

Q4 是已接受的 `(3.91,4.50) pH` comparator；Q5 是本轮 `(4.50,4.50) pH` point。

| point | F_local | G_local | BJL1 forward (turn) | BJL2 largest (turn) | BJL2/BJL1 | BJs→BJL1 overlap (ps) | BJL1→BJL2 overlap (ps) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Q2 | 0.21866043 | 0.51518504 | 0.8154138 | 0.94432281 | 1.1580903 | 4.325 | 4.35 |
| Q3 | 0.22494524 | 0.52658494 | 0.82107048 | 0.95053722 | 1.1576804 | 4.2875 | 4.3375 |
| Q4 | 0.077782092 | 0.51855988 | 0.57597983 | 0.96540202 | 1.6761039 | 2.6125 | 2.7875 |
| Q5 | 0.34348517 | 0.51973976 | 0.74886825 | 0.96817867 | 1.2928558 | 2.45 | 4.6875 |

Q5 的 BJL1/BJL2 complete-event count、read0/control separation 和 post-retrap 详情见本报告上方的 Q5 case table；Q4 的原始四-case详情保留在 accepted Q4 report。

## Discrete Q2/Q3/Q4/Q5 interaction

定义：`interaction = Q5 - Q3 - Q4 + Q2`；`additive prediction = Q3 + Q4 - Q2`。这些是四点离散设计的 derived quantities，不是 universal thresholds。

| metric | Q2 | Q3 | Q4 | additive prediction | Q5 | interaction |
|---|---:|---:|---:|---:|---:|---:|
| F_local | 0.21866043 | 0.22494524 | 0.077782092 | 0.084066906 | 0.34348517 | 0.25941826 |
| BJL1_forward_phase_turns | 0.8154138 | 0.82107048 | 0.57597983 | 0.58163651 | 0.74886825 | 0.16723174 |
| BJL2_largest_forward_phase_turns | 0.94432281 | 0.95053722 | 0.96540202 | 0.97161643 | 0.96817867 | -0.0034377627 |
| BJL2_over_BJL1 | 1.1580903 | 1.1576804 | 1.6761039 | 1.675694 | 1.2928558 | -0.38283818 |
| BJL1_positive_current_area_uA_ps | 41.439459 | 44.066199 | 24.994805 | 27.621545 | 98.091813 | 70.470268 |
| BJL1_negative_current_area_uA_ps | -44.326902 | -45.692528 | -48.613352 | -49.978977 | -47.552139 | 2.4268387 |
| BJL1_signed_current_area_uA_ps | -2.8874431 | -1.6263288 | -23.618547 | -22.357433 | 50.539674 | 72.897107 |
| BJs_to_BJL1_delay_ps | -0.025 | -0.05 | -0.175 | -0.2 | -2.7625 | -2.5625 |
| BJs_to_BJL1_overlap_ps | 4.325 | 4.2875 | 2.6125 | 2.575 | 2.45 | -0.125 |
| BJL1_to_BJL2_delay_ps | -2.2625 | -2.2 | -2.0875 | -2.025 | 0.525 | 2.55 |
| BJL1_to_BJL2_overlap_ps | 4.35 | 4.3375 | 2.7875 | 2.775 | 4.6875 | 1.9125 |

interaction 的机制解释必须结合 current decomposition、正负 phase segments、timing/overlap 和 KCL；不能由 interaction scalar 单独宣称 nonlinear coupling。
