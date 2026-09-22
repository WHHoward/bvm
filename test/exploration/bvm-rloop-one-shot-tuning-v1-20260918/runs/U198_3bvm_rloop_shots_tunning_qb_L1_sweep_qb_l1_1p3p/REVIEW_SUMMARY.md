# U198_3bvm_rloop_shots_tunning_qb_L1_sweep_qb_l1_1p3p review summary

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
| 000 | BVM1 | -1.075097400291735 | 0.11125376155964145 | 2.007055877468737 | -0.11108410239030553 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.075097400291735 | 0.11125376155964145 | 2.007055877468737 | -0.11108410239030553 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.075097400291735 | 0.11125376155964145 | 2.007055877468737 | -0.11108410239030553 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.075097400291735 | 0.11125376155964145 | 2.007055877468737 | -0.11108410239030553 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.075097400291735 | 0.11125376155964145 | 2.007055877468737 | -0.11108410239030553 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.075097400291735 | 0.11125376155964145 | 2.007055877468737 | -0.11108410239030553 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.075097400291735 | 0.11125376155964145 | 2.007055877468737 | -0.11108410239030553 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.028196255774529288 | 0.039347510524240174 | -0.008267510420334523 | 0.04033409610097252 | AMBIGUOUS |
| 001 | BVM3 | -2.3622871798862524 | 2.4182571191459075 | -3.0412720564145905 | 3.0441264844034492 | AMBIGUOUS |
| 011 | BVM2 | -2.459968526208903 | 2.4602471428522796 | -3.0110708144134724 | 3.16604045996688 | AMBIGUOUS |
| 011 | BVM3 | -2.459968526208903 | 2.4602471428522796 | -3.0110708144134724 | 3.16604045996688 | AMBIGUOUS |
| 111 | BVM1 | -3.180179657787209 | 3.1804552664021615 | -2.8935253396435225 | 3.308512495444985 | AMBIGUOUS |
| 111 | BVM2 | -3.180179657787209 | 3.1804552664021615 | -2.8935253396435225 | 3.308512495444985 | AMBIGUOUS |
| 111 | BVM3 | -3.180179657787209 | 3.1804552664021615 | -2.8935253396435225 | 3.308512495444985 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.424729e-06 | -3.852192e-06 | -0.0011277347443826237 | 0.00666209464330232 | 9 |
| 001 | 2.687896e-05 | -4.002385e-05 | 0.030527342320590643 | 0.0849102746866342 | 2 |
| 011 | 8.307718e-05 | -1.11614e-05 | 0.12299280456502128 | 0.13114413135382608 | 8 |
| 111 | 0.0001010471 | -4.622048e-06 | 0.21321708561180266 | 0.21426875792198527 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.00666209464330232, 0.0849102746866342, 0.13114413135382608, 0.21426875792198527]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.424729e-06, 2.687896e-05, 8.307718e-05, 0.0001010471]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011277347443826237, 0.030527342320590643, 0.12299280456502128, 0.21321708561180266]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
