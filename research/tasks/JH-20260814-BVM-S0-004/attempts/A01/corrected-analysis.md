# Corrected analysis: `bvm-s0-canonical-20260814-01`
> Correction note: the predecessor `test/final/bvm/runs/bvm-s0-canonical-20260814-01/analysis.md` (S0-001 A01 D5) is retained as immutable evidence but is **superseded for human-readable numeric tables** by this report; its "Observed" tables contained values not present in any case x timestep of `analysis.json`/raw. This corrected report is deterministically rendered by `regenerate_s0_report.py` from the twelve frozen CSVs and byte-for-byte re-render checked.
## Reconstruction consistency
- reconstruction matches frozen analysis.json: True
- numerical_status: `INCONCLUSIVE` (frozen rule; 0.1->0.05 ps control-latency 0.85 ps > 0.5-ps band)
- evidence_quality: `INCONCLUSIVE`

## Direct-JJ phase-area `[94,108) ps` (reconstructed from raw, actual time)

| case | step | JJ | phase_delta_rad | phase_delta_turns | area_turns | residual_turns |
|---|---|---|---|---|---|---|
| init_positive_read | 0.1ps | JM1 | 0.068792 | 0.010949 | 0.011125 | -0.000176 |
| init_positive_read | 0.1ps | JM2 | 0.401532 | 0.063906 | 0.064783 | -0.000877 |
| init_positive_read | 0.05ps | JM1 | 0.107697 | 0.017141 | 0.017215 | -0.000075 |
| init_positive_read | 0.05ps | JM2 | 0.192666 | 0.030664 | 0.030777 | -0.000113 |
| init_positive_read | 0.025ps | JM1 | 0.117587 | 0.018715 | 0.018735 | -0.000021 |
| init_positive_read | 0.025ps | JM2 | 0.099908 | 0.015901 | 0.015914 | -0.000013 |
| init_positive_control | 0.1ps | JM1 | -0.000080 | -0.000013 | -0.000013 | 0.000000 |
| init_positive_control | 0.1ps | JM2 | -0.001946 | -0.000310 | -0.000313 | 0.000004 |
| init_positive_control | 0.05ps | JM1 | -0.000125 | -0.000020 | -0.000020 | 0.000000 |
| init_positive_control | 0.05ps | JM2 | 0.001153 | 0.000183 | 0.000184 | -0.000000 |
| init_positive_control | 0.025ps | JM1 | -0.000090 | -0.000014 | -0.000014 | 0.000000 |
| init_positive_control | 0.025ps | JM2 | 0.001631 | 0.000260 | 0.000260 | -0.000000 |
| init_negative_read | 0.1ps | JM1 | -0.098687 | -0.015707 | -0.015826 | 0.000119 |
| init_negative_read | 0.1ps | JM2 | -0.041179 | -0.006554 | -0.006618 | 0.000065 |
| init_negative_read | 0.05ps | JM1 | -0.086939 | -0.013837 | -0.013852 | 0.000016 |
| init_negative_read | 0.05ps | JM2 | -0.022169 | -0.003528 | -0.003534 | 0.000006 |
| init_negative_read | 0.025ps | JM1 | -0.081733 | -0.013008 | -0.013010 | 0.000002 |
| init_negative_read | 0.025ps | JM2 | -0.012308 | -0.001959 | -0.001959 | 0.000000 |
| init_negative_control | 0.1ps | JM1 | 0.000080 | 0.000013 | 0.000013 | -0.000000 |
| init_negative_control | 0.1ps | JM2 | 0.001946 | 0.000310 | 0.000313 | -0.000004 |
| init_negative_control | 0.05ps | JM1 | 0.000125 | 0.000020 | 0.000020 | -0.000000 |
| init_negative_control | 0.05ps | JM2 | -0.001153 | -0.000183 | -0.000184 | 0.000000 |
| init_negative_control | 0.025ps | JM1 | 0.000090 | 0.000014 | 0.000014 | -0.000000 |
| init_negative_control | 0.025ps | JM2 | -0.001631 | -0.000260 | -0.000260 | 0.000000 |

## Pre/post storage signature (JM1/JM2 P means, rad)

| case | step | pre JM1 | post JM1 | pre JM2 | post JM2 |
|---|---|---|---|---|---|
| init_positive_read | 0.1ps | 5.911066 | 5.910628 | 0.316806 | 0.312313 |
| init_positive_read | 0.05ps | 5.911065 | 5.910355 | 0.317027 | 0.320423 |
| init_positive_read | 0.025ps | 5.911068 | 5.910362 | 0.317063 | 0.323739 |
| init_positive_control | 0.1ps | 5.911066 | 5.911077 | 0.316806 | 0.316918 |
| init_positive_control | 0.05ps | 5.911065 | 5.911076 | 0.317027 | 0.316914 |
| init_positive_control | 0.025ps | 5.911068 | 5.911075 | 0.317063 | 0.316920 |
| init_negative_read | 0.1ps | -5.911066 | -5.910976 | -0.316806 | -0.317754 |
| init_negative_read | 0.05ps | -5.911065 | -5.911038 | -0.317027 | -0.319424 |
| init_negative_read | 0.025ps | -5.911068 | -5.911076 | -0.317063 | -0.319623 |
| init_negative_control | 0.1ps | -5.911066 | -5.911077 | -0.316806 | -0.316918 |
| init_negative_control | 0.05ps | -5.911065 | -5.911076 | -0.317027 | -0.316914 |
| init_negative_control | 0.025ps | -5.911068 | -5.911075 | -0.317063 | -0.316920 |

## Source-port waveform `[94,130) ps` (reconstructed)

| case | step | key | abs_peak | latency_from_96ps_s |
|---|---|---|---|---|
| init_positive_read | 0.1ps | V_SL1 | 8.901184e-04 | 5.000000e-12 |
| init_positive_read | 0.1ps | I_LSL | 7.417653e-05 | 5.000000e-12 |
| init_positive_read | 0.05ps | V_SL1 | 9.006698e-04 | 5.000000e-12 |
| init_positive_read | 0.05ps | I_LSL | 7.505582e-05 | 5.000000e-12 |
| init_positive_read | 0.025ps | V_SL1 | 9.036045e-04 | 5.025000e-12 |
| init_positive_read | 0.025ps | I_LSL | 7.530036e-05 | 5.025000e-12 |
| init_positive_control | 0.1ps | V_SL1 | 1.792371e-08 | -7.000000e-13 |
| init_positive_control | 0.1ps | I_LSL | 1.493642e-09 | -7.000000e-13 |
| init_positive_control | 0.05ps | V_SL1 | 1.547836e-08 | 1.500000e-13 |
| init_positive_control | 0.05ps | I_LSL | 1.289863e-09 | 1.500000e-13 |
| init_positive_control | 0.025ps | V_SL1 | 1.670116e-08 | 0.000000e+00 |
| init_positive_control | 0.025ps | I_LSL | 1.391764e-09 | 0.000000e+00 |
| init_negative_read | 0.1ps | V_SL1 | 3.068146e-04 | 1.000000e-11 |
| init_negative_read | 0.1ps | I_LSL | 2.556787e-05 | 1.000000e-11 |
| init_negative_read | 0.05ps | V_SL1 | 3.151862e-04 | 1.000000e-11 |
| init_negative_read | 0.05ps | I_LSL | 2.626552e-05 | 1.000000e-11 |
| init_negative_read | 0.025ps | V_SL1 | 3.166624e-04 | 1.000000e-11 |
| init_negative_read | 0.025ps | I_LSL | 2.638852e-05 | 1.000000e-11 |
| init_negative_control | 0.1ps | V_SL1 | 1.792371e-08 | -7.000000e-13 |
| init_negative_control | 0.1ps | I_LSL | 1.493642e-09 | -7.000000e-13 |
| init_negative_control | 0.05ps | V_SL1 | 1.547836e-08 | 1.500000e-13 |
| init_negative_control | 0.05ps | I_LSL | 1.289863e-09 | 1.500000e-13 |
| init_negative_control | 0.025ps | V_SL1 | 1.670116e-08 | 0.000000e+00 |
| init_negative_control | 0.025ps | I_LSL | 1.391764e-09 | 0.000000e+00 |

## Controls
- init_positive_control / init_negative_control: identical netlist/model/load/timestep/stop/PWL knots; only the two read-pulse amplitudes are zero.

## Provenance
- Raw root (frozen): `test/final/bvm/runs/bvm-s0-canonical-20260814-01/raw/`
- Frozen analysis.json: `test/final/bvm/runs/bvm-s0-canonical-20260814-01/analysis.json`
- Generator: `research/tasks/JH-20260814-BVM-S0-004/attempts/A01/regenerate_s0_report.py`
- Source-evidence manifest: `research/tasks/JH-20260814-BVM-S0-004/attempts/A01/source-evidence-manifest.sha256`
- This report is deterministic output of the generator; no manual edits.
