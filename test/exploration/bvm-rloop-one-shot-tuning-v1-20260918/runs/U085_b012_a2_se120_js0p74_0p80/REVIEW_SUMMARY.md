# U085_b012_a2_se120_js0p74_0p80 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.740, JS2_AREA=0.800, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0774289900800007 | 0.12081785955486274 | 2.0095649551465806 | -0.11241336447500895 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0774289900800007 | 0.12081785955486274 | 2.0095649551465806 | -0.11241336447500895 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0774289900800007 | 0.12081785955486274 | 2.0095649551465806 | -0.11241336447500895 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0774289900800007 | 0.12081785955486274 | 2.0095649551465806 | -0.11241336447500895 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0774289900800007 | 0.12081785955486274 | 2.0095649551465806 | -0.11241336447500895 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.4020306213050888 | 1.4086114235540295 | -1.9317209833252955 | 1.9517299427708088 | AMBIGUOUS |
| 1111 | BVM1 | -1.761855437774628 | 1.766943064262975 | -1.9130998549835438 | 2.0153441735246393 | AMBIGUOUS |
| 1111 | BVM2 | -1.761855437774628 | 1.766943064262975 | -1.9130998549835438 | 2.0153441735246393 | AMBIGUOUS |
| 1111 | BVM3 | -1.761855437774628 | 1.766943064262975 | -1.9130998549835438 | 2.0153441735246393 | AMBIGUOUS |
| 1111 | BVM4 | -1.761855437774628 | 1.766943064262975 | -1.9130998549835438 | 2.0153441735246393 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.833189e-05 | -3.316192e-07 | 0.12982816428875857 | 0.1298442013219235 | 1 |
| 1111 | 0.0001657908 | -3.316192e-07 | 0.5820638890808986 | 0.5820799261140635 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1298442013219235, 0.5820799261140635]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.833189e-05, 0.0001657908]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.12982816428875857, 0.5820638890808986]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
