# U130_QB_L1_screen_qb_l1_1p0p review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780288177484116 | 0.11256774476980817 | 2.00949492697162 | -0.11126378832105623 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780288177484116 | 0.11256774476980817 | 2.00949492697162 | -0.11126378832105623 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780288177484116 | 0.11256774476980817 | 2.00949492697162 | -0.11126378832105623 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780288177484116 | 0.11256774476980817 | 2.00949492697162 | -0.11126378832105623 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0018991481894326536 | 0.002332081465631228 | -0.002460885561075506 | 0.0034303619814254763 | AMBIGUOUS |
| 0001 | BVM4 | -1.1459394316721216 | 1.1559017353349588 | -1.3724889333036379 | 1.3862714330655095 | AMBIGUOUS |
| 0011 | BVM3 | -1.471985521329723 | 1.4807793094003794 | -1.9513104740027956 | 1.9583498971357503 | AMBIGUOUS |
| 0011 | BVM4 | -1.471985521329723 | 1.4807793094003794 | -1.9513104740027956 | 1.9583498971357503 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.328808e-07 | -0.0015438032202575683 | 0.0015438032202575683 | 0 |
| 0001 | 2.06844e-05 | -8.328808e-07 | 0.06421824605416747 | 0.06425852399046324 | 1 |
| 0011 | 3.500201e-05 | -4.864657e-05 | 0.014594336865695898 | 0.10472333212334561 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0015438032202575683, 0.06425852399046324, 0.10472333212334561]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.06844e-05, 3.500201e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0015438032202575683, 0.06421824605416747, 0.014594336865695898]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
