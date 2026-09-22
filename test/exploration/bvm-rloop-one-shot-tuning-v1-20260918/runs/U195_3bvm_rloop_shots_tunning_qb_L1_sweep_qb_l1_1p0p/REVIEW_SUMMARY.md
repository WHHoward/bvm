# U195_3bvm_rloop_shots_tunning_qb_L1_sweep_qb_l1_1p0p review summary

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
| 000 | BVM1 | -1.0750915225599487 | 0.1108302502560738 | 2.0071416619830633 | -0.11107184745968729 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0750915225599487 | 0.1108302502560738 | 2.0071416619830633 | -0.11107184745968729 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0750915225599487 | 0.1108302502560738 | 2.0071416619830633 | -0.11107184745968729 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0750915225599487 | 0.1108302502560738 | 2.0071416619830633 | -0.11107184745968729 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0750915225599487 | 0.1108302502560738 | 2.0071416619830633 | -0.11107184745968729 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0750915225599487 | 0.1108302502560738 | 2.0071416619830633 | -0.11107184745968729 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0750915225599487 | 0.1108302502560738 | 2.0071416619830633 | -0.11107184745968729 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.028514915801587885 | 0.039332136156737495 | -0.008818043283983697 | 0.040031940441512565 | AMBIGUOUS |
| 001 | BVM3 | -2.3821642794614135 | 2.4219767134054138 | -3.0546526899451556 | 3.0573525784842723 | AMBIGUOUS |
| 011 | BVM2 | -2.46331579339454 | 2.463734370894872 | -3.0159096021482954 | 3.167051428080894 | AMBIGUOUS |
| 011 | BVM3 | -2.46331579339454 | 2.463734370894872 | -3.0159096021482954 | 3.167051428080894 | AMBIGUOUS |
| 111 | BVM1 | -3.1922279257116806 | 3.1926434951835874 | -2.8947178876321096 | 3.3073494070363645 | AMBIGUOUS |
| 111 | BVM2 | -3.1922279257116806 | 3.1926434951835874 | -2.8947178876321096 | 3.3073494070363645 | AMBIGUOUS |
| 111 | BVM3 | -3.1922279257116806 | 3.1926434951835874 | -2.8947178876321096 | 3.3073494070363645 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.536693e-06 | -3.987922e-06 | -0.0011375192108761816 | 0.006876692293606378 | 9 |
| 001 | 2.584127e-05 | -4.328264e-05 | 0.018310582877159812 | 0.08076660050396843 | 4 |
| 011 | 7.66606e-05 | -1.343778e-05 | 0.12066487683298623 | 0.13108863794940637 | 8 |
| 111 | 9.769871e-05 | -3.806762e-06 | 0.21360799216881726 | 0.21439003440183518 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.006876692293606378, 0.08076660050396843, 0.13108863794940637, 0.21439003440183518]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.536693e-06, 2.584127e-05, 7.66606e-05, 9.769871e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011375192108761816, 0.018310582877159812, 0.12066487683298623, 0.21360799216881726]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
