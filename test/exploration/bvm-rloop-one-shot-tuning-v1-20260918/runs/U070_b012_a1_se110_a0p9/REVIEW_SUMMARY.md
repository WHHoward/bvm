# U070_b012_a1_se110_a0p9 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.900, JS2_AREA=0.900, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0768000097449015 | 0.11608697887145615 | 2.009342456536138 | -0.11288653212082128 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0768000097449015 | 0.11608697887145615 | 2.009342456536138 | -0.11288653212082128 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0768000097449015 | 0.11608697887145615 | 2.009342456536138 | -0.11288653212082128 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0768000097449015 | 0.11608697887145615 | 2.009342456536138 | -0.11288653212082128 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0768000097449015 | 0.11608697887145615 | 2.009342456536138 | -0.11288653212082128 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0918556058120596 | 1.1327146108308437 | -1.219271647335649 | 1.2298678651368213 | AMBIGUOUS |
| 1111 | BVM1 | -1.0907109634613428 | 1.1372291999465884 | -1.3509410092204033 | 1.388983815267659 | AMBIGUOUS |
| 1111 | BVM2 | -1.0907109634613428 | 1.1372291999465884 | -1.3509410092204033 | 1.388983815267659 | AMBIGUOUS |
| 1111 | BVM3 | -1.0907109634613428 | 1.1372291999465884 | -1.3509410092204033 | 1.388983815267659 | AMBIGUOUS |
| 1111 | BVM4 | -1.0907109634613428 | 1.1372291999465884 | -1.3509410092204033 | 1.388983815267659 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.962586e-05 | -3.410403e-07 | 0.08732271154650333 | 0.08733920418203735 | 1 |
| 1111 | 0.0001250176 | -3.410403e-07 | 0.405316644176046 | 0.40533313681158006 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.08733920418203735, 0.40533313681158006]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [2.962586e-05, 0.0001250176]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.08732271154650333, 0.405316644176046]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
