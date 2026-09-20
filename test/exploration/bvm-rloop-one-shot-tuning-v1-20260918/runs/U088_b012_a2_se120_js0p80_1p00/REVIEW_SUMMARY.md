# U088_b012_a2_se120_js0p80_1p00 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.800, JS2_AREA=1.000, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.076858260454073 | 0.11654454933284528 | 2.0092848424467387 | -0.1128061588745598 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.076858260454073 | 0.11654454933284528 | 2.0092848424467387 | -0.1128061588745598 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.076858260454073 | 0.11654454933284528 | 2.0092848424467387 | -0.1128061588745598 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.076858260454073 | 0.11654454933284528 | 2.0092848424467387 | -0.1128061588745598 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.076858260454073 | 0.11654454933284528 | 2.0092848424467387 | -0.1128061588745598 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0725207152970238 | 1.1212650519712957 | -1.2868774999777184 | 1.3217341832192175 | AMBIGUOUS |
| 1111 | BVM1 | -1.204587964539508 | 1.210541616735195 | -1.7268382626885148 | 1.7268382626885148 | AMBIGUOUS |
| 1111 | BVM2 | -1.204587964539508 | 1.210541616735195 | -1.7268382626885148 | 1.7268382626885148 | AMBIGUOUS |
| 1111 | BVM3 | -1.204587964539508 | 1.210541616735195 | -1.7268382626885148 | 1.7268382626885148 | AMBIGUOUS |
| 1111 | BVM4 | -1.204587964539508 | 1.210541616735195 | -1.7268382626885148 | 1.7268382626885148 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.221056e-05 | -2.715985e-07 | 0.09524823924586422 | 0.09526137369089048 | 1 |
| 1111 | 0.0001367533 | -2.715985e-07 | 0.4663492139408096 | 0.4663623483858358 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09526137369089048, 0.4663623483858358]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.221056e-05, 0.0001367533]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09524823924586422, 0.4663492139408096]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
