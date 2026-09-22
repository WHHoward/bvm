# U161_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 0001, 0011, 0111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0748305412261454 | 0.11040021359983962 | 2.0072212394546094 | -0.11115683619929836 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0748305412261454 | 0.11040021359983962 | 2.0072212394546094 | -0.11115683619929836 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0748305412261454 | 0.11040021359983962 | 2.0072212394546094 | -0.11115683619929836 | REVIEW_REQUIRED |
| 0111 | BVM2 | -1.0748305412261454 | 0.11040021359983962 | 2.0072212394546094 | -0.11115683619929836 | REVIEW_REQUIRED |
| 0111 | BVM3 | -1.0748305412261454 | 0.11040021359983962 | 2.0072212394546094 | -0.11115683619929836 | REVIEW_REQUIRED |
| 0111 | BVM4 | -1.0748305412261454 | 0.11040021359983962 | 2.0072212394546094 | -0.11115683619929836 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.4093471320512996 | 2.425497348070561 | -2.5409916975959206 | 2.542349734894335 | AMBIGUOUS |
| 0011 | BVM3 | -2.237216286449122 | 2.3509722661085597 | -3.0924667585081993 | 3.09371061805044 | AMBIGUOUS |
| 0011 | BVM4 | -2.237216286449122 | 2.3509722661085597 | -3.0924667585081993 | 3.09371061805044 | AMBIGUOUS |
| 0111 | BVM2 | -2.499653238311072 | 2.500465708380062 | -3.0559518399146257 | 3.2218991817523026 | AMBIGUOUS |
| 0111 | BVM3 | -2.499653238311072 | 2.500465708380062 | -3.0559518399146257 | 3.2218991817523026 | AMBIGUOUS |
| 0111 | BVM4 | -2.499653238311072 | 2.500465708380062 | -3.0559518399146257 | 3.2218991817523026 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.937001e-05 | -2.433618e-05 | 0.04946531488104365 | 0.07207345024221683 | 2 |
| 0011 | 6.725435e-05 | -2.323701e-05 | 0.06272931755008206 | 0.08726967495311061 | 5 |
| 0111 | 8.193219e-05 | -1.250436e-05 | 0.15379419651031823 | 0.16117725580919084 | 5 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.07207345024221683, 0.08726967495311061, 0.16117725580919084]}, "peak_positive_a": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [2.937001e-05, 6.725435e-05, 8.193219e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.04946531488104365, 0.06272931755008206, 0.15379419651031823]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
