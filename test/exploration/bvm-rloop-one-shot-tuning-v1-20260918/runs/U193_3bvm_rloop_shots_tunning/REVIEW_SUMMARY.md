# U193_3bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.85, JS2_AREA=0.85, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0752762807607572 | 0.11190613767137514 | 2.00672451687722 | -0.11092669815158755 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0752762807607572 | 0.11190613767137514 | 2.00672451687722 | -0.11092669815158755 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0752762807607572 | 0.11190613767137514 | 2.00672451687722 | -0.11092669815158755 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0752762807607572 | 0.11190613767137514 | 2.00672451687722 | -0.11092669815158755 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0752762807607572 | 0.11190613767137514 | 2.00672451687722 | -0.11092669815158755 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0752762807607572 | 0.11190613767137514 | 2.00672451687722 | -0.11092669815158755 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0752762807607572 | 0.11190613767137514 | 2.00672451687722 | -0.11092669815158755 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02818309366073559 | 0.04088688896481361 | -0.009678689554247432 | 0.04539757878445255 | AMBIGUOUS |
| 001 | BVM3 | -2.373782097904581 | 2.417229805819238 | -3.127172292300244 | 3.1327968439046057 | AMBIGUOUS |
| 011 | BVM2 | -2.606587582461682 | 2.606587582461682 | -2.9237945567208348 | 3.17526453934168 | AMBIGUOUS |
| 011 | BVM3 | -2.606587582461682 | 2.606587582461682 | -2.9237945567208348 | 3.17526453934168 | AMBIGUOUS |
| 111 | BVM1 | -3.254333876900818 | 3.254333876900818 | -2.8225560974200796 | 3.273202491179078 | AMBIGUOUS |
| 111 | BVM2 | -3.254333876900818 | 3.254333876900818 | -2.8225560974200796 | 3.273202491179078 | AMBIGUOUS |
| 111 | BVM3 | -3.254333876900818 | 3.254333876900818 | -2.8225560974200796 | 3.273202491179078 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.652674e-06 | -4.14914e-06 | -0.0010511134006739688 | 0.00708206961510189 | 10 |
| 001 | 2.809516e-05 | -3.770798e-05 | 0.03288125937959807 | 0.08470705235791252 | 2 |
| 011 | 8.588266e-05 | -7.689395e-06 | 0.12590045068263123 | 0.13152944637358488 | 8 |
| 111 | 0.000108839 | -4.098508e-06 | 0.20988802719801472 | 0.21008623016311095 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.00708206961510189, 0.08470705235791252, 0.13152944637358488, 0.21008623016311095]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.652674e-06, 2.809516e-05, 8.588266e-05, 0.000108839]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0010511134006739688, 0.03288125937959807, 0.12590045068263123, 0.20988802719801472]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
