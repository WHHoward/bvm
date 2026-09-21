# U135_QB_BJ1_screen_qb_bj1_area_0p70 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780218314682284 | 0.11735767193710178 | 2.0093168325903004 | -0.11119789817461616 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780218314682284 | 0.11735767193710178 | 2.0093168325903004 | -0.11119789817461616 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780218314682284 | 0.11735767193710178 | 2.0093168325903004 | -0.11119789817461616 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780218314682284 | 0.11735767193710178 | 2.0093168325903004 | -0.11119789817461616 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0018665691725817512 | 0.002273050897238452 | -0.0025420545820523696 | 0.003540815511931252 | AMBIGUOUS |
| 0001 | BVM4 | -1.212112253206592 | 1.2220045127789743 | -1.5944458121508112 | 1.5944458121508112 | AMBIGUOUS |
| 0011 | BVM3 | -1.563218880203443 | 1.5719211700973161 | -1.9485018985530416 | 1.985548394656542 | AMBIGUOUS |
| 0011 | BVM4 | -1.563218880203443 | 1.5719211700973161 | -1.9485018985530416 | 1.985548394656542 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.351203e-07 | -0.0017513097478806714 | 0.0017513097478806714 | 0 |
| 0001 | 1.512746e-05 | -5.979805e-05 | -0.00864508311955993 | 0.06108240133295248 | 2 |
| 0011 | 1.654757e-05 | -4.713715e-05 | -0.00905344831409297 | 0.07560071188321132 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0017513097478806714, 0.06108240133295248, 0.07560071188321132]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.512746e-05, 1.654757e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0017513097478806714, -0.00864508311955993, -0.00905344831409297]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
