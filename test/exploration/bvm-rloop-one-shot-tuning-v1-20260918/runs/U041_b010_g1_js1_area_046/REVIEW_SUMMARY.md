# U041_b010_g1_js1_area_046 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.46, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0782069394418339 | 0.11293921240698457 | 2.00980273263156 | -0.11117625310235575 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0782069394418339 | 0.11293921240698457 | 2.00980273263156 | -0.11117625310235575 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0782069394418339 | 0.11293921240698457 | 2.00980273263156 | -0.11117625310235575 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0782069394418339 | 0.11293921240698457 | 2.00980273263156 | -0.11117625310235575 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0782069394418339 | 0.11293921240698457 | 2.00980273263156 | -0.11117625310235575 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.1341332384160934 | 1.1447772345311817 | -1.3147635468526677 | 1.3400126827994814 | AMBIGUOUS |
| 1111 | BVM1 | -1.14686022259538 | 1.1552880816208795 | -1.334645023188764 | 1.3650619201377716 | AMBIGUOUS |
| 1111 | BVM2 | -1.14686022259538 | 1.1552880816208795 | -1.334645023188764 | 1.3650619201377716 | AMBIGUOUS |
| 1111 | BVM3 | -1.14686022259538 | 1.1552880816208795 | -1.334645023188764 | 1.3650619201377716 | AMBIGUOUS |
| 1111 | BVM4 | -1.14686022259538 | 1.1552880816208795 | -1.334645023188764 | 1.3650619201377716 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.068158e-05 | -2.635282e-07 | 0.09972954932499006 | 0.09974229349204464 | 1 |
| 1111 | 0.0001313836 | -2.20682e-06 | 0.421337649024691 | 0.42145711453215373 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09974229349204464, 0.42145711453215373]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.068158e-05, 0.0001313836]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09972954932499006, 0.421337649024691]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
