# U132_QB_L1_screen_qb_l1_1p6p review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780308330770039 | 0.11312860678926397 | 2.0095143438746774 | -0.11129243621081267 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780308330770039 | 0.11312860678926397 | 2.0095143438746774 | -0.11129243621081267 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780308330770039 | 0.11312860678926397 | 2.0095143438746774 | -0.11129243621081267 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780308330770039 | 0.11312860678926397 | 2.0095143438746774 | -0.11129243621081267 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0019167666416329383 | 0.0023454186498623416 | -0.0024904565495019776 | 0.003514077481491813 | AMBIGUOUS |
| 0001 | BVM4 | -1.1395838336676556 | 1.1495880587425034 | -1.352570485274261 | 1.3709765952878954 | AMBIGUOUS |
| 0011 | BVM3 | -1.4118630863653516 | 1.420698668524064 | -1.935512229140182 | 1.935512229140182 | AMBIGUOUS |
| 0011 | BVM4 | -1.4118630863653516 | 1.420698668524064 | -1.935512229140182 | 1.935512229140182 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.158157e-07 | -0.001646384143142239 | 0.001646384143142239 | 0 |
| 0001 | 2.124641e-05 | -8.158157e-07 | 0.07178314407541311 | 0.0718225967471444 | 1 |
| 0011 | 3.915122e-05 | -3.695426e-05 | 0.03486046699289755 | 0.10945514196602879 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.001646384143142239, 0.0718225967471444, 0.10945514196602879]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.124641e-05, 3.915122e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.001646384143142239, 0.07178314407541311, 0.03486046699289755]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
