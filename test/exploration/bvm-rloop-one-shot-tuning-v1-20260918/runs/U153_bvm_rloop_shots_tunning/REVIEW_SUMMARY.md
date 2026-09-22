# U153_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.74, JS2_AREA=0.74, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: passive
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0765370857789136 | 0.11680890569332084 | 2.0057972801787662 | -0.10943557548975966 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0765370857789136 | 0.11680890569332084 | 2.0057972801787662 | -0.10943557548975966 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0765370857789136 | 0.11680890569332084 | 2.0057972801787662 | -0.10943557548975966 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0765370857789136 | 0.11680890569332084 | 2.0057972801787662 | -0.10943557548975966 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0765370857789136 | 0.11680890569332084 | 2.0057972801787662 | -0.10943557548975966 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0765370857789136 | 0.11680890569332084 | 2.0057972801787662 | -0.10943557548975966 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0765370857789136 | 0.11680890569332084 | 2.0057972801787662 | -0.10943557548975966 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.3415458053081246 | 2.3868662416916604 | -2.9464394721648244 | 3.0504673446601847 | AMBIGUOUS |
| 0011 | BVM3 | -2.658090663173026 | 2.6744872669596877 | -2.7827533878431026 | 3.0971570069346344 | AMBIGUOUS |
| 0011 | BVM4 | -2.658090663173026 | 2.6744872669596877 | -2.7827533878431026 | 3.0971570069346344 | AMBIGUOUS |
| 1111 | BVM1 | -3.2318728809090653 | 3.2445701349449823 | -2.907546778721458 | 3.1730897666218008 | AMBIGUOUS |
| 1111 | BVM2 | -3.2318728809090653 | 3.2445701349449823 | -2.907546778721458 | 3.1730897666218008 | AMBIGUOUS |
| 1111 | BVM3 | -3.2318728809090653 | 3.2445701349449823 | -2.907546778721458 | 3.1730897666218008 | AMBIGUOUS |
| 1111 | BVM4 | -3.2318728809090653 | 3.2445701349449823 | -2.907546778721458 | 3.1730897666218008 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 7.031751e-05 | -4.562726e-06 | 0.1958131246819593 | 0.19603377712966016 | 1 |
| 0011 | 0.000141484 | -4.562726e-06 | 0.4100870065649487 | 0.41030765901264954 | 1 |
| 1111 | 0.0002838168 | -4.562726e-06 | 0.8910811516515998 | 0.8913018040993007 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.19603377712966016, 0.41030765901264954, 0.8913018040993007]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [7.031751e-05, 0.000141484, 0.0002838168]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.1958131246819593, 0.4100870065649487, 0.8910811516515998]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
