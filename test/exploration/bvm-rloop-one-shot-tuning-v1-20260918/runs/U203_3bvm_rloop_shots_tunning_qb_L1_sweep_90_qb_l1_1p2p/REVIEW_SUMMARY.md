# U203_3bvm_rloop_shots_tunning_qb_L1_sweep_90_qb_l1_1p2p review summary

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
| 000 | BVM1 | -1.0748690752750654 | 0.11043459106754747 | 2.0075872958237206 | -0.11130134888762594 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0748690752750654 | 0.11043459106754747 | 2.0075872958237206 | -0.11130134888762594 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0748690752750654 | 0.11043459106754747 | 2.0075872958237206 | -0.11130134888762594 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0748690752750654 | 0.11043459106754747 | 2.0075872958237206 | -0.11130134888762594 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0748690752750654 | 0.11043459106754747 | 2.0075872958237206 | -0.11130134888762594 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0748690752750654 | 0.11043459106754747 | 2.0075872958237206 | -0.11130134888762594 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0748690752750654 | 0.11043459106754747 | 2.0075872958237206 | -0.11130134888762594 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.026505950701421813 | 0.036554452681437574 | -0.0064160927983351185 | 0.03387893076410834 | AMBIGUOUS |
| 001 | BVM3 | -2.397039123259703 | 2.425178815367457 | -2.7357001201856654 | 2.7363651968618576 | AMBIGUOUS |
| 011 | BVM2 | -2.287833367507768 | 2.322092853656303 | -3.108627208190302 | 3.1400186108558605 | AMBIGUOUS |
| 011 | BVM3 | -2.287833367507768 | 2.322092853656303 | -3.108627208190302 | 3.1400186108558605 | AMBIGUOUS |
| 111 | BVM1 | -2.87750243166324 | 2.8783714972299936 | -2.984378127217321 | 3.3173073339382664 | AMBIGUOUS |
| 111 | BVM2 | -2.87750243166324 | 2.8783714972299936 | -2.984378127217321 | 3.3173073339382664 | AMBIGUOUS |
| 111 | BVM3 | -2.87750243166324 | 2.8783714972299936 | -2.984378127217321 | 3.3173073339382664 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.058638e-06 | -3.388203e-06 | -0.001215471025261994 | 0.005898401344526211 | 9 |
| 001 | 2.597484e-05 | -4.516317e-05 | 0.028508860127721455 | 0.08695907708151601 | 2 |
| 011 | 7.268741e-05 | -1.455681e-05 | 0.11995130791233682 | 0.129552364360466 | 7 |
| 111 | 9.363978e-05 | -4.695084e-06 | 0.2097469158701958 | 0.21072823257606296 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005898401344526211, 0.08695907708151601, 0.129552364360466, 0.21072823257606296]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.058638e-06, 2.597484e-05, 7.268741e-05, 9.363978e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.001215471025261994, 0.028508860127721455, 0.11995130791233682, 0.2097469158701958]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
