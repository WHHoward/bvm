# U110_LM3_LM1 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.8, JS2_AREA=0.9, RSH_JS1=12, RSH_JS2=10
- Mode: closed
- Masks: 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 1111 | BVM1 | -2.058251659849918 | 1.001523223071183 | 2.0829212191220092 | -0.15043102404125613 | REVIEW_REQUIRED |
| 1111 | BVM2 | -2.058251659849918 | 1.001523223071183 | 2.0829212191220092 | -0.15043102404125613 | REVIEW_REQUIRED |
| 1111 | BVM3 | -2.058251659849918 | 1.001523223071183 | 2.0829212191220092 | -0.15043102404125613 | REVIEW_REQUIRED |
| 1111 | BVM4 | -2.058251659849918 | 1.001523223071183 | 2.0829212191220092 | -0.15043102404125613 | REVIEW_REQUIRED |

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
| 1111 | BVM1 | -0.29589310343522895 | 0.3652038079122046 | -0.9650950280061001 | 1.0675612403688544 | AMBIGUOUS |
| 1111 | BVM2 | -0.29589310343522895 | 0.3652038079122046 | -0.9650950280061001 | 1.0675612403688544 | AMBIGUOUS |
| 1111 | BVM3 | -0.29589310343522895 | 0.3652038079122046 | -0.9650950280061001 | 1.0675612403688544 | AMBIGUOUS |
| 1111 | BVM4 | -0.29589310343522895 | 0.3652038079122046 | -0.9650950280061001 | 1.0675612403688544 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 1111 | 4.353907e-05 | -4.473837e-05 | 0.04274444078545734 | 0.1345925366001647 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.1345925366001647]}, "peak_positive_a": {"masks": ["1111"], "nondecreasing": true, "values": [4.353907e-05]}, "signed_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.04274444078545734]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
