# U157_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 0001, 0011, 0111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0748250363097203 | 0.11048934036797109 | 2.0072764662198623 | -0.11120108127347803 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0748250363097203 | 0.11048934036797109 | 2.0072764662198623 | -0.11120108127347803 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0748250363097203 | 0.11048934036797109 | 2.0072764662198623 | -0.11120108127347803 | REVIEW_REQUIRED |
| 0111 | BVM2 | -1.0748250363097203 | 0.11048934036797109 | 2.0072764662198623 | -0.11120108127347803 | REVIEW_REQUIRED |
| 0111 | BVM3 | -1.0748250363097203 | 0.11048934036797109 | 2.0072764662198623 | -0.11120108127347803 | REVIEW_REQUIRED |
| 0111 | BVM4 | -1.0748250363097203 | 0.11048934036797109 | 2.0072764662198623 | -0.11120108127347803 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.400959380071459 | 2.4184422481757117 | -2.4955878799376983 | 2.496828699620526 | AMBIGUOUS |
| 0011 | BVM3 | -2.23563240828646 | 2.361877785626137 | -3.091413057291965 | 3.092539826542573 | AMBIGUOUS |
| 0011 | BVM4 | -2.23563240828646 | 2.361877785626137 | -3.091413057291965 | 3.092539826542573 | AMBIGUOUS |
| 0111 | BVM2 | -2.4693355267225994 | 2.470154888200625 | -3.0547310260081453 | 3.209097490242729 | AMBIGUOUS |
| 0111 | BVM3 | -2.4693355267225994 | 2.470154888200625 | -3.0547310260081453 | 3.209097490242729 | AMBIGUOUS |
| 0111 | BVM4 | -2.4693355267225994 | 2.470154888200625 | -3.0547310260081453 | 3.209097490242729 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.555414e-05 | -6.97467e-06 | 0.07765323383467508 | 0.08123438551529112 | 2 |
| 0011 | 6.691811e-05 | -3.905945e-05 | 0.07209742680447707 | 0.09917742791489488 | 7 |
| 0111 | 9.61726e-05 | -1.008489e-05 | 0.1683413504990657 | 0.17477416269665383 | 8 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.08123438551529112, 0.09917742791489488, 0.17477416269665383]}, "peak_positive_a": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [3.555414e-05, 6.691811e-05, 9.61726e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": false, "values": [0.07765323383467508, 0.07209742680447707, 0.1683413504990657]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
