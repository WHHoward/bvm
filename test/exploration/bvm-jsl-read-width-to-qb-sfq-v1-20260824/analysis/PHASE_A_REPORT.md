# BVM_JSL_READ_WIDTH_TO_QB_SFQ_V1 — Phase A report

## Status

`DURATION_SUPPORTED`: the shortest registered point with a clear useful read1 area gain and preserved read0/control/source guards is W*=12 ps. This is a Phase-A source result only; it is not a QB result.

All phase values below are raw JoSIM `P(...)` unwrapped trajectories in rad for absolute statistics; only explicitly named pre/post differences are shown as turns. Current areas are baseline-subtracted using the `[80,90) ps` pre median and use the actual CSV time axis.

## Source waveform table

| width | case | I(L_SL) min..max (µA) | signed area (µA·ps) | positive area | negative area | duration ≥10% (ps) | FWHM around peak (ps) | V(SL) p2p (µV) |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 9 | logical1-read | -45.151..75.3409 | 258.393 | 357.742 | -99.3498 | 2.025 | 1.3125 | 1445.9 |
| 9 | logical0-read | -26.4115..22.7349 | 0.00896769 | 56.6062 | -56.5972 | 1.7875 | 1.05 | 589.757 |
| 9 | logical1-read0-control | -0.000888561..0.000827329 | -0.00526471 | 0.00269915 | -0.00796386 | 1.225 | 0.9875 | 0.0205907 |
| 9 | logical0-read0-control | -0.000827329..0.000888561 | 0.00526471 | 0.00796386 | -0.00269915 | 1.225 | 0.9875 | 0.0205907 |
| 12 | logical1-read | -50.096..75.3409 | 344.587 | 466.278 | -121.691 | 2.025 | 1.3125 | 1505.24 |
| 12 | logical0-read | -24.6149..22.7349 | 0.0760496 | 57.5138 | -57.4378 | 1.8625 | 1.1 | 568.198 |
| 12 | logical1-read0-control | -0.000888561..0.000827329 | -0.00526471 | 0.00269915 | -0.00796386 | 1.225 | 0.9875 | 0.0205907 |
| 12 | logical0-read0-control | -0.000827329..0.000888561 | 0.00526471 | 0.00796386 | -0.00269915 | 1.225 | 0.9875 | 0.0205907 |
| 15 | logical1-read | -51.2104..75.3409 | 430.803 | 568.366 | -137.563 | 2.025 | 1.3125 | 1518.62 |
| 15 | logical0-read | -24.0602..22.7349 | 0.0892129 | 57.3185 | -57.2293 | 1.8875 | 1.1 | 561.541 |
| 15 | logical1-read0-control | -0.000888561..0.000827329 | -0.00526471 | 0.00269915 | -0.00796386 | 1.225 | 0.9875 | 0.0205907 |
| 15 | logical0-read0-control | -0.000827329..0.000888561 | 0.00526471 | 0.00796386 | -0.00269915 | 1.225 | 0.9875 | 0.0205907 |
| 20 | logical1-read | -45.8848..78.1208 | 602.839 | 775.59 | -172.751 | 1.95 | 1.4625 | 1488.07 |
| 20 | logical0-read | -24.6616..22.7349 | -0.284472 | 57.1002 | -57.3847 | 1.8625 | 1.075 | 568.758 |
| 20 | logical1-read0-control | -0.000888561..0.000827329 | -0.00526471 | 0.00269915 | -0.00796386 | 1.225 | 0.9875 | 0.0205907 |
| 20 | logical0-read0-control | -0.000827329..0.000888561 | 0.00526471 | 0.00796386 | -0.00269915 | 1.225 | 0.9875 | 0.0205907 |

## Width-specific current-area decomposition

| width | case | leading signed | plateau signed | falling signed | total absolute |
|---:|---|---:|---:|---:|---:|
| 9 | logical1-read | 11.3344 | 254.412 | -8.27051 | 457.092 |
| 9 | logical0-read | 11.2645 | 10.6802 | -12.3064 | 113.203 |
| 12 | logical1-read | 11.3344 | 344.279 | -7.63002 | 587.969 |
| 12 | logical0-read | 11.2645 | 10.4923 | -12.2705 | 114.952 |
| 15 | logical1-read | 11.3344 | 422.469 | 4.81451 | 705.929 |
| 15 | logical0-read | 11.2645 | 9.86372 | -11.378 | 114.548 |
| 20 | logical1-read | 11.3344 | 595.583 | -15.8415 | 948.341 |
| 20 | logical0-read | 11.2645 | 10.0449 | -11.6363 | 114.485 |

## Storage/source guard summary

| width | case | JM1 pre→post Δturns | JM2 pre→post Δturns | JS1 post p2p (rad) | JS2 post p2p (rad) | I(L_SL) post p2p (µA) |
|---:|---|---:|---:|---:|---:|---:|
| 9 | logical1-read | 2.39528e-05 | 0.000333453 | 0.08524 | 0.00814 | 0.171473 |
| 9 | logical0-read | -4.53592e-06 | 5.31896e-05 | 0.0158968 | 0.0017455 | 0.0447554 |
| 9 | logical1-read0-control | 2.70563e-06 | -4.01389e-05 | 6.42e-05 | 7.6e-06 | 0.000182928 |
| 9 | logical0-read0-control | -2.70563e-06 | 4.01389e-05 | 6.42e-05 | 7.6e-06 | 0.000182928 |
| 12 | logical1-read | 1.60746e-05 | 0.00022522 | 0.07152 | 0.00732 | 0.198561 |
| 12 | logical0-read | -4.61549e-06 | 5.6874e-05 | 0.0184461 | 0.002446 | 0.0626417 |
| 12 | logical1-read0-control | 2.70563e-06 | -4.01389e-05 | 6.42e-05 | 7.6e-06 | 0.000182928 |
| 12 | logical0-read0-control | -2.70563e-06 | 4.01389e-05 | 6.42e-05 | 7.6e-06 | 0.000182928 |
| 15 | logical1-read | 9.23099e-06 | 7.68639e-05 | 0.04368 | 0.00934 | 0.24599 |
| 15 | logical0-read | -5.33169e-06 | 6.31447e-05 | 0.0206579 | 0.0025501 | 0.0675818 |
| 15 | logical1-read0-control | 2.70563e-06 | -4.01389e-05 | 6.42e-05 | 7.6e-06 | 0.000182928 |
| 15 | logical0-read0-control | -2.70563e-06 | 4.01389e-05 | 6.42e-05 | 7.6e-06 | 0.000182928 |
| 20 | logical1-read | 1.71887e-05 | -2.92049e-05 | 0.07841 | 0.02376 | 0.596089 |
| 20 | logical0-read | -1.43239e-06 | 5.32532e-05 | 0.0195649 | 0.0043027 | 0.121197 |
| 20 | logical1-read0-control | 2.70563e-06 | -4.01389e-05 | 6.42e-05 | 7.6e-06 | 0.000182928 |
| 20 | logical0-read0-control | -2.70563e-06 | 4.01389e-05 | 6.42e-05 | 7.6e-06 | 0.000182928 |

## Observed

- New JoSIM raw exists only for 12/15/20 ps read1/read0; 9 ps and READ=0 controls are explicitly reused accepted matched raw.
- No SFQ/event count is assigned in Phase A.

## Derived

- Width-specific leading/plateau/falling areas are obtained from the registered windows; they are source-waveform diagnostics, not universal thresholds.
- The registered rule selects W*=12 ps: read1 positive baseline-subtracted I(L_SL) area is about 466.3 µA·ps versus 357.7 µA·ps at 9 ps, while logical0 remains about 57.5 µA·ps versus 56.6 µA·ps and READ=0 controls remain near zero.
- The gain is primarily plateau-area gain; the diagnostic peak-duration metric does not increase materially. This is why the result is not described as a universal dwell requirement.

## Inference

- Phase A supports `DURATION_SUPPORTED` for this canonical BVM + 12 Ω external-load fixture; it does not identify whether the downstream QB dynamic window will close.

## Unknown

- This Phase-A report does not establish the response of the 12-JSL load or frozen scaled QB; those are gated Phase B/C questions.
