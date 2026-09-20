# U095_b012_b_rsl_10_closed review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.07803012950775 | 0.11281634479091769 | 2.0094884016189534 | -0.11128161367468246 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.07803012950775 | 0.11281634479091769 | 2.0094884016189534 | -0.11128161367468246 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.07803012950775 | 0.11281634479091769 | 2.0094884016189534 | -0.11128161367468246 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.07803012950775 | 0.11281634479091769 | 2.0094884016189534 | -0.11128161367468246 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.07803012950775 | 0.11281634479091769 | 2.0094884016189534 | -0.11128161367468246 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.07803012950775 | 0.11281634479091769 | 2.0094884016189534 | -0.11128161367468246 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.07803012950775 | 0.11281634479091769 | 2.0094884016189534 | -0.11128161367468246 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.1096753094378722 | 1.120196772162274 | -1.268168979656715 | 1.3057658335534272 | AMBIGUOUS |
| 0011 | BVM3 | -1.3129941576883375 | 1.322186406074519 | -1.827582848285361 | 1.827582848285361 | AMBIGUOUS |
| 0011 | BVM4 | -1.3129941576883375 | 1.322186406074519 | -1.827582848285361 | 1.827582848285361 | AMBIGUOUS |
| 1111 | BVM1 | -1.99091638849264 | 1.9980526892394546 | -2.0252660200009425 | 2.0414075143293227 | AMBIGUOUS |
| 1111 | BVM2 | -1.99091638849264 | 1.9980526892394546 | -2.0252660200009425 | 2.0414075143293227 | AMBIGUOUS |
| 1111 | BVM3 | -1.99091638849264 | 1.9980526892394546 | -2.0252660200009425 | 2.0414075143293227 | AMBIGUOUS |
| 1111 | BVM4 | -1.99091638849264 | 1.9980526892394546 | -2.0252660200009425 | 2.0414075143293227 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.171396e-05 | -9.127698e-07 | 0.07032081106063794 | 0.0703649524117858 | 1 |
| 0011 | 3.960831e-05 | -4.838003e-05 | 0.029009113023282112 | 0.11386855052098922 | 2 |
| 1111 | 9.66148e-05 | -6.285411e-06 | 0.1747247551777188 | 0.17530354615802768 | 4 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.0703649524117858, 0.11386855052098922, 0.17530354615802768]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [2.171396e-05, 3.960831e-05, 9.66148e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": false, "values": [0.07032081106063794, 0.029009113023282112, 0.1747247551777188]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
