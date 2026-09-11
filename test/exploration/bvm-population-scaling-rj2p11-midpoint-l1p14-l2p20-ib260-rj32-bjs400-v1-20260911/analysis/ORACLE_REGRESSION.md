# RJ2=11 midpoint generalized oracle regression

ORACLE_REGRESSION_PASS

Status: `PASS`. No solver was invoked and no raw file was modified.

The detector supports navigation response indices 1–4 using cumulative 0.5, 1.5, 2.5 and 3.5 turn thresholds from the common FINAL-origin baseline. Hamming weight is not passed to the detector. RJ2=12 references are used only to exercise the navigation code before RJ2=11 solves.

| reference mask | response candidates reported | terminal segmentation |
|:---:|---:|:---|
| 0001 | 1 | ONE_RESPONSE_CLUSTER |
| 0011 | 2 | 2_SEPARATED_PULSES |
| 0111 | 0 | 4_SEPARATED_PULSES |
| 1111 | 0 | 4_SEPARATED_PULSES |

Phase landmarks, voltage clusters and terminal pulse-local areas are supporting mechanical evidence; no response candidate is labeled an SFQ count.
