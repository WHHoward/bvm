# U206_3bvm_rloop_shots_tunning_qb_L1_sweep_90_qb_l1_1p6p review summary

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
| 000 | BVM1 | -1.074870637105494 | 0.1104944333261499 | 2.007542891594598 | -0.11131248973364237 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.074870637105494 | 0.1104944333261499 | 2.007542891594598 | -0.11131248973364237 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.074870637105494 | 0.1104944333261499 | 2.007542891594598 | -0.11131248973364237 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.074870637105494 | 0.1104944333261499 | 2.007542891594598 | -0.11131248973364237 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.074870637105494 | 0.1104944333261499 | 2.007542891594598 | -0.11131248973364237 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.074870637105494 | 0.1104944333261499 | 2.007542891594598 | -0.11131248973364237 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.074870637105494 | 0.1104944333261499 | 2.007542891594598 | -0.11131248973364237 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02632110815051489 | 0.03658181141615507 | -0.005818609226473838 | 0.03417931980369998 | AMBIGUOUS |
| 001 | BVM3 | -2.392104269601229 | 2.424110201333055 | -2.6849955198238136 | 2.685815374682163 | AMBIGUOUS |
| 011 | BVM2 | -2.284650809772736 | 2.3275177613000504 | -3.1063168513744026 | 3.1397426361845393 | AMBIGUOUS |
| 011 | BVM3 | -2.284650809772736 | 2.3275177613000504 | -3.1063168513744026 | 3.1397426361845393 | AMBIGUOUS |
| 111 | BVM1 | -2.864003450516992 | 2.8648442342503575 | -2.98137226330011 | 3.317965073571582 | AMBIGUOUS |
| 111 | BVM2 | -2.864003450516992 | 2.8648442342503575 | -2.98137226330011 | 3.317965073571582 | AMBIGUOUS |
| 111 | BVM3 | -2.864003450516992 | 2.8648442342503575 | -2.98137226330011 | 3.317965073571582 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 1.924801e-06 | -3.222166e-06 | -0.0011801431830513363 | 0.005637705244391574 | 9 |
| 001 | 3.185951e-05 | -2.773638e-05 | 0.05314086719601864 | 0.08357304467529914 | 2 |
| 011 | 8.233451e-05 | -9.272798e-06 | 0.12398470849278809 | 0.12929866165156234 | 7 |
| 111 | 9.758951e-05 | -5.991411e-06 | 0.20951535396280987 | 0.21084034049528685 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005637705244391574, 0.08357304467529914, 0.12929866165156234, 0.21084034049528685]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [1.924801e-06, 3.185951e-05, 8.233451e-05, 9.758951e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011801431830513363, 0.05314086719601864, 0.12398470849278809, 0.20951535396280987]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
