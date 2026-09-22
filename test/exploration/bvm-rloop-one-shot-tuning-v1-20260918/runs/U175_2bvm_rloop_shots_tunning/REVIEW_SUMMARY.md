# U175_2bvm_rloop_shots_tunning review summary

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
| 00 | BVM1 | -1.0749646579544772 | 0.11054743192219955 | 2.0081287409401196 | -0.11156602355798771 | REVIEW_REQUIRED |
| 01 | BVM2 | -1.0749646579544772 | 0.11054743192219955 | 2.0081287409401196 | -0.11156602355798771 | REVIEW_REQUIRED |
| 11 | BVM1 | -1.0749646579544772 | 0.11054743192219955 | 2.0081287409401196 | -0.11156602355798771 | REVIEW_REQUIRED |
| 11 | BVM2 | -1.0749646579544772 | 0.11054743192219955 | 2.0081287409401196 | -0.11156602355798771 | REVIEW_REQUIRED |

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
| 00 | BVM1 | -0.023629384259978906 | 0.0320307280719594 | -0.00658906239048739 | 0.029279862204570458 | AMBIGUOUS |
| 01 | BVM2 | -2.3580097793821975 | 2.414824815474176 | -2.976482068518668 | 2.9769289755988706 | AMBIGUOUS |
| 11 | BVM1 | -2.5976382363496473 | 2.598684998410363 | -3.0371980877587954 | 3.2549400821635612 | AMBIGUOUS |
| 11 | BVM2 | -2.5976382363496473 | 2.598684998410363 | -3.0371980877587954 | 3.2549400821635612 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 00 | 1.764341e-06 | -2.329607e-06 | -0.00043343949170137106 | 0.004351792240321234 | 9 |
| 01 | 3.459017e-05 | -2.493873e-05 | 0.06667082277250733 | 0.09232554684296833 | 3 |
| 11 | 8.616438e-05 | -1.973059e-06 | 0.17949937927121104 | 0.17964403825156833 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["00", "01", "11"], "nondecreasing": true, "values": [0.004351792240321234, 0.09232554684296833, 0.17964403825156833]}, "peak_positive_a": {"masks": ["00", "01", "11"], "nondecreasing": true, "values": [1.764341e-06, 3.459017e-05, 8.616438e-05]}, "signed_area_phi0": {"masks": ["00", "01", "11"], "nondecreasing": true, "values": [-0.00043343949170137106, 0.06667082277250733, 0.17949937927121104]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
