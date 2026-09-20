# U065_b012_a1_se100_a0p8 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.800, JS2_AREA=0.800, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.077285591476275 | 0.11456131958697716 | 2.0095538143005642 | -0.11256376589623075 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.077285591476275 | 0.11456131958697716 | 2.0095538143005642 | -0.11256376589623075 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.077285591476275 | 0.11456131958697716 | 2.0095538143005642 | -0.11256376589623075 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.077285591476275 | 0.11456131958697716 | 2.0095538143005642 | -0.11256376589623075 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.077285591476275 | 0.11456131958697716 | 2.0095538143005642 | -0.11256376589623075 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0959007515076606 | 1.1186018645620561 | -1.1963447093325006 | 1.2049812523193821 | AMBIGUOUS |
| 1111 | BVM1 | -1.07555836245637 | 1.1203783361213533 | -1.2771346232349223 | 1.3357334042670979 | AMBIGUOUS |
| 1111 | BVM2 | -1.07555836245637 | 1.1203783361213533 | -1.2771346232349223 | 1.3357334042670979 | AMBIGUOUS |
| 1111 | BVM3 | -1.07555836245637 | 1.1203783361213533 | -1.2771346232349223 | 1.3357334042670979 | AMBIGUOUS |
| 1111 | BVM4 | -1.07555836245637 | 1.1203783361213533 | -1.2771346232349223 | 1.3357334042670979 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.769603e-05 | -3.501252e-07 | 0.08473151496647711 | 0.08474844694582055 | 1 |
| 1111 | 0.0001154632 | -3.501252e-07 | 0.3848054557234427 | 0.38482238770278615 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.08474844694582055, 0.38482238770278615]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [2.769603e-05, 0.0001154632]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.08473151496647711, 0.3848054557234427]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
