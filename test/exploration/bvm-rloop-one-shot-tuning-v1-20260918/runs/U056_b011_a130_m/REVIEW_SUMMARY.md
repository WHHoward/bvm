# U056_b011_a130_m review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.676, JS2_AREA=0.962, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.077320605563755 | 0.11926880449374923 | 2.0094404959810825 | -0.11246652222600172 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.077320605563755 | 0.11926880449374923 | 2.0094404959810825 | -0.11246652222600172 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.077320605563755 | 0.11926880449374923 | 2.0094404959810825 | -0.11246652222600172 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.077320605563755 | 0.11926880449374923 | 2.0094404959810825 | -0.11246652222600172 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.077320605563755 | 0.11926880449374923 | 2.0094404959810825 | -0.11246652222600172 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.4082647363414926 | 1.4148877305658472 | -1.9792912817308612 | 1.9854999160608764 | AMBIGUOUS |
| 1111 | BVM1 | -1.8279055508479745 | 1.8330523352286687 | -1.9345385032828515 | 2.078034191523935 | AMBIGUOUS |
| 1111 | BVM2 | -1.8279055508479745 | 1.8330523352286687 | -1.9345385032828515 | 2.078034191523935 | AMBIGUOUS |
| 1111 | BVM3 | -1.8279055508479745 | 1.8330523352286687 | -1.9345385032828515 | 2.078034191523935 | AMBIGUOUS |
| 1111 | BVM4 | -1.8279055508479745 | 1.8330523352286687 | -1.9345385032828515 | 2.078034191523935 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.979459e-05 | -2.491298e-07 | 0.12956062532254276 | 0.1295726731860711 | 1 |
| 1111 | 0.0001698556 | -2.491298e-07 | 0.5810080689858209 | 0.5810201168493492 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1295726731860711, 0.5810201168493492]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.979459e-05, 0.0001698556]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.12956062532254276, 0.5810080689858209]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
