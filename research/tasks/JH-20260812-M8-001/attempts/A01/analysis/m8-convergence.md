# M8 bounded timestep-convergence (JH-20260812-M8-001) — A01 analysis

## Classification

**CONVERGED**

CONVERGED: all six runs passed QA, every registered scalar is computable and both adjacent pairs are within their preregistered task-local bands. INCONCLUSIVE: any valid required scalar is missing/ambiguous/outside its band at the maximum registered depth. This is a bounded numerical-convergence classification for this calibration fixture only; not a physical Gate, not a global tolerance freeze (M9 owns METRIC_SPEC_V2).

downstream_count remains NOT_APPLICABLE (M9 has not frozen a downstream event-counting semantic; this task must not invent one).

## Raw scalars by dt (control-corrected, turns unless noted)

| dt | junction | platform turns | voltage-area turns | residual turns | downstream platform turns |
|---|---|---|---|---|---|
| 0.1ps | B1 | 0.999988816843 | 1.00016095182 | -0.000194852965476 | 0.999619119115 |
| 0.1ps | B2 | 0.999889519862 | 0.998732497057 | 0.00136046420287 | 0.998723782054 |
| 0.05ps | B1 | 0.999959689632 | 0.999920843466 | 2.78201795934e-07 | 0.999709820668 |
| 0.05ps | B2 | 0.999833272861 | 1.00007252889 | -4.48754063687e-07 | 0.998718910587 |
| 0.025ps | B1 | 0.999946948483 | 0.999978107578 | -5.61869751836e-08 | 0.999722783759 |
| 0.025ps | B2 | 0.999823653324 | 0.999954707007 | 1.07762143986e-07 | 0.998733275222 |

| dt | activity peak time (ps) | activity FWHM (ps) |
|---|---|---|
| 0.1ps | 13.1 | 3.2 |
| 0.05ps | 13.15 | 3.2 |
| 0.025ps | 13.15 | 3.175 |

## Adjacent-refinement comparison

### 0.1ps->0.05ps — WITHIN_BAND

| observable | difference | band | within band |
|---|---|---|---|
| dut_platform_phase_turns | B1=2.91272e-05, B2=5.6247e-05 | 0.01 | True |
| dut_voltage_area_turns | B1=0.000240108, B2=0.00134003 | 0.01 | True |
| dut_phase_area_residual_turns | B1=0.000195131, B2=0.00136091 | 0.005 | True |
| activity_peak_time_ps | 0.05 | 0.25 | True |
| activity_fwhm_ps | 0 | 0.25 | True |
| downstream_platform_phase_turns | B1=9.07016e-05, B2=4.87147e-06 | 0.01 | True |

### 0.05ps->0.025ps — WITHIN_BAND

| observable | difference | band | within band |
|---|---|---|---|
| dut_platform_phase_turns | B1=1.27411e-05, B2=9.61954e-06 | 0.01 | True |
| dut_voltage_area_turns | B1=5.72641e-05, B2=0.000117822 | 0.01 | True |
| dut_phase_area_residual_turns | B1=3.34389e-07, B2=5.56516e-07 | 0.005 | True |
| activity_peak_time_ps | 0 | 0.25 | True |
| activity_fwhm_ps | 0.025 | 0.25 | True |
| downstream_platform_phase_turns | B1=1.29631e-05, B2=1.43646e-05 | 0.01 | True |

## Wording limits

- `activity_peak_time_ps` / `activity_fwhm_ps` are activity-timing proxies and
  waveform diagnostics for V(B1|XDUT) in the single-input run, not event or pulse counts.
- `downstream_platform_phase_turns` is a loaded-downstream platform diagnostic only.
- This is a bounded numerical-convergence classification for this calibration fixture
  and these registered observables; no physical Gate, no global tolerance freeze.
