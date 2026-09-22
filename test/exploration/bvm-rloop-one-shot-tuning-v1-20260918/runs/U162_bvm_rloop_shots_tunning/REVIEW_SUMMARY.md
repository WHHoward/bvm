# U162_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 0001, 0011, 0111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0748315773916701 | 0.11037522627377408 | 2.0072007084669505 | -0.11114665028294061 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0748315773916701 | 0.11037522627377408 | 2.0072007084669505 | -0.11114665028294061 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0748315773916701 | 0.11037522627377408 | 2.0072007084669505 | -0.11114665028294061 | REVIEW_REQUIRED |
| 0111 | BVM2 | -1.0748315773916701 | 0.11037522627377408 | 2.0072007084669505 | -0.11114665028294061 | REVIEW_REQUIRED |
| 0111 | BVM3 | -1.0748315773916701 | 0.11037522627377408 | 2.0072007084669505 | -0.11114665028294061 | REVIEW_REQUIRED |
| 0111 | BVM4 | -1.0748315773916701 | 0.11037522627377408 | 2.0072007084669505 | -0.11114665028294061 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.410497010599644 | 2.426598477459837 | -2.5480030139659244 | 2.549410007324834 | AMBIGUOUS |
| 0011 | BVM3 | -2.2378266297403853 | 2.3486531398552963 | -3.0923065531424827 | 3.0935993369142296 | AMBIGUOUS |
| 0011 | BVM4 | -2.2378266297403853 | 2.3486531398552963 | -3.0923065531424827 | 3.0935993369142296 | AMBIGUOUS |
| 0111 | BVM2 | -2.508074906209285 | 2.508881598953841 | -3.0563041134656657 | 3.225450039941143 | AMBIGUOUS |
| 0111 | BVM3 | -2.508074906209285 | 2.508881598953841 | -3.0563041134656657 | 3.225450039941143 | AMBIGUOUS |
| 0111 | BVM4 | -2.508074906209285 | 2.508881598953841 | -3.0563041134656657 | 3.225450039941143 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.857327e-05 | -2.717729e-05 | 0.045806891332983046 | 0.07236448790831465 | 4 |
| 0011 | 6.545196e-05 | -2.037917e-05 | 0.06012855576876122 | 0.08766991873420575 | 5 |
| 0111 | 7.855935e-05 | -1.529106e-05 | 0.14873432839754905 | 0.1583859526899472 | 5 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.07236448790831465, 0.08766991873420575, 0.1583859526899472]}, "peak_positive_a": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [2.857327e-05, 6.545196e-05, 7.855935e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.045806891332983046, 0.06012855576876122, 0.14873432839754905]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
