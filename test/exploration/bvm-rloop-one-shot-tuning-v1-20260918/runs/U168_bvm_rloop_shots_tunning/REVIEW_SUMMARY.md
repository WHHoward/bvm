# U168_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=12, RSH_JS2=12
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0767272171184485 | 0.11312415045085733 | 2.009016029747857 | -0.1125729968829301 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0767272171184485 | 0.11312415045085733 | 2.009016029747857 | -0.1125729968829301 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0767272171184485 | 0.11312415045085733 | 2.009016029747857 | -0.1125729968829301 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0767272171184485 | 0.11312415045085733 | 2.009016029747857 | -0.1125729968829301 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0767272171184485 | 0.11312415045085733 | 2.009016029747857 | -0.1125729968829301 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0767272171184485 | 0.11312415045085733 | 2.009016029747857 | -0.1125729968829301 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0767272171184485 | 0.11312415045085733 | 2.009016029747857 | -0.1125729968829301 | REVIEW_REQUIRED |

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
| 000 | BVM1 | 0.002356909636753567 | 0.0029127264445133936 | -0.0018637202991004039 | 0.0025923952905523347 | AMBIGUOUS |
| 001 | BVM3 | -0.07209344907946594 | 0.0820264841482685 | -0.24307419331637856 | 0.2946846399523322 | AMBIGUOUS |
| 011 | BVM2 | -0.06564692585601163 | 0.07450090632614548 | -0.21789826864338707 | 0.2771796652264839 | AMBIGUOUS |
| 011 | BVM3 | -0.06564692585601163 | 0.07450090632614548 | -0.21789826864338707 | 0.2771796652264839 | AMBIGUOUS |
| 111 | BVM1 | -0.08412132925572698 | 0.09194315808892126 | -0.281859616328101 | 0.33429050669569343 | AMBIGUOUS |
| 111 | BVM2 | -0.08412132925572698 | 0.09194315808892126 | -0.281859616328101 | 0.33429050669569343 | AMBIGUOUS |
| 111 | BVM3 | -0.08412132925572698 | 0.09194315808892126 | -0.281859616328101 | 0.33429050669569343 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 0.0 | -7.130552e-07 | -0.001077600854708516 | 0.001077600854708516 | 0 |
| 001 | 7.573178e-06 | -5.900049e-06 | 0.021343709269817535 | 0.023418909781768867 | 2 |
| 011 | 1.568194e-05 | -1.232407e-05 | 0.041496611259649 | 0.04603537317665569 | 2 |
| 111 | 2.402446e-05 | -1.116201e-05 | 0.06123423304172557 | 0.06329455666207852 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.001077600854708516, 0.023418909781768867, 0.04603537317665569, 0.06329455666207852]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.0, 7.573178e-06, 1.568194e-05, 2.402446e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.001077600854708516, 0.021343709269817535, 0.041496611259649, 0.06123423304172557]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
