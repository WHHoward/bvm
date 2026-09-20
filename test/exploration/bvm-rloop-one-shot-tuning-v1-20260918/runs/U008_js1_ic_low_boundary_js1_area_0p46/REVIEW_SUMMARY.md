# U008_js1_ic_low_boundary_js1_area_0p46 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.46, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=12
- Mode: passive
- Masks: 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 1111 | BVM1 | -1.078153781690841 | 0.11301592508955484 | 2.009671429803509 | -0.11104049393589818 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.078153781690841 | 0.11301592508955484 | 2.009671429803509 | -0.11104049393589818 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.078153781690841 | 0.11301592508955484 | 2.009671429803509 | -0.11104049393589818 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.078153781690841 | 0.11301592508955484 | 2.009671429803509 | -0.11104049393589818 | REVIEW_REQUIRED |

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
| 1111 | BVM1 | -1.085501663019002 | 1.0948072774711477 | -1.188933579829955 | 1.2447524014711444 | AMBIGUOUS |
| 1111 | BVM2 | -1.085501663019002 | 1.0948072774711477 | -1.188933579829955 | 1.2447524014711444 | AMBIGUOUS |
| 1111 | BVM3 | -1.085501663019002 | 1.0948072774711477 | -1.188933579829955 | 1.2447524014711444 | AMBIGUOUS |
| 1111 | BVM4 | -1.085501663019002 | 1.0948072774711477 | -1.188933579829955 | 1.2447524014711444 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 1111 | 0.000117683 | -2.831506e-07 | 0.368545955085846 | 0.3685596481879428 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.3685596481879428]}, "peak_positive_a": {"masks": ["1111"], "nondecreasing": true, "values": [0.000117683]}, "signed_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.368545955085846]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
