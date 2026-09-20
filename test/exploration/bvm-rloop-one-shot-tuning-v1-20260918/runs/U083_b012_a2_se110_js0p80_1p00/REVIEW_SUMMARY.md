# U083_b012_a2_se110_js0p80_1p00 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.800, JS2_AREA=1.000, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.076858260454073 | 0.11393074770244714 | 2.009295505827926 | -0.11280966028330774 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.076858260454073 | 0.11393074770244714 | 2.009295505827926 | -0.11280966028330774 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.076858260454073 | 0.11393074770244714 | 2.009295505827926 | -0.11280966028330774 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.076858260454073 | 0.11393074770244714 | 2.009295505827926 | -0.11280966028330774 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.076858260454073 | 0.11393074770244714 | 2.009295505827926 | -0.11280966028330774 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -0.13618248677502254 | 0.1450066734398096 | -0.46944671465117654 | 0.46944671465117654 | AMBIGUOUS |
| 1111 | BVM1 | -0.0877436798450042 | 0.09486248946357297 | -0.2638134352182688 | 0.3164763734928891 | AMBIGUOUS |
| 1111 | BVM2 | -0.0877436798450042 | 0.09486248946357297 | -0.2638134352182688 | 0.3164763734928891 | AMBIGUOUS |
| 1111 | BVM3 | -0.0877436798450042 | 0.09486248946357297 | -0.2638134352182688 | 0.3164763734928891 | AMBIGUOUS |
| 1111 | BVM4 | -0.0877436798450042 | 0.09486248946357297 | -0.2638134352182688 | 0.3164763734928891 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 1.299199e-05 | -2.716815e-07 | 0.03286128128269233 | 0.03287441974158073 | 1 |
| 1111 | 5.928742e-05 | -4.302758e-05 | 0.10251374748025724 | 0.11697473416877711 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.03287441974158073, 0.11697473416877711]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [1.299199e-05, 5.928742e-05]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.03286128128269233, 0.10251374748025724]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
