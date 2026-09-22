# U208_3bvm_rloop_shots_tunning_qb_BJ1_area_sweep_qb_bj1_area_0p82 review summary

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
| 000 | BVM1 | -1.0748727433604193 | 0.11041453754471776 | 2.007537639481476 | -0.11128384184388593 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0748727433604193 | 0.11041453754471776 | 2.007537639481476 | -0.11128384184388593 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0748727433604193 | 0.11041453754471776 | 2.007537639481476 | -0.11128384184388593 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0748727433604193 | 0.11041453754471776 | 2.007537639481476 | -0.11128384184388593 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0748727433604193 | 0.11041453754471776 | 2.007537639481476 | -0.11128384184388593 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0748727433604193 | 0.11041453754471776 | 2.007537639481476 | -0.11128384184388593 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0748727433604193 | 0.11041453754471776 | 2.007537639481476 | -0.11128384184388593 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.026507001124046223 | 0.03666417409920513 | -0.006270338701451566 | 0.03413841698332537 | AMBIGUOUS |
| 001 | BVM3 | -2.39463737967548 | 2.4239727232932125 | -2.747118405098896 | 2.747886852910627 | AMBIGUOUS |
| 011 | BVM2 | -2.292813230184147 | 2.3228793814695687 | -3.108107280822209 | 3.1427786599634664 | AMBIGUOUS |
| 011 | BVM3 | -2.292813230184147 | 2.3228793814695687 | -3.108107280822209 | 3.1427786599634664 | AMBIGUOUS |
| 111 | BVM1 | -2.8848568860905504 | 2.885700884753767 | -2.981935608136678 | 3.320454113642091 | AMBIGUOUS |
| 111 | BVM2 | -2.8848568860905504 | 2.885700884753767 | -2.981935608136678 | 3.320454113642091 | AMBIGUOUS |
| 111 | BVM3 | -2.8848568860905504 | 2.885700884753767 | -2.981935608136678 | 3.320454113642091 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 1.990491e-06 | -3.308638e-06 | -0.0012253504965840047 | 0.005750413588596992 | 9 |
| 001 | 2.559622e-05 | -4.423343e-05 | 0.025439291498627226 | 0.08471205860152838 | 2 |
| 011 | 7.321367e-05 | -1.428657e-05 | 0.11838301927244607 | 0.1281887450659432 | 8 |
| 111 | 9.227965e-05 | -6.2844e-06 | 0.20676545485679626 | 0.20822229622870514 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005750413588596992, 0.08471205860152838, 0.1281887450659432, 0.20822229622870514]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [1.990491e-06, 2.559622e-05, 7.321367e-05, 9.227965e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0012253504965840047, 0.025439291498627226, 0.11838301927244607, 0.20676545485679626]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
