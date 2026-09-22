# U183_1bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=1; bit order: mask left-to-right: b0=BVM1 (rightmost bit is highest-index BVM)
- Parameters: JS1_AREA=0.74, JS2_AREA=0.74, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 0, 1
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0 | BVM1 | -1.0764514585940228 | 0.1145617970518065 | 2.0078779127498065 | -0.11094054463163663 | REVIEW_REQUIRED |
| 1 | BVM1 | -1.0764514585940228 | 0.1145617970518065 | 2.0078779127498065 | -0.11094054463163663 | REVIEW_REQUIRED |

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
| 0 | BVM1 | -0.022434846834602677 | 0.033760567232930895 | -0.019317319809318636 | 0.042100700053798255 | AMBIGUOUS |
| 1 | BVM1 | -3.3060331160795227 | 3.3060331160795227 | -2.889386069714577 | 3.1587129186404463 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0 | 1.675234e-06 | -1.962761e-06 | 9.268759977276065e-05 | 0.0030410744248055223 | 10 |
| 1 | 5.962262e-05 | -1.926388e-05 | 0.15615382844337672 | 0.16496465960257345 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0", "1"], "nondecreasing": true, "values": [0.0030410744248055223, 0.16496465960257345]}, "peak_positive_a": {"masks": ["0", "1"], "nondecreasing": true, "values": [1.675234e-06, 5.962262e-05]}, "signed_area_phi0": {"masks": ["0", "1"], "nondecreasing": true, "values": [9.268759977276065e-05, 0.15615382844337672]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
