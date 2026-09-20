# U094_b012_a2_se130_js0p90_1p00 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.900, JS2_AREA=1.000, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0765701900070768 | 0.12018123978249509 | 2.009190145255599 | -0.112979956072416 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0765701900070768 | 0.12018123978249509 | 2.009190145255599 | -0.112979956072416 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0765701900070768 | 0.12018123978249509 | 2.009190145255599 | -0.112979956072416 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0765701900070768 | 0.12018123978249509 | 2.009190145255599 | -0.112979956072416 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0765701900070768 | 0.12018123978249509 | 2.009190145255599 | -0.112979956072416 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.2057025743524632 | 1.211668242746354 | -1.760164448335265 | 1.760164448335265 | AMBIGUOUS |
| 1111 | BVM1 | -1.5382608068165557 | 1.5429646789061198 | -1.9119632499574528 | 2.0541793324560778 | AMBIGUOUS |
| 1111 | BVM2 | -1.5382608068165557 | 1.5429646789061198 | -1.9119632499574528 | 2.0541793324560778 | AMBIGUOUS |
| 1111 | BVM3 | -1.5382608068165557 | 1.5429646789061198 | -1.9119632499574528 | 2.0541793324560778 | AMBIGUOUS |
| 1111 | BVM4 | -1.5382608068165557 | 1.5429646789061198 | -1.9119632499574528 | 2.0541793324560778 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.503651e-05 | -2.998138e-07 | 0.117487850895262 | 0.11750234982612581 | 1 |
| 1111 | 0.0001724239 | -2.998138e-07 | 0.5556531826390722 | 0.555667681569936 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11750234982612581, 0.555667681569936]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.503651e-05, 0.0001724239]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.117487850895262, 0.5556531826390722]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
