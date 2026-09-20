# U066_b012_a1_se100_a0p9 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.900, JS2_AREA=0.900, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0768000097449015 | 0.11333455328562482 | 2.0093555072414717 | -0.11289242085371565 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0768000097449015 | 0.11333455328562482 | 2.0093555072414717 | -0.11289242085371565 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0768000097449015 | 0.11333455328562482 | 2.0093555072414717 | -0.11289242085371565 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0768000097449015 | 0.11333455328562482 | 2.0093555072414717 | -0.11289242085371565 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0768000097449015 | 0.11333455328562482 | 2.0093555072414717 | -0.11289242085371565 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -0.10439585463928319 | 0.11361251739373485 | -0.3699158287348548 | 0.38853090918876904 | AMBIGUOUS |
| 1111 | BVM1 | -0.07561035951894478 | 0.08302729817691328 | -0.24608437033254707 | 0.30499525420812595 | AMBIGUOUS |
| 1111 | BVM2 | -0.07561035951894478 | 0.08302729817691328 | -0.24608437033254707 | 0.30499525420812595 | AMBIGUOUS |
| 1111 | BVM3 | -0.07561035951894478 | 0.08302729817691328 | -0.24608437033254707 | 0.30499525420812595 | AMBIGUOUS |
| 1111 | BVM4 | -0.07561035951894478 | 0.08302729817691328 | -0.24608437033254707 | 0.30499525420812595 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 1.258139e-05 | -5.570668e-06 | 0.02925733483834534 | 0.029989852462749683 | 4 |
| 1111 | 5.695584e-05 | -4.439672e-05 | 0.09810527867904434 | 0.11354755243371925 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.029989852462749683, 0.11354755243371925]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [1.258139e-05, 5.695584e-05]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.02925733483834534, 0.09810527867904434]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
