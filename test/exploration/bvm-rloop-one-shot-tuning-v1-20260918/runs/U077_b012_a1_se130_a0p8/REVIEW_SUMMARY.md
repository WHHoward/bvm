# U077_b012_a1_se130_a0p8 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.800, JS2_AREA=0.800, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.077285591476275 | 0.1259717740770075 | 2.0095197551427426 | -0.1125515109656128 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.077285591476275 | 0.1259717740770075 | 2.0095197551427426 | -0.1125515109656128 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.077285591476275 | 0.1259717740770075 | 2.0095197551427426 | -0.1125515109656128 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.077285591476275 | 0.1259717740770075 | 2.0095197551427426 | -0.1125515109656128 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.077285591476275 | 0.1259717740770075 | 2.0095197551427426 | -0.1125515109656128 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.6414315344504007 | 1.6467784880030218 | -1.9442997146750922 | 2.0082338468645373 | AMBIGUOUS |
| 1111 | BVM1 | -2.0376636807719835 | 2.041791523376015 | -2.070850176125182 | 2.070850176125182 | AMBIGUOUS |
| 1111 | BVM2 | -2.0376636807719835 | 2.041791523376015 | -2.070850176125182 | 2.070850176125182 | AMBIGUOUS |
| 1111 | BVM3 | -2.0376636807719835 | 2.041791523376015 | -2.070850176125182 | 2.070850176125182 | AMBIGUOUS |
| 1111 | BVM4 | -2.0376636807719835 | 2.041791523376015 | -2.070850176125182 | 2.070850176125182 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 4.217188e-05 | -3.498007e-07 | 0.14292142458681714 | 0.1429383408734104 | 1 |
| 1111 | 0.000180809 | -3.498007e-07 | 0.6214115114750745 | 0.6214284277616678 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1429383408734104, 0.6214284277616678]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [4.217188e-05, 0.000180809]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.14292142458681714, 0.6214115114750745]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
