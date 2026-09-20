# U103_b013_s2_rsl12_closed review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=1.00, JS2_AREA=1.00, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0762802967219116 | 0.11708997332282124 | 2.0088785198770256 | -0.11292202367313064 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0762802967219116 | 0.11708997332282124 | 2.0088785198770256 | -0.11292202367313064 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0762802967219116 | 0.11708997332282124 | 2.0088785198770256 | -0.11292202367313064 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0762802967219116 | 0.11708997332282124 | 2.0088785198770256 | -0.11292202367313064 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0762802967219116 | 0.11708997332282124 | 2.0088785198770256 | -0.11292202367313064 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0762802967219116 | 0.11708997332282124 | 2.0088785198770256 | -0.11292202367313064 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0762802967219116 | 0.11708997332282124 | 2.0088785198770256 | -0.11292202367313064 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.048787514267666 | 1.1459523550535007 | -1.2667074916452907 | 1.2891634583408418 | AMBIGUOUS |
| 0011 | BVM3 | -1.1362409273274592 | 1.1600671544210543 | -1.7015776835012928 | 1.7015776835012928 | AMBIGUOUS |
| 0011 | BVM4 | -1.1362409273274592 | 1.1600671544210543 | -1.7015776835012928 | 1.7015776835012928 | AMBIGUOUS |
| 1111 | BVM1 | -1.5654773525078942 | 1.5702863146063817 | -1.9016561371104073 | 2.0680239822232274 | AMBIGUOUS |
| 1111 | BVM2 | -1.5654773525078942 | 1.5702863146063817 | -1.9016561371104073 | 2.0680239822232274 | AMBIGUOUS |
| 1111 | BVM3 | -1.5654773525078942 | 1.5702863146063817 | -1.9016561371104073 | 2.0680239822232274 | AMBIGUOUS |
| 1111 | BVM4 | -1.5654773525078942 | 1.5702863146063817 | -1.9016561371104073 | 2.0680239822232274 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.234078e-05 | -9.108553e-07 | 0.06520370337559148 | 0.06524775214193124 | 1 |
| 0011 | 4.176331e-05 | -4.660496e-05 | 0.020291213375573016 | 0.11579379107107045 | 2 |
| 1111 | 0.0001024256 | -2.171299e-05 | 0.14176427563004104 | 0.15767211864258063 | 4 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.06524775214193124, 0.11579379107107045, 0.15767211864258063]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [2.234078e-05, 4.176331e-05, 0.0001024256]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": false, "values": [0.06520370337559148, 0.020291213375573016, 0.14176427563004104]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
