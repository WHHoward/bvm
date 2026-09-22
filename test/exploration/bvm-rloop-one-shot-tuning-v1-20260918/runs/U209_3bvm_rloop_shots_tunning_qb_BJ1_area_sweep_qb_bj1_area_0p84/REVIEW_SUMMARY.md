# U209_3bvm_rloop_shots_tunning_qb_BJ1_area_sweep_qb_bj1_area_0p84 review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0748711417062409 | 0.11047851783184075 | 2.007552440891184 | -0.11130071226785362 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0748711417062409 | 0.11047851783184075 | 2.007552440891184 | -0.11130071226785362 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0748711417062409 | 0.11047851783184075 | 2.007552440891184 | -0.11130071226785362 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0748711417062409 | 0.11047851783184075 | 2.007552440891184 | -0.11130071226785362 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0748711417062409 | 0.11047851783184075 | 2.007552440891184 | -0.11130071226785362 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0748711417062409 | 0.11047851783184075 | 2.007552440891184 | -0.11130071226785362 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0748711417062409 | 0.11047851783184075 | 2.007552440891184 | -0.11130071226785362 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.026424033652212416 | 0.03658249578241037 | -0.006139099535377988 | 0.03403154443903916 | AMBIGUOUS |
| 001 | BVM3 | -2.3935237884541603 | 2.4243280207881703 | -2.720109508861809 | 2.7208574097703866 | AMBIGUOUS |
| 011 | BVM2 | -2.2882555259943187 | 2.3243996931479596 | -3.107398738931058 | 3.1405631435781554 | AMBIGUOUS |
| 011 | BVM3 | -2.2882555259943187 | 2.3243996931479596 | -3.107398738931058 | 3.1405631435781554 | AMBIGUOUS |
| 111 | BVM1 | -2.8746030264874634 | 2.8754437306433576 | -2.9824398269118872 | 3.3183104397980916 | AMBIGUOUS |
| 111 | BVM2 | -2.8746030264874634 | 2.8754437306433576 | -2.9824398269118872 | 3.3183104397980916 | AMBIGUOUS |
| 111 | BVM3 | -2.8746030264874634 | 2.8754437306433576 | -2.9824398269118872 | 3.3183104397980916 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 1.991092e-06 | -3.306576e-06 | -0.0012095168484736079 | 0.005763676759874765 | 9 |
| 001 | 2.631423e-05 | -4.203897e-05 | 0.034732086221271725 | 0.08650747384419435 | 2 |
| 011 | 7.609974e-05 | -1.335217e-05 | 0.1207430939320809 | 0.128977350763919 | 8 |
| 111 | 9.462142e-05 | -5.81619e-06 | 0.20856788864692152 | 0.20986976737504262 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005763676759874765, 0.08650747384419435, 0.128977350763919, 0.20986976737504262]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [1.991092e-06, 2.631423e-05, 7.609974e-05, 9.462142e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0012095168484736079, 0.034732086221271725, 0.1207430939320809, 0.20856788864692152]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
