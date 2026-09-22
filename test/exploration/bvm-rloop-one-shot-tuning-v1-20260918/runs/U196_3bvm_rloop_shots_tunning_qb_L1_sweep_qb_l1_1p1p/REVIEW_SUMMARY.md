# U196_3bvm_rloop_shots_tunning_qb_L1_sweep_qb_l1_1p1p review summary

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
| 000 | BVM1 | -1.0750939573062201 | 0.11105688689503668 | 2.00710235071212 | -0.1110755080233785 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0750939573062201 | 0.11105688689503668 | 2.00710235071212 | -0.1110755080233785 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0750939573062201 | 0.11105688689503668 | 2.00710235071212 | -0.1110755080233785 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0750939573062201 | 0.11105688689503668 | 2.00710235071212 | -0.1110755080233785 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0750939573062201 | 0.11105688689503668 | 2.00710235071212 | -0.1110755080233785 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0750939573062201 | 0.11105688689503668 | 2.00710235071212 | -0.1110755080233785 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0750939573062201 | 0.11105688689503668 | 2.00710235071212 | -0.1110755080233785 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02840818649675046 | 0.039346253200189744 | -0.0086192269290733 | 0.0401246641113579 | AMBIGUOUS |
| 001 | BVM3 | -2.3768613322505576 | 2.4204294727106515 | -3.0535227216801912 | 3.056275131350528 | AMBIGUOUS |
| 011 | BVM2 | -2.4621827056926917 | 2.4625484278364227 | -3.0141732535501515 | 3.16658671156256 | AMBIGUOUS |
| 011 | BVM3 | -2.4621827056926917 | 2.4625484278364227 | -3.0141732535501515 | 3.16658671156256 | AMBIGUOUS |
| 111 | BVM1 | -3.1878305701270175 | 3.188193284242324 | -2.8941449616679678 | 3.307610437058529 | AMBIGUOUS |
| 111 | BVM2 | -3.1878305701270175 | 3.188193284242324 | -2.8941449616679678 | 3.307610437058529 | AMBIGUOUS |
| 111 | BVM3 | -3.1878305701270175 | 3.188193284242324 | -2.8941449616679678 | 3.307610437058529 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.501159e-06 | -3.946365e-06 | -0.0011386879909512043 | 0.006811640903171841 | 9 |
| 001 | 2.621473e-05 | -4.309544e-05 | 0.022533564582602902 | 0.08272740146189914 | 4 |
| 011 | 7.864233e-05 | -1.308355e-05 | 0.12135706208393583 | 0.13098143820934288 | 8 |
| 111 | 9.888383e-05 | -3.85882e-06 | 0.21340151769776006 | 0.21425021682399664 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.006811640903171841, 0.08272740146189914, 0.13098143820934288, 0.21425021682399664]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.501159e-06, 2.621473e-05, 7.864233e-05, 9.888383e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011386879909512043, 0.022533564582602902, 0.12135706208393583, 0.21340151769776006]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
