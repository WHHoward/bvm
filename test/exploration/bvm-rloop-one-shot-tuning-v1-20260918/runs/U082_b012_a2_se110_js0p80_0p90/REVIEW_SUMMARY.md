# U082_b012_a2_se110_js0p80_0p90 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.800, JS2_AREA=0.900, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0770567266681086 | 0.11554744361437456 | 2.0094129621759276 | -0.11269872928797274 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0770567266681086 | 0.11554744361437456 | 2.0094129621759276 | -0.11269872928797274 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0770567266681086 | 0.11554744361437456 | 2.0094129621759276 | -0.11269872928797274 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0770567266681086 | 0.11554744361437456 | 2.0094129621759276 | -0.11269872928797274 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0770567266681086 | 0.11554744361437456 | 2.0094129621759276 | -0.11269872928797274 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0649108649325336 | 1.1198102643829755 | -1.2493702662294615 | 1.2756239881770712 | AMBIGUOUS |
| 1111 | BVM1 | -1.126342603951745 | 1.1328303801364488 | -1.4068470796013959 | 1.424313538831016 | AMBIGUOUS |
| 1111 | BVM2 | -1.126342603951745 | 1.1328303801364488 | -1.4068470796013959 | 1.424313538831016 | AMBIGUOUS |
| 1111 | BVM3 | -1.126342603951745 | 1.1328303801364488 | -1.4068470796013959 | 1.424313538831016 | AMBIGUOUS |
| 1111 | BVM4 | -1.126342603951745 | 1.1328303801364488 | -1.4068470796013959 | 1.424313538831016 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.005617e-05 | -3.108264e-07 | 0.09038280580945399 | 0.09039783730728446 | 1 |
| 1111 | 0.0001266256 | -3.108264e-07 | 0.4195402324123287 | 0.4195552639101592 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09039783730728446, 0.4195552639101592]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.005617e-05, 0.0001266256]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09038280580945399, 0.4195402324123287]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
