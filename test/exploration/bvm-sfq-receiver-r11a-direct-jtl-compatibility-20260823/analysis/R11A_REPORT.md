# R11-A report：canonical BVM → standard JTL direct compatibility screening

本报告从 raw CSV 的实际 time 列读取相位和直接同 JJ 电压；未使用旧 `sfq_metrics.py` 事件计数。相位单位先保留 rad，turns = Δphase/(2π)，电压面积为同一 JJ、同一段的 `∫Vdt/Φ0`。

## Artifact / fixture

- positive control 与四个 BVM case 均 exit 0、13,600 rows、median dt=0.0125 ps；详细 hash 在 `manifest.yaml` 和 `analysis/sha256sums.txt`。
- positive control 使用仓库 `test/standard/test_jtl.cir` 的 1.5 mV、11–13 ps 单次 stimulus；所有 run 使用原样 `circuits/standard/JTL.cir` 的两 cell chain。

## Positive-control validation

同一标准两-cell chain 的 positive control 在四颗 JJ 上都有约一圈的 activity-window phase change；同一 JJ 直接 voltage-area 的残差约为 `10^-6 turns`，并且 post phase p2p 很小。最大的逐点单调前向段因标准 JTL 的欠阻尼 ringing 小于或接近一圈，故同时报告完整 activity-window 的 phase/area 双证据，不把 ringing 的局部峰谷误计为额外事件。

| JJ | activity phase turns | activity V-area turns | residual | largest monotonic turns | segment onset→end (ps) | post p2p turns |
|---|---:|---:|---:|---:|---:|---:|
| `P(B1|XJTL1)` | 1.00488 | 1.00488 | 7.06023e-07 | 1.02733 | 10→13.7875 | 0.00443708 |
| `P(B2|XJTL1)` | 1.00371 | 1.00371 | 2.92934e-07 | 0.92721 | 10→15.4125 | 0.00411829 |
| `P(B1|XJTL2)` | 1.00319 | 1.00319 | 2.85746e-07 | 0.923721 | 10→17.3125 | 0.00705518 |
| `P(B2|XJTL2)` | 1.00413 | 1.00413 | -7.23266e-07 | 0.869682 | 10→19.775 | 0.0081056 |

## JTL phase / voltage-area evidence

| case | JJ | pre→post turns | activity range | largest monotonic turns | same-segment V-area | residual | segment onset→end (ps) | post p2p turns |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| positive-control | `P(B1|XJTL1)` | 1.00421 | 1.08365 | 1.02733 | 1.02739 | 5.78097e-05 | 10→13.7875 | 0.00443708 |
| positive-control | `P(B2|XJTL1)` | 1.00281 | 1.03489 | 0.92721 | 0.927254 | 4.41389e-05 | 10→15.4125 | 0.00411829 |
| positive-control | `P(B1|XJTL2)` | 1.00505 | 1.01026 | 0.923721 | 0.923761 | 3.97945e-05 | 10→17.3125 | 0.00705518 |
| positive-control | `P(B2|XJTL2)` | 1.01466 | 1.00811 | 0.869682 | 0.86971 | 2.833e-05 | 10→19.775 | 0.0081056 |
| read1 | `P(B1|XJTL1)` | 1.13e-06 | 0.158625 | -0.150955 | -0.150987 | -3.14564e-05 | 108.412→109.75 | 0.0019842 |
| read1 | `P(B2|XJTL1)` | -8.43521e-07 | 0.0663253 | 0.0600364 | 0.0600498 | 1.34449e-05 | 110.2→111.5 | 0.00137843 |
| read1 | `P(B1|XJTL2)` | -1.20162e-06 | 0.0280843 | -0.0270025 | -0.0270084 | -5.82929e-06 | 111.9→113.225 | 0.000633898 |
| read1 | `P(B2|XJTL2)` | 2.78521e-07 | 0.00952418 | -0.00952418 | -0.00952647 | -2.28506e-06 | 114.875→116.125 | 0.00130575 |
| read0 | `P(B1|XJTL1)` | -4.29718e-07 | 0.0470723 | 0.0346417 | 0.0346486 | 6.88522e-06 | 106.875→108.2 | 0.000324787 |
| read0 | `P(B2|XJTL1)` | 3.8993e-07 | 0.0131097 | 0.0125246 | 0.0125273 | 2.71885e-06 | 107.475→108.763 | 0.000357064 |
| read0 | `P(B1|XJTL2)` | 4.77465e-08 | 0.0050825 | 0.0050825 | 0.00508379 | 1.28981e-06 | 110.587→111.812 | 0.000227958 |
| read0 | `P(B2|XJTL2)` | -3.1831e-08 | 0.00236051 | -0.00236051 | -0.00236117 | -6.6206e-07 | 112.3→113.475 | 0.00038011 |
| logical1-read0-control | `P(B1|XJTL1)` | -1.59155e-08 | 2.45099e-06 | 2.45099e-06 | 2.43905e-06 | -1.19374e-08 | 94.6625→96.3 | 4.29718e-07 |
| logical1-read0-control | `P(B2|XJTL1)` | 0 | 9.86761e-07 | 9.86761e-07 | 9.75165e-07 | -1.15956e-08 | 94.825→96.5625 | 1.90986e-07 |
| logical1-read0-control | `P(B1|XJTL2)` | -1.59155e-08 | 4.45634e-07 | 4.45634e-07 | 4.31745e-07 | -1.38885e-08 | 94.9875→96.625 | 6.3662e-08 |
| logical1-read0-control | `P(B2|XJTL2)` | 0 | 1.59155e-07 | 1.59155e-07 | 1.45168e-07 | -1.39867e-08 | 95.3875→97.1125 | 1.59155e-08 |
| logical0-read0-control | `P(B1|XJTL1)` | 7.95775e-09 | 2.4669e-06 | -2.4669e-06 | -2.45363e-06 | 1.32712e-08 | 94.7→96.2875 | 4.29718e-07 |
| logical0-read0-control | `P(B2|XJTL1)` | 0 | 1.00268e-06 | -1.00268e-06 | -9.87956e-07 | 1.47197e-08 | 94.9125→96.55 | 1.7507e-07 |
| logical0-read0-control | `P(B1|XJTL2)` | 1.59155e-08 | 4.61549e-07 | 4.61549e-07 | 4.47681e-07 | -1.38687e-08 | 94→95.275 | 6.3662e-08 |
| logical0-read0-control | `P(B2|XJTL2)` | 0 | 1.7507e-07 | -1.7507e-07 | -1.60718e-07 | 1.43522e-08 | 95.4625→97.05 | 1.59155e-08 |

`largest monotonic` 是描述性轨迹分段，不单独定义 event；complete local event 仍要求 continuous unwrapped phase、同段 voltage-area 一致以及事件后 retrap/bounded behavior 联合成立。

## BVM direct-loading observations

| case | V(SL1) activity p2p (V) | I(L_SL) activity p2p (A) | V(N6) activity p2p (V) | JTL OUT activity p2p (V) |
|---|---:|---:|---:|---:|
| read1 | 0.000989448 | 0.000132007 | 0.00219196 | 7.6781e-06 |
| read0 | 0.000234483 | 6.57784e-05 | 0.00106284 | 1.81724e-06 |
| logical1-read0-control | 1.6116e-08 | 1.83078e-09 | 3.46507e-08 | 1.38625e-10 |
| logical0-read0-control | 1.61966e-08 | 1.82995e-09 | 3.464e-08 | 1.41159e-10 |

## Source/storage differential versus canonical no-receiver

下表只报告 direct JTL loaded case 与 matched canonical no-receiver raw 在 post `[130,165) ps` 的 median/p2p 差异；是否可接受必须结合 canonical baseline 和本项目 storage guard 解释，不能用 absolute JS phase change 单独判定。

| case | SL median Δ | N6 median Δ | L_SL median Δ | JM1 median Δ | JM2 median Δ | JS1 median Δ | JS2 median Δ |
|---|---:|---:|---:|---:|---:|---:|---:|
| read1 | 2.12286e-08 | 5.0879e-08 | 2.02634e-09 | 0.0005695 | 0.001076 | -6e-05 | -3.5e-05 |
| read0 | -2.54187e-09 | -9.39982e-09 | -4.55664e-10 | 2e-06 | 6.135e-05 | -1.34e-05 | 3.325e-05 |
| logical1-read0-control | 4.35933e-11 | 4.56071e-11 | 4.41371e-13 | 0 | 9e-07 | -1e-07 | 0 |
| logical0-read0-control | -4.2174e-11 | -4.42094e-11 | -4.29194e-13 | 0 | -1e-06 | 1.5e-07 | 0 |

## BVM storage/readout phase comparison

| case | JM1 net turns | JM2 net turns | JS1 net turns | JS2 net turns | JS1 post p2p | JS2 post p2p |
|---|---:|---:|---:|---:|---:|---:|
| read1 | 6.85162e-05 | -0.000222156 | -2.99984 | -2.99998 | 0.0160906 | 0.00275179 |
| read0 | 1.15387e-05 | -8.44635e-05 | 1.56688e-05 | 1.36873e-06 | 0.00335635 | 0.000521933 |
| logical1-read0-control | 1.59155e-07 | -3.39796e-06 | 5.72958e-07 | 7.16197e-08 | 1.73956e-05 | 1.98944e-06 |
| logical0-read0-control | -1.59155e-07 | 3.40592e-06 | -5.72958e-07 | -7.16197e-08 | 1.73797e-05 | 1.98944e-06 |

## Interpretation

### Observed

- 详见上表；positive-control 是判定 BVM 前提的唯一正向 fixture。
- BVM 四-case 的 JTL phase、same-JJ area、post stability 和 source guards 必须以 JSON 原始数值联合读取。

### Derived

- 由 phase/area 同段一致性判断 local JTL transition 是否有双证据；由 XJTL1→XJTL2 的 onset 顺序判断是否有逐级传播。
- read1/read0/control 的 propagated-event 判定不使用 `I>Ic`、voltage peak 或 phase range alone。

### Inference

- 仅能把结果归因于本次 fixed direct galvanic load、standard JTL fixture、stimulus、model、dt 和 windows；不能外推到所有 direct-JTL topology。

### Unknown / audit boundary

- 本轮没有额外时间步收敛组，也没有 T1；即使 chain 传播通过，也只建立两-cell loaded-JTL screening evidence，不是 downstream T1 或 hardware claim。

## Verdict

`DIRECT_JTL_SELECTIVE_PASS` 未满足：positive control fixture 通过，但 canonical BVM read1 的最大 JTL phase excursion 仍远低于一圈，且 read1→XJTL2 没有对应完整 event。read0 与两个 READ=0 controls 没有完整 event，post phase p2p 处于 bounded 数值背景。故本 fixed direct-galvanic point 的主 verdict 为 **`NO_JTL_TRIGGER`**，不是 `DIRECT_JTL_NONSELECTIVE` 或 `SOURCE_BACK_ACTION_FAILURE`。

这只表示在当前 canonical BVM source、standard JTL、direct load、stimulus、模型、`dt=0.0125 ps` 和预注册窗口下，read1 没有触发第一颗标准 JTL JJ 的 complete transition；它不否定带 temporal rectification/hold/regeneration 的后续 receiver，也不把整个 direct-JTL family 宣判为普遍不可能。
