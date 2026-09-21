# U131_QB_L1_screen_qb_l1_1p2p review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780297523554163 | 0.11290722226342315 | 2.0094990650001407 | -0.11127477001212954 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780297523554163 | 0.11290722226342315 | 2.0094990650001407 | -0.11127477001212954 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780297523554163 | 0.11290722226342315 | 2.0094990650001407 | -0.11127477001212954 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780297523554163 | 0.11290722226342315 | 2.0094990650001407 | -0.11127477001212954 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0019086179085466286 | 0.002338670480275237 | -0.002467490491213815 | 0.003456527054069781 | AMBIGUOUS |
| 0001 | BVM4 | -1.1430303657912992 | 1.1530100969204051 | -1.3632129853328845 | 1.3792604190898972 | AMBIGUOUS |
| 0011 | BVM3 | -1.4512953468967882 | 1.4601064828562416 | -1.9460614644021534 | 1.9507040140921441 | AMBIGUOUS |
| 0011 | BVM4 | -1.4512953468967882 | 1.4601064828562416 | -1.9460614644021534 | 1.9507040140921441 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.427165e-07 | -0.0016072781387704604 | 0.0016072781387704604 | 0 |
| 0001 | 2.092416e-05 | -8.427165e-07 | 0.06764826010576064 | 0.0676890136943923 | 1 |
| 0011 | 3.671817e-05 | -4.500798e-05 | 0.022437039968116582 | 0.10586117069160175 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0016072781387704604, 0.0676890136943923, 0.10586117069160175]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.092416e-05, 3.671817e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0016072781387704604, 0.06764826010576064, 0.022437039968116582]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
