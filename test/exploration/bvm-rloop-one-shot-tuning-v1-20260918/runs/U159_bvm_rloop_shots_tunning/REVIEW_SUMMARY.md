# U159_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 0001, 0011, 0111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0748341580476921 | 0.11256090110725513 | 2.006106359078251 | -0.11103365027334526 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0748341580476921 | 0.11256090110725513 | 2.006106359078251 | -0.11103365027334526 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0748341580476921 | 0.11256090110725513 | 2.006106359078251 | -0.11103365027334526 | REVIEW_REQUIRED |
| 0111 | BVM2 | -1.0748341580476921 | 0.11256090110725513 | 2.006106359078251 | -0.11103365027334526 | REVIEW_REQUIRED |
| 0111 | BVM3 | -1.0748341580476921 | 0.11256090110725513 | 2.006106359078251 | -0.11103365027334526 | REVIEW_REQUIRED |
| 0111 | BVM4 | -1.0748341580476921 | 0.11256090110725513 | 2.006106359078251 | -0.11103365027334526 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.4031538243423043 | 2.430452414406807 | -2.629931999796055 | 2.6317760644596837 | AMBIGUOUS |
| 0011 | BVM3 | -2.2490425013969912 | 2.351940246472445 | -3.1022274765201163 | 3.103957236103616 | AMBIGUOUS |
| 0011 | BVM4 | -2.2490425013969912 | 2.351940246472445 | -3.1022274765201163 | 3.103957236103616 | AMBIGUOUS |
| 0111 | BVM2 | -2.538585131616922 | 2.540214734994734 | -3.0408891614524998 | 3.23297806874939 | AMBIGUOUS |
| 0111 | BVM3 | -2.538585131616922 | 2.540214734994734 | -3.0408891614524998 | 3.23297806874939 | AMBIGUOUS |
| 0111 | BVM4 | -2.538585131616922 | 2.540214734994734 | -3.0408891614524998 | 3.23297806874939 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.12331e-05 | -4.69447e-05 | 0.021375485231925832 | 0.07611951241258505 | 2 |
| 0011 | 5.892609e-05 | -1.949044e-05 | 0.05742462289745828 | 0.08533322859409931 | 5 |
| 0111 | 7.873705e-05 | -1.155286e-05 | 0.1505212874390474 | 0.1577631374515539 | 5 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.07611951241258505, 0.08533322859409931, 0.1577631374515539]}, "peak_positive_a": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [2.12331e-05, 5.892609e-05, 7.873705e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.021375485231925832, 0.05742462289745828, 0.1505212874390474]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
