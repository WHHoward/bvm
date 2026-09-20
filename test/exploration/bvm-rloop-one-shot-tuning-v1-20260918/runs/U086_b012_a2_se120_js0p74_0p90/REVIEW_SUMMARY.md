# U086_b012_a2_se120_js0p74_0p90 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.740, JS2_AREA=0.900, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.077225271752843 | 0.11810792833883695 | 2.00945115936227 | -0.11255915040288114 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.077225271752843 | 0.11810792833883695 | 2.00945115936227 | -0.11255915040288114 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.077225271752843 | 0.11810792833883695 | 2.00945115936227 | -0.11255915040288114 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.077225271752843 | 0.11810792833883695 | 2.00945115936227 | -0.11255915040288114 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.077225271752843 | 0.11810792833883695 | 2.00945115936227 | -0.11255915040288114 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.204227701410325 | 1.2114129423021405 | -1.6833892815343137 | 1.6833892815343137 | AMBIGUOUS |
| 1111 | BVM1 | -1.5176703111244794 | 1.5233247201961653 | -1.943951388166641 | 2.0279708741742835 | AMBIGUOUS |
| 1111 | BVM2 | -1.5176703111244794 | 1.5233247201961653 | -1.943951388166641 | 2.0279708741742835 | AMBIGUOUS |
| 1111 | BVM3 | -1.5176703111244794 | 1.5233247201961653 | -1.943951388166641 | 2.0279708741742835 | AMBIGUOUS |
| 1111 | BVM4 | -1.5176703111244794 | 1.5233247201961653 | -1.943951388166641 | 2.0279708741742835 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.368999e-05 | -2.924367e-07 | 0.11497387398651376 | 0.11498801616240874 | 1 |
| 1111 | 0.0001597281 | -2.924367e-07 | 0.5403835843705559 | 0.5403977265464508 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11498801616240874, 0.5403977265464508]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.368999e-05, 0.0001597281]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11497387398651376, 0.5403835843705559]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
