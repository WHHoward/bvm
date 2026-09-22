# U147_B019_QB_IB_downward_qb_ib_240u review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.078027204504252 | 0.11312239974648336 | 2.009519277677913 | -0.11129784747887798 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.078027204504252 | 0.11312239974648336 | 2.009519277677913 | -0.11129784747887798 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.078027204504252 | 0.11312239974648336 | 2.009519277677913 | -0.11129784747887798 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.078027204504252 | 0.11312239974648336 | 2.009519277677913 | -0.11129784747887798 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0018905538225057004 | 0.0023061710408958736 | -0.002500005846087492 | 0.0035214304398626583 | AMBIGUOUS |
| 0001 | BVM4 | -1.1388926714962906 | 1.1488471288204334 | -1.3503742902990419 | 1.369233514435659 | AMBIGUOUS |
| 0011 | BVM3 | -1.3166714485639701 | 1.3254461062104672 | -1.8380081655086413 | 1.8380081655086413 | AMBIGUOUS |
| 0011 | BVM4 | -1.3166714485639701 | 1.3254461062104672 | -1.8380081655086413 | 1.8380081655086413 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.472548e-07 | -0.0016835504696700366 | 0.0016835504696700366 | 0 |
| 0001 | 2.110768e-05 | -8.472548e-07 | 0.07250693236065062 | 0.07254790542049387 | 1 |
| 0011 | 3.96867e-05 | -4.317933e-05 | 0.06855670554823048 | 0.09825810492294426 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0016835504696700366, 0.07254790542049387, 0.09825810492294426]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.110768e-05, 3.96867e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0016835504696700366, 0.07250693236065062, 0.06855670554823048]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
