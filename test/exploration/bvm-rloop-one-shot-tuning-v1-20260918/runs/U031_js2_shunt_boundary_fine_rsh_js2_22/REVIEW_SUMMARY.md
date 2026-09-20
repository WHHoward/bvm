# U031_js2_shunt_boundary_fine_rsh_js2_22 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=22
- Mode: passive
- Masks: 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 1111 | BVM1 | -1.0780788197126447 | 0.11362723922597087 | 2.009776949530779 | -0.11152241510358052 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0780788197126447 | 0.11362723922597087 | 2.009776949530779 | -0.11152241510358052 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0780788197126447 | 0.11362723922597087 | 2.009776949530779 | -0.11152241510358052 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0780788197126447 | 0.11362723922597087 | 2.009776949530779 | -0.11152241510358052 | REVIEW_REQUIRED |

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
| 1111 | BVM1 | -1.1889821698340808 | 1.1969346171290707 | -1.4990935074343785 | 1.4990935074343785 | AMBIGUOUS |
| 1111 | BVM2 | -1.1889821698340808 | 1.1969346171290707 | -1.4990935074343785 | 1.4990935074343785 | AMBIGUOUS |
| 1111 | BVM3 | -1.1889821698340808 | 1.1969346171290707 | -1.4990935074343785 | 1.4990935074343785 | AMBIGUOUS |
| 1111 | BVM4 | -1.1889821698340808 | 1.1969346171290707 | -1.4990935074343785 | 1.4990935074343785 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 1111 | 0.0001311173 | -2.863119e-07 | 0.445257676672386 | 0.4452715226542708 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.4452715226542708]}, "peak_positive_a": {"masks": ["1111"], "nondecreasing": true, "values": [0.0001311173]}, "signed_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.445257676672386]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
