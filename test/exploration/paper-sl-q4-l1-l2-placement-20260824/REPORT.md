# PAPER-SL-Q4 — L1/L2 placement analysis report

## Verdict

**Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT**。Q4 仍没有 BJL1/BJL2 complete event；本单点不升级为 downstream SFQ evidence。

Q4 直接从 accepted Q2 `inputs/40u` 构建，只改变 `L2=3.91p → 4.50p`；Q3 仅作为 sibling comparator。所有事件判断使用同一 JJ、同一 monotonic segment 的 continuous unwrapped phase 与直接 voltage-area，未使用 `I>Ic`、voltage peak 或旧 fast-event 指标。

## Observed

- 四个 Q4 JoSIM runs 均返回 0，CSV 均为 13,599 个 data rows，stderr 为空；首个 logical1 READ=0 control 已先通过 stop gate。
- Q4 四 case 的完整 segment/event 汇总如下；`complete_event_count` 仅统计 phase/area-consistent 的 ≥1 turn segment。
- read1 的 BJs 是预期的 multi-turn source activity，因此表中 BJs 的 segment count 不等同于输出 event；本轮 local-output 判据只对 BJL1/BJL2 读取。

| case | JJ | main phase range (turn) | post phase range (turn) | complete event count | main largest segment | post largest segment |
|---|---|---:|---:|---:|---|---|
| Q4_paper-j1-logical1-read0-control | BJs | 0.000180388 | 1.02104e-05 | 0 | [95.3875, 96.7] ps; Δ=0.000180388 turn; area=0.000180427 Φ0; consistent=yes | [141.088, 142.575] ps; Δ=1.02104e-05 turn; area=1.02122e-05 Φ0; consistent=yes |
| Q4_paper-j1-logical1-read0-control | BJL1 | 7.69992e-05 | 1.27324e-06 | 0 | [94, 94.925] ps; Δ=-7.69992e-05 turn; area=-7.70238e-05 Φ0; consistent=yes | [143.675, 144.875] ps; Δ=-1.27324e-06 turn; area=-1.26215e-06 Φ0; consistent=yes |
| Q4_paper-j1-logical1-read0-control | BJL2 | 2.44144e-05 | 3.97887e-07 | 0 | [94.35, 95.4375] ps; Δ=-2.44144e-05 turn; area=-2.44191e-05 Φ0; consistent=yes | [144.275, 145.412] ps; Δ=-3.97887e-07 turn; area=-3.83112e-07 Φ0; consistent=yes |
| Q4_paper-j0-logical0-read0-control | BJs | 0.000180388 | 1.02104e-05 | 0 | [95.3875, 96.7] ps; Δ=-0.000180388 turn; area=-0.000180427 Φ0; consistent=yes | [141.088, 142.575] ps; Δ=-1.02104e-05 turn; area=-1.02122e-05 Φ0; consistent=yes |
| Q4_paper-j0-logical0-read0-control | BJL1 | 7.69992e-05 | 1.27324e-06 | 0 | [94, 94.9125] ps; Δ=7.69992e-05 turn; area=7.70331e-05 Φ0; consistent=yes | [143.713, 144.85] ps; Δ=1.27324e-06 turn; area=1.26144e-06 Φ0; consistent=yes |
| Q4_paper-j0-logical0-read0-control | BJL2 | 2.44303e-05 | 3.97887e-07 | 0 | [94.35, 95.425] ps; Δ=2.44303e-05 turn; area=2.44252e-05 Φ0; consistent=yes | [144.262, 145.412] ps; Δ=3.97887e-07 turn; area=3.85157e-07 Φ0; consistent=yes |
| Q4_paper-j0-logical0-read | BJs | 0.0344871 | 0.001489 | 0 | [106.487, 107.7] ps; Δ=0.0236757 turn; area=0.0236817 Φ0; consistent=yes | [140.275, 141.488] ps; Δ=-0.001489 turn; area=-0.00148939 Φ0; consistent=yes |
| Q4_paper-j0-logical0-read | BJL1 | 0.0238759 | 0.00102873 | 0 | [108.175, 109.325] ps; Δ=0.0200203 turn; area=0.0200258 Φ0; consistent=yes | [140.763, 141.85] ps; Δ=0.00102873 turn; area=0.00102907 Φ0; consistent=yes |
| Q4_paper-j0-logical0-read | BJL2 | 0.00860011 | 0.000336772 | 0 | [108.65, 109.837] ps; Δ=0.00644189 turn; area=0.00644355 Φ0; consistent=yes | [140.188, 141.275] ps; Δ=-0.000336772 turn; area=-0.000336883 Φ0; consistent=yes |
| Q4_paper-j1-logical1-read | BJs | 14.3749 | 0.242442 | 14 | [102.55, 120.263] ps; Δ=14.0921 turn; area=14.0921 Φ0; consistent=yes | [141.238, 142.825] ps; Δ=-0.242442 turn; area=-0.24248 Φ0; consistent=yes |
| Q4_paper-j1-logical1-read | BJL1 | 1.15334 | 0.0113894 | 0 | [102.375, 105.162] ps; Δ=0.57598 turn; area=0.57599 Φ0; consistent=yes | [140.013, 141.113] ps; Δ=-0.0113894 turn; area=-0.011393 Φ0; consistent=yes |
| Q4_paper-j1-logical1-read | BJL2 | 1.05553 | 0.00343727 | 0 | [100.287, 107.288] ps; Δ=0.965402 turn; area=0.965413 Φ0; consistent=yes | [140.525, 141.625] ps; Δ=-0.00343727 turn; area=-0.00343826 Φ0; consistent=yes |

## Settled post-window operating points

READ=0 post window `[140,170)` ps 的均值/范围用于比较静态工作点；不以该表的电流比值判定 event。

| case | I(BJs) mean | I(BJL1) mean | I(BJL2) mean | I(L1) mean | I(L2) mean | I(LIN) mean | I(RB) mean | I(RJ1) mean | I(RJ2) mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q4_paper-j1-logical1-read0-control | 1.0098e-08 | 17.7814 | 22.2186 | -17.7814 | 22.2186 | 1.0098e-08 | 40 | -6.53809e-08 | -6.61477e-07 |
| Q4_paper-j0-logical0-read0-control | -1.0098e-08 | 17.7814 | 22.2186 | -17.7814 | 22.2186 | -1.0098e-08 | 40 | 6.53797e-08 | 6.61476e-07 |
| Q4_paper-j0-logical0-read | -0.000930213 | 17.7826 | 22.2183 | -17.7829 | 22.2171 | -0.000930213 | 40 | -0.000688094 | -0.000470645 |
| Q4_paper-j1-logical1-read | -0.0180171 | 17.7798 | 22.2117 | -17.7861 | 22.2139 | -0.0180171 | 40 | -0.011735 | -0.000574252 |

## Q2/Q3/Q4 read1 comparison

`F_local`/`F_L1` 是 paired dominant BJL1 interval 的 signed-area routing fractions；`G_local` 是 `[94,130)` ps 中 read1 减去 logical1 READ=0 后，local `(BJL1+RJ1)` RMS 与 BJs RMS 的比值。正负 current area 仅作波形抵消诊断。

| dataset | F_local | F_L1 | G_local | BJL1 +area | BJL1 -area | BJL1 signed | cancellation | BJL1 forward | BJL1 backward | BJL2 largest | BJL2/BJL1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Q2 | 0.21866 | 0.78134 | 0.515185 | 41.4395 | -44.3269 | -2.88744 | 0.966334 | 0.815414 | -0.135229 | 0.944323 | 1.15809 |
| Q3 | 0.224945 | 0.775055 | 0.526585 | 44.0662 | -45.6925 | -1.62633 | 0.981881 | 0.82107 | -0.141668 | 0.950537 | 1.15768 |
| Q4 | 0.0777821 | 0.922218 | 0.51856 | 24.9948 | -48.6134 | -23.6185 | 0.679131 | 0.57598 | -0.167653 | 0.965402 | 1.6761 |

### Major BJL1 phase segments

| dataset | positive segment | negative segment |
|---|---|---|
| Q2 | [102.525, 106.875] ps; Δ=0.815414 turn; area=0.815445 Φ0; consistent=yes | [111.35, 112.5] ps; Δ=-0.135229 turn; area=-0.135267 Φ0; consistent=yes |
| Q3 | [102.5, 106.837] ps; Δ=0.82107 turn; area=0.821102 Φ0; consistent=yes | [111.362, 112.525] ps; Δ=-0.141668 turn; area=-0.141708 Φ0; consistent=yes |
| Q4 | [102.375, 105.162] ps; Δ=0.57598 turn; area=0.57599 Φ0; consistent=yes | [106.725, 108.088] ps; Δ=-0.167653 turn; area=-0.167686 Φ0; consistent=yes |

### Onset/delay/overlap

| dataset | BJs→BJL1 delay (ps) | BJs/BJL1 overlap (ps) | BJL1→BJL2 delay (ps) | BJL1/BJL2 overlap (ps) |
|---|---:|---:|---:|---:|
| Q2 | -0.025 | 4.325 | -2.2625 | 4.35 |
| Q3 | -0.05 | 4.2875 | -2.2 | 4.3375 |
| Q4 | -0.175 | 2.6125 | -2.0875 | 2.7875 |

### KCL residuals

残差单位为 µA，在各 read1 dominant BJs interval 上计算：
`node2: I(BJs)-I(L1)-I(BJL1)-I(RJ1)`；`node3: I(L1)+I(RB)-I(L2)`；`node4: I(L2)-I(L0)-I(BJL2)-I(RJ2)`。

| dataset | node2 max/RMS | node3 max/RMS | node4 max/RMS |
|---|---:|---:|---:|
| Q2 | 1e-05/3.82119e-06 | 5e-05/7.11273e-06 | 5.5e-05/8.37259e-06 |
| Q3 | 1e-05/3.88815e-06 | 5e-05/6.70528e-06 | 5e-05/7.86912e-06 |
| Q4 | 1e-05/3.97358e-06 | 5e-05/7.74322e-06 | 5e-05/8.73098e-06 |

## Derived

- Q4 的 current decomposition、phase segment、BJs→BJL1 与 BJL1→BJL2 的时序，以及三条 node KCL residual 均已从 raw 独立计算；没有把总 phase range 当作 event count。
- BJL1 的 `positive/negative/signed area` 和 cancellation fraction 是在 paired dominant BJL1 interval 上定义的诊断量，不是 acceptance threshold。forward/backward segment 分开报告，避免将 backward motion 的减小误读为 forward event。
- Q4 的 `F_local=0.0777821` 明显低于 Q2/Q3 的 `0.21866/0.224945`；BJL1 forward segment 为 `0.57598` turn，低于 Q3 `0.82107`，而 BJL2 为 `0.965402` turn，高于 Q3 `0.950537`。
- Q4 的 BJL1 正面积下降、负向 excursion 增大，且 BJL1→BJL2 overlap 缩短；这说明它不是单纯把整条响应同比放大。三条 KCL residual 仍保持微安以下的数值误差，因此该方向性差异不是 KCL 不闭合造成的。
- Q2/Q3/Q4 raw 是 ideal replay QB fixture，不包含 `V(SL)`、`V(N6)`、`I(L_SL)`、`JM1/JM2`、`JS1/JS2` 这些 canonical BVM列；因此本轮只能确认 replay input boundary 未被改写，不能把 replay 结果冒充 physical BVM source-guard measurement。

## Inference

基于 current decomposition、phase dynamics、timing 和 KCL 的联合判断，本单点归类为 **Q4_DEGRADES_OPPOSES_Q3_DIRECTIONAL_PLACEMENT_EFFECT**：Q4 在下游 BJL2 上比 Q3 更强，但在 proximal BJL1 上反而更弱，且 BJL1 forward/backward 波形与 overlap 同时改变。因此支持 L1/L2 placement 的方向性动态效应；它不支持 Q4≈Q2、Q4≈Q3，也不满足“BJL1 cancellation 减少且 BJL1 phase 超过 Q3”的更强 downstream-timing 说法。

## Unknown

- 本轮只测试一个 Q4 point；即使看到 routing 方向，也不证明整个 L1/L2 family 的普遍机制。
- local JJ phase transition 不等同于 downstream SFQ delivery；本轮没有接 JTL。
- 没有进行新的 timestep/convergence 或额外 placement/bias/AREA/RJ 点。

## Stop boundary

本 checkpoint 完成后停止，不运行 Q5，不连接 physical BVM→12JSL→QB，不接 JTL，也不追加参数点。

## Provenance

运行、source fixture、模型和 raw hash 见 `logs/`、`reference/`、`inputs/deck-hashes.json` 与 `sha256sums.txt`。
