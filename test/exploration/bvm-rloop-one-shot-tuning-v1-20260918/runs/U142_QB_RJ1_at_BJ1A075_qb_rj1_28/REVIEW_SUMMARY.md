# U142_QB_RJ1_at_BJ1A075_qb_rj1_28 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780241708518818 | 0.11913113546797471 | 2.009316991745244 | -0.11122797845886064 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780241708518818 | 0.11913113546797471 | 2.009316991745244 | -0.11122797845886064 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780241708518818 | 0.11913113546797471 | 2.009316991745244 | -0.11122797845886064 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780241708518818 | 0.11913113546797471 | 2.009316991745244 | -0.11122797845886064 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0019060873449514655 | 0.0023000117445982167 | -0.002452704997000581 | 0.0034706281820277266 | AMBIGUOUS |
| 0001 | BVM4 | -1.176009482253649 | 1.1859279228141701 | -1.474476375766583 | 1.474476375766583 | AMBIGUOUS |
| 0011 | BVM3 | -1.5359749916928815 | 1.5447111020121616 | -1.9579216111838902 | 1.9839689091703097 | AMBIGUOUS |
| 0011 | BVM4 | -1.5359749916928815 | 1.5447111020121616 | -1.9579216111838902 | 1.9839689091703097 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -9.694717e-07 | -0.002008158846522566 | 0.002008158846522566 | 0 |
| 0001 | 1.774768e-05 | -2.277979e-05 | 0.028202373658504986 | 0.043620640044286466 | 2 |
| 0011 | 2.409493e-05 | -4.978373e-05 | -0.003737259588082712 | 0.08179714159268364 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.002008158846522566, 0.043620640044286466, 0.08179714159268364]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.774768e-05, 2.409493e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.002008158846522566, 0.028202373658504986, -0.003737259588082712]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
