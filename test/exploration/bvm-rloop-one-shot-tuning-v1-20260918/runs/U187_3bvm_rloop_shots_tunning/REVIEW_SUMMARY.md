# U187_3bvm_rloop_shots_tunning review summary

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
| 000 | BVM1 | -1.0748673882772322 | 0.11046292064741782 | 2.0076425225889736 | -0.11133349818613046 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0748673882772322 | 0.11046292064741782 | 2.0076425225889736 | -0.11133349818613046 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0748673882772322 | 0.11046292064741782 | 2.0076425225889736 | -0.11133349818613046 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0748673882772322 | 0.11046292064741782 | 2.0076425225889736 | -0.11133349818613046 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0748673882772322 | 0.11046292064741782 | 2.0076425225889736 | -0.11133349818613046 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0748673882772322 | 0.11046292064741782 | 2.0076425225889736 | -0.11133349818613046 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0748673882772322 | 0.11046292064741782 | 2.0076425225889736 | -0.11133349818613046 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.026458060979045468 | 0.03647446140703959 | -0.006422570404518964 | 0.033804509912718564 | AMBIGUOUS |
| 001 | BVM3 | -2.3900035835073594 | 2.4217482305691114 | -2.674424687236064 | 2.6750436408097484 | AMBIGUOUS |
| 011 | BVM2 | -2.278588757145309 | 2.3322668333934526 | -3.110017442533704 | 3.1407789417654937 | AMBIGUOUS |
| 011 | BVM3 | -2.278588757145309 | 2.3322668333934526 | -3.110017442533704 | 3.1407789417654937 | AMBIGUOUS |
| 111 | BVM1 | -2.8380597623985246 | 2.8389623459962934 | -2.9586881479936373 | 3.301180497780145 | AMBIGUOUS |
| 111 | BVM2 | -2.8380597623985246 | 2.8389623459962934 | -2.9586881479936373 | 3.301180497780145 | AMBIGUOUS |
| 111 | BVM3 | -2.8380597623985246 | 2.8389623459962934 | -2.9586881479936373 | 3.301180497780145 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.043767e-06 | -3.397196e-06 | -0.001220204721399847 | 0.005921702038509241 | 9 |
| 001 | 3.17931e-05 | -2.687228e-05 | 0.05531438957759054 | 0.08166251365569085 | 2 |
| 011 | 8.280034e-05 | -3.963384e-06 | 0.12963999504906074 | 0.13086264158927735 | 3 |
| 111 | 0.0001055532 | -3.033405e-06 | 0.23050534254046076 | 0.23065203735363127 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005921702038509241, 0.08166251365569085, 0.13086264158927735, 0.23065203735363127]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.043767e-06, 3.17931e-05, 8.280034e-05, 0.0001055532]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.001220204721399847, 0.05531438957759054, 0.12963999504906074, 0.23050534254046076]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
