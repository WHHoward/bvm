# U071_b012_a1_se110_a1 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=1.000, JS2_AREA=1.000, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0763153829431866 | 0.11485464214709552 | 2.0091260058135334 | -0.11312797016949165 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0763153829431866 | 0.11485464214709552 | 2.0091260058135334 | -0.11312797016949165 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0763153829431866 | 0.11485464214709552 | 2.0091260058135334 | -0.11312797016949165 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0763153829431866 | 0.11485464214709552 | 2.0091260058135334 | -0.11312797016949165 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0763153829431866 | 0.11485464214709552 | 2.0091260058135334 | -0.11312797016949165 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -0.08528346273468969 | 0.09322656763451999 | -0.31246383864512783 | 0.34717823736750275 | AMBIGUOUS |
| 1111 | BVM1 | -0.06572803121501126 | 0.0800638172210479 | -0.22480734387794932 | 0.2889792535523739 | AMBIGUOUS |
| 1111 | BVM2 | -0.06572803121501126 | 0.0800638172210479 | -0.22480734387794932 | 0.2889792535523739 | AMBIGUOUS |
| 1111 | BVM3 | -0.06572803121501126 | 0.0800638172210479 | -0.22480734387794932 | 0.2889792535523739 | AMBIGUOUS |
| 1111 | BVM4 | -0.06572803121501126 | 0.0800638172210479 | -0.22480734387794932 | 0.2889792535523739 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 1.2973e-05 | -8.943415e-06 | 0.027368520816958855 | 0.029907813408130205 | 2 |
| 1111 | 5.939244e-05 | -4.829744e-05 | 0.09564460927375276 | 0.11433915369635607 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.029907813408130205, 0.11433915369635607]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [1.2973e-05, 5.939244e-05]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.027368520816958855, 0.09564460927375276]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
