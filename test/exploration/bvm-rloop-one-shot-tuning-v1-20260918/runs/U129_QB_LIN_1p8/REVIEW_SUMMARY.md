# U129_QB_LIN_1p8 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780265575454562 | 0.11307465326355576 | 2.009503043873718 | -0.11128018128019472 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780265575454562 | 0.11307465326355576 | 2.009503043873718 | -0.11128018128019472 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780265575454562 | 0.11307465326355576 | 2.009503043873718 | -0.11128018128019472 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780265575454562 | 0.11307465326355576 | 2.009503043873718 | -0.11128018128019472 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0019089362184328128 | 0.002334818930652417 | -0.002486620915373463 | 0.0034956950855646964 | AMBIGUOUS |
| 0001 | BVM4 | -1.1412918845169178 | 1.1512598540957293 | -1.3577489574041248 | 1.3750651743674664 | AMBIGUOUS |
| 0011 | BVM3 | -1.4277787398294841 | 1.436558347194711 | -1.9400532857229629 | 1.9414156520358294 | AMBIGUOUS |
| 0011 | BVM4 | -1.4277787398294841 | 1.436558347194711 | -1.9400532857229629 | 1.9414156520358294 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.393935e-07 | -0.0016622558849805611 | 0.0016622558849805611 | 0 |
| 0001 | 2.096531e-05 | -8.393935e-07 | 0.069564252245957 | 0.06960484513502359 | 1 |
| 0011 | 3.8117e-05 | -4.025972e-05 | 0.03055838107888461 | 0.10632900321157697 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0016622558849805611, 0.06960484513502359, 0.10632900321157697]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.096531e-05, 3.8117e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0016622558849805611, 0.069564252245957, 0.03055838107888461]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
