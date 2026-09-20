# U084_b012_a2_se110_js0p90_1p00 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.900, JS2_AREA=1.000, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0765701900070768 | 0.11443192661824346 | 2.00920510582025 | -0.1129877546646276 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0765701900070768 | 0.11443192661824346 | 2.00920510582025 | -0.1129877546646276 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0765701900070768 | 0.11443192661824346 | 2.00920510582025 | -0.1129877546646276 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0765701900070768 | 0.11443192661824346 | 2.00920510582025 | -0.1129877546646276 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0765701900070768 | 0.11443192661824346 | 2.00920510582025 | -0.1129877546646276 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -0.10486338820010996 | 0.11322010496604748 | -0.3702344250999362 | 0.38708145329104265 | AMBIGUOUS |
| 1111 | BVM1 | -0.07482927480473268 | 0.08428336490328883 | -0.23970890979118334 | 0.299611806427054 | AMBIGUOUS |
| 1111 | BVM2 | -0.07482927480473268 | 0.08428336490328883 | -0.23970890979118334 | 0.299611806427054 | AMBIGUOUS |
| 1111 | BVM3 | -0.07482927480473268 | 0.08428336490328883 | -0.23970890979118334 | 0.299611806427054 | AMBIGUOUS |
| 1111 | BVM4 | -0.07482927480473268 | 0.08428336490328883 | -0.23970890979118334 | 0.299611806427054 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 1.298477e-05 | -5.562851e-06 | 0.029485907288427416 | 0.030259090782616856 | 4 |
| 1111 | 5.935672e-05 | -4.655653e-05 | 0.09841446199211294 | 0.11559495894275515 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.030259090782616856, 0.11559495894275515]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [1.298477e-05, 5.935672e-05]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.029485907288427416, 0.09841446199211294]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
