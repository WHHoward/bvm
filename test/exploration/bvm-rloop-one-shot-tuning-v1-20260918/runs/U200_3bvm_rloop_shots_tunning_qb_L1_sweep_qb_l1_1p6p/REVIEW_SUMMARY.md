# U200_3bvm_rloop_shots_tunning_qb_L1_sweep_qb_l1_1p6p review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.87, JS2_AREA=0.87, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0751004152800052 | 0.11130660100074785 | 2.0070130647890454 | -0.11109174182757386 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0751004152800052 | 0.11130660100074785 | 2.0070130647890454 | -0.11109174182757386 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0751004152800052 | 0.11130660100074785 | 2.0070130647890454 | -0.11109174182757386 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0751004152800052 | 0.11130660100074785 | 2.0070130647890454 | -0.11109174182757386 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0751004152800052 | 0.11130660100074785 | 2.0070130647890454 | -0.11109174182757386 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0751004152800052 | 0.11130660100074785 | 2.0070130647890454 | -0.11109174182757386 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0751004152800052 | 0.11130660100074785 | 2.0070130647890454 | -0.11109174182757386 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.027903299270780037 | 0.03930659178837125 | -0.0077672546032080845 | 0.040745081910518725 | AMBIGUOUS |
| 001 | BVM3 | -2.3481585340386495 | 2.4177953947405033 | -3.0104143161887125 | 3.0135531858918654 | AMBIGUOUS |
| 011 | BVM2 | -2.4566258108546384 | 2.4568442350985373 | -3.0077484708919235 | 3.1660633782786856 | AMBIGUOUS |
| 011 | BVM3 | -2.4566258108546384 | 2.4568442350985373 | -3.0077484708919235 | 3.1660633782786856 | AMBIGUOUS |
| 111 | BVM1 | -3.1711025898333443 | 3.1713180060488186 | -2.8935309259820245 | 3.310555074069133 | AMBIGUOUS |
| 111 | BVM2 | -3.1711025898333443 | 3.1713180060488186 | -2.8935309259820245 | 3.310555074069133 | AMBIGUOUS |
| 111 | BVM3 | -3.1711025898333443 | 3.1713180060488186 | -2.8935309259820245 | 3.310555074069133 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.310711e-06 | -3.713574e-06 | -0.0011005831963729498 | 0.0064348451123719215 | 9 |
| 001 | 3.108937e-05 | -2.709334e-05 | 0.046304611336452146 | 0.08565504471808016 | 2 |
| 011 | 8.981236e-05 | -9.711372e-06 | 0.12582262662527027 | 0.13127340210749833 | 8 |
| 111 | 0.0001036471 | -5.368165e-06 | 0.21338224922024748 | 0.21461453343034706 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.0064348451123719215, 0.08565504471808016, 0.13127340210749833, 0.21461453343034706]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.310711e-06, 3.108937e-05, 8.981236e-05, 0.0001036471]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011005831963729498, 0.046304611336452146, 0.12582262662527027, 0.21338224922024748]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
