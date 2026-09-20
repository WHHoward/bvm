# U102_b013_s1_rsl6_closed review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.74, JS2_AREA=0.90, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.077145216455186 | 0.11385865051322647 | 2.009148446660509 | -0.11233458277817847 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.077145216455186 | 0.11385865051322647 | 2.009148446660509 | -0.11233458277817847 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.077145216455186 | 0.11385865051322647 | 2.009148446660509 | -0.11233458277817847 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.077145216455186 | 0.11385865051322647 | 2.009148446660509 | -0.11233458277817847 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.077145216455186 | 0.11385865051322647 | 2.009148446660509 | -0.11233458277817847 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.077145216455186 | 0.11385865051322647 | 2.009148446660509 | -0.11233458277817847 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.077145216455186 | 0.11385865051322647 | 2.009148446660509 | -0.11233458277817847 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -0.5671173180151685 | 0.5773294312766828 | -0.9221959271802814 | 0.9540390115743355 | AMBIGUOUS |
| 0011 | BVM3 | -1.0380281467343304 | 1.0465961576027167 | -1.0833192986083373 | 1.0833192986083373 | AMBIGUOUS |
| 0011 | BVM4 | -1.0380281467343304 | 1.0465961576027167 | -1.0833192986083373 | 1.0833192986083373 | AMBIGUOUS |
| 1111 | BVM1 | -1.6665614155983557 | 1.6726768806246846 | -1.9400798009364821 | 2.061974980301134 | AMBIGUOUS |
| 1111 | BVM2 | -1.6665614155983557 | 1.6726768806246846 | -1.9400798009364821 | 2.061974980301134 | AMBIGUOUS |
| 1111 | BVM3 | -1.6665614155983557 | 1.6726768806246846 | -1.9400798009364821 | 2.061974980301134 | AMBIGUOUS |
| 1111 | BVM4 | -1.6665614155983557 | 1.6726768806246846 | -1.9400798009364821 | 2.061974980301134 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.293811e-05 | -4.55199e-07 | 0.05806011907877421 | 0.05808213240447929 | 1 |
| 0011 | 4.234946e-05 | -4.370572e-05 | 0.07768829993540195 | 0.10429559933385889 | 2 |
| 1111 | 0.000103013 | -4.55199e-07 | 0.18704678097038288 | 0.18706879429608797 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.05808213240447929, 0.10429559933385889, 0.18706879429608797]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [2.293811e-05, 4.234946e-05, 0.000103013]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.05806011907877421, 0.07768829993540195, 0.18704678097038288]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
