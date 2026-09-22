# U174_2bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=2; bit order: mask left-to-right: b1=BVM1, b0=BVM2; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 00, 01, 11
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 00 | BVM1 | -1.074969268832811 | 0.11056382488133805 | 2.008076219808899 | -0.11153785313306047 | REVIEW_REQUIRED |
| 01 | BVM2 | -1.074969268832811 | 0.11056382488133805 | 2.008076219808899 | -0.11153785313306047 | REVIEW_REQUIRED |
| 11 | BVM1 | -1.074969268832811 | 0.11056382488133805 | 2.008076219808899 | -0.11153785313306047 | REVIEW_REQUIRED |
| 11 | BVM2 | -1.074969268832811 | 0.11056382488133805 | 2.008076219808899 | -0.11153785313306047 | REVIEW_REQUIRED |

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
| 00 | BVM1 | -0.023493131713197925 | 0.03188825256690353 | -0.006471446887542482 | 0.02910791120405398 | AMBIGUOUS |
| 01 | BVM2 | -2.336700444474152 | 2.404107608085266 | -2.9632555924659827 | 2.9636973588415225 | AMBIGUOUS |
| 11 | BVM1 | -2.624603778780236 | 2.6255648359040964 | -3.0318481898397276 | 3.262785322688884 | AMBIGUOUS |
| 11 | BVM2 | -2.624603778780236 | 2.6255648359040964 | -3.0318481898397276 | 3.262785322688884 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 00 | 1.753453e-06 | -2.37584e-06 | -0.00048459470327811855 | 0.004353628235995486 | 9 |
| 01 | 3.274531e-05 | -2.46351e-05 | 0.05389673626911237 | 0.0809659135853356 | 3 |
| 11 | 8.58523e-05 | -4.185371e-06 | 0.17223571086935788 | 0.1732874300595159 | 4 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["00", "01", "11"], "nondecreasing": true, "values": [0.004353628235995486, 0.0809659135853356, 0.1732874300595159]}, "peak_positive_a": {"masks": ["00", "01", "11"], "nondecreasing": true, "values": [1.753453e-06, 3.274531e-05, 8.58523e-05]}, "signed_area_phi0": {"masks": ["00", "01", "11"], "nondecreasing": true, "values": [-0.00048459470327811855, 0.05389673626911237, 0.17223571086935788]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
