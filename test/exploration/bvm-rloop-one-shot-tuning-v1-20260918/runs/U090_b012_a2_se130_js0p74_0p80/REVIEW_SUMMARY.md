# U090_b012_a2_se130_js0p74_0p80 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.740, JS2_AREA=0.800, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0774289900800007 | 0.12555765291508245 | 2.009546334018239 | -0.1124073165871716 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0774289900800007 | 0.12555765291508245 | 2.009546334018239 | -0.1124073165871716 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0774289900800007 | 0.12555765291508245 | 2.009546334018239 | -0.1124073165871716 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0774289900800007 | 0.12555765291508245 | 2.009546334018239 | -0.1124073165871716 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0774289900800007 | 0.12555765291508245 | 2.009546334018239 | -0.1124073165871716 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.750872282475811 | 1.7564122273124252 | -1.9664197689477532 | 2.015557266077945 | AMBIGUOUS |
| 1111 | BVM1 | -2.0816551415497133 | 2.0859394493782983 | -2.1131001476001057 | 2.1131001476001057 | AMBIGUOUS |
| 1111 | BVM2 | -2.0816551415497133 | 2.0859394493782983 | -2.1131001476001057 | 2.1131001476001057 | AMBIGUOUS |
| 1111 | BVM3 | -2.0816551415497133 | 2.0859394493782983 | -2.1131001476001057 | 2.1131001476001057 | AMBIGUOUS |
| 1111 | BVM4 | -2.0816551415497133 | 2.0859394493782983 | -2.1131001476001057 | 2.1131001476001057 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 4.268582e-05 | -3.314828e-07 | 0.1452906304104564 | 0.1453066608473467 | 1 |
| 1111 | 0.0001810932 | -3.314828e-07 | 0.6289868408034684 | 0.6290028712403587 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1453066608473467, 0.6290028712403587]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [4.268582e-05, 0.0001810932]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1452906304104564, 0.6289868408034684]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
