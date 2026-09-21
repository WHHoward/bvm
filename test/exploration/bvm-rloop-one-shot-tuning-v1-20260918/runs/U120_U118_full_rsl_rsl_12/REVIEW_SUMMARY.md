# U120_U118_full_rsl_rsl_12 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.6, JS2_AREA=1.1, RSH_JS1=20, RSH_JS2=10
- Mode: closed
- Masks: 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 1111 | BVM1 | -1.0747697007319834 | 0.1346248691779708 | 2.0191648630039976 | -0.13194103937261206 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0747697007319834 | 0.1346248691779708 | 2.0191648630039976 | -0.13194103937261206 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0747697007319834 | 0.1346248691779708 | 2.0191648630039976 | -0.13194103937261206 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0747697007319834 | 0.1346248691779708 | 2.0191648630039976 | -0.13194103937261206 | REVIEW_REQUIRED |

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
| 1111 | BVM1 | -0.9186829160369082 | 0.9372610247975424 | -1.0581007681570802 | 1.0984949293335755 | AMBIGUOUS |
| 1111 | BVM2 | -0.9186829160369082 | 0.9372610247975424 | -1.0581007681570802 | 1.0984949293335755 | AMBIGUOUS |
| 1111 | BVM3 | -0.9186829160369082 | 0.9372610247975424 | -1.0581007681570802 | 1.0984949293335755 | AMBIGUOUS |
| 1111 | BVM4 | -0.9186829160369082 | 0.9372610247975424 | -1.0581007681570802 | 1.0984949293335755 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 1111 | 5.183993e-05 | -3.234416e-05 | 0.0833150771695853 | 0.11988959510445132 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.11988959510445132]}, "peak_positive_a": {"masks": ["1111"], "nondecreasing": true, "values": [5.183993e-05]}, "signed_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.0833150771695853]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
