# QB load-boundary matrix：Q0/Q5 output boundary compatibility

## 主结论

本报告只覆盖五个 preregistered output-boundary fixtures。每个 fixture 先独立判定，再做矩阵比较；不做参数优化，也不把局部 JJ event自动解释为 downstream SFQ delivery。

## Artifact validity

- v2 raw 使用 JoSIM `v2.7.2837d13`；所有 11 个 v2 jobs exit=0、stderr 为空、时间轴严格递增。
- v1 A/B/D/E raw 保留在 `raw/`，但因删除 `R_LOAD` 后遗留 `.print I(R_LOAD)` 导致 invalid probe，完全排除；C v1 也不作为本次 matched package 的来源。详见 `ATTEMPT-01-INVALID.md`。
- v2 parser 从 JoSIM data header开始读取，未把 progress text当成数据；Q0 为 2999 rows、0.1 ps，Q5 为 13599 rows、0.0125 ps。

## Local verdicts

| fixture | independent local verdict | key BJL2 result |
|---|---|---|
| A Q0 OPEN | **Q0_MULTIEVENT** | A-q0-open: BJL2 `3,3,3,3,3,3`, max post p2p=9.549297e-06 turn |
| B Q0 JTL-only | **Q0_EVENT_LOST_UNDER_LOAD** | B-q0-jtl-only: BJL2 `0,0,0,0,0,0`, max post p2p=0.0001430962 turn |
| C Q0 10Ω || JTL | **Q0_EVENT_LOST_UNDER_LOAD** | C-q0-10ohm-parallel-jtl: BJL2 `0,0,0,0,0,0`, max post p2p=7.73493e-05 turn |
| D Q5 OPEN | **Q5_MULTIFIRE** | D-q5-open/paper-j1-logical1-read: BJL2 largest=3.043892 / 3.043909 / 1.68148e-05, complete=3; read0 D-q5-open/paper-j0-logical0-read: BJL2 largest=0.01050432 / 0.01050727 / 2.949265e-06, complete=0 |
| E Q5 JTL-only | **Q5_NO_JTL_TRIGGER** | E-q5-jtl-only/paper-j1-logical1-read: BJL2 largest=-0.2587884 / -0.2587969 / -8.449217e-06, complete=0; read0 E-q5-jtl-only/paper-j0-logical0-read: BJL2 largest=0.005870812 / 0.005872571 / 1.7586e-06, complete=0 |

## Q0：六个 registered pulses

| fixture | JJ | pulse event units | activity largest Δturn/area | post complete |
|---|---|---|---|---:|
| A-q0-open | BJs | `16,15,15,16,16,16` | 16.42329 / 16.42597 / 0.002674723 | 0 |
| A-q0-open | BJL1 | `3,3,3,3,3,3` | 3.147799 / 3.149008 / 0.001209625 | 0 |
| A-q0-open | BJL2 | `3,3,3,3,3,3` | 3.147755 / 3.150168 / 0.002412904 | 0 |
| B-q0-jtl-only | BJs | `16,15,15,16,16,16` | 16.42329 / 16.42597 / 0.002674723 | 0 |
| B-q0-jtl-only | BJL1 | `0,0,0,0,0,0` | -0.8540611 / -0.8561398 / -0.002078689 | 0 |
| B-q0-jtl-only | BJL2 | `0,0,0,0,0,0` | -0.3567469 / -0.3574953 / -0.0007483522 | 0 |
| B-q0-jtl-only | B1|XJTL1 | `0,0,0,0,0,0` | -0.1150832 / -0.1154875 / -0.0004043266 | 0 |
| B-q0-jtl-only | B2|XJTL1 | `0,0,0,0,0,0` | 0.02945858 / 0.02951022 / 5.16453e-05 | 0 |
| B-q0-jtl-only | B1|XJTL2 | `0,0,0,0,0,0` | -0.008784987 / -0.008896047 / -0.0001110597 | 0 |
| B-q0-jtl-only | B2|XJTL2 | `0,0,0,0,0,0` | 0.01098241 / 0.01098898 / 6.576292e-06 | 0 |
| C-q0-10ohm-parallel-jtl | BJs | `16,15,15,16,16,16` | 16.42329 / 16.42597 / 0.002674723 | 0 |
| C-q0-10ohm-parallel-jtl | BJL1 | `0,0,0,0,0,0` | -0.805862 / -0.8075956 / -0.001733617 | 0 |
| C-q0-10ohm-parallel-jtl | BJL2 | `0,0,0,0,0,0` | -0.3114611 / -0.3121088 / -0.0006476457 | 0 |
| C-q0-10ohm-parallel-jtl | B1|XJTL1 | `0,0,0,0,0,0` | -0.09375832 / -0.09400158 / -0.0002432615 | 0 |
| C-q0-10ohm-parallel-jtl | B2|XJTL1 | `0,0,0,0,0,0` | 0.02560057 / 0.02564598 / 4.540911e-05 | 0 |
| C-q0-10ohm-parallel-jtl | B1|XJTL2 | `0,0,0,0,0,0` | -0.006919293 / -0.006958768 / -3.947532e-05 | 0 |
| C-q0-10ohm-parallel-jtl | B2|XJTL2 | `0,0,0,0,0,0` | 0.01068654 / 0.01069101 / 4.469821e-06 | 0 |

Q0 的完整 local event 只在 BJL2 的同一 pulse、同一 monotonic segment 中计数；JTL 的四颗 JJ分别计数。

## Q0 JTL propagation details

| fixture | pulse | JTL JJ | largest segment (turn) | area (Φ0) | events | onset (ps) | final output signal |
|---|---:|---|---:|---:|---:|---:|---:|
| B-q0-jtl-only | 1 | B1|XJTL1 | -0.1145722 | -0.1149724 | 0 | 15.8 | 1.503806e-05 V |
| B-q0-jtl-only | 1 | B2|XJTL1 | 0.02945858 | 0.02951022 | 0 | 10 | 1.503806e-05 V |
| B-q0-jtl-only | 1 | B1|XJTL2 | -0.008784987 | -0.008896047 | 0 | 21.6 | 1.503806e-05 V |
| B-q0-jtl-only | 1 | B2|XJTL2 | 0.01098241 | 0.01098898 | 0 | 10 | 1.503806e-05 V |
| B-q0-jtl-only | 2 | B1|XJTL1 | -0.1150832 | -0.1154875 | 0 | 65.8 | 2.648332e-06 V |
| B-q0-jtl-only | 2 | B2|XJTL1 | -0.02945111 | -0.02957534 | 0 | 67.7 | 2.648332e-06 V |
| B-q0-jtl-only | 2 | B1|XJTL2 | -0.00874558 | -0.008855134 | 0 | 71.6 | 2.648332e-06 V |
| B-q0-jtl-only | 2 | B2|XJTL2 | -0.003105002 | -0.003148429 | 0 | 74.6 | 2.648332e-06 V |
| B-q0-jtl-only | 3 | B1|XJTL1 | -0.1150832 | -0.1154875 | 0 | 115.8 | 2.648335e-06 V |
| B-q0-jtl-only | 3 | B2|XJTL1 | -0.02945111 | -0.02957533 | 0 | 117.7 | 2.648335e-06 V |
| B-q0-jtl-only | 3 | B1|XJTL2 | -0.008745612 | -0.008855159 | 0 | 121.6 | 2.648335e-06 V |
| B-q0-jtl-only | 3 | B2|XJTL2 | -0.003105002 | -0.003148434 | 0 | 124.6 | 2.648335e-06 V |
| B-q0-jtl-only | 4 | B1|XJTL1 | -0.1150832 | -0.1154875 | 0 | 165.8 | 2.648335e-06 V |
| B-q0-jtl-only | 4 | B2|XJTL1 | -0.02945111 | -0.02957533 | 0 | 167.7 | 2.648335e-06 V |
| B-q0-jtl-only | 4 | B1|XJTL2 | -0.008745612 | -0.008855159 | 0 | 171.6 | 2.648335e-06 V |
| B-q0-jtl-only | 4 | B2|XJTL2 | -0.003105002 | -0.003148434 | 0 | 174.6 | 2.648335e-06 V |
| B-q0-jtl-only | 5 | B1|XJTL1 | -0.1150832 | -0.1154875 | 0 | 215.8 | 2.648335e-06 V |
| B-q0-jtl-only | 5 | B2|XJTL1 | -0.02945111 | -0.02957533 | 0 | 217.7 | 2.648335e-06 V |
| B-q0-jtl-only | 5 | B1|XJTL2 | -0.008745612 | -0.008855159 | 0 | 221.6 | 2.648335e-06 V |
| B-q0-jtl-only | 5 | B2|XJTL2 | -0.003105002 | -0.003148434 | 0 | 224.6 | 2.648335e-06 V |
| B-q0-jtl-only | 6 | B1|XJTL1 | -0.1150832 | -0.1154875 | 0 | 265.8 | 2.648335e-06 V |
| B-q0-jtl-only | 6 | B2|XJTL1 | -0.02945111 | -0.02957533 | 0 | 267.7 | 2.648335e-06 V |
| B-q0-jtl-only | 6 | B1|XJTL2 | -0.008745612 | -0.008855159 | 0 | 271.6 | 2.648335e-06 V |
| B-q0-jtl-only | 6 | B2|XJTL2 | -0.003105002 | -0.003148434 | 0 | 274.6 | 2.648335e-06 V |
| C-q0-10ohm-parallel-jtl | 1 | B1|XJTL1 | -0.09368745 | -0.09393159 | 0 | 17 | 1.468453e-05 V |
| C-q0-10ohm-parallel-jtl | 1 | B2|XJTL1 | 0.02560057 | 0.02564598 | 0 | 10 | 1.468453e-05 V |
| C-q0-10ohm-parallel-jtl | 1 | B1|XJTL2 | -0.006808187 | -0.006851787 | 0 | 18.6 | 1.468453e-05 V |
| C-q0-10ohm-parallel-jtl | 1 | B2|XJTL2 | 0.01068654 | 0.01069101 | 0 | 10 | 1.468453e-05 V |
| C-q0-10ohm-parallel-jtl | 2 | B1|XJTL1 | -0.09375832 | -0.09400158 | 0 | 67 | 2.084894e-06 V |
| C-q0-10ohm-parallel-jtl | 2 | B2|XJTL1 | -0.02510607 | -0.02519793 | 0 | 67.7 | 2.084894e-06 V |
| C-q0-10ohm-parallel-jtl | 2 | B1|XJTL2 | -0.006919293 | -0.006958768 | 0 | 68.5 | 2.084894e-06 V |
| C-q0-10ohm-parallel-jtl | 2 | B2|XJTL2 | -0.002174088 | -0.002204833 | 0 | 74.7 | 2.084894e-06 V |
| C-q0-10ohm-parallel-jtl | 3 | B1|XJTL1 | -0.09375832 | -0.09400158 | 0 | 117 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 3 | B2|XJTL1 | -0.02510606 | -0.02519792 | 0 | 117.7 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 3 | B1|XJTL2 | -0.006919277 | -0.006958755 | 0 | 118.5 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 3 | B2|XJTL2 | -0.002174088 | -0.002204843 | 0 | 124.7 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 4 | B1|XJTL1 | -0.09375832 | -0.09400158 | 0 | 167 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 4 | B2|XJTL1 | -0.02510606 | -0.02519792 | 0 | 167.7 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 4 | B1|XJTL2 | -0.006919277 | -0.006958755 | 0 | 168.5 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 4 | B2|XJTL2 | -0.002174088 | -0.002204843 | 0 | 174.7 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 5 | B1|XJTL1 | -0.09375832 | -0.09400158 | 0 | 217 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 5 | B2|XJTL1 | -0.02510606 | -0.02519792 | 0 | 217.7 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 5 | B1|XJTL2 | -0.006919277 | -0.006958755 | 0 | 218.5 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 5 | B2|XJTL2 | -0.002174088 | -0.002204843 | 0 | 224.7 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 6 | B1|XJTL1 | -0.09375832 | -0.09400158 | 0 | 267 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 6 | B2|XJTL1 | -0.02510606 | -0.02519792 | 0 | 267.7 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 6 | B1|XJTL2 | -0.006919277 | -0.006958755 | 0 | 268.5 | 2.084889e-06 V |
| C-q0-10ohm-parallel-jtl | 6 | B2|XJTL2 | -0.002174088 | -0.002204843 | 0 | 274.7 | 2.084889e-06 V |

## Q5：四个 matched cases

| fixture | case | JJ | activity range (turn) | largest Δturn/area | complete | post complete |
|---|---|---|---:|---|---:|---:|
| D-q5-open | paper-j0-logical0-read | BJs | 0.03448714 | 0.02367573 / 0.02368166 / 5.933251e-06 | 0 | 0 |
| D-q5-open | paper-j0-logical0-read | BJL1 | 0.02177147 | 0.01696405 / 0.01696851 / 4.456313e-06 | 0 | 0 |
| D-q5-open | paper-j0-logical0-read | BJL2 | 0.012297 | 0.01050432 / 0.01050727 / 2.949265e-06 | 0 | 0 |
| D-q5-open | paper-j0-logical0-read0-control | BJs | 0.0001803877 | -0.0001803877 / -0.0001804266 / -3.893254e-08 | 0 | 0 |
| D-q5-open | paper-j0-logical0-read0-control | BJL1 | 5.056353e-05 | -5.056353e-05 / -5.057374e-05 / -1.021847e-08 | 0 | 0 |
| D-q5-open | paper-j0-logical0-read0-control | BJL2 | 4.542282e-05 | 4.542282e-05 / 4.544336e-05 / 2.053502e-08 | 0 | 0 |
| D-q5-open | paper-j1-logical1-read | BJs | 14.37493 | 14.09212 / 14.09214 / 2.268232e-05 | 14 | 0 |
| D-q5-open | paper-j1-logical1-read | BJL1 | 3.204434 | 2.976218 / 2.976257 / 3.861762e-05 | 2 | 0 |
| D-q5-open | paper-j1-logical1-read | BJL2 | 3.167938 | 3.043892 / 3.043909 / 1.68148e-05 | 3 | 0 |
| D-q5-open | paper-j1-logical1-read0-control | BJs | 0.0001803877 | 0.0001803877 / 0.0001804266 / 3.893254e-08 | 0 | 0 |
| D-q5-open | paper-j1-logical1-read0-control | BJL1 | 5.056353e-05 | 5.056353e-05 / 5.058056e-05 / 1.703696e-08 | 0 | 0 |
| D-q5-open | paper-j1-logical1-read0-control | BJL2 | 4.542282e-05 | -4.542282e-05 / -4.544359e-05 / -2.076941e-08 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read | BJs | 0.03448714 | 0.02367573 / 0.02368166 / 5.933251e-06 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read | BJL1 | 0.02380681 | 0.02116477 / 0.02117061 / 5.834726e-06 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read | BJL2 | 0.006546488 | 0.005870812 / 0.005872571 / 1.7586e-06 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read | B1|XJTL1 | 0.004210667 | 0.004210667 / 0.004211986 / 1.319573e-06 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read | B2|XJTL1 | 0.002145918 | -0.002145918 / -0.002146596 / -6.783572e-07 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read | B1|XJTL2 | 0.001026342 | 0.001026342 / 0.001026648 / 3.055078e-07 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read | B2|XJTL2 | 0.0006127943 | -0.0006127943 / -0.0006129813 / -1.870578e-07 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read0-control | BJs | 0.0001803877 | -0.0001803877 / -0.0001804266 / -3.893254e-08 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read0-control | BJL1 | 9.455395e-05 | 9.455395e-05 / 9.458883e-05 / 3.487846e-08 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read0-control | BJL2 | 1.84938e-05 | 1.84938e-05 / 1.848862e-05 / -5.188106e-09 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read0-control | B1|XJTL1 | 2.847282e-05 | -2.847282e-05 / -2.84724e-05 / 4.211137e-10 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read0-control | B2|XJTL1 | 1.817549e-05 | -1.817549e-05 / -1.817476e-05 / 7.298809e-10 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read0-control | B1|XJTL2 | 1.257324e-05 | 1.257324e-05 / 1.256765e-05 / -5.592775e-09 | 0 | 0 |
| E-q5-jtl-only | paper-j0-logical0-read0-control | B2|XJTL2 | 1.20162e-05 | -1.20162e-05 / -1.201019e-05 / 6.008031e-09 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read | BJs | 14.37493 | 14.09212 / 14.09214 / 2.268232e-05 | 14 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read | BJL1 | 0.7710401 | -0.7710401 / -0.7710581 / -1.798091e-05 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read | BJL2 | 0.2592004 | -0.2587884 / -0.2587969 / -8.449217e-06 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read | B1|XJTL1 | 0.08109731 | -0.07500555 / -0.0750086 / -3.042438e-06 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read | B2|XJTL1 | 0.02436118 | -0.02042714 / -0.02042833 / -1.19481e-06 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read | B1|XJTL2 | 0.008555629 | 0.006837535 / 0.006839506 / 1.971052e-06 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read | B2|XJTL2 | 0.003742815 | -0.003742815 / -0.003743906 / -1.091045e-06 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read0-control | BJs | 0.0001803877 | 0.0001803877 / 0.0001804266 / 3.893254e-08 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read0-control | BJL1 | 9.456987e-05 | -9.456987e-05 / -9.458924e-05 / -1.937484e-08 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read0-control | BJL2 | 1.84938e-05 | -1.84938e-05 / -1.848883e-05 / 4.974726e-09 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read0-control | B1|XJTL1 | 2.847282e-05 | 2.847282e-05 / 2.847226e-05 / -5.558492e-10 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read0-control | B2|XJTL1 | 1.819141e-05 | 1.819141e-05 / 1.818522e-05 / -6.187995e-09 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read0-control | B1|XJTL2 | 1.257324e-05 | -1.257324e-05 / -1.256891e-05 / 4.329682e-09 | 0 | 0 |
| E-q5-jtl-only | paper-j1-logical1-read0-control | B2|XJTL2 | 1.200028e-05 | 1.200028e-05 / 1.200569e-05 / 5.406172e-09 | 0 | 0 |

## BJL1/BJL2 directional activity

正、负 monotonic segment 分开报告；Q0 单元格按 pulse 1→6 排列。负值不是事件失败或成功的替代判据，只用于识别方向与 cancellation。

| fixture/case | BJL1 forward Δturn | BJL1 backward Δturn | BJL2 forward Δturn | BJL2 backward Δturn |
|---|---|---|---|---|
| A-q0-open/scaled-iin-68p4u | `3.147799; 3.147778; 3.147778; 3.147779; 3.147778; 3.14777` | `-0.1922815; -0.1922799; -0.1922815; -0.1922815; -0.1922815; -0.1922751` | `3.147755; 3.147725; 3.147725; 3.147727; 3.147725; 3.147725` | `-0.1888055; -0.1887991; -0.1888007; -0.1888007; -0.1887991; -0.1888055` |
| B-q0-jtl-only/scaled-iin-68p4u | `0.7501278; 0.7497462; 0.7497462; 0.7497462; 0.7497462; 0.7497462` | `-0.8540013; -0.8540611; -0.8540611; -0.8540611; -0.8540611; -0.8540611` | `0.3113585; 0.3109774; 0.3109774; 0.3109774; 0.3109774; 0.3109774` | `-0.3561937; -0.3567469; -0.3567469; -0.3567469; -0.3567469; -0.3567469` |
| C-q0-10ohm-parallel-jtl/scaled-iin-68p4u | `0.7297886; 0.7295133; 0.7295133; 0.7295133; 0.7295133; 0.7295133` | `-0.8058249; -0.805862; -0.805862; -0.805862; -0.805862; -0.805862` | `0.2873311; 0.2871036; 0.2871036; 0.2871036; 0.2871036; 0.2871036` | `-0.311014; -0.3114611; -0.3114611; -0.3114611; -0.3114611; -0.3114611` |
| D-q5-open/paper-j0-logical0-read | `0.01696405` | `-0.01471443` | `0.01050432` | `-0.009470483` |
| D-q5-open/paper-j0-logical0-read0-control | `5.007015e-05` | `-5.056353e-05` | `4.542282e-05` | `-3.931127e-05` |
| D-q5-open/paper-j1-logical1-read | `2.976218` | `-0.2357578` | `3.043892` | `-0.2286659` |
| D-q5-open/paper-j1-logical1-read0-control | `5.056353e-05` | `-5.007015e-05` | `3.931127e-05` | `-4.542282e-05` |
| E-q5-jtl-only/paper-j0-logical0-read | `0.02116477` | `-0.01816879` | `0.005870812` | `-0.005050066` |
| E-q5-jtl-only/paper-j0-logical0-read0-control | `9.455395e-05` | `-8.357226e-05` | `1.84938e-05` | `-1.559718e-05` |
| E-q5-jtl-only/paper-j1-logical1-read | `0.4287104` | `-0.7710401` | `0.1589749` | `-0.2587884` |
| E-q5-jtl-only/paper-j1-logical1-read0-control | `8.357226e-05` | `-9.456987e-05` | `1.56131e-05` | `-1.84938e-05` |

## Output boundary / ringing signals

| fixture/case | V(OUT) activity p2p | I(L0) activity p2p (µA) | I(R_LOAD) activity p2p (µA) | JTL input I(L1) activity p2p (µA) | V(JTL_OUT) activity p2p (µV) | I(R_TERM) activity p2p (µA) |
|---|---:|---:|---:|---:|---:|---:|
| A-q0-open/scaled-iin-68p4u | 0.002120029 | 0 | — | — | — | — |
| B-q0-jtl-only/scaled-iin-68p4u | 0.0004596955 | 144.8143 | — | 144.8143 | 15.03806 | 15.03806 |
| C-q0-10ohm-parallel-jtl/scaled-iin-68p4u | 0.0003743612 | 140.5269 | 37.43612 | 127.3703 | 14.68453 | 14.68453 |
| D-q5-open/paper-j0-logical0-read | 5.80899e-05 | 0 | — | — | — | — |
| D-q5-open/paper-j0-logical0-read0-control | 2.827167e-07 | 0 | — | — | — | — |
| D-q5-open/paper-j1-logical1-read | 0.002196427 | 0 | — | — | — | — |
| D-q5-open/paper-j1-logical1-read0-control | 2.827154e-07 | 0 | — | — | — | — |
| E-q5-jtl-only/paper-j0-logical0-read | 1.901612e-05 | 4.25555 | — | 4.25555 | 0.4460638 | 0.4460638 |
| E-q5-jtl-only/paper-j0-logical0-read0-control | 5.511973e-08 | 0.02177 | — | 0.02177 | 0.008487831 | 0.008487831 |
| E-q5-jtl-only/paper-j1-logical1-read | 0.0003511273 | 110.1819 | — | 110.1819 | 2.783239 | 2.783239 |
| E-q5-jtl-only/paper-j1-logical1-read0-control | 5.512112e-08 | 0.02178 | — | 0.02178 | 0.008488231 | 0.008488231 |

## Required comparison matrix

| QB source | 10Ω | OPEN | JTL-only | 10Ω || JTL |
|---|---|---|---|---|
| Q0 true-event | accepted Q0: BJL2 one per pulse | `A` — **Q0_MULTIEVENT**; open boundary result | `B` — **Q0_EVENT_LOST_UNDER_LOAD**; direct JTL result | `C` — **Q0_EVENT_LOST_UNDER_LOAD**; parallel-load result |
| Q5 near-event | accepted Q5: BJL2≈0.968179 turn, zero complete event | `D` — **Q5_MULTIFIRE**; open boundary result | `E` — **Q5_NO_JTL_TRIGGER**; direct JTL result | accepted Q6: `NO_JTL_TRIGGER` |

## Observed

- A：A-q0-open: BJL2 `3,3,3,3,3,3`, max post p2p=9.549297e-06 turn。
- B：B-q0-jtl-only: BJL2 `0,0,0,0,0,0`, max post p2p=0.0001430962 turn。
- C：C-q0-10ohm-parallel-jtl: BJL2 `0,0,0,0,0,0`, max post p2p=7.73493e-05 turn。
- D read1：D-q5-open/paper-j1-logical1-read: BJL2 largest=3.043892 / 3.043909 / 1.68148e-05, complete=3；E read1：E-q5-jtl-only/paper-j1-logical1-read: BJL2 largest=-0.2587884 / -0.2587969 / -8.449217e-06, complete=0。
- 所有 BJs/BJL1/BJL2 与 JTL JJ 的 event 计数均来自 continuous unwrapped phase、同一 monotonic segment 和同一 JJ 直接电压面积；phase total range、current peak、voltage peak 不单独构成 event。

## Derived

- phase turns = raw `P(...)` 的连续 unwrap 后的 Δphase/(2π)。
- 同段 voltage area = `∫V_sameJJ dt / Φ0`；candidate 至少 1 turn、area 同号，残差阈值为 `max(0.02, 0.05×|Δturn|)` turn。该阈值是本探索的 analysis rule，不是器件 universal threshold。
- Q0 local event vector按六个 pulse分别报告；Q5按四个 matched case分别报告。

## Inference

- A 与 accepted Q0 的对比表明：10Ω 不是 Q0 产生 local BJL2 phase/area transition 的必要条件，但在本 frozen point 下它把 OPEN 的约 3-unit/pulse multi-event 行为压到 accepted 的 exactly-one/pulse；因此 10Ω 对 one-shot/retrap 边界具有因果影响。
- B/C 对比区分 direct JTL loading 与 `10Ω || JTL` 并联 loading；若两者都丢失而 A 保留，支持 JTL input boundary/interface mismatch，而不是把 Q0 standalone event否定。
- D/E 与 accepted Q5/Q6 显示 near-event 对 load boundary 极敏感：OPEN 变成 read1-selective multi-event，而 JTL-only 与 `10Ω || JTL` 均不给出完整 JTL event；这支持“Q5 near-event 的 margin 小于 Q0 true-event”，但不是整个 QB/JTL family 的普遍不可能性。
- B/C 均未出现完整 Q0 BJL2 或 JTL JJ event，且 C 相比 B 仅改变保留的 10Ω 并联支路；在本已验证 JTL chain 下，这支持 direct JTL input boundary 对 Q0 true-event 的强加载/接口不兼容解释，而不否定 Q0 在 10Ω isolated boundary 下的 local event。

## Unknown / limits

- 本矩阵没有连接 canonical BVM，也没有 physical BVM back-action evidence；Q5仍是 frozen replay fixture。
- R11-A 的 standard-JTL positive control provenance被复用，本矩阵不重复运行该 positive control。
- OPEN 是无 downstream load的边界诊断，不代表实际封装或后端接口。
- 本报告不把 Q0 BJL2 local event自动称作 downstream SFQ delivery；只有 JTL四颗 JJ的事件序列达到完整、面积一致、时序合理且无 post event时，才称 tested-chain propagation。

## Stop

本 bounded matrix 已完成；不调 QB/JTL 参数、不加 conditioner、不接 T1、不连接 physical BVM。
