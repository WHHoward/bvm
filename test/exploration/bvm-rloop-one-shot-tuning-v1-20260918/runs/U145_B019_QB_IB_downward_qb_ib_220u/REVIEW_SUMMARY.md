# U145_B019_QB_IB_downward_qb_ib_220u review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780264142647864 | 0.11316600820089055 | 2.009555246695052 | -0.1113323841015288 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780264142647864 | 0.11316600820089055 | 2.009555246695052 | -0.1113323841015288 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780264142647864 | 0.11316600820089055 | 2.009555246695052 | -0.1113323841015288 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780264142647864 | 0.11316600820089055 | 2.009555246695052 | -0.1113323841015288 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0018717735392208557 | 0.0022688492067408287 | -0.0024949128879085507 | 0.0035458766391215737 | AMBIGUOUS |
| 0001 | BVM4 | -1.135402387678791 | 1.1453262713383658 | -1.339794210809099 | 1.3611375252974947 | AMBIGUOUS |
| 0011 | BVM3 | -1.1737324683983277 | 1.1824791943523119 | -1.455546645990176 | 1.4578472306925694 | AMBIGUOUS |
| 0011 | BVM4 | -1.1737324683983277 | 1.1824791943523119 | -1.455546645990176 | 1.4578472306925694 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.526131e-07 | -0.0016433137874141226 | 0.0016433137874141226 | 0 |
| 0001 | 2.218938e-05 | -8.526131e-07 | 0.07813765701788623 | 0.07817888920396467 | 1 |
| 0011 | 4.385265e-05 | -8.526131e-07 | 0.15425195614894477 | 0.1542931883350232 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0016433137874141226, 0.07817888920396467, 0.1542931883350232]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.218938e-05, 4.385265e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [-0.0016433137874141226, 0.07813765701788623, 0.15425195614894477]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
