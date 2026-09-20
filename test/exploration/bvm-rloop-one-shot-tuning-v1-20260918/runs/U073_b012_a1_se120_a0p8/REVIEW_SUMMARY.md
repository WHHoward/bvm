# U073_b012_a1_se120_a0p8 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.800, JS2_AREA=0.800, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.077285591476275 | 0.1212736793118779 | 2.0095348748623367 | -0.11255755885345028 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.077285591476275 | 0.1212736793118779 | 2.0095348748623367 | -0.11255755885345028 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.077285591476275 | 0.1212736793118779 | 2.0095348748623367 | -0.11255755885345028 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.077285591476275 | 0.1212736793118779 | 2.0095348748623367 | -0.11255755885345028 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.077285591476275 | 0.1212736793118779 | 2.0095348748623367 | -0.11255755885345028 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.351628288011157 | 1.3579597740417446 | -1.919999555991958 | 1.9296188807524322 | AMBIGUOUS |
| 1111 | BVM1 | -1.6594108704841342 | 1.6643188906192021 | -1.8901452717667802 | 2.0068519999866363 | AMBIGUOUS |
| 1111 | BVM2 | -1.6594108704841342 | 1.6643188906192021 | -1.8901452717667802 | 2.0068519999866363 | AMBIGUOUS |
| 1111 | BVM3 | -1.6594108704841342 | 1.6643188906192021 | -1.8901452717667802 | 2.0068519999866363 | AMBIGUOUS |
| 1111 | BVM4 | -1.6594108704841342 | 1.6643188906192021 | -1.8901452717667802 | 2.0068519999866363 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.806927e-05 | -3.49934e-07 | 0.12770578823603812 | 0.1277227109689907 | 1 |
| 1111 | 0.0001651044 | -3.49934e-07 | 0.5737801322613806 | 0.5737970549943332 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1277227109689907, 0.5737970549943332]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.806927e-05, 0.0001651044]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.12770578823603812, 0.5737801322613806]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
