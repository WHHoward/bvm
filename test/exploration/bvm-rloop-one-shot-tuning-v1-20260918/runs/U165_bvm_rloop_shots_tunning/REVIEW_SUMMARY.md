# U165_bvm_rloop_shots_tunning review summary

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
| 00 | BVM1 | -1.0749892013394897 | 0.11059501925018404 | 2.008069216991403 | -0.11151764045528766 | REVIEW_REQUIRED |
| 01 | BVM2 | -1.0749892013394897 | 0.11059501925018404 | 2.008069216991403 | -0.11151764045528766 | REVIEW_REQUIRED |
| 11 | BVM1 | -1.0749892013394897 | 0.11059501925018404 | 2.008069216991403 | -0.11151764045528766 | REVIEW_REQUIRED |
| 11 | BVM2 | -1.0749892013394897 | 0.11059501925018404 | 2.008069216991403 | -0.11151764045528766 | REVIEW_REQUIRED |

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
| 00 | BVM1 | -0.02259669149623283 | 0.030335664266053476 | -0.006586293094477596 | 0.027519879097377357 | AMBIGUOUS |
| 01 | BVM2 | -2.25861253587159 | 2.38415307963029 | -2.912905828049754 | 2.913485422606012 | AMBIGUOUS |
| 11 | BVM1 | -2.677589515110435 | 2.678414144617077 | -3.1040731963951536 | 3.311734857831284 | AMBIGUOUS |
| 11 | BVM2 | -2.677589515110435 | 2.678414144617077 | -3.1040731963951536 | 3.311734857831284 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 00 | 1.951478e-06 | -2.420356e-06 | -0.0004599131584579857 | 0.004600561967491305 | 9 |
| 01 | 3.159565e-05 | -4.489056e-05 | 0.03844917733448361 | 0.07687545367039544 | 7 |
| 11 | 8.268785e-05 | -1.301536e-05 | 0.13484388988974502 | 0.14307446843282348 | 5 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["00", "01", "11"], "nondecreasing": true, "values": [0.004600561967491305, 0.07687545367039544, 0.14307446843282348]}, "peak_positive_a": {"masks": ["00", "01", "11"], "nondecreasing": true, "values": [1.951478e-06, 3.159565e-05, 8.268785e-05]}, "signed_area_phi0": {"masks": ["00", "01", "11"], "nondecreasing": true, "values": [-0.0004599131584579857, 0.03844917733448361, 0.13484388988974502]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
