# U061_b011_b_lm3_8p9 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0782311309931838 | 0.1143041251989406 | 2.009823263619219 | -0.11120155873830737 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0782311309931838 | 0.1143041251989406 | 2.009823263619219 | -0.11120155873830737 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0782311309931838 | 0.1143041251989406 | 2.009823263619219 | -0.11120155873830737 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0782311309931838 | 0.1143041251989406 | 2.009823263619219 | -0.11120155873830737 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0782311309931838 | 0.1143041251989406 | 2.009823263619219 | -0.11120155873830737 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.1354383885269184 | 1.1464600274909753 | -1.3553093826899296 | 1.3712277417880947 | AMBIGUOUS |
| 1111 | BVM1 | -1.1902605819144665 | 1.198978341668808 | -1.5241621139292434 | 1.5241621139292434 | AMBIGUOUS |
| 1111 | BVM2 | -1.1902605819144665 | 1.198978341668808 | -1.5241621139292434 | 1.5241621139292434 | AMBIGUOUS |
| 1111 | BVM3 | -1.1902605819144665 | 1.198978341668808 | -1.5241621139292434 | 1.5241621139292434 | AMBIGUOUS |
| 1111 | BVM4 | -1.1902605819144665 | 1.198978341668808 | -1.5241621139292434 | 1.5241621139292434 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.079819e-05 | -2.956895e-07 | 0.10159227349343591 | 0.10160657297403906 | 1 |
| 1111 | 0.0001311889 | -2.956895e-07 | 0.4471819287702267 | 0.44719622825082983 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10160657297403906, 0.44719622825082983]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.079819e-05, 0.0001311889]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10159227349343591, 0.4471819287702267]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
