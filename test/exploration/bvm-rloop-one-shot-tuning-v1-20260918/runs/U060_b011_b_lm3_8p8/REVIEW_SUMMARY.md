# U060_b011_b_lm3_8p8 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0781962760606467 | 0.1141408322273284 | 2.0098067115051372 | -0.11127636156156041 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0781962760606467 | 0.1141408322273284 | 2.0098067115051372 | -0.11127636156156041 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0781962760606467 | 0.1141408322273284 | 2.0098067115051372 | -0.11127636156156041 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0781962760606467 | 0.1141408322273284 | 2.0098067115051372 | -0.11127636156156041 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0781962760606467 | 0.1141408322273284 | 2.0098067115051372 | -0.11127636156156041 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.1329863201496901 | 1.143816877689071 | -1.344205301465351 | 1.3626575664124825 | AMBIGUOUS |
| 1111 | BVM1 | -1.1792018916796578 | 1.1877677698718068 | -1.4821934329007398 | 1.4822435667078135 | AMBIGUOUS |
| 1111 | BVM2 | -1.1792018916796578 | 1.1877677698718068 | -1.4821934329007398 | 1.4822435667078135 | AMBIGUOUS |
| 1111 | BVM3 | -1.1792018916796578 | 1.1877677698718068 | -1.4821934329007398 | 1.4822435667078135 | AMBIGUOUS |
| 1111 | BVM4 | -1.1792018916796578 | 1.1877677698718068 | -1.4821934329007398 | 1.4822435667078135 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.065842e-05 | -2.939382e-07 | 0.10102824423831562 | 0.10104245902642754 | 1 |
| 1111 | 0.0001303671 | -2.939382e-07 | 0.44164704019778667 | 0.4416612549858986 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10104245902642754, 0.4416612549858986]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.065842e-05, 0.0001303671]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10102824423831562, 0.44164704019778667]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
