# U089_b012_a2_se120_js0p90_1p00 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.900, JS2_AREA=1.000, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0765701900070768 | 0.11713915220023659 | 2.009194919903892 | -0.11298298001633487 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0765701900070768 | 0.11713915220023659 | 2.009194919903892 | -0.11298298001633487 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0765701900070768 | 0.11713915220023659 | 2.009194919903892 | -0.11298298001633487 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0765701900070768 | 0.11713915220023659 | 2.009194919903892 | -0.11298298001633487 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0765701900070768 | 0.11713915220023659 | 2.009194919903892 | -0.11298298001633487 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0558668852913367 | 1.1353043164028578 | -1.2730008282360192 | 1.299061813547545 | AMBIGUOUS |
| 1111 | BVM1 | -1.178730999949532 | 1.1843549945115928 | -1.6753811300092418 | 1.6753811300092418 | AMBIGUOUS |
| 1111 | BVM2 | -1.178730999949532 | 1.1843549945115928 | -1.6753811300092418 | 1.6753811300092418 | AMBIGUOUS |
| 1111 | BVM3 | -1.178730999949532 | 1.1843549945115928 | -1.6753811300092418 | 1.6753811300092418 | AMBIGUOUS |
| 1111 | BVM4 | -1.178730999949532 | 1.1843549945115928 | -1.6753811300092418 | 1.6753811300092418 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.174737e-05 | -2.999197e-07 | 0.09283522152936535 | 0.09284972558153039 | 1 |
| 1111 | 0.0001352311 | -2.999197e-07 | 0.45673084055010565 | 0.4567453446022707 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09284972558153039, 0.4567453446022707]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.174737e-05, 0.0001352311]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09283522152936535, 0.45673084055010565]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
