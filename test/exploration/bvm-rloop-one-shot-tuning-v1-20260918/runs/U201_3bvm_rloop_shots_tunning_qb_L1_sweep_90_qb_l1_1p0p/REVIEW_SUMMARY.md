# U201_3bvm_rloop_shots_tunning_qb_L1_sweep_90_qb_l1_1p0p review summary

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
| 000 | BVM1 | -1.074866533010399 | 0.1101998375264869 | 2.0076352014615915 | -0.11129291367564202 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.074866533010399 | 0.1101998375264869 | 2.0076352014615915 | -0.11129291367564202 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.074866533010399 | 0.1101998375264869 | 2.0076352014615915 | -0.11129291367564202 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.074866533010399 | 0.1101998375264869 | 2.0076352014615915 | -0.11129291367564202 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.074866533010399 | 0.1101998375264869 | 2.0076352014615915 | -0.11129291367564202 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.074866533010399 | 0.1101998375264869 | 2.0076352014615915 | -0.11129291367564202 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.074866533010399 | 0.1101998375264869 | 2.0076352014615915 | -0.11129291367564202 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.026615672119189363 | 0.0365364840883625 | -0.0067796822658285575 | 0.03380414385634945 | AMBIGUOUS |
| 001 | BVM3 | -2.403203480684549 | 2.427326659070965 | -2.7590285424482572 | 2.7596242116537675 | AMBIGUOUS |
| 011 | BVM2 | -2.2897148654140116 | 2.318371078974076 | -3.1108373610540303 | 3.1410636381276964 | AMBIGUOUS |
| 011 | BVM3 | -2.2897148654140116 | 2.318371078974076 | -3.1108373610540303 | 3.1410636381276964 | AMBIGUOUS |
| 111 | BVM1 | -2.8869437893663488 | 2.887865949022118 | -2.987290153380085 | 3.3183515176889036 | AMBIGUOUS |
| 111 | BVM2 | -2.8869437893663488 | 2.887865949022118 | -2.987290153380085 | 3.3183515176889036 | AMBIGUOUS |
| 111 | BVM3 | -2.8869437893663488 | 2.887865949022118 | -2.987290153380085 | 3.3183515176889036 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.119611e-06 | -3.464892e-06 | -0.0012207018464280475 | 0.006011341458436174 | 9 |
| 001 | 2.517673e-05 | -4.326474e-05 | 0.019436325848361895 | 0.0838905682474349 | 2 |
| 011 | 6.922535e-05 | -1.599208e-05 | 0.11813553649451645 | 0.12987283933607438 | 7 |
| 111 | 9.129443e-05 | -3.387477e-06 | 0.21016956726012506 | 0.21078250093524883 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.006011341458436174, 0.0838905682474349, 0.12987283933607438, 0.21078250093524883]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.119611e-06, 2.517673e-05, 6.922535e-05, 9.129443e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0012207018464280475, 0.019436325848361895, 0.11813553649451645, 0.21016956726012506]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
