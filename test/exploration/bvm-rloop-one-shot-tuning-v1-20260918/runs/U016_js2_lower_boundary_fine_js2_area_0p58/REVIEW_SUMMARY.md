# U016_js2_lower_boundary_fine_js2_area_0p58 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.58, RSH_JS1=12, RSH_JS2=12
- Mode: passive
- Masks: 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 1111 | BVM1 | -1.0782015281737687 | 0.11856311147607979 | 2.009750848120112 | -0.11098749533984867 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0782015281737687 | 0.11856311147607979 | 2.009750848120112 | -0.11098749533984867 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0782015281737687 | 0.11856311147607979 | 2.009750848120112 | -0.11098749533984867 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0782015281737687 | 0.11856311147607979 | 2.009750848120112 | -0.11098749533984867 | REVIEW_REQUIRED |

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
| 1111 | BVM1 | -1.1790721644855435 | 1.1867882507745477 | -1.4578259516766778 | 1.4639147423345444 | AMBIGUOUS |
| 1111 | BVM2 | -1.1790721644855435 | 1.1867882507745477 | -1.4578259516766778 | 1.4639147423345444 | AMBIGUOUS |
| 1111 | BVM3 | -1.1790721644855435 | 1.1867882507745477 | -1.4578259516766778 | 1.4639147423345444 | AMBIGUOUS |
| 1111 | BVM4 | -1.1790721644855435 | 1.1867882507745477 | -1.4578259516766778 | 1.4639147423345444 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 1111 | 0.0001136384 | -4.169983e-07 | 0.43302028398028225 | 0.43304044992835417 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.43304044992835417]}, "peak_positive_a": {"masks": ["1111"], "nondecreasing": true, "values": [0.0001136384]}, "signed_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.43302028398028225]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
