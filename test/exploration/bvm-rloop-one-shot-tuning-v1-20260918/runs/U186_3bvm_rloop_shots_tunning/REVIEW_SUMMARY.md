# U186_3bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.74, JS2_AREA=0.74, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.076637000417319 | 0.11546229571982036 | 2.00598380977207 | -0.10925748110843966 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.076637000417319 | 0.11546229571982036 | 2.00598380977207 | -0.10925748110843966 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.076637000417319 | 0.11546229571982036 | 2.00598380977207 | -0.10925748110843966 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.076637000417319 | 0.11546229571982036 | 2.00598380977207 | -0.10925748110843966 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.076637000417319 | 0.11546229571982036 | 2.00598380977207 | -0.10925748110843966 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.076637000417319 | 0.11546229571982036 | 2.00598380977207 | -0.10925748110843966 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.076637000417319 | 0.11546229571982036 | 2.00598380977207 | -0.10925748110843966 | REVIEW_REQUIRED |

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
| 000 | BVM1 | 0.005149824240107382 | 0.0655554897496559 | 0.005195804103166636 | 0.06132085577035929 | AMBIGUOUS |
| 001 | BVM3 | -3.0495335348625816 | 3.0703118811339896 | -2.976717808820376 | 3.2245160232421144 | AMBIGUOUS |
| 011 | BVM2 | -3.2553463410712973 | 3.2733795192222788 | -2.9804181612472624 | 3.181865808916302 | AMBIGUOUS |
| 011 | BVM3 | -3.2553463410712973 | 3.2733795192222788 | -2.9804181612472624 | 3.181865808916302 | AMBIGUOUS |
| 111 | BVM1 | -7.359562393800703 | 7.375224433863019 | -7.369680717054252 | 7.39283989395036 | AMBIGUOUS |
| 111 | BVM2 | -7.359562393800703 | 7.375224433863019 | -7.369680717054252 | 7.39283989395036 | AMBIGUOUS |
| 111 | BVM3 | -7.359562393800703 | 7.375224433863019 | -7.369680717054252 | 7.39283989395036 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 3.624938e-06 | -4.146357e-06 | -0.0008341983238490878 | 0.00886805542221687 | 10 |
| 001 | 3.256158e-05 | -4.020046e-05 | 0.022929703779565887 | 0.08712866552322712 | 4 |
| 011 | 7.741955e-05 | -4.146357e-06 | 0.1553947661562799 | 0.15559528308872156 | 1 |
| 111 | 0.000315262 | -4.146357e-06 | 0.7282176511939945 | 0.7284181681264361 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.00886805542221687, 0.08712866552322712, 0.15559528308872156, 0.7284181681264361]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [3.624938e-06, 3.256158e-05, 7.741955e-05, 0.000315262]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0008341983238490878, 0.022929703779565887, 0.1553947661562799, 0.7282176511939945]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
