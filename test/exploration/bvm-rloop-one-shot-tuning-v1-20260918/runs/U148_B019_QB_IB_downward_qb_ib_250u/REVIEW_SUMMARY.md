# U148_B019_QB_IB_downward_qb_ib_250u review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780270672071715 | 0.11288685043070737 | 2.009484422745376 | -0.11126076437713749 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780270672071715 | 0.11288685043070737 | 2.009484422745376 | -0.11126076437713749 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780270672071715 | 0.11288685043070737 | 2.009484422745376 | -0.11126076437713749 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780270672071715 | 0.11288685043070737 | 2.009484422745376 | -0.11126076437713749 | REVIEW_REQUIRED |

WRITE0 state: reported by windowed JM1/JM2 phase and LM1/LM2/LM3/LPM I/V metrics.
CONTROL retention: reported; no fixed percentage threshold applied.
WRITE1 transition: reported; no functional-family classifier applied.
PRE-READ state: reported for 101–110 ps.
POST-READ state: reported for recovery and tail windows.
TAIL state: reported for 150–200 ps.
Gate-S: REVIEW_REQUIRED

## R-LOOP

| mask | BVM | JS1 110→121 turns | JS1 p2p turns | JS2 110→121 turns | JS2 p2p turns | label |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | 0.0018931321325837836 | 0.0023221661126766094 | -0.0025063720438111654 | 0.0034958383250134786 | AMBIGUOUS |
| 0001 | BVM4 | -1.1454899144508528 | 1.1554511040290882 | -1.3709701813436888 | 1.3852190050888202 | AMBIGUOUS |
| 0011 | BVM3 | -1.4386420196251644 | 1.4474216906523685 | -1.941897636865489 | 1.944525284975936 | AMBIGUOUS |
| 0011 | BVM4 | -1.4386420196251644 | 1.4474216906523685 | -1.941897636865489 | 1.944525284975936 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.13577e-07 | -0.001602498212902838 | 0.001602498212902838 | 0 |
| 0001 | 2.0108e-05 | -8.13577e-07 | 0.0641302672350878 | 0.06416961164376873 | 1 |
| 0011 | 3.454433e-05 | -3.97845e-05 | 0.02463849972727611 | 0.09785912605875849 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.001602498212902838, 0.06416961164376873, 0.09785912605875849]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.0108e-05, 3.454433e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.001602498212902838, 0.0641302672350878, 0.02463849972727611]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
