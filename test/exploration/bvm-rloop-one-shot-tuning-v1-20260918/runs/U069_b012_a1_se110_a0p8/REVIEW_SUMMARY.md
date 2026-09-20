# U069_b012_a1_se110_a0p8 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.800, JS2_AREA=0.800, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.077285591476275 | 0.11764351421489477 | 2.00954331007432 | -0.11256058279736889 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.077285591476275 | 0.11764351421489477 | 2.00954331007432 | -0.11256058279736889 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.077285591476275 | 0.11764351421489477 | 2.00954331007432 | -0.11256058279736889 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.077285591476275 | 0.11764351421489477 | 2.00954331007432 | -0.11256058279736889 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.077285591476275 | 0.11764351421489477 | 2.00954331007432 | -0.11256058279736889 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.1339773302338405 | 1.1415933398946283 | -1.4441213105129667 | 1.4467297008752997 | AMBIGUOUS |
| 1111 | BVM1 | -1.306835513925948 | 1.3128136759828715 | -1.8993930970590895 | 1.8993930970590895 | AMBIGUOUS |
| 1111 | BVM2 | -1.306835513925948 | 1.3128136759828715 | -1.8993930970590895 | 1.8993930970590895 | AMBIGUOUS |
| 1111 | BVM3 | -1.306835513925948 | 1.3128136759828715 | -1.8993930970590895 | 1.8993930970590895 | AMBIGUOUS |
| 1111 | BVM4 | -1.306835513925948 | 1.3128136759828715 | -1.8993930970590895 | 1.8993930970590895 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.117635e-05 | -3.500398e-07 | 0.10490296501327023 | 0.10491989286268805 | 1 |
| 1111 | 0.0001407204 | -3.500398e-07 | 0.5002188014334116 | 0.5002357292828294 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10491989286268805, 0.5002357292828294]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.117635e-05, 0.0001407204]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10490296501327023, 0.5002188014334116]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
