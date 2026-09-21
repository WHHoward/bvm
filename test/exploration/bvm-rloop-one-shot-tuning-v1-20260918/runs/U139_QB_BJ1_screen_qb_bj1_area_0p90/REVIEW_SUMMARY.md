# U139_QB_BJ1_screen_qb_bj1_area_0p90 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780305304548612 | 0.11308086030633636 | 2.0095082959868398 | -0.11128447846365809 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780305304548612 | 0.11308086030633636 | 2.0095082959868398 | -0.11128447846365809 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780305304548612 | 0.11308086030633636 | 2.0095082959868398 | -0.11128447846365809 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780305304548612 | 0.11308086030633636 | 2.0095082959868398 | -0.11128447846365809 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.001913822275185733 | 0.002343142734176124 | -0.002479824999303438 | 0.0034865755073255292 | AMBIGUOUS |
| 0001 | BVM4 | -1.1410149867469268 | 1.151008739426519 | -1.3569418667722115 | 1.3744134189600106 | AMBIGUOUS |
| 0011 | BVM3 | -1.4314740311291803 | 1.4402991568081316 | -1.941512402325735 | 1.9434079376979592 | AMBIGUOUS |
| 0011 | BVM4 | -1.4314740311291803 | 1.4402991568081316 | -1.941512402325735 | 1.9434079376979592 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.317136e-07 | -0.0016327056759252734 | 0.0016327056759252734 | 0 |
| 0001 | 2.110581e-05 | -8.317136e-07 | 0.07004205421537325 | 0.07008227570612816 | 1 |
| 0011 | 3.807806e-05 | -4.099521e-05 | 0.029080200751216423 | 0.10754475142917748 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0016327056759252734, 0.07008227570612816, 0.10754475142917748]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.110581e-05, 3.807806e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0016327056759252734, 0.07004205421537325, 0.029080200751216423]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
