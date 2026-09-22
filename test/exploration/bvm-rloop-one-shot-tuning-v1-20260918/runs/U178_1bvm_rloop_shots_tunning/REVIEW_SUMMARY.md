# U178_1bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=1; bit order: mask left-to-right: b0=BVM1 (rightmost bit is highest-index BVM)
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: passive
- Masks: 0, 1
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0 | BVM1 | -1.0753537687770254 | 0.11081672208591108 | 2.009392431188269 | -0.11223908981232342 | REVIEW_REQUIRED |
| 1 | BVM1 | -1.0753537687770254 | 0.11081672208591108 | 2.009392431188269 | -0.11223908981232342 | REVIEW_REQUIRED |

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
| 0 | BVM1 | -0.01830375746973221 | 0.025098161567796765 | -0.008811947649663284 | 0.021292130258697178 | AMBIGUOUS |
| 1 | BVM1 | -2.3717155823769933 | 2.4099785156260394 | -2.418261877878706 | 2.4184592459236343 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0 | 1.128716e-06 | -1.316027e-06 | -0.0001688025970933835 | 0.0024628489261967006 | 9 |
| 1 | 6.985481e-05 | -1.040589e-06 | 0.1868703162605353 | 0.18692063892069516 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0", "1"], "nondecreasing": true, "values": [0.0024628489261967006, 0.18692063892069516]}, "peak_positive_a": {"masks": ["0", "1"], "nondecreasing": true, "values": [1.128716e-06, 6.985481e-05]}, "signed_area_phi0": {"masks": ["0", "1"], "nondecreasing": true, "values": [-0.0001688025970933835, 0.1868703162605353]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
