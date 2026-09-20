# U042_b010_g2_lm3_8p0 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0777858154624127 | 0.1127792616891772 | 2.0096340283918828 | -0.11184167991942282 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0777858154624127 | 0.1127792616891772 | 2.0096340283918828 | -0.11184167991942282 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0777858154624127 | 0.1127792616891772 | 2.0096340283918828 | -0.11184167991942282 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0777858154624127 | 0.1127792616891772 | 2.0096340283918828 | -0.11184167991942282 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0777858154624127 | 0.1127792616891772 | 2.0096340283918828 | -0.11184167991942282 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.1157236269937107 | 1.1249093500272254 | -1.2690029833895051 | 1.3077237894943323 | AMBIGUOUS |
| 1111 | BVM1 | -1.11706450738926 | 1.1243225457520454 | -1.2616493883988873 | 1.3182009593980717 | AMBIGUOUS |
| 1111 | BVM2 | -1.11706450738926 | 1.1243225457520454 | -1.2616493883988873 | 1.3182009593980717 | AMBIGUOUS |
| 1111 | BVM3 | -1.11706450738926 | 1.1243225457520454 | -1.2616493883988873 | 1.3182009593980717 | AMBIGUOUS |
| 1111 | BVM4 | -1.11706450738926 | 1.1243225457520454 | -1.2616493883988873 | 1.3182009593980717 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.975919e-05 | -2.78003e-07 | 0.09614924508673582 | 0.09616268925200416 | 1 |
| 1111 | 0.0001282303 | -1.230717e-05 | 0.40727620741606135 | 0.40793497100159665 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09616268925200416, 0.40793497100159665]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [2.975919e-05, 0.0001282303]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09614924508673582, 0.40727620741606135]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
