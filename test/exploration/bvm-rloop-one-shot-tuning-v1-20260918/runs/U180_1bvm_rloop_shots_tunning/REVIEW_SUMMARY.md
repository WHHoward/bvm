# U180_1bvm_rloop_shots_tunning review summary

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
| 0 | BVM1 | -1.0764687470575474 | 0.114543812543237 | 2.0078182296461473 | -0.11090521223427025 | REVIEW_REQUIRED |
| 1 | BVM1 | -1.0764687470575474 | 0.114543812543237 | 2.0078182296461473 | -0.11090521223427025 | REVIEW_REQUIRED |

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
| 0 | BVM1 | -0.0218138242466581 | 0.03274229390702895 | -0.019096205846881063 | 0.041342947454243426 | AMBIGUOUS |
| 1 | BVM1 | -3.2804200882708234 | 3.2804200882708234 | -2.9173027220850822 | 3.1344201924931547 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0 | 1.659413e-06 | -1.971056e-06 | 9.114578972690836e-05 | 0.002979243503078585 | 10 |
| 1 | 5.824084e-05 | -2.023956e-06 | 0.15317057452480573 | 0.15359078884755725 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0", "1"], "nondecreasing": true, "values": [0.002979243503078585, 0.15359078884755725]}, "peak_positive_a": {"masks": ["0", "1"], "nondecreasing": true, "values": [1.659413e-06, 5.824084e-05]}, "signed_area_phi0": {"masks": ["0", "1"], "nondecreasing": true, "values": [9.114578972690836e-05, 0.15317057452480573]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
