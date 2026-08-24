# JTL transport-gate reconciliation + pulse-5 polarity replay

parent HEAD: `090b8268132b9d5d4ae2e81a0131cafc458c24c1`
JoSIM: `v2.7.2837d13`; raw phase is radians; turns are derived by `ΔP/(2π)`.

本报告将 strict monotonic local-event evidence 与 full-window/pre-post settled-well evidence 分开。
full-window 接近一圈不能替代一个连续单调 segment 的 local event。未使用 legacy `fast_events`。

## 1. Artifact / fixture boundary

新 replay 是理想电压源 counterfactual fixture：只用于检验 accepted Q0 pulse 5 的极性/波形对冻结标准 JTL 的 transport response，不是物理 Q0→JTL 接口。
原极性和反极性各自独立 deck；后者只把同一 pulse-5 V(OUT,t) 逐点乘以 -1。

| fixture | topology | raw | strict vector | full-window approx-one-turn vector | local verdict |
|---|---|---|---|---|---|
| R11-positive-control | standard JTL; accepted R11 positive control | `test/exploration/bvm-sfq-receiver-r11a-direct-jtl-compatibility-20260823/raw/positive-control/run-02.csv` | `[1, 0, 0, 0]` | `[True, True, True, True]` | **STRICT_FIRST_STAGE_ONLY** |
| M1-ideal-replay | standard JTL; Q0 ideal V(OUT) replay | `test/exploration/parallel-qb-jtl-interface-mechanism-20260824/raw-v2/M1-ideal-replay/run.csv` | `[1, 0, 0, 0]` | `[True, True, True, True]` | **STRICT_FIRST_STAGE_ONLY** |
| M5-positive-control | scaled-JTL control from accepted M5-PC | `test/exploration/parallel-qb-jtl-interface-mechanism-20260824/raw-v2/M5-positive-control/run.csv` | `[1, 1, 0, 0]` | `[True, True, True, True]` | **STRICT_PARTIAL_CHAIN** |
| pulse5-original | standard JTL; exact accepted Q0 pulse-5 V(OUT,t), original polarity | `test/exploration/jtl-transport-gate-polarity-replay-20260824/raw/original/run.csv` | `[1, 0, 0, 0]` | `[True, True, True, True]` | **STRICT_FIRST_STAGE_ONLY** |
| pulse5-reverse | standard JTL; exact accepted Q0 pulse-5 V(OUT,t), reversed polarity | `test/exploration/jtl-transport-gate-polarity-replay-20260824/raw/reverse/run.csv` | `[0, 0, 0, 0]` | `[False, False, False, False]` | **NO_STRICT_LOCAL_EVENT** |

## 2. Strict monotonic local-event evidence

事件计数只来自同一 JJ 的连续单调 segment：`|Δphase| >= 1 turn`、同段直接电压面积同号且残差在注册限制内。

| fixture | JJ | count | largest forward (turn/area) | largest backward (turn/area) | onset of largest segment (ps) |
|---|---|---:|---:|---:|---|
| R11-positive-control | `P(B1|XJTL1)` | 1 | 1.02733/1.02739 | -0.275321/-0.275427 | 10→13.7875 |
| R11-positive-control | `P(B2|XJTL1)` | 0 | 0.92721/0.927254 | -0.160011/-0.160088 | 10→15.4125 |
| R11-positive-control | `P(B1|XJTL2)` | 0 | 0.923721/0.923761 | -0.163675/-0.163743 | 10→17.3125 |
| R11-positive-control | `P(B2|XJTL2)` | 0 | 0.869682/0.86971 | -0.103192/-0.103242 | 10→19.775 |
| M1-ideal-replay | `P(B1|XJTL1)` | 1 | 1.07462/1.07908 | -0.304361/-0.312077 | 10.6→16.8 |
| M1-ideal-replay | `P(B2|XJTL1)` | 0 | 0.929944/0.932699 | -0.145119/-0.149618 | 11.5→18.4 |
| M1-ideal-replay | `P(B1|XJTL2)` | 0 | 0.914721/0.917261 | -0.158574/-0.162761 | 14.3→20.3 |
| M1-ideal-replay | `P(B2|XJTL2)` | 0 | 0.867192/0.868925 | -0.0941056/-0.0970185 | 10→22.8 |
| M5-positive-control | `P(B1|XJTL1)` | 1 | 1.26042/1.26045 | -0.144529/-0.144578 | 10→13.4 |
| M5-positive-control | `P(B2|XJTL1)` | 1 | 1.06427/1.06434 | -0.303871/-0.303997 | 10→14.5625 |
| M5-positive-control | `P(B1|XJTL2)` | 0 | 0.985369/0.985431 | -0.206142/-0.206218 | 19.5125→24.5875 |
| M5-positive-control | `P(B2|XJTL2)` | 0 | 0.893874/0.893908 | -0.140944/-0.141016 | 10→18.6125 |
| pulse5-original | `P(B1|XJTL1)` | 1 | 1.07619/1.07626 | -0.31636/-0.316488 | 210→216.9 |
| pulse5-original | `P(B2|XJTL1)` | 0 | 0.927474/0.927512 | -0.13842/-0.138486 | 210→218.638 |
| pulse5-original | `P(B1|XJTL2)` | 0 | 0.921813/0.921853 | -0.165163/-0.165233 | 210→220.512 |
| pulse5-original | `P(B2|XJTL2)` | 0 | 0.859426/0.859455 | -0.103507/-0.103558 | 210→222.938 |
| pulse5-reverse | `P(B1|XJTL1)` | 0 | 0.0861148/0.0861356 | -0.876683/-0.876697 | 210→219.325 |
| pulse5-reverse | `P(B2|XJTL1)` | 0 | 0.0210646/0.02107 | -0.16474/-0.164743 | 210→219.7 |
| pulse5-reverse | `P(B1|XJTL2)` | 0 | 0.00896252/0.00896472 | -0.0426023/-0.0426028 | 210→219.963 |
| pulse5-reverse | `P(B2|XJTL2)` | 0 | 0.00306827/0.00306913 | -0.0112327/-0.0112328 | 210→220.375 |

### Strict evidence details for every JTL JJ

| fixture | JJ | largest absolute turns | same-segment area Φ0 | residual turns | direction | start→end ps |
|---|---|---:|---:|---:|---|---|
| R11-positive-control | `P(B1|XJTL1)` | 1.02733 | 1.02739 | 5.78097e-05 | forward | 10→13.7875 |
| R11-positive-control | `P(B2|XJTL1)` | 0.92721 | 0.927254 | 4.41389e-05 | forward | 10→15.4125 |
| R11-positive-control | `P(B1|XJTL2)` | 0.923721 | 0.923761 | 3.97945e-05 | forward | 10→17.3125 |
| R11-positive-control | `P(B2|XJTL2)` | 0.869682 | 0.86971 | 2.833e-05 | forward | 10→19.775 |
| M1-ideal-replay | `P(B1|XJTL1)` | 1.07462 | 1.07908 | 0.0044626 | forward | 10.6→16.8 |
| M1-ideal-replay | `P(B2|XJTL1)` | 0.929944 | 0.932699 | 0.00275443 | forward | 11.5→18.4 |
| M1-ideal-replay | `P(B1|XJTL2)` | 0.914721 | 0.917261 | 0.00253991 | forward | 14.3→20.3 |
| M1-ideal-replay | `P(B2|XJTL2)` | 0.867192 | 0.868925 | 0.00173331 | forward | 10→22.8 |
| M5-positive-control | `P(B1|XJTL1)` | 1.26042 | 1.26045 | 3.47481e-05 | forward | 10→13.4 |
| M5-positive-control | `P(B2|XJTL1)` | 1.06427 | 1.06434 | 6.64642e-05 | forward | 10→14.5625 |
| M5-positive-control | `P(B1|XJTL2)` | 0.985369 | 0.985431 | 6.12319e-05 | forward | 19.5125→24.5875 |
| M5-positive-control | `P(B2|XJTL2)` | 0.893874 | 0.893908 | 3.46546e-05 | forward | 10→18.6125 |
| pulse5-original | `P(B1|XJTL1)` | 1.07619 | 1.07626 | 7.0274e-05 | forward | 210→216.9 |
| pulse5-original | `P(B2|XJTL1)` | 0.927474 | 0.927512 | 3.83726e-05 | forward | 210→218.638 |
| pulse5-original | `P(B1|XJTL2)` | 0.921813 | 0.921853 | 4.02356e-05 | forward | 210→220.512 |
| pulse5-original | `P(B2|XJTL2)` | 0.859426 | 0.859455 | 2.85688e-05 | forward | 210→222.938 |
| pulse5-reverse | `P(B1|XJTL1)` | -0.876683 | -0.876697 | -1.33446e-05 | backward | 210→219.325 |
| pulse5-reverse | `P(B2|XJTL1)` | -0.16474 | -0.164743 | -2.60566e-06 | backward | 210→219.7 |
| pulse5-reverse | `P(B1|XJTL2)` | -0.0426023 | -0.0426028 | -5.50424e-07 | backward | 210→219.963 |
| pulse5-reverse | `P(B2|XJTL2)` | -0.0112327 | -0.0112328 | -5.80838e-08 | backward | 210→220.375 |

## 3. Full-window and pre/post settled-well evidence

这些量描述注册 activity/full window 的端点净变化，以及 activity 前后的稳定井；它们不单独构成 strict local event。

| fixture | JJ | full phase turns | full V-area Φ0 | residual | pre p2p | post p2p | pre→post median turns | post V RMS (µV) | post complete segments |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| R11-positive-control | `P(B1|XJTL1)` | 1.00488 | 1.00488 | 7.06023e-07 | 0.00295864 | 0.00443708 | 1.00421 | 3.5348 | 0 |
| R11-positive-control | `P(B2|XJTL1)` | 1.00371 | 1.00371 | 2.92934e-07 | 0.00277444 | 0.00411829 | 1.00281 | 3.50519 | 0 |
| R11-positive-control | `P(B1|XJTL2)` | 1.00319 | 1.00319 | 2.85746e-07 | 0.00271372 | 0.00705518 | 1.00505 | 5.61473 | 0 |
| R11-positive-control | `P(B2|XJTL2)` | 1.00413 | 1.00413 | -7.23266e-07 | 0.00626138 | 0.0081056 | 1.01466 | 5.77422 | 0 |
| M1-ideal-replay | `P(B1|XJTL1)` | 1.00184 | 1.00203 | 0.000191204 | 0.000904891 | 0.00740946 | 1.00038 | 10.8216 | 0 |
| M1-ideal-replay | `P(B2|XJTL1)` | 1.0017 | 1.0017 | 2.22278e-06 | 0.00259458 | 0.0239622 | 1.00139 | 18.7368 | 0 |
| M1-ideal-replay | `P(B1|XJTL2)` | 0.996874 | 0.996852 | -2.26278e-05 | 0.00307721 | 0.0213772 | 1.0043 | 16.0412 | 0 |
| M1-ideal-replay | `P(B2|XJTL2)` | 1.0002 | 1.0002 | -7.19206e-07 | 0.00545626 | 0.0127386 | 1.01394 | 7.84779 | 0 |
| M5-positive-control | `P(B1|XJTL1)` | 2.01222 | 2.01222 | 3.755e-06 | 0.00613969 | 0.0379967 | 2.02086 | 36.2557 | 0 |
| M5-positive-control | `P(B2|XJTL1)` | 1.97663 | 1.97663 | -7.10865e-06 | 0.00271491 | 0.0445554 | 2.00722 | 30.8638 | 0 |
| M5-positive-control | `P(B1|XJTL2)` | 2.01169 | 2.0117 | 7.25226e-06 | 0.0027603 | 0.0380874 | 2.00595 | 34.9097 | 0 |
| M5-positive-control | `P(B2|XJTL2)` | 1.95277 | 1.95276 | -7.31483e-06 | 0.00622708 | 0.0657819 | 2.01407 | 41.9293 | 0 |
| pulse5-original | `P(B1|XJTL1)` | 0.99294 | 0.992938 | -2.60452e-06 | 0 | 0.0178815 | 1.00001 | 21.2575 | 0 |
| pulse5-original | `P(B2|XJTL1)` | 1.01275 | 1.01275 | 4.56491e-06 | 0 | 0.0237481 | 0.999964 | 16.1998 | 0 |
| pulse5-original | `P(B1|XJTL2)` | 0.985742 | 0.985739 | -3.40729e-06 | 0 | 0.0216389 | 0.999898 | 14.563 | 0 |
| pulse5-original | `P(B2|XJTL2)` | 0.983071 | 0.983069 | -1.78585e-06 | 0 | 0.0174377 | 0.999744 | 9.38 | 0 |
| pulse5-reverse | `P(B1|XJTL1)` | -0.845557 | -0.845557 | 2.1115e-07 | 0 | 0.0027346 | -0.846988 | 1.77664 | 0 |
| pulse5-reverse | `P(B2|XJTL1)` | -0.161104 | -0.161104 | 4.52999e-08 | 0 | 0.000661973 | -0.161461 | 0.464012 | 0 |
| pulse5-reverse | `P(B1|XJTL2)` | -0.0432411 | -0.043241 | 3.48844e-08 | 0 | 0.000294071 | -0.0434037 | 0.30625 | 0 |
| pulse5-reverse | `P(B2|XJTL2)` | -0.0145345 | -0.0145345 | -1.58791e-08 | 0 | 0.000455072 | -0.014583 | 0.361871 | 0 |

## 4. Timing / transport observables

`onset` 使用各 JJ 最大绝对单调段的起点；它是 activity timing，不自动等于 event onset。

| fixture | JTL JJ | largest-segment onset (ps) | duration (ps) | activity range (turn) |
|---|---|---|---:|---:|
| R11-positive-control | `P(B1|XJTL1)` | 10→13.7875 | 3.7875 | 1.08365 |
| R11-positive-control | `P(B2|XJTL1)` | 10→15.4125 | 5.4125 | 1.03489 |
| R11-positive-control | `P(B1|XJTL2)` | 10→17.3125 | 7.3125 | 1.01026 |
| R11-positive-control | `P(B2|XJTL2)` | 10→19.775 | 9.775 | 1.00811 |
| M1-ideal-replay | `P(B1|XJTL1)` | 10.6→16.8 | 6.2 | 1.13233 |
| M1-ideal-replay | `P(B2|XJTL1)` | 11.5→18.4 | 6.9 | 1.03176 |
| M1-ideal-replay | `P(B1|XJTL2)` | 14.3→20.3 | 6 | 1.01371 |
| M1-ideal-replay | `P(B2|XJTL2)` | 10→22.8 | 12.8 | 1.00198 |
| M5-positive-control | `P(B1|XJTL1)` | 10→13.4 | 3.4 | 2.01896 |
| M5-positive-control | `P(B2|XJTL1)` | 10→14.5625 | 4.5625 | 2.0333 |
| M5-positive-control | `P(B1|XJTL2)` | 19.5125→24.5875 | 5.075 | 2.02365 |
| M5-positive-control | `P(B2|XJTL2)` | 10→18.6125 | 8.6125 | 1.99765 |
| pulse5-original | `P(B1|XJTL1)` | 210→216.9 | 6.9 | 1.13417 |
| pulse5-original | `P(B2|XJTL1)` | 210→218.638 | 8.6375 | 1.04713 |
| pulse5-original | `P(B1|XJTL2)` | 210→220.512 | 10.5125 | 1.00848 |
| pulse5-original | `P(B2|XJTL2)` | 210→222.938 | 12.9375 | 0.995253 |
| pulse5-reverse | `P(B1|XJTL1)` | 210→219.325 | 9.325 | 0.876683 |
| pulse5-reverse | `P(B2|XJTL1)` | 210→219.7 | 9.7 | 0.170837 |
| pulse5-reverse | `P(B1|XJTL2)` | 210→219.963 | 9.9625 | 0.0471321 |
| pulse5-reverse | `P(B2|XJTL2)` | 210→220.375 | 10.375 | 0.0154768 |

| fixture | V(JTL_IN) p2p (mV) | V(JTL_MID) p2p (mV) | V(JTL_OUT) p2p (mV) | I(L1/XJTL1) p2p (µA) | I(R_TERM) p2p (µA) |
|---|---:|---:|---:|---:|---:|
| R11-positive-control | — | — | — | 390.686 | 396.436 |
| M1-ideal-replay | 1.16937 | 0.918313 | 0.393063 | 562.297 | 393.063 |
| M5-positive-control | — | 1.12198 | 0.414532 | 147.94 | 89.539 |
| pulse5-original | 1.16937 | 0.912143 | 0.400133 | 594.007 | 400.132 |
| pulse5-reverse | 1.16937 | 0.0862218 | 0.00522791 | 612.729 | 5.22791 |

## 5. Reconciliation

### Observed

- R11 standard positive control has approximately one-turn full-window phase/area response in all four JJ, but its strict largest monotonic segments are not all one turn; therefore full-window calibration and strict local-event evidence are different rows of evidence.
- M1 Q0 V(OUT) ideal replay and the new original pulse-5 replay are the same diagnostic family: first-stage response may have a strict event while downstream segments can remain below one turn.
- M5-PC is a scaled-JTL positive-control fixture; it is reported as its own topology and is not silently merged with standard-JTL results.
- The reverse replay is a polarity diagnostic only; any resulting JTL activity is not read0 evidence and cannot establish selectivity.

### Derived

- For every table above, strict count uses the same-JJ direct voltage area over the exact reported monotonic segment. Full-window residuals use the activity-window endpoints and its direct same-JJ voltage integral.
- Pre/post well deltas and p2p values quantify retrap/boundedness evidence separately; a small post p2p does not repair a sub-turn strict segment.

### Inference

- This batch can reconcile polarity and transport behavior of the frozen diagnostic JTL fixture, but cannot identify a physical QB→JTL interface mechanism because the new source is ideal voltage replay.

### Unknown

- No new read0/BVM case is run in this batch, no additional timestep convergence group is run, and no T1 is attached. Reverse polarity is not a logical-state control.

## 6. Stop / disposition

本 checkpoint 在两个 polarity replay 与统一 evidence table 完成后停止；不进行任何 R/L/Ic/bias sweep，不修改 QB/JTL 参数，不连接 T1。
