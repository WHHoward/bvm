# U172_3bvm_rloop_shots_tunning review summary

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
| 000 | BVM1 | -1.074870340649173 | 0.11048934036797109 | 2.0075615127229396 | -0.11130803339523573 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.074870340649173 | 0.11048934036797109 | 2.0075615127229396 | -0.11130803339523573 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.074870340649173 | 0.11048934036797109 | 2.0075615127229396 | -0.11130803339523573 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.074870340649173 | 0.11048934036797109 | 2.0075615127229396 | -0.11130803339523573 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.074870340649173 | 0.11048934036797109 | 2.0075615127229396 | -0.11130803339523573 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.074870340649173 | 0.11048934036797109 | 2.0075615127229396 | -0.11130803339523573 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.074870340649173 | 0.11048934036797109 | 2.0075615127229396 | -0.11130803339523573 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02638559773345572 | 0.03654114732819509 | -0.006084095587045425 | 0.033991310069425525 | AMBIGUOUS |
| 001 | BVM3 | -2.3934668269000277 | 2.4245256753119966 | -2.706799890266852 | 2.7075435735694375 | AMBIGUOUS |
| 011 | BVM2 | -2.28617888821235 | 2.3251130096874033 | -3.107109586230449 | 3.1396379599784674 | AMBIGUOUS |
| 011 | BVM3 | -2.28617888821235 | 2.3251130096874033 | -3.107109586230449 | 3.1396379599784674 | AMBIGUOUS |
| 111 | BVM1 | -2.8698573603098434 | 2.8707012157336114 | -2.982470575646893 | 3.3172353799884946 | AMBIGUOUS |
| 111 | BVM2 | -2.8698573603098434 | 2.8707012157336114 | -2.982470575646893 | 3.3172353799884946 | AMBIGUOUS |
| 111 | BVM3 | -2.8698573603098434 | 2.8707012157336114 | -2.982470575646893 | 3.3172353799884946 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 1.99128e-06 | -3.302994e-06 | -0.0011994232275474453 | 0.005767454780535156 | 9 |
| 001 | 2.740084e-05 | -3.898811e-05 | 0.04027652810720417 | 0.08637958856934222 | 2 |
| 011 | 7.764189e-05 | -1.261579e-05 | 0.12193390432498631 | 0.12933579386016528 | 7 |
| 111 | 9.574816e-05 | -5.495506e-06 | 0.20953378682676405 | 0.2107326471715629 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005767454780535156, 0.08637958856934222, 0.12933579386016528, 0.2107326471715629]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [1.99128e-06, 2.740084e-05, 7.764189e-05, 9.574816e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011994232275474453, 0.04027652810720417, 0.12193390432498631, 0.20953378682676405]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
