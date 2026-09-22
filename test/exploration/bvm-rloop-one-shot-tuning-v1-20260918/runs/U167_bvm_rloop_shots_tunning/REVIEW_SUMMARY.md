# U167_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=20, RSH_JS2=20
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.076732705776878 | 0.11276382365969738 | 2.0092732241358933 | -0.112745998306071 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.076732705776878 | 0.11276382365969738 | 2.0092732241358933 | -0.112745998306071 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.076732705776878 | 0.11276382365969738 | 2.0092732241358933 | -0.112745998306071 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.076732705776878 | 0.11276382365969738 | 2.0092732241358933 | -0.112745998306071 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.076732705776878 | 0.11276382365969738 | 2.0092732241358933 | -0.112745998306071 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.076732705776878 | 0.11276382365969738 | 2.0092732241358933 | -0.112745998306071 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.076732705776878 | 0.11276382365969738 | 2.0092732241358933 | -0.112745998306071 | REVIEW_REQUIRED |

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
| 000 | BVM1 | 0.002127774265184167 | 0.0028983070066692725 | -0.0017506088810449968 | 0.002826512211840517 | AMBIGUOUS |
| 001 | BVM3 | -0.14466837369277347 | 0.15472335327897305 | -0.5340862215484051 | 0.5340862215484051 | AMBIGUOUS |
| 011 | BVM2 | -0.45290255831677395 | 0.4616824044144156 | -0.9315877876960886 | 0.9936443690218789 | AMBIGUOUS |
| 011 | BVM3 | -0.45290255831677395 | 0.4616824044144156 | -0.9315877876960886 | 0.9936443690218789 | AMBIGUOUS |
| 111 | BVM1 | -1.2093173014199663 | 1.217129565041081 | -1.7895647112542847 | 1.7895647112542847 | AMBIGUOUS |
| 111 | BVM2 | -1.2093173014199663 | 1.217129565041081 | -1.7895647112542847 | 1.7895647112542847 | AMBIGUOUS |
| 111 | BVM3 | -1.2093173014199663 | 1.217129565041081 | -1.7895647112542847 | 1.7895647112542847 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 0.0 | -8.26306e-07 | -0.0010688494721844788 | 0.0010688494721844788 | 0 |
| 001 | 8.053948e-06 | -8.26306e-07 | 0.029460906314557996 | 0.029500866294940326 | 1 |
| 011 | 3.976214e-05 | -8.26306e-07 | 0.07996284157932979 | 0.08000280155971211 | 1 |
| 111 | 6.815773e-05 | -1.352969e-05 | 0.09792935505449746 | 0.10597281476819101 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.0010688494721844788, 0.029500866294940326, 0.08000280155971211, 0.10597281476819101]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.0, 8.053948e-06, 3.976214e-05, 6.815773e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0010688494721844788, 0.029460906314557996, 0.07996284157932979, 0.09792935505449746]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
