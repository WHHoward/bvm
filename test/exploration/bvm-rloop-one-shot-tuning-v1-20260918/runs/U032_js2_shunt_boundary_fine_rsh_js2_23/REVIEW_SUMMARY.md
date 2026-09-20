# U032_js2_shunt_boundary_fine_rsh_js2_23 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=23
- Mode: passive
- Masks: 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 1111 | BVM1 | -1.078082798586222 | 0.11362039556341781 | 2.00978936361634 | -0.11153482918914173 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.078082798586222 | 0.11362039556341781 | 2.00978936361634 | -0.11153482918914173 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.078082798586222 | 0.11362039556341781 | 2.00978936361634 | -0.11153482918914173 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.078082798586222 | 0.11362039556341781 | 2.00978936361634 | -0.11153482918914173 | REVIEW_REQUIRED |

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
| 1111 | BVM1 | -1.2145959934174952 | 1.222482184509676 | -1.581146697782098 | 1.581146697782098 | AMBIGUOUS |
| 1111 | BVM2 | -1.2145959934174952 | 1.222482184509676 | -1.581146697782098 | 1.581146697782098 | AMBIGUOUS |
| 1111 | BVM3 | -1.2145959934174952 | 1.222482184509676 | -1.581146697782098 | 1.581146697782098 | AMBIGUOUS |
| 1111 | BVM4 | -1.2145959934174952 | 1.222482184509676 | -1.581146697782098 | 1.581146697782098 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 1111 | 0.0001329705 | -2.855834e-07 | 0.4564166024474514 | 0.45643041319923283 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.45643041319923283]}, "peak_positive_a": {"masks": ["1111"], "nondecreasing": true, "values": [0.0001329705]}, "signed_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.4564166024474514]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
