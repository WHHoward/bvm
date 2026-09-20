# U081_b012_a2_se110_js0p74_0p90 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.740, JS2_AREA=0.900, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.077225271752843 | 0.11517088301901908 | 2.009459435419311 | -0.11256106026219824 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.077225271752843 | 0.11517088301901908 | 2.009459435419311 | -0.11256106026219824 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.077225271752843 | 0.11517088301901908 | 2.009459435419311 | -0.11256106026219824 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.077225271752843 | 0.11517088301901908 | 2.009459435419311 | -0.11256106026219824 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.077225271752843 | 0.11517088301901908 | 2.009459435419311 | -0.11256106026219824 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0693726941846433 | 1.1118185694790195 | -1.2550249458645506 | 1.2891856445399088 | AMBIGUOUS |
| 1111 | BVM1 | -1.1321858981098925 | 1.1389290224852928 | -1.4015770456327712 | 1.418821324561835 | AMBIGUOUS |
| 1111 | BVM2 | -1.1321858981098925 | 1.1389290224852928 | -1.4015770456327712 | 1.418821324561835 | AMBIGUOUS |
| 1111 | BVM3 | -1.1321858981098925 | 1.1389290224852928 | -1.4015770456327712 | 1.418821324561835 | AMBIGUOUS |
| 1111 | BVM4 | -1.1321858981098925 | 1.1389290224852928 | -1.4015770456327712 | 1.418821324561835 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.033359e-05 | -2.925316e-07 | 0.09178608958527891 | 0.09180023635051746 | 1 |
| 1111 | 0.000127718 | -2.925316e-07 | 0.42166538344622356 | 0.4216795302114621 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09180023635051746, 0.4216795302114621]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.033359e-05, 0.000127718]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09178608958527891, 0.42166538344622356]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
