# U169_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=30, RSH_JS2=30
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0765913268337828 | 0.11243389546266784 | 2.0092550804723808 | -0.11269204478036293 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0765913268337828 | 0.11243389546266784 | 2.0092550804723808 | -0.11269204478036293 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0765913268337828 | 0.11243389546266784 | 2.0092550804723808 | -0.11269204478036293 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0765913268337828 | 0.11243389546266784 | 2.0092550804723808 | -0.11269204478036293 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0765913268337828 | 0.11243389546266784 | 2.0092550804723808 | -0.11269204478036293 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0765913268337828 | 0.11243389546266784 | 2.0092550804723808 | -0.11269204478036293 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0765913268337828 | 0.11243389546266784 | 2.0092550804723808 | -0.11269204478036293 | REVIEW_REQUIRED |

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
| 000 | BVM1 | 0.0012403103870094491 | 0.0036472424223768013 | -0.0011293475606857784 | 0.0033702809904082812 | AMBIGUOUS |
| 001 | BVM3 | -1.0427073975541978 | 1.0515554415449544 | -1.013297442099144 | 1.013297442099144 | AMBIGUOUS |
| 011 | BVM2 | -1.2289856852027572 | 1.2365323988013228 | -1.9183713372621505 | 1.9183713372621505 | AMBIGUOUS |
| 011 | BVM3 | -1.2289856852027572 | 1.2365323988013228 | -1.9183713372621505 | 1.9183713372621505 | AMBIGUOUS |
| 111 | BVM1 | -2.177931117893874 | 2.184443403939814 | -2.0563634475711163 | 2.0563634475711163 | AMBIGUOUS |
| 111 | BVM2 | -2.177931117893874 | 2.184443403939814 | -2.0563634475711163 | 2.0563634475711163 | AMBIGUOUS |
| 111 | BVM3 | -2.177931117893874 | 2.184443403939814 | -2.0563634475711163 | 2.0563634475711163 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 0.0 | -1.037641e-06 | -0.0010612972667618315 | 0.0010612972667618315 | 0 |
| 001 | 2.231059e-05 | -1.037641e-06 | 0.051472800826306966 | 0.051522980921821095 | 1 |
| 011 | 4.461535e-05 | -2.437687e-05 | 0.06139272645274939 | 0.08605659562643936 | 3 |
| 111 | 7.114506e-05 | -1.214958e-05 | 0.14110071194172666 | 0.1445198500638915 | 4 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.0010612972667618315, 0.051522980921821095, 0.08605659562643936, 0.1445198500638915]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.0, 2.231059e-05, 4.461535e-05, 7.114506e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0010612972667618315, 0.051472800826306966, 0.06139272645274939, 0.14110071194172666]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
