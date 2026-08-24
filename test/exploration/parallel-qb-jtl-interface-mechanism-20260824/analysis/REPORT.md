# Parallel QB→JTL interface mechanism batch report

parent HEAD: `d05d96ab3eb13dc19af9dbaa0b7a5d3ac92ac63d`  
JoSIM: `v2.7.2837d13`, binary SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`

本报告只使用 raw CSV 的 continuous unwrapped phase、同一 JJ/同一 monotonic segment 的直接 voltage area，以及 post window。没有使用 legacy `fast_events`。

## Local verdicts

| fixture | local verdict | key result |
|---|---|---|
| M1-ideal-replay | **M1_FIRST_STAGE_ONLY** | JTL event vector `[1, 0, 0, 0]`; positive-control gate `False` |
| M2-riso10 | **M2-riso10_Q0_EVENT_LOST_UNDER_BOUNDARY** | BJL2 events `[0, 0, 0, 0, 0, 0]`; JTL event vectors `[(0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)]` |
| M3-rseries10 | **M3-rseries10_Q0_EVENT_PRESERVED_JTL_SUBTHRESHOLD** | BJL2 events `[1, 1, 1, 1, 1, 1]`; JTL event vectors `[(0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)]` |
| M4-liso10p | **M4-liso10p_Q0_EVENT_LOST_UNDER_BOUNDARY** | BJL2 events `[0, 0, 0, 0, 0, 0]`; JTL event vectors `[(0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)]` |
| M5-positive-control | **M5_SCALED_JTL_POSITIVE_CONTROL_PASS** | JTL event vector `[1, 1, 0, 0]`; positive-control gate `True` |
| M5-q0-scaled | **M5-q0-scaled_Q0_EVENT_LOST_UNDER_BOUNDARY** | BJL2 events `[0, 0, 0, 0, 0, 0]`; JTL event vectors `[(0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)]` |

## Matrix comparison

| source/boundary | Q0 local BJL2 result | JTL result | interpretation |
|---|---|---|---|
| accepted Q0 + 10Ω | exactly one per six pulse (accepted comparator) | not attached | local one-shot reference |
| accepted Q0 OPEN | about three local units per pulse (accepted prior matrix) | not attached | open boundary is multi-event |
| M1 ideal V(OUT) replay | no QB | first JTL JJ one strict event; downstream strict segments sub-turn | replay starts first stage but does not establish full waveform-compatible chain |
| M2 Q0 + 10Ω + 10Ω series | zero complete BJL2; largest near 1 turn | zero | retained shunt plus series branch suppresses this Q0 local event |
| M3 Q0 + 10Ω series, no shunt | one BJL2 event per pulse | zero | local event survives this series boundary, but JTL remains subthreshold |
| M4 Q0 + 10Ω + 10pH series | zero complete BJL2 | zero | selected inductive boundary strongly changes/diminishes the local trajectory |
| M5 coherent scaled JTL + Q0 + 10Ω | zero complete BJL2; largest ≈0.961 turn | zero | current-class scaling alone does not close Q0→JTL interface |

## Q0 pulse-level event vectors

| fixture | pulse | BJs | BJL1 | BJL2 | JTL B1/X1 | JTL B2/X1 | JTL B1/X2 | JTL B2/X2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| M2-riso10 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M2-riso10 | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M2-riso10 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M2-riso10 | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M2-riso10 | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M2-riso10 | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M3-rseries10 | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| M3-rseries10 | 2 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| M3-rseries10 | 3 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| M3-rseries10 | 4 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| M3-rseries10 | 5 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| M3-rseries10 | 6 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| M4-liso10p | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| M4-liso10p | 2 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M4-liso10p | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M4-liso10p | 4 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M4-liso10p | 5 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M4-liso10p | 6 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| M5-q0-scaled | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| M5-q0-scaled | 2 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| M5-q0-scaled | 3 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| M5-q0-scaled | 4 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| M5-q0-scaled | 5 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| M5-q0-scaled | 6 | 1 | 1 | 0 | 0 | 0 | 0 | 0 |

## Largest same-segment phase/area evidence

| fixture/case | JJ | largest segment turns | same-segment area Φ0 | residual turns |
|---|---|---:|---:|---:|
| M1-ideal-replay/replay | `P(B1|XJTL1)` | 1.07462 | 1.07908 | 0.0044626 |
| M1-ideal-replay/replay | `P(B2|XJTL1)` | 0.929944 | 0.932699 | 0.00275443 |
| M1-ideal-replay/replay | `P(B1|XJTL2)` | 0.914721 | 0.917261 | 0.00253991 |
| M1-ideal-replay/replay | `P(B2|XJTL2)` | 0.867192 | 0.868925 | 0.00173331 |
| M2-riso10/pulse 1 | `P(BJS|XBQ)` | 16.3905 | 16.3961 | 0.00564104 |
| M2-riso10/pulse 1 | `P(BJL1|XBQ)` | 0.993483 | 0.994051 | 0.000568116 |
| M2-riso10/pulse 1 | `P(BJL2|XBQ)` | 0.998809 | 0.998841 | 3.14541e-05 |
| M2-riso10/pulse 1 | `P(B1|XJTL1)` | -0.0361599 | -0.0363818 | -0.000221836 |
| M2-riso10/pulse 1 | `P(B2|XJTL1)` | -0.00965069 | -0.00970382 | -5.31214e-05 |
| M2-riso10/pulse 1 | `P(B1|XJTL2)` | 0.00363841 | 0.00368097 | 4.2559e-05 |
| M2-riso10/pulse 1 | `P(B2|XJTL2)` | 0.0096513 | 0.00965122 | -8.30892e-08 |
| M2-riso10/pulse 2 | `P(BJS|XBQ)` | 15.3375 | 15.3385 | 0.000954028 |
| M2-riso10/pulse 2 | `P(BJL1|XBQ)` | 0.990731 | 0.991513 | 0.000781981 |
| M2-riso10/pulse 2 | `P(BJL2|XBQ)` | 0.999944 | 0.999944 | -2.47348e-07 |
| M2-riso10/pulse 2 | `P(B1|XJTL1)` | -0.0357973 | -0.0360142 | -0.000216967 |
| M2-riso10/pulse 2 | `P(B2|XJTL1)` | -0.00984069 | -0.00989753 | -5.68368e-05 |
| M2-riso10/pulse 2 | `P(B1|XJTL2)` | -0.00280105 | -0.00283449 | -3.34376e-05 |
| M2-riso10/pulse 2 | `P(B2|XJTL2)` | -0.00106573 | -0.00108061 | -1.48771e-05 |
| M2-riso10/pulse 3 | `P(BJS|XBQ)` | 15.3413 | 15.3417 | 0.000406585 |
| M2-riso10/pulse 3 | `P(BJL1|XBQ)` | 0.990732 | 0.991513 | 0.000781677 |
| M2-riso10/pulse 3 | `P(BJL2|XBQ)` | 0.999943 | 0.999944 | 7.02609e-08 |
| M2-riso10/pulse 3 | `P(B1|XJTL1)` | -0.0357973 | -0.0360142 | -0.000216952 |
| M2-riso10/pulse 3 | `P(B2|XJTL1)` | -0.00984069 | -0.00989752 | -5.68246e-05 |
| M2-riso10/pulse 3 | `P(B1|XJTL2)` | -0.00280103 | -0.00283446 | -3.34274e-05 |
| M2-riso10/pulse 3 | `P(B2|XJTL2)` | -0.00106573 | -0.0010806 | -1.48671e-05 |
| M2-riso10/pulse 4 | `P(BJS|XBQ)` | 16.3408 | 16.3429 | 0.00219097 |
| M2-riso10/pulse 4 | `P(BJL1|XBQ)` | 0.990732 | 0.991513 | 0.000781677 |
| M2-riso10/pulse 4 | `P(BJL2|XBQ)` | 0.999943 | 0.999944 | 7.02608e-08 |
| M2-riso10/pulse 4 | `P(B1|XJTL1)` | -0.0357973 | -0.0360142 | -0.000216952 |
| M2-riso10/pulse 4 | `P(B2|XJTL1)` | -0.00984069 | -0.00989752 | -5.68246e-05 |
| M2-riso10/pulse 4 | `P(B1|XJTL2)` | -0.00280103 | -0.00283446 | -3.34274e-05 |
| M2-riso10/pulse 4 | `P(B2|XJTL2)` | -0.00106573 | -0.0010806 | -1.48671e-05 |
| M2-riso10/pulse 5 | `P(BJS|XBQ)` | 16.4233 | 16.426 | 0.00267472 |
| M2-riso10/pulse 5 | `P(BJL1|XBQ)` | 0.990732 | 0.991513 | 0.000781677 |
| M2-riso10/pulse 5 | `P(BJL2|XBQ)` | 0.999943 | 0.999944 | 7.02608e-08 |
| M2-riso10/pulse 5 | `P(B1|XJTL1)` | -0.0357973 | -0.0360142 | -0.000216952 |
| M2-riso10/pulse 5 | `P(B2|XJTL1)` | -0.00984069 | -0.00989752 | -5.68246e-05 |
| M2-riso10/pulse 5 | `P(B1|XJTL2)` | -0.00280103 | -0.00283446 | -3.34274e-05 |
| M2-riso10/pulse 5 | `P(B2|XJTL2)` | -0.00106573 | -0.0010806 | -1.48671e-05 |
| M2-riso10/pulse 6 | `P(BJS|XBQ)` | 16.383 | 16.3844 | 0.00143504 |
| M2-riso10/pulse 6 | `P(BJL1|XBQ)` | 0.990732 | 0.991513 | 0.000781677 |
| M2-riso10/pulse 6 | `P(BJL2|XBQ)` | 0.999943 | 0.999944 | 7.02608e-08 |
| M2-riso10/pulse 6 | `P(B1|XJTL1)` | -0.0357973 | -0.0360142 | -0.000216952 |
| M2-riso10/pulse 6 | `P(B2|XJTL1)` | -0.00984069 | -0.00989752 | -5.68246e-05 |
| M2-riso10/pulse 6 | `P(B1|XJTL2)` | -0.00280103 | -0.00283446 | -3.34274e-05 |
| M2-riso10/pulse 6 | `P(B2|XJTL2)` | -0.00106573 | -0.0010806 | -1.48671e-05 |
| M3-rseries10/pulse 1 | `P(BJS|XBQ)` | 16.3905 | 16.3961 | 0.00564104 |
| M3-rseries10/pulse 1 | `P(BJL1|XBQ)` | 1.26338 | 1.26487 | 0.00148423 |
| M3-rseries10/pulse 1 | `P(BJL2|XBQ)` | 1.0893 | 1.08884 | -0.000463703 |
| M3-rseries10/pulse 1 | `P(B1|XJTL1)` | -0.0678327 | -0.0683207 | -0.000488052 |
| M3-rseries10/pulse 1 | `P(B2|XJTL1)` | -0.0223225 | -0.022503 | -0.000180473 |
| M3-rseries10/pulse 1 | `P(B1|XJTL2)` | -0.00680052 | -0.00685858 | -5.80647e-05 |
| M3-rseries10/pulse 1 | `P(B2|XJTL2)` | 0.0102592 | 0.010266 | 6.80506e-06 |
| M3-rseries10/pulse 2 | `P(BJS|XBQ)` | 15.3375 | 15.3385 | 0.000954028 |
| M3-rseries10/pulse 2 | `P(BJL1|XBQ)` | 1.26284 | 1.26402 | 0.00118247 |
| M3-rseries10/pulse 2 | `P(BJL2|XBQ)` | 1.08892 | 1.08939 | 0.000468156 |
| M3-rseries10/pulse 2 | `P(B1|XJTL1)` | -0.0684565 | -0.0689498 | -0.000493319 |
| M3-rseries10/pulse 2 | `P(B2|XJTL1)` | -0.0221436 | -0.0223175 | -0.000173905 |
| M3-rseries10/pulse 2 | `P(B1|XJTL2)` | -0.00700887 | -0.00706673 | -5.78673e-05 |
| M3-rseries10/pulse 2 | `P(B2|XJTL2)` | -0.00186875 | -0.00189763 | -2.88807e-05 |
| M3-rseries10/pulse 3 | `P(BJS|XBQ)` | 15.3413 | 15.3417 | 0.000406585 |
| M3-rseries10/pulse 3 | `P(BJL1|XBQ)` | 1.26284 | 1.26402 | 0.00118183 |
| M3-rseries10/pulse 3 | `P(BJL2|XBQ)` | 1.08892 | 1.08939 | 0.000466599 |
| M3-rseries10/pulse 3 | `P(B1|XJTL1)` | -0.0684565 | -0.0689498 | -0.000493316 |
| M3-rseries10/pulse 3 | `P(B2|XJTL1)` | -0.0221437 | -0.0223176 | -0.000173899 |
| M3-rseries10/pulse 3 | `P(B1|XJTL2)` | -0.00700883 | -0.00706669 | -5.78607e-05 |
| M3-rseries10/pulse 3 | `P(B2|XJTL2)` | -0.00186875 | -0.00189762 | -2.88736e-05 |
| M3-rseries10/pulse 4 | `P(BJS|XBQ)` | 16.3408 | 16.3429 | 0.00219097 |
| M3-rseries10/pulse 4 | `P(BJL1|XBQ)` | 1.26284 | 1.26402 | 0.00118183 |
| M3-rseries10/pulse 4 | `P(BJL2|XBQ)` | 1.08892 | 1.08939 | 0.000468191 |
| M3-rseries10/pulse 4 | `P(B1|XJTL1)` | -0.0684565 | -0.0689498 | -0.000493316 |
| M3-rseries10/pulse 4 | `P(B2|XJTL1)` | -0.0221437 | -0.0223176 | -0.000173899 |
| M3-rseries10/pulse 4 | `P(B1|XJTL2)` | -0.00700883 | -0.00706669 | -5.78607e-05 |
| M3-rseries10/pulse 4 | `P(B2|XJTL2)` | -0.00186875 | -0.00189762 | -2.88736e-05 |
| M3-rseries10/pulse 5 | `P(BJS|XBQ)` | 16.4233 | 16.426 | 0.00267472 |
| M3-rseries10/pulse 5 | `P(BJL1|XBQ)` | 1.26284 | 1.26402 | 0.00118183 |
| M3-rseries10/pulse 5 | `P(BJL2|XBQ)` | 1.08892 | 1.08939 | 0.000468191 |
| M3-rseries10/pulse 5 | `P(B1|XJTL1)` | -0.0684565 | -0.0689498 | -0.000493316 |
| M3-rseries10/pulse 5 | `P(B2|XJTL1)` | -0.0221437 | -0.0223176 | -0.000173899 |
| M3-rseries10/pulse 5 | `P(B1|XJTL2)` | -0.00700883 | -0.00706669 | -5.78607e-05 |
| M3-rseries10/pulse 5 | `P(B2|XJTL2)` | -0.00186875 | -0.00189762 | -2.88736e-05 |
| M3-rseries10/pulse 6 | `P(BJS|XBQ)` | 16.383 | 16.3844 | 0.00143504 |
| M3-rseries10/pulse 6 | `P(BJL1|XBQ)` | 1.26284 | 1.26402 | 0.00118342 |
| M3-rseries10/pulse 6 | `P(BJL2|XBQ)` | 1.08892 | 1.08939 | 0.000468191 |
| M3-rseries10/pulse 6 | `P(B1|XJTL1)` | -0.0684565 | -0.0689498 | -0.000493316 |
| M3-rseries10/pulse 6 | `P(B2|XJTL1)` | -0.0221437 | -0.0223176 | -0.000173899 |
| M3-rseries10/pulse 6 | `P(B1|XJTL2)` | -0.00700883 | -0.00706669 | -5.78607e-05 |
| M3-rseries10/pulse 6 | `P(B2|XJTL2)` | -0.00186875 | -0.00189762 | -2.88736e-05 |
| M4-liso10p/pulse 1 | `P(BJS|XBQ)` | 16.3905 | 16.3961 | 0.00564104 |
| M4-liso10p/pulse 1 | `P(BJL1|XBQ)` | 1.04115 | 1.04253 | 0.00138646 |
| M4-liso10p/pulse 1 | `P(BJL2|XBQ)` | 0.823903 | 0.824176 | 0.000272198 |
| M4-liso10p/pulse 1 | `P(B1|XJTL1)` | 0.0875875 | 0.0876497 | 6.22238e-05 |
| M4-liso10p/pulse 1 | `P(B2|XJTL1)` | 0.0223539 | 0.022377 | 2.30318e-05 |
| M4-liso10p/pulse 1 | `P(B1|XJTL2)` | 0.00519106 | 0.00519802 | 6.95868e-06 |
| M4-liso10p/pulse 1 | `P(B2|XJTL2)` | 0.0121422 | 0.0121395 | -2.7091e-06 |
| M4-liso10p/pulse 2 | `P(BJS|XBQ)` | 15.3375 | 15.3385 | 0.000954028 |
| M4-liso10p/pulse 2 | `P(BJL1|XBQ)` | -0.219241 | -0.220102 | -0.000861127 |
| M4-liso10p/pulse 2 | `P(BJL2|XBQ)` | 0.0899351 | 0.0901858 | 0.000250684 |
| M4-liso10p/pulse 2 | `P(B1|XJTL1)` | -0.0150842 | -0.0151373 | -5.30632e-05 |
| M4-liso10p/pulse 2 | `P(B2|XJTL1)` | -0.00442481 | -0.00444522 | -2.04076e-05 |
| M4-liso10p/pulse 2 | `P(B1|XJTL2)` | -0.00134231 | -0.00135041 | -8.10117e-06 |
| M4-liso10p/pulse 2 | `P(B2|XJTL2)` | -0.000335053 | -0.000339788 | -4.73494e-06 |
| M4-liso10p/pulse 3 | `P(BJS|XBQ)` | 15.3413 | 15.3417 | 0.000406585 |
| M4-liso10p/pulse 3 | `P(BJL1|XBQ)` | -0.219241 | -0.220102 | -0.000860966 |
| M4-liso10p/pulse 3 | `P(BJL2|XBQ)` | 0.0899351 | 0.0901858 | 0.000250679 |
| M4-liso10p/pulse 3 | `P(B1|XJTL1)` | -0.0150842 | -0.0151373 | -5.3069e-05 |
| M4-liso10p/pulse 3 | `P(B2|XJTL1)` | -0.00442483 | -0.00444523 | -2.04078e-05 |
| M4-liso10p/pulse 3 | `P(B1|XJTL2)` | -0.00134228 | -0.00135038 | -8.09981e-06 |
| M4-liso10p/pulse 3 | `P(B2|XJTL2)` | -0.000335037 | -0.000339779 | -4.74219e-06 |
| M4-liso10p/pulse 4 | `P(BJS|XBQ)` | 16.3408 | 16.3429 | 0.00219097 |
| M4-liso10p/pulse 4 | `P(BJL1|XBQ)` | -0.219241 | -0.220102 | -0.000860966 |
| M4-liso10p/pulse 4 | `P(BJL2|XBQ)` | 0.0899351 | 0.0901858 | 0.000250679 |
| M4-liso10p/pulse 4 | `P(B1|XJTL1)` | -0.0150842 | -0.0151373 | -5.3069e-05 |
| M4-liso10p/pulse 4 | `P(B2|XJTL1)` | -0.00442483 | -0.00444523 | -2.04078e-05 |
| M4-liso10p/pulse 4 | `P(B1|XJTL2)` | -0.00134228 | -0.00135038 | -8.09985e-06 |
| M4-liso10p/pulse 4 | `P(B2|XJTL2)` | -0.000335037 | -0.000339779 | -4.74219e-06 |
| M4-liso10p/pulse 5 | `P(BJS|XBQ)` | 16.4233 | 16.426 | 0.00267472 |
| M4-liso10p/pulse 5 | `P(BJL1|XBQ)` | -0.219241 | -0.220102 | -0.000860966 |
| M4-liso10p/pulse 5 | `P(BJL2|XBQ)` | 0.0899351 | 0.0901858 | 0.000250679 |
| M4-liso10p/pulse 5 | `P(B1|XJTL1)` | -0.0150842 | -0.0151373 | -5.3069e-05 |
| M4-liso10p/pulse 5 | `P(B2|XJTL1)` | -0.00442483 | -0.00444523 | -2.04078e-05 |
| M4-liso10p/pulse 5 | `P(B1|XJTL2)` | -0.00134228 | -0.00135038 | -8.09985e-06 |
| M4-liso10p/pulse 5 | `P(B2|XJTL2)` | -0.000335037 | -0.000339779 | -4.74219e-06 |
| M4-liso10p/pulse 6 | `P(BJS|XBQ)` | 16.383 | 16.3844 | 0.00143504 |
| M4-liso10p/pulse 6 | `P(BJL1|XBQ)` | -0.219241 | -0.220102 | -0.000860966 |
| M4-liso10p/pulse 6 | `P(BJL2|XBQ)` | 0.0899351 | 0.0901858 | 0.000250679 |
| M4-liso10p/pulse 6 | `P(B1|XJTL1)` | -0.0150842 | -0.0151373 | -5.3069e-05 |
| M4-liso10p/pulse 6 | `P(B2|XJTL1)` | -0.00442483 | -0.00444523 | -2.04078e-05 |
| M4-liso10p/pulse 6 | `P(B1|XJTL2)` | -0.00134228 | -0.00135038 | -8.09985e-06 |
| M4-liso10p/pulse 6 | `P(B2|XJTL2)` | -0.000335037 | -0.000339779 | -4.74219e-06 |
| M5-positive-control/positive-control | `P(B1|XJTL1)` | 1.26042 | 1.26045 | 3.47481e-05 |
| M5-positive-control/positive-control | `P(B2|XJTL1)` | 1.06427 | 1.06434 | 6.64642e-05 |
| M5-positive-control/positive-control | `P(B1|XJTL2)` | 0.985369 | 0.985431 | 6.12319e-05 |
| M5-positive-control/positive-control | `P(B2|XJTL2)` | 0.893874 | 0.893908 | 3.46546e-05 |
| M5-q0-scaled/pulse 1 | `P(BJS|XBQ)` | 16.3905 | 16.3961 | 0.00564104 |
| M5-q0-scaled/pulse 1 | `P(BJL1|XBQ)` | 1.06791 | 1.06934 | 0.00142906 |
| M5-q0-scaled/pulse 1 | `P(BJL2|XBQ)` | 0.960883 | 0.961158 | 0.000275236 |
| M5-q0-scaled/pulse 1 | `P(B1|XJTL1)` | 0.984281 | 0.987754 | 0.00347279 |
| M5-q0-scaled/pulse 1 | `P(B2|XJTL1)` | 0.92031 | 0.922725 | 0.00241535 |
| M5-q0-scaled/pulse 1 | `P(B1|XJTL2)` | 0.914257 | 0.916749 | 0.00249172 |
| M5-q0-scaled/pulse 1 | `P(B2|XJTL2)` | 0.866797 | 0.868551 | 0.00175416 |
| M5-q0-scaled/pulse 2 | `P(BJS|XBQ)` | 15.3375 | 15.3385 | 0.000954028 |
| M5-q0-scaled/pulse 2 | `P(BJL1|XBQ)` | 1.06807 | 1.06922 | 0.00114403 |
| M5-q0-scaled/pulse 2 | `P(BJL2|XBQ)` | 0.960989 | 0.961398 | 0.000408597 |
| M5-q0-scaled/pulse 2 | `P(B1|XJTL1)` | 0.983668 | 0.987103 | 0.00343511 |
| M5-q0-scaled/pulse 2 | `P(B2|XJTL1)` | 0.920837 | 0.923239 | 0.00240246 |
| M5-q0-scaled/pulse 2 | `P(B1|XJTL2)` | 0.918573 | 0.921141 | 0.00256844 |
| M5-q0-scaled/pulse 2 | `P(B2|XJTL2)` | 0.855011 | 0.856719 | 0.00170739 |
| M5-q0-scaled/pulse 3 | `P(BJS|XBQ)` | 15.3413 | 15.3417 | 0.000406585 |
| M5-q0-scaled/pulse 3 | `P(BJL1|XBQ)` | 1.06807 | 1.06922 | 0.00114342 |
| M5-q0-scaled/pulse 3 | `P(BJL2|XBQ)` | 0.960989 | 0.961399 | 0.00040987 |
| M5-q0-scaled/pulse 3 | `P(B1|XJTL1)` | 0.983665 | 0.9871 | 0.00343487 |
| M5-q0-scaled/pulse 3 | `P(B2|XJTL1)` | 0.920839 | 0.923242 | 0.00240333 |
| M5-q0-scaled/pulse 3 | `P(B1|XJTL2)` | 0.918574 | 0.921143 | 0.00256944 |
| M5-q0-scaled/pulse 3 | `P(B2|XJTL2)` | 0.855014 | 0.85672 | 0.00170604 |
| M5-q0-scaled/pulse 4 | `P(BJS|XBQ)` | 16.3408 | 16.3429 | 0.00219097 |
| M5-q0-scaled/pulse 4 | `P(BJL1|XBQ)` | 1.06807 | 1.06922 | 0.00114342 |
| M5-q0-scaled/pulse 4 | `P(BJL2|XBQ)` | 0.96099 | 0.961399 | 0.000408278 |
| M5-q0-scaled/pulse 4 | `P(B1|XJTL1)` | 0.983665 | 0.9871 | 0.00343488 |
| M5-q0-scaled/pulse 4 | `P(B2|XJTL1)` | 0.920839 | 0.92324 | 0.00240175 |
| M5-q0-scaled/pulse 4 | `P(B1|XJTL2)` | 0.918575 | 0.921143 | 0.00256784 |
| M5-q0-scaled/pulse 4 | `P(B2|XJTL2)` | 0.855012 | 0.85672 | 0.00170763 |
| M5-q0-scaled/pulse 5 | `P(BJS|XBQ)` | 16.4233 | 16.426 | 0.00267472 |
| M5-q0-scaled/pulse 5 | `P(BJL1|XBQ)` | 1.06807 | 1.06922 | 0.00114501 |
| M5-q0-scaled/pulse 5 | `P(BJL2|XBQ)` | 0.960989 | 0.961399 | 0.00040987 |
| M5-q0-scaled/pulse 5 | `P(B1|XJTL1)` | 0.983665 | 0.9871 | 0.00343488 |
| M5-q0-scaled/pulse 5 | `P(B2|XJTL1)` | 0.920839 | 0.923242 | 0.00240333 |
| M5-q0-scaled/pulse 5 | `P(B1|XJTL2)` | 0.918574 | 0.921143 | 0.00256944 |
| M5-q0-scaled/pulse 5 | `P(B2|XJTL2)` | 0.855014 | 0.85672 | 0.00170604 |
| M5-q0-scaled/pulse 6 | `P(BJS|XBQ)` | 16.383 | 16.3844 | 0.00143504 |
| M5-q0-scaled/pulse 6 | `P(BJL1|XBQ)` | 1.06807 | 1.06922 | 0.00114342 |
| M5-q0-scaled/pulse 6 | `P(BJL2|XBQ)` | 0.96099 | 0.961399 | 0.000408278 |
| M5-q0-scaled/pulse 6 | `P(B1|XJTL1)` | 0.983665 | 0.9871 | 0.00343488 |
| M5-q0-scaled/pulse 6 | `P(B2|XJTL1)` | 0.920839 | 0.92324 | 0.00240175 |
| M5-q0-scaled/pulse 6 | `P(B1|XJTL2)` | 0.918575 | 0.921143 | 0.00256784 |
| M5-q0-scaled/pulse 6 | `P(B2|XJTL2)` | 0.855014 | 0.85672 | 0.00170604 |

## Observed

- M1 是 Q0 `V(OUT,t)` 的 ideal replay；它只测 waveform/interface compatibility，不测 QB loading。其第一颗 JTL JJ有严格 complete segment，但后三级的最大严格 monotonic segment分别低于一 turn。
- M2/M3/M4 保留各自 preregistered load boundary，Q0 与 JTL 原始 trace 均被直接记录；M3 的 BJL2 六脉冲均满足同段 phase/area event，而 M2/M4 不满足。
- M5 scaled-JTL positive control 的 full-window phase/area calibration 通过；M5-Q0 coupling 的 BJL2 最大严格 forward segment约 `0.961` turn，JTL四颗 JJ均未达到严格 complete event。
- 所有 post window 均保持有界；本报告没有观察到由这些 fixture 单独产生的 free-running/multifire JTL sequence。

## Derived

- 每个 phase turn 为 raw JoSIM `P(...)` unwrap 后的同一窗口端点差除以 `2π`。
- 同段 area 为同一 JJ、同一段端点上的 `∫Vdt/Φ0`；candidate event 规则为绝对 turns≥1、同号 area、residual≤`max(0.02,0.05×|turns|)`。该规则是本探索的分析规则，不是器件 universal threshold。
- M5 positive-control gate 使用已接受 R11-A 的 bounded full-window phase/area calibration，并仍单独报告 largest monotonic segment；这不替代新 Q0/JTL event 的严格同段证据。

## Inference

- 不能把 M1 归结为“完整 waveform compatibility”：ideal replay只完成第一阶段，因此 M1 尚未满足“若物理 direct fail则纯粹归因 reflected loading”的条件。当前证据更谨慎地支持 waveform shape/temporal delivery 与 JTL boundary 共同受限。
- M2 与 M3 的差异表明，保留原始 10Ω shunt 后再加 10Ω series 会把 Q0 BJL2 最大段压到约 `0.999` 以下；移除 shunt、只保留 series branch 则 local BJL2 event恢复，但仍没有 JTL propagation。因此 series branch可以改变 local retrap/load-line，却不是已证明的 JTL receiver。
- M4 的 10pH series boundary在本点显著改变 transient transfer，不能被解释成温和的 passive isolation success。
- M5 的 coherent current-class positive control有效而 Q0 coupling仍失败，说明“只把 JTL Ic降到QB current class”不是充分机制；失败仍位于 Q0 output waveform 与 JTL input dynamic boundary/drive matching之间。
- 这些结论只适用于本次冻结的 Q0/JTL fixtures，不否定更广泛的 conditioner、regenerator 或其他接口 family。

## Unknown / limits

- 本批次没有 canonical BVM、12-JSL、DCSFQ 或 T1；没有新的 BVM back-action evidence。
- M1 是 ideal voltage counterfactual；M5 是 coherent scaling diagnostic，不是 standard JTL 的 replacement claim。
- M3 改变了原始 Q0 shunt boundary，故不能与 accepted Q0+10Ω 直接视为同一 one-shot operating point。

## Stop

本批次完成后不进行 QB/JTL 参数调整、conditioner、T1 或 physical BVM integration。
