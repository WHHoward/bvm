# U107_LM3_LM1 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.54, JS2_AREA=0.9, RSH_JS1=25, RSH_JS2=10
- Mode: closed
- Masks: 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 1111 | BVM1 | -2.0677119867519558 | 1.9910415161088986 | 2.0674198972226363 | -0.1424420825178154 | REVIEW_REQUIRED |
| 1111 | BVM2 | -2.0677119867519558 | 1.9910415161088986 | 2.0674198972226363 | -0.1424420825178154 | REVIEW_REQUIRED |
| 1111 | BVM3 | -2.0677119867519558 | 1.9910415161088986 | 2.0674198972226363 | -0.1424420825178154 | REVIEW_REQUIRED |
| 1111 | BVM4 | -2.0677119867519558 | 1.9910415161088986 | 2.0674198972226363 | -0.1424420825178154 | REVIEW_REQUIRED |

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
| 1111 | BVM1 | -0.037146763717648364 | 0.08861325470757538 | -0.11499533511678878 | 0.18932721889337067 | AMBIGUOUS |
| 1111 | BVM2 | -0.037146763717648364 | 0.08861325470757538 | -0.11499533511678878 | 0.18932721889337067 | AMBIGUOUS |
| 1111 | BVM3 | -0.037146763717648364 | 0.08861325470757538 | -0.11499533511678878 | 0.18932721889337067 | AMBIGUOUS |
| 1111 | BVM4 | -0.037146763717648364 | 0.08861325470757538 | -0.11499533511678878 | 0.18932721889337067 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 1111 | 2.01813e-05 | -1.53912e-05 | 0.050218875651173764 | 0.05754153013554882 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.05754153013554882]}, "peak_positive_a": {"masks": ["1111"], "nondecreasing": true, "values": [2.01813e-05]}, "signed_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.050218875651173764]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
