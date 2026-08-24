# QB_TO_JTL_LOAD_BACKACTION_CAUSAL_AUDIT_V1

parent accepted HEAD: `8bb86f61c3243655467d61f00680977349b41cf3`  
本报告只审计已接受 raw；没有参数 sweep、没有 topology 改动、没有新 JoSIM run。
所有 phase 为 raw rad 解包后换算的 turns；电压面积使用同一 JJ、同一窗口和 CSV 实际时间轴。

## 1. Registered reference and regions

Q0+10Ω pulse-5 reference BJL2 segment: `210–217.1 ps`, `1.09601 turn`, same-segment area `1.09652 Φ0`, residual `0.000501262 turn`.

| region | window (ps) | meaning |
|---|---:|---|
| pre_crossing | `208–210` | settled state before registered crossing |
| crossing | `210–217.1` | same reference event interval |
| retrap_post | `217.1–259` | event end through registered post window |

## 2. Local fixture verdicts

| case | BJL2 activity range | largest segment | same-window phase / area | complete event units | JTL local status |
|---|---:|---|---:|---:|---|
| Q0_10ohm | 1.0960141 turn | positive 1.09601 turn / 1.09652 Φ0 (210–217.1 ps) | 1.0000007 / 1 | 1 | not attached |
| Q0_OPEN | 3.1477251 turn | positive 3.14773 turn / 3.14902 Φ0 (210–219.1 ps) | 2.9999927 / 2.9999928 | 3 | not attached |
| Q0_JTL_ONLY | 0.35674692 turn | negative -0.356747 turn / -0.357495 Φ0 (216.3–219.3 ps) | -3.8833806e-06 / -3.8329487e-06 | 0 | B1|XJTL1: -0.1151 turn/0; B2|XJTL1: -0.02945 turn/0; B1|XJTL2: -0.008746 turn/0; B2|XJTL2: -0.003105 turn/0 |
| Q0_10ohm_PARALLEL_JTL | 0.31146113 turn | negative -0.311461 turn / -0.312109 Φ0 (216.5–219.4 ps) | -7.018733e-06 / -6.9415919e-06 | 0 | B1|XJTL1: -0.09376 turn/0; B2|XJTL1: -0.02511 turn/0; B1|XJTL2: -0.006919 turn/0; B2|XJTL2: -0.002174 turn/0 |
| M3_SERIES_10ohm_JTL | 1.088919 turn | positive 1.08892 turn / 1.08939 Φ0 (210–216.9 ps) | 0.99996255 / 0.99996321 | 1 | B1|XJTL1: -0.06846 turn/0; B2|XJTL1: -0.02214 turn/0; B1|XJTL2: -0.007009 turn/0; B2|XJTL2: -0.001869 turn/0 |

## 3. Node-4 current partition and KCL

Values are region min/max/mean/p2p in µA. The requested KCL is `I(L2)=I(L0)+I(BJL2)+I(RJ2)`; residuals are reported as `L2−L0−BJL2−RJ2`.

| case | region | I(L2) mean/p2p | I(L0) mean/p2p | I(BJL2) mean/p2p | I(RJ2) mean/p2p | KCL RMS/max µA |
|---|---|---:|---:|---:|---:|---:|
| Q0_10ohm | pre_crossing | 19.8783/0 | 4.67773e-13/0 | 19.8783/0 | 7.97195e-13/0 | 1.265e-12/1.265e-12 |
| Q0_10ohm | crossing | 71.2558/100.394 | 31.8152/95.6956 | 24.9223/124.744 | 14.5183/44.4683 | 1.348e-05/5e-05 |
| Q0_10ohm | retrap_post | 19.6569/28.9519 | -0.455949/25.8399 | 20.3298/18.2398 | -0.216891/11.6354 | 2.745e-06/9e-06 |
| Q0_OPEN | pre_crossing | 19.8783/0 | 0/0 | 19.8783/0 | 2.29433e-10/4.81506e-10 | 2.753e-10/4.145e-10 |
| Q0_OPEN | crossing | 56.8173/80.9184 | 0/0 | 24.4578/97.2447 | 32.3595/81.9935 | 4.965e-06/1e-05 |
| Q0_OPEN | retrap_post | 20.0751/16.5082 | 0/0 | 18.8287/67.0428 | 1.24642/65.9734 | 3.533e-06/1e-05 |
| Q0_JTL_ONLY | pre_crossing | 14.7333/0.00068 | -18.5331/0.00101 | 33.2664/0.00045 | -9.59891e-06/0.000340938 | 4.774e-06/8.058e-06 |
| Q0_JTL_ONLY | crossing | 100.049/125.952 | 57.4048/124.389 | 38.8215/41.1917 | 3.82304/15.4364 | 2.628e-05/6.1e-05 |
| Q0_JTL_ONLY | retrap_post | 16.1765/103.048 | -16.9369/130.813 | 33.7612/37.8362 | -0.64782/28.3312 | 5.364e-06/3e-05 |
| Q0_10ohm_PARALLEL_JTL | pre_crossing | 14.7333/0.00042 | -18.5331/0.00067 | 33.2664/0.00032 | -1.01177e-05/0.000240008 | 6.93e-06/1.247e-05 |
| Q0_10ohm_PARALLEL_JTL | crossing | 99.9659/126.818 | 53.9782/117.353 | 42.3676/32.709 | 3.62008/12.4371 | 2.367e-05/5.16e-05 |
| Q0_10ohm_PARALLEL_JTL | retrap_post | 15.9947/103.406 | -17.3059/124.73 | 33.9141/29.042 | -0.613428/21.0354 | 4.943e-06/1.282e-05 |
| M3_SERIES_10ohm_JTL | pre_crossing | 19.8783/0.00032 | -3.05224e-05/0.000453832 | 19.8783/0.0002 | 1.0021e-05/0.000182024 | 4.471e-06/8.644e-06 |
| M3_SERIES_10ohm_JTL | crossing | 70.8583/97.9926 | 30.7678/90.05 | 25.6821/130.267 | 14.4085/51.1703 | 1.467e-05/5e-05 |
| M3_SERIES_10ohm_JTL | retrap_post | 19.7001/28.7491 | -0.278468/32.2083 | 20.1768/19.0973 | -0.198278/14.9908 | 4.138e-06/9.79e-06 |

## 4. Interface branch and dissipation

Current values are mean/p2p in µA; energies are pJ over the registered region. Missing branches are not inferred.

| case | region | JTL input I mean/p2p | R_LOAD I mean/p2p | R_SER I mean/p2p | E_RJ2 | E_RLOAD | E_RSER |
|---|---|---:|---:|---:|---:|---:|---:|
| Q0_10ohm | pre_crossing | — | 4.67773e-13/0 | — | 2.6565e-35 | 4.1574e-36 | — |
| Q0_10ohm | crossing | — | 31.8152/95.6956 | — | 5.784e-08 | 1.2544e-07 | — |
| Q0_10ohm | retrap_post | — | -0.455949/25.8399 | — | 1.6512e-09 | 3.3768e-09 | — |
| Q0_OPEN | pre_crossing | — | — | — | 3.3073e-30 | — | — |
| Q0_OPEN | crossing | — | — | — | 2.6238e-07 | — | — |
| Q0_OPEN | retrap_post | — | — | — | 6.0813e-08 | — | — |
| Q0_JTL_ONLY | pre_crossing | -18.5331/0.00101 | — | — | 7.1309e-19 | — | — |
| Q0_JTL_ONLY | crossing | 57.4048/124.389 | — | — | 4.3714e-09 | — | — |
| Q0_JTL_ONLY | retrap_post | -16.9369/130.813 | — | — | 1.2162e-08 | — | — |
| Q0_10ohm_PARALLEL_JTL | pre_crossing | -18.5331/0.00118 | -2.01763e-06/0.00050912 | — | 3.5428e-19 | 7.1398e-19 | — |
| Q0_10ohm_PARALLEL_JTL | crossing | 47.9632/116.456 | 6.01508/16.5862 | — | 3.3118e-09 | 3.8492e-09 | — |
| Q0_10ohm_PARALLEL_JTL | retrap_post | -16.2866/120.204 | -1.01927/33.9783 | — | 8.5941e-09 | 1.0232e-08 | — |
| M3_SERIES_10ohm_JTL | pre_crossing | -3.05224e-05/0.000453832 | — | -3.05224e-05/0.000453832 | 1.406e-19 | — | 4.2239e-19 |
| M3_SERIES_10ohm_JTL | crossing | 30.7678/90.05 | — | 30.7678/90.05 | 6.316e-08 | — | 1.1298e-07 |
| M3_SERIES_10ohm_JTL | retrap_post | -0.278468/32.2083 | — | -0.278468/32.2083 | 2.1196e-09 | — | 2.7198e-09 |

## 5. Observed

- accepted Q0+10Ω 在 pulse 5 的 BJL2 有一个约 `1.0960 turn / 1.0965 Φ0` 的同段 local event；节点 4 KCL residual 在 crossing 的 RMS 约 `1.35e-5 µA`，说明当前 probe 方向闭合。
- Q0 OPEN 的同一窗口最大 BJL2 段约 `3.1477 turn`，对应约三个 event units；它不是 exactly-one 边界。
- Q0 JTL-only 与 Q0 10Ω||JTL 在 crossing 前已处于不同 settled load-line：`I(L0)` 约 `−18.53 µA`、`I(BJL2)` 约 `33.27 µA`，而 accepted 10Ω 是约 `0`/`19.88 µA`。两者的 BJL2 最大段分别约 `0.3567`/`0.3115 turn`，无 complete event。
- M3 series-10Ω→JTL 在 crossing 前接近 accepted Q0+10Ω 的 settled partition；BJL2 仍有约 `1.0889 turn / 1.0894 Φ0` local event，但 series branch 在 crossing 承担约 `90.05 µA` p2p/mean量级的 transient，JTL仍未形成 complete transport event。
- Q0 10Ω、M3、OPEN 的 crossing 中 `I(L2)`、`I(L0)`/interface branch、`I(BJL2)` 和 `I(RJ2)` 都发生同步重分配；因此单一静态阻抗不能描述全部行为。

## 6. Derived

- `I(L2)=I(L0)+I(BJL2)+I(RJ2)` 在所有可审计区间的数值 residual 为 pA/亚-pA 量级到数十 pA（显示单位为 µA），与 JoSIM 输出精度相容；未把 residual 设为零。
- 直接 JTL-only/parallel 的 pre-crossing bias split 已改变，说明 load boundary 在 barrier crossing 之前就改变了 operating point，而不是仅影响 event 后 retrap。
- M3 保留 BJL2 event 但 JTL 未触发，说明“BJL2 local event 被保存”和“JTL 接收”是两个独立证据层；series branch 的 event preservation 不能升级为 transport success。

## 7. Inference

- 最符合本冻结矩阵的机制是 `MIXED_DYNAMIC_LOADING`：直接/并联 JTL 先改变 settled current partition，再在 crossing 中分流并改变 `L2→L0/BJL2/RJ2` 轨迹；M3 则显示一个不同的 series boundary 可保留 local event，但仍不足以给 JTL 标准输入事件。
- 证据不支持把失败只归因于 retrap：direct/parallel 在 complete BJL2 crossing 之前已经没有完整 crossing；也不支持把 Q0 event loss 简化成一个等效电阻。

## 8. Unknown / limits

- 本审计只覆盖已接受的 Q0 fixtures；没有新的 probe-only rerun，没有 canonical BVM，也没有 transformer/interface optimization。
- Q0 OPEN 的多 event 与 accepted 10Ω 的 exactly-one 差异支持 boundary causality，但不冻结一个普适 one-shot load specification。
- M3 JTL 仍是 subthreshold/未传播；本报告没有把其 local BJL2 event称为 downstream SFQ delivery。

## 9. Final bounded mechanism classification

`MIXED_DYNAMIC_LOADING`

停止于本包；不设计或调节 transformer、R/L/Ic/bias，不接 T1。
