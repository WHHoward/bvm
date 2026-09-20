# U046_b010_g6_rs_3p5 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0780635408381078 | 0.11362517021171067 | 2.009745755161933 | -0.11148947003036042 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0780635408381078 | 0.11362517021171067 | 2.009745755161933 | -0.11148947003036042 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0780635408381078 | 0.11362517021171067 | 2.009745755161933 | -0.11148947003036042 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0780635408381078 | 0.11362517021171067 | 2.009745755161933 | -0.11148947003036042 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0780635408381078 | 0.11362517021171067 | 2.009745755161933 | -0.11148947003036042 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.1258692134890125 | 1.135913800257428 | -1.313495750406986 | 1.3401142554841625 | AMBIGUOUS |
| 1111 | BVM1 | -1.1506864029202748 | 1.1586148496498463 | -1.3761311782608014 | 1.3963311236380247 | AMBIGUOUS |
| 1111 | BVM2 | -1.1506864029202748 | 1.1586148496498463 | -1.3761311782608014 | 1.3963311236380247 | AMBIGUOUS |
| 1111 | BVM3 | -1.1506864029202748 | 1.1586148496498463 | -1.3761311782608014 | 1.3963311236380247 | AMBIGUOUS |
| 1111 | BVM4 | -1.1506864029202748 | 1.1586148496498463 | -1.3761311782608014 | 1.3963311236380247 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.010129e-05 | -2.888422e-07 | 0.09931110400316845 | 0.09932507234981677 | 1 |
| 1111 | 0.0001273065 | -2.888422e-07 | 0.4268642391620239 | 0.4268782075086722 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09932507234981677, 0.4268782075086722]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.010129e-05, 0.0001273065]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09931110400316845, 0.4268642391620239]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
