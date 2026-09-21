# U141_QB_RJ1_at_BJ1A075_qb_rj1_24 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780230899622267 | 0.11955782987040407 | 2.0092947100532106 | -0.11123243479726712 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780230899622267 | 0.11955782987040407 | 2.0092947100532106 | -0.11123243479726712 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780230899622267 | 0.11955782987040407 | 2.0092947100532106 | -0.11123243479726712 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780230899622267 | 0.11955782987040407 | 2.0092947100532106 | -0.11123243479726712 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0018978908653822268 | 0.002287247518162242 | -0.0024529596449095266 | 0.0034773286051318934 | AMBIGUOUS |
| 0001 | BVM4 | -1.17317326159028 | 1.1830815480654318 | -1.464685545639433 | 1.464685545639433 | AMBIGUOUS |
| 0011 | BVM3 | -1.5269855226196936 | 1.5357132454734725 | -1.9585987199737804 | 1.9809950035656718 | AMBIGUOUS |
| 0011 | BVM4 | -1.5269855226196936 | 1.5357132454734725 | -1.9585987199737804 | 1.9809950035656718 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -9.716465e-07 | -0.002045262557768132 | 0.002045262557768132 | 0 |
| 0001 | 1.787534e-05 | -1.975422e-05 | 0.031312680321306054 | 0.043074743653195004 | 2 |
| 0011 | 2.51632e-05 | -4.871087e-05 | -0.0019069016709508725 | 0.08397100751491324 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.002045262557768132, 0.043074743653195004, 0.08397100751491324]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.787534e-05, 2.51632e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.002045262557768132, 0.031312680321306054, -0.0019069016709508725]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
