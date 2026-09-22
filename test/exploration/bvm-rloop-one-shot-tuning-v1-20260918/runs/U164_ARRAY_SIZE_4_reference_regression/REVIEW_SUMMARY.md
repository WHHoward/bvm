# U164_ARRAY_SIZE_4_reference_regression review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=4; bit order: b3..b0=BVM1/BVM2/.../BVM4; rightmost bit maps to highest-numbered BVM
- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780249402848627 | 0.11878322276237598 | 2.0093338621692114 | -0.11122479535999863 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780249402848627 | 0.11878322276237598 | 2.0093338621692114 | -0.11122479535999863 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780249402848627 | 0.11878322276237598 | 2.0093338621692114 | -0.11122479535999863 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780249402848627 | 0.11878322276237598 | 2.0093338621692114 | -0.11122479535999863 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0019133448103564614 | 0.002311057097648794 | -0.0024521797856883803 | 0.003464723533639015 | AMBIGUOUS |
| 0001 | BVM4 | -1.1783943394984095 | 1.1883213744258576 | -1.482690171393624 | 1.482690171393624 | AMBIGUOUS |
| 0011 | BVM3 | -1.5425674281681625 | 1.5513107641218589 | -1.9571371046384016 | 1.9857818112960808 | AMBIGUOUS |
| 0011 | BVM4 | -1.5425674281681625 | 1.5513107641218589 | -1.9571371046384016 | 1.9857818112960808 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -9.682059e-07 | -0.0019819015168766104 | 0.0019819015168766104 | 0 |
| 0001 | 1.764882e-05 | -2.520911e-05 | 0.02564421822831107 | 0.044422905955836624 | 2 |
| 0011 | 2.321515e-05 | -5.041125e-05 | -0.005043857360729284 | 0.08027167373023858 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0019819015168766104, 0.044422905955836624, 0.08027167373023858]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.764882e-05, 2.321515e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0019819015168766104, 0.02564421822831107, -0.005043857360729284]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
