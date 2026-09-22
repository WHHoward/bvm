# U205_3bvm_rloop_shots_tunning_qb_L1_sweep_90_qb_l1_1p5p review summary

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
| 000 | BVM1 | -1.0748706502580585 | 0.11049427417120693 | 2.007551485961525 | -0.11131026156443906 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0748706502580585 | 0.11049427417120693 | 2.007551485961525 | -0.11131026156443906 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0748706502580585 | 0.11049427417120693 | 2.007551485961525 | -0.11131026156443906 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0748706502580585 | 0.11049427417120693 | 2.007551485961525 | -0.11131026156443906 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0748706502580585 | 0.11049427417120693 | 2.007551485961525 | -0.11131026156443906 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0748706502580585 | 0.11049427417120693 | 2.007551485961525 | -0.11131026156443906 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0748706502580585 | 0.11049427417120693 | 2.007551485961525 | -0.11131026156443906 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02634439251868924 | 0.03655217676575136 | -0.005941874729898512 | 0.03407583725970163 | AMBIGUOUS |
| 001 | BVM3 | -2.39268701542536 | 2.424388483751051 | -2.694697191351843 | 2.6954800108549346 | AMBIGUOUS |
| 011 | BVM2 | -2.2854038513859756 | 2.3263875224716832 | -3.106618831963425 | 3.1396383419503318 | AMBIGUOUS |
| 011 | BVM3 | -2.2854038513859756 | 2.3263875224716832 | -3.106618831963425 | 3.1396383419503318 | AMBIGUOUS |
| 111 | BVM1 | -2.8667220556774162 | 2.8675623619459527 | -2.981823849535639 | 3.3175093493075325 | AMBIGUOUS |
| 111 | BVM2 | -2.8667220556774162 | 2.8675623619459527 | -2.981823849535639 | 3.3175093493075325 | AMBIGUOUS |
| 111 | BVM3 | -2.8667220556774162 | 2.8675623619459527 | -2.981823849535639 | 3.3175093493075325 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 1.957585e-06 | -3.261541e-06 | -0.0011899589484812483 | 0.005701612653648761 | 9 |
| 001 | 2.974235e-05 | -3.36978e-05 | 0.04677324668205169 | 0.08503850683171509 | 2 |
| 011 | 8.006765e-05 | -1.107091e-05 | 0.12295609711868895 | 0.12933260171684755 | 7 |
| 111 | 9.670703e-05 | -5.774909e-06 | 0.20950090432507476 | 0.21077226232249935 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005701612653648761, 0.08503850683171509, 0.12933260171684755, 0.21077226232249935]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [1.957585e-06, 2.974235e-05, 8.006765e-05, 9.670703e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011899589484812483, 0.04677324668205169, 0.12295609711868895, 0.20950090432507476]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
