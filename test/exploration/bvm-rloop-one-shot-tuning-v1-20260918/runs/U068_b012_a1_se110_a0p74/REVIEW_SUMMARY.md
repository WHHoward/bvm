# U068_b012_a1_se110_a0p74 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.740, JS2_AREA=0.740, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0775653858662304 | 0.11883542558371006 | 2.009649784731249 | -0.11231039122682852 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0775653858662304 | 0.11883542558371006 | 2.009649784731249 | -0.11231039122682852 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0775653858662304 | 0.11883542558371006 | 2.009649784731249 | -0.11231039122682852 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0775653858662304 | 0.11883542558371006 | 2.009649784731249 | -0.11231039122682852 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0775653858662304 | 0.11883542558371006 | 2.009649784731249 | -0.11231039122682852 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.2299084337318154 | 1.237370572393622 | -1.7350246836653442 | 1.7350246836653442 | AMBIGUOUS |
| 1111 | BVM1 | -1.4719753035823766 | 1.4778198709800687 | -1.8980311763800632 | 1.9729597320382968 | AMBIGUOUS |
| 1111 | BVM2 | -1.4719753035823766 | 1.4778198709800687 | -1.8980311763800632 | 1.9729597320382968 | AMBIGUOUS |
| 1111 | BVM3 | -1.4719753035823766 | 1.4778198709800687 | -1.8980311763800632 | 1.9729597320382968 | AMBIGUOUS |
| 1111 | BVM4 | -1.4719753035823766 | 1.4778198709800687 | -1.8980311763800632 | 1.9729597320382968 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.15724e-05 | -3.568018e-07 | 0.11702394147578529 | 0.11704119633406827 | 1 |
| 1111 | 0.0001498567 | -3.568018e-07 | 0.534395767570393 | 0.5344130224286759 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11704119633406827, 0.5344130224286759]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.15724e-05, 0.0001498567]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11702394147578529, 0.534395767570393]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
