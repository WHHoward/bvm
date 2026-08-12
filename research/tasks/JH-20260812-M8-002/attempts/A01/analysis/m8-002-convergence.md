# M8-002 (JH-20260812-M8-002) A01 — preserved-evidence reanalysis

## Classification

**CONVERGED**

CONVERGED: all six preserved runs pass QA, every preregistered scalar is computable and both adjacent pairs are within their preregistered task-local bands. Classification is bounded numerical convergence for this calibration fixture only; downstream_count remains NOT_APPLICABLE; not a physical Gate, not a global tolerance freeze (M9 owns METRIC_SPEC_V2).

## Raw scalars by dt (control-corrected)

| dt | sub | junction | platform turns | area turns | residual turns |
|---|---|---|---|---|---|
| 0.1ps | XDUT | B1 | 0.999988816843 | 1.00016095182 | -0.000194852965476 |
| 0.1ps | XDUT | B2 | 0.999889519862 | 0.998732497057 | 0.00136046420287 |
| 0.1ps | XLOAD | B1 | 0.999619119115 | 0.9999112647 | -6.61236019904e-05 |
| 0.1ps | XLOAD | B2 | 0.998723782054 | 0.999939267868 | -9.05845352542e-06 |
| 0.05ps | XDUT | B1 | 0.999959689632 | 0.999920843466 | 2.78201795873e-07 |
| 0.05ps | XDUT | B2 | 0.999833272861 | 1.00007252889 | -4.48754063537e-07 |
| 0.05ps | XLOAD | B1 | 0.999709820668 | 0.99979113408 | 9.60675310205e-07 |
| 0.05ps | XLOAD | B2 | 0.998718910587 | 1.00010327991 | -1.16724326213e-06 |
| 0.025ps | XDUT | B1 | 0.999946948483 | 0.999978107578 | -5.6186975109e-08 |
| 0.025ps | XDUT | B2 | 0.999823653324 | 0.999954707007 | 1.07762144021e-07 |
| 0.025ps | XLOAD | B1 | 0.999722783759 | 0.999949065058 | 4.21752572102e-09 |
| 0.025ps | XLOAD | B2 | 0.998733275222 | 0.999952584678 | -9.35709253691e-08 |

| dt | activity peak (ps) | activity FWHM (ps) |
|---|---|---|
| 0.1ps | 13.1 | 3.2 |
| 0.05ps | 13.15 | 3.2 |
| 0.025ps | 13.15 | 3.175 |

## Adjacent-refinement comparison

### 0.1ps->0.05ps — WITHIN_BAND
| observable | difference | band | within band |
|---|---|---|---|
| dut_platform_phase_turns | platform_XDUT_B1=2.91272e-05, platform_XDUT_B2=5.6247e-05 | 0.01 | True |
| dut_voltage_area_turns | area_XDUT_B1=0.000240108, area_XDUT_B2=0.00134003 | 0.01 | True |
| dut_phase_area_residual_turns | residual_XDUT_B1=0.000195131, residual_XDUT_B2=0.00136091 | 0.005 | True |
| downstream_platform_phase_turns | platform_XLOAD_B1=9.07016e-05, platform_XLOAD_B2=4.87147e-06 | 0.01 | True |
| activity_peak_time_ps | activity_peak_time_ps=0.05 | 0.25 | True |
| activity_fwhm_ps | activity_fwhm_ps=0 | 0.25 | True |

### 0.05ps->0.025ps — WITHIN_BAND
| observable | difference | band | within band |
|---|---|---|---|
| dut_platform_phase_turns | platform_XDUT_B1=1.27411e-05, platform_XDUT_B2=9.61954e-06 | 0.01 | True |
| dut_voltage_area_turns | area_XDUT_B1=5.72641e-05, area_XDUT_B2=0.000117822 | 0.01 | True |
| dut_phase_area_residual_turns | residual_XDUT_B1=3.34389e-07, residual_XDUT_B2=5.56516e-07 | 0.005 | True |
| downstream_platform_phase_turns | platform_XLOAD_B1=1.29631e-05, platform_XLOAD_B2=1.43646e-05 | 0.01 | True |
| activity_peak_time_ps | activity_peak_time_ps=0 | 0.25 | True |
| activity_fwhm_ps | activity_fwhm_ps=0.025 | 0.25 | True |

## Wording limits

- activity_peak_time_ps / activity_fwhm_ps are activity-timing proxies and waveform
  diagnostics for V(B1|XDUT) in the single-input run, not event/pulse counts.
- downstream_platform_phase_turns is a loaded-downstream platform diagnostic only.
- Bounded numerical-convergence classification for this calibration fixture only;
  no physical Gate, no global tolerance freeze.
