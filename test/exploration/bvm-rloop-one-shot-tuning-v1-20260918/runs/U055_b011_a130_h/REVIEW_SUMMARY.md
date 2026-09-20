# U055_b011_a130_h review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.598, JS2_AREA=0.851, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.077729474612558 | 0.12189836246351354 | 2.0095893058528738 | -0.1120495362751009 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.077729474612558 | 0.12189836246351354 | 2.0095893058528738 | -0.1120495362751009 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.077729474612558 | 0.12189836246351354 | 2.0095893058528738 | -0.1120495362751009 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.077729474612558 | 0.12189836246351354 | 2.0095893058528738 | -0.1120495362751009 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.077729474612558 | 0.12189836246351354 | 2.0095893058528738 | -0.1120495362751009 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.836379166919613 | 1.8427160005562881 | -1.988944029029385 | 2.041519272930362 | AMBIGUOUS |
| 1111 | BVM1 | -2.063681073544596 | 2.068609035794033 | -2.0705220782099976 | 2.0705220782099976 | AMBIGUOUS |
| 1111 | BVM2 | -2.063681073544596 | 2.068609035794033 | -2.0705220782099976 | 2.0705220782099976 | AMBIGUOUS |
| 1111 | BVM3 | -2.063681073544596 | 2.068609035794033 | -2.0705220782099976 | 2.0705220782099976 | AMBIGUOUS |
| 1111 | BVM4 | -2.063681073544596 | 2.068609035794033 | -2.0705220782099976 | 2.0705220782099976 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 4.24831e-05 | -2.672754e-07 | 0.14504082159216106 | 0.1450537469730014 | 1 |
| 1111 | 0.0001742364 | -2.672754e-07 | 0.6234193716660738 | 0.623432297046914 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1450537469730014, 0.623432297046914]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [4.24831e-05, 0.0001742364]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.14504082159216106, 0.6234193716660738]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
