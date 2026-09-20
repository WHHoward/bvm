# U058_b011_b_lm3_8p6 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0781159028143852 | 0.11380963079075423 | 2.0097705833330552 | -0.11142357988392035 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0781159028143852 | 0.11380963079075423 | 2.0097705833330552 | -0.11142357988392035 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0781159028143852 | 0.11380963079075423 | 2.0097705833330552 | -0.11142357988392035 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0781159028143852 | 0.11380963079075423 | 2.0097705833330552 | -0.11142357988392035 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0781159028143852 | 0.11380963079075423 | 2.0097705833330552 | -0.11142357988392035 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.1282452376344314 | 1.138684576408198 | -1.3230878119257086 | 1.3472166562280987 | AMBIGUOUS |
| 1111 | BVM1 | -1.1592705839308792 | 1.1675254733642264 | -1.4069226781993645 | 1.4190049257041857 | AMBIGUOUS |
| 1111 | BVM2 | -1.1592705839308792 | 1.1675254733642264 | -1.4069226781993645 | 1.4190049257041857 | AMBIGUOUS |
| 1111 | BVM3 | -1.1592705839308792 | 1.1675254733642264 | -1.4069226781993645 | 1.4190049257041857 | AMBIGUOUS |
| 1111 | BVM4 | -1.1592705839308792 | 1.1675254733642264 | -1.4069226781993645 | 1.4190049257041857 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.027353e-05 | -2.902662e-07 | 0.09988072561524296 | 0.0998947628262249 | 1 |
| 1111 | 0.0001281322 | -2.902662e-07 | 0.4313320502286314 | 0.43134608743961333 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.0998947628262249, 0.43134608743961333]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.027353e-05, 0.0001281322]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09988072561524296, 0.4313320502286314]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
