# BVM-S1 canonical source convergence — corrected analysis (A02)

> Generated deterministically by `gen_analysis_corrected.py` from the sealed A01 raw CSVs (read-only).  Corrects the A01 report layer per Codex REWORK instruction; data and verdict unchanged: **artifact VALID, numerical INCONCLUSIVE**.  A01 analysis.json/analysis.md/raw untouched.

## 1. Artifact validity

Same as A01 (verified in analysis.json and by Copilot independent recomputation): 12/12 CSVs exact registered header, no NaN/Inf, strictly increasing time, no duplicates.  Last samples are 169.95 / 169.975 / 169.9875 ps (JoSIM discrete output convention); every registered window (all ending at 150 ps) is fully covered.  Exact-decimal timestamp matching in source [94,130) ps: 0 missing tokens, both adjacent pairs, all four cases.

## 2. Readiness (timestep comparability only)

| step | JM1 p2p max (rad) | JM2 p2p max (rad) | L∞ sep (rad) | band |
|---|---:|---:|---:|---|
| 0.05ps | 0.00037 | 0.00581 | 11.8221 | PASS (p2p ≤ 0.020, sep ≥ 0.100) |
| 0.025ps | 0.00036 | 0.00555 | 11.8221 | PASS (p2p ≤ 0.020, sep ≥ 0.100) |
| 0.0125ps | 0.00035 | 0.00548 | 11.8221 | PASS (p2p ≤ 0.020, sep ≥ 0.100) |

## 3. Control observables (registered, 1%/0.2% bands vs paired-read scale)

### 0.05ps

| case:col | rctrl | ctrl max (band) | ctrl RMS (band) | ctrl L1/time (0.002) | pair max (band) | pair RMS (band) | pass |
|---|---:|---:|---:|---:|---:|---:|---|
| posit:V | 1.32e-05 | 0.012 (9.036 µV) | 0.004 (1.807) | 3.93e-06 | 0.003 (9.036) | 0.001 (1.807) | PASS |
| posit:I | 1.32e-05 | 0.001 (0.753 µA) | 0.000 (0.151) | 3.93e-06 | 0.000 (0.753) | 0.000 (0.151) | PASS |
| negat:V | 3.77e-05 | 0.012 (3.167 µV) | 0.004 (0.633) | 1.12e-05 | 0.003 (3.167) | 0.001 (0.633) | PASS |
| negat:I | 3.77e-05 | 0.001 (0.264 µA) | 0.000 (0.053) | 1.12e-05 | 0.000 (0.264) | 0.000 (0.053) | PASS |

### 0.025ps

| case:col | rctrl | ctrl max (band) | ctrl RMS (band) | ctrl L1/time (0.002) | pair max (band) | pair RMS (band) | pass |
|---|---:|---:|---:|---:|---:|---:|---|
| posit:V | 1.30e-05 | 0.012 (9.041 µV) | 0.004 (1.808) | 3.82e-06 | 0.003 (9.036) | 0.001 (1.807) | PASS |
| posit:I | 1.30e-05 | 0.001 (0.753 µA) | 0.000 (0.151) | 3.82e-06 | 0.000 (0.753) | 0.000 (0.151) | PASS |
| negat:V | 3.72e-05 | 0.012 (3.169 µV) | 0.004 (0.634) | 1.09e-05 | 0.003 (3.167) | 0.001 (0.633) | PASS |
| negat:I | 3.72e-05 | 0.001 (0.264 µA) | 0.000 (0.053) | 1.09e-05 | 0.000 (0.264) | 0.000 (0.053) | PASS |

### 0.0125ps

| case:col | rctrl | ctrl max (band) | ctrl RMS (band) | ctrl L1/time (0.002) | pair max (band) | pair RMS (band) | pass |
|---|---:|---:|---:|---:|---:|---:|---|
| posit:V | 1.29e-05 | 0.012 (9.041 µV) | 0.004 (1.808) | 3.78e-06 | 0.001 (9.041) | 0.000 (1.808) | PASS |
| posit:I | 1.29e-05 | 0.001 (0.753 µA) | 0.000 (0.151) | 3.78e-06 | 0.000 (0.753) | 0.000 (0.151) | PASS |
| negat:V | 3.69e-05 | 0.012 (3.169 µV) | 0.004 (0.634) | 1.08e-05 | 0.001 (3.169) | 0.000 (0.634) | PASS |
| negat:I | 3.69e-05 | 0.001 (0.264 µA) | 0.000 (0.053) | 1.08e-05 | 0.000 (0.264) | 0.000 (0.053) | PASS |

All controls sit at ~1e-5 of paired-read scale (V residual ≈ 12 nV, I ≈ 1 nA): every registered control band passes; latency/FWHM remain NOT_APPLICABLE per the rctrl ≤ 0.01 hierarchy.  Control-corrected source waveforms (read − control, exact common timestamps) and control-corrected activity-window endpoint deltas are in `analysis-corrected.json` (`control_corrected`).

## 4. Read observables (baseline-subtracted, source window)

| case | step | V peak | V latency | V FWHM | I peak | I latency | I FWHM |
|---|---|---:|---:|---:|---:|---:|---:|
| init_positive_read | 0.05ps | +0.9007 mV | 5.00 ps | 6.668 ps | +75.06 µA | 5.00 ps | 6.668 ps |
| init_positive_read | 0.025ps | +0.9036 mV | 5.02 ps | 6.653 ps | +75.30 µA | 5.02 ps | 6.653 ps |
| init_positive_read | 0.0125ps | +0.9041 mV | 5.01 ps | 6.650 ps | +75.34 µA | 5.01 ps | 6.650 ps |
| init_negative_read | 0.05ps | -0.3152 mV | 10.00 ps | 1.073 ps | -26.27 µA | 10.00 ps | 1.073 ps |
| init_negative_read | 0.025ps | -0.3167 mV | 10.00 ps | 1.067 ps | -26.39 µA | 10.00 ps | 1.067 ps |
| init_negative_read | 0.0125ps | -0.3169 mV | 10.00 ps | 1.066 ps | -26.41 µA | 10.00 ps | 1.066 ps |

Negative-read FWHM (two half-height crossings, standard two-sided filter): ≈1.07 ps at all steps; reported for completeness and NOT_APPLICABLE for the ladder (control hierarchy PASS region).

## 5. Adjacent-pair comparisons (exact common timestamps; bands are floor-limited: max(Afloor, 1%·Aref) / max(0.2%·Aref, 0.2·Afloor))

### 05_to_025

| case:col | pw_max (band) | RMS (band) | latency Δ (≤0.25) | FWHM Δ (≤0.25) | verdict |
|---|---:|---:|---:|---:|---|
| init_positive_read:V_SL1 | 24.45 (9.04 µV) | 8.00 (1.81) | 0.025 ✓ | 0.014673617875184064 ✓ | FAIL |
| init_positive_read:I_LSL | 2.04 (0.75 µA) | 0.67 (0.15) | 0.025 ✓ | 0.014673422701789285 ✓ | FAIL |
| init_negative_read:V_SL1 | 5.94 (5.00 µV) | 1.94 (1.00) | 0.000 ✓ | 0.005840067495583634 ✓ | FAIL |
| init_negative_read:I_LSL | 0.50 (0.50 µA) | 0.16 (0.10) | 0.000 ✓ | 0.005839866371464497 ✓ | FAIL |

### 025_to_0125

| case:col | pw_max (band) | RMS (band) | latency Δ (≤0.25) | FWHM Δ (≤0.25) | verdict |
|---|---:|---:|---:|---:|---|
| init_positive_read:V_SL1 | 6.25 (9.04 µV) | 2.00 (1.81) | 0.012 ✓ | 0.003277950693539644 ✓ | FAIL |
| init_positive_read:I_LSL | 0.52 (0.75 µA) | 0.17 (0.15) | 0.012 ✓ | 0.0032780206064568773 ✓ | FAIL |
| init_negative_read:V_SL1 | 1.54 (5.00 µV) | 0.50 (1.00) | 0.000 ✓ | 0.0012996556354318844 ✓ | PASS |
| init_negative_read:I_LSL | 0.13 (0.50 µA) | 0.04 (0.10) | 0.000 ✓ | 0.0012997700120214173 ✓ | PASS |

## 6. Verdict

**Artifact: VALID.  Numerical: INCONCLUSIVE.**

Failing required comparisons at the fixed 0.0125 ps depth:
- band 05_to_025 init_positive_read:V_SL1
- band 05_to_025 init_positive_read:I_LSL
- band 05_to_025 init_negative_read:V_SL1
- band 05_to_025 init_negative_read:I_LSL
- band 025_to_0125 init_positive_read:V_SL1
- band 025_to_0125 init_positive_read:I_LSL

Bounded per-timestep observations are unchanged from A01 (peaks, latency, FWHM, control bands, platforms/deltas/areas in the JSON).  No logical/state/SFQ/event/fluxoid/Gate claim; nothing changes BVM-S0 or C02.
