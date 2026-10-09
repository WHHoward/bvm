# A023/A024 CB_DIRECT D1 evidence brief

Status: `MECHANICAL_QA_PASS_AWAITING_USER_REVIEW`

Scientific interpretation: `NOT PERFORMED`; SFQ/event count: `NOT_CLASSIFIED`.
No parameter changes, additional sJTL, or follow-up solve.

| Run | Raw bytes | Raw SHA-256 | Artifact / QA | Samples |
|---|---:|---|---|---:|
| A023_CB_DIRECT_D1_ALL_CLOCK | 94468129 | `c56ed579b684cdb1fe122488ce1de85e544e9797710ff7443e8dd1c6097b280a` | VALID / PASS | 29999 |
| A024_CB_DIRECT_D1_PAPER_CLOCK | 94583444 | `20cb27683ab2455df6e424dcc74ab09446902389c62fb310b3cc2f4146ee86ed` | VALID / PASS | 29999 |

## Matched pair records

| Pair | Native time grids exactly equal | Common signals | D1 timing descriptor |
|---|---:|---:|---|
| A021_vs_A023_D1 | True | 62 | `descriptive lobe-candidate navigation only; not event timing/count` |
| A022_vs_A024_D1 | True | 62 | `descriptive lobe-candidate navigation only; not event timing/count` |

Registered PRE_CLOCK stored-sample voltage maxima (peak times are descriptive extrema, **not** thresholded arrival or event times):

| Run | V(DOUT_D1) max time (ps) | V(CBU_OUT_D1) max time (ps) | V(T1_I_D1) max time (ps) | DOUT→CBU max-time difference (ps) |
|---|---:|---:|---:|---:|
| A021 baseline | 131.77 | 137.57 | 137.57 | 5.80 |
| A023 CB_DIRECT | 131.09 | 133.87 | 133.87 | 2.78 |
| A022 baseline | 123.68 | 125.07 | 125.07 | 1.39 |
| A024 CB_DIRECT | 131.97 | 134.92 | 134.92 | 2.95 |

## Selected mechanical arithmetic

All `signed area/Φ0` values below are signed voltage-time integrals divided by Φ0, **not event counts**. Phase turns are independently unwrapped `ΔP/(2π)` navigation values, not SFQ counts. Paired raw grids were identical, so these matched scalar differences use the same stored sample times; no interpolation was used.

| Matched pair | Signal / metric | Window | Baseline | CB_DIRECT D1 |
|---|---|---|---:|---:|
| A021 / A023 | `V(DOUT_D1)` signed area/Φ0 | PRE_CLOCK | 1.336679 | 1.222285 |
| A021 / A023 | `I(V_CBU_A_D1)` charge (C), DOUT→JOIN | PRE_CLOCK | 1.7309e-14 | 2.0997e-14 |
| A021 / A023 | `I(V_CBU_B_D1)` charge (C), C_D0→JOIN | PRE_CLOCK | -2.2783e-15 | -1.3407e-14 |
| A021 / A023 | `V(CBU_OUT_D1)` signed area/Φ0 | TOTAL | 1.161905 | 2.173122 |
| A021 / A023 | `V(C_D0)` signed area/Φ0 | TOTAL | 0.074636 | 2.125639 |
| A021 / A023 | `P(B_J11|XT1_D0)` phase turns (rad/2π) | TOTAL | 0.041620 | 2.076310 |
| A021 / A023 | `V(S_D1)` signed area/Φ0 | TOTAL | 1.051290 | 1.137816 |
| A021 / A023 | `V(C_D1)` signed area/Φ0 | TOTAL | 0.074494 | 0.083116 |
| A021 / A023 | `V(CBU_OUT_D2)` signed area/Φ0 | TOTAL | 2.161890 | 2.161998 |
| A022 / A024 | `V(DOUT_D1)` signed area/Φ0 | PRE_CLOCK | 0.338584 | 0.990912 |
| A022 / A024 | `I(V_CBU_A_D1)` charge (C), DOUT→JOIN | PRE_CLOCK | 1.6894e-14 | 6.7539e-15 |
| A022 / A024 | `I(V_CBU_B_D1)` charge (C), C_D0→JOIN | PRE_CLOCK | -2.2801e-15 | -5.4988e-15 |
| A022 / A024 | `V(CBU_OUT_D1)` signed area/Φ0 | TOTAL | 0.161905 | 1.180230 |
| A022 / A024 | `V(C_D0)` signed area/Φ0 | TOTAL | 0.074636 | 1.119849 |
| A022 / A024 | `P(B_J11|XT1_D0)` phase turns (rad/2π) | TOTAL | 0.041620 | 1.064490 |
| A022 / A024 | `V(S_D1)` signed area/Φ0 | TOTAL | 0.051290 | 1.052919 |
| A022 / A024 | `V(C_D1)` signed area/Φ0 | TOTAL | 0.074494 | 0.075339 |
| A022 / A024 | `V(CBU_OUT_D2)` signed area/Φ0 | TOTAL | 0.161902 | 0.161913 |

CB_DIRECT-only same-JJ TOTAL checks (turns are navigation; area is same-JJ `∫Vdt/Φ0` arithmetic):

| Run | JJ | Δphase/(2π) | Voltage area/Φ0 | Difference |
|---|---|---:|---:|---:|
| A023 | CB BJ1 | 2.115791 | 2.115790 | 6.80e-7 |
| A023 | CB BJ2 | -0.144065 | -0.144065 | -1.51e-7 |
| A024 | CB BJ1 | 1.113444 | 1.113444 | 1.44e-7 |
| A024 | CB BJ2 | -0.148156 | -0.148156 | -1.58e-7 |

Same-JJ D0 carry output check, TOTAL window (both columns are navigation/arithmetic, not counts):

| Pair | JJ | Baseline Δphase/(2π) | Baseline area/Φ0 | CB_DIRECT Δphase/(2π) | CB_DIRECT area/Φ0 | CB_DIRECT residual |
|---|---|---:|---:|---:|---:|---:|
| A021 / A023 | T1_D0 B_J11 | 0.0416203 | 0.0416203 | 2.0763096 | 2.0763098 | -2.15e-7 |
| A022 / A024 | T1_D0 B_J11 | 0.0416203 | 0.0416203 | 1.0644901 | 1.0644901 | 7.58e-9 |
| A021 / A023 | T1_D1 B_J11 | 0.0413951 | 0.0413951 | 0.0551336 | 0.0551336 | -1.22e-8 |
| A022 / A024 | T1_D1 B_J11 | 0.0413952 | 0.0413952 | 0.0427405 | 0.0427405 | 3.90e-9 |

These are registered arithmetic and raw observations only; no SFQ/event classification, functional verdict, or mechanism explanation is made.

Waveform/pulse candidates are descriptive navigation only. Cross-run pointwise subtraction was performed only when the complete stored grids were exactly identical; otherwise each case is reported on its native grid without interpolation. Same-JJ phase and voltage-area values are paired within the same raw, junction, direction, and window.

Detailed actual-grid metrics:
- All-run metrics: `analysis/cb-direct-d1-20261009/CB_DIRECT_D1_METRICS.csv`
- Paired common signals: `analysis/cb-direct-d1-20261009/PAIRED_COMPARISON.csv`
- D1 CB/direct focus: `analysis/cb-direct-d1-20261009/CB_DIRECT_D1_FOCUS.csv`
- Independent raw arithmetic recheck: `analysis/cb-direct-d1-20261009/NUMERICAL_RECHECK.json` (80 same-JJ/window checks; recomputed phase and voltage-area values exactly matched the stored mechanical metrics; raw SHA unchanged)
- Comparison JSON: `analysis/cb-direct-d1-20261009/CB_DIRECT_D1_COMPARISON.json`
- Local HTML pages: `plots/comparison/A021_vs_A023_D1.html`, `plots/comparison/A022_vs_A024_D1.html`

This artifact does not decide whether CB_DIRECT functionally succeeds or explain any observed difference.
