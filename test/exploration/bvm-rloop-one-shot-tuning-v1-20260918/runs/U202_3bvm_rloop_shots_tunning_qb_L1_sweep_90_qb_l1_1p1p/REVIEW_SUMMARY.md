# U202_3bvm_rloop_shots_tunning_qb_L1_sweep_90_qb_l1_1p1p review summary

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
| 000 | BVM1 | -1.0748679629618583 | 0.11035342204657056 | 2.007606871881721 | -0.11129705170416242 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0748679629618583 | 0.11035342204657056 | 2.007606871881721 | -0.11129705170416242 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0748679629618583 | 0.11035342204657056 | 2.007606871881721 | -0.11129705170416242 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0748679629618583 | 0.11035342204657056 | 2.007606871881721 | -0.11129705170416242 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0748679629618583 | 0.11035342204657056 | 2.007606871881721 | -0.11129705170416242 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0748679629618583 | 0.11035342204657056 | 2.007606871881721 | -0.11129705170416242 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0748679629618583 | 0.11035342204657056 | 2.007606871881721 | -0.11129705170416242 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02656577704453006 | 0.03655410254056278 | -0.00659455323602406 | 0.033839985549533755 | AMBIGUOUS |
| 001 | BVM3 | -2.4000158140758447 | 2.426060947555038 | -2.7491963479513983 | 2.749825551103417 | AMBIGUOUS |
| 011 | BVM2 | -2.288734677865991 | 2.3203234804074673 | -3.1096456884176296 | 3.1404510189207473 | AMBIGUOUS |
| 011 | BVM3 | -2.288734677865991 | 2.3203234804074673 | -3.1096456884176296 | 3.1404510189207473 | AMBIGUOUS |
| 111 | BVM1 | -2.882002235284771 | 2.8828951104310114 | -2.9856878609905073 | 3.3176943350978885 | AMBIGUOUS |
| 111 | BVM2 | -2.882002235284771 | 2.8828951104310114 | -2.9856878609905073 | 3.3176943350978885 | AMBIGUOUS |
| 111 | BVM3 | -2.882002235284771 | 2.8828951104310114 | -2.9856878609905073 | 3.3176943350978885 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.090397e-06 | -3.428721e-06 | -0.001220309821285029 | 0.005958589585530379 | 9 |
| 001 | 2.559433e-05 | -4.530774e-05 | 0.023684322397260624 | 0.08577910356364374 | 2 |
| 011 | 7.079783e-05 | -1.551614e-05 | 0.11901556681260028 | 0.12969394559112588 | 7 |
| 111 | 9.249859e-05 | -4.124343e-06 | 0.2099302766611833 | 0.21075193310212184 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005958589585530379, 0.08577910356364374, 0.12969394559112588, 0.21075193310212184]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.090397e-06, 2.559433e-05, 7.079783e-05, 9.249859e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.001220309821285029, 0.023684322397260624, 0.11901556681260028, 0.2099302766611833]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
