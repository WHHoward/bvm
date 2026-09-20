# U047_b011_a110_h review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.546, JS2_AREA=0.777, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0779677295623666 | 0.1160648563343664 | 2.009705329806388 | -0.11170066863984347 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0779677295623666 | 0.1160648563343664 | 2.009705329806388 | -0.11170066863984347 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0779677295623666 | 0.1160648563343664 | 2.009705329806388 | -0.11170066863984347 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0779677295623666 | 0.1160648563343664 | 2.009705329806388 | -0.11170066863984347 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0779677295623666 | 0.1160648563343664 | 2.009705329806388 | -0.11170066863984347 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.2469740453217641 | 1.2556400478886123 | -1.693928505950365 | 1.693928505950365 | AMBIGUOUS |
| 1111 | BVM1 | -1.465601689238353 | 1.4724317758746586 | -1.9514173306315876 | 1.9640462753659296 | AMBIGUOUS |
| 1111 | BVM2 | -1.465601689238353 | 1.4724317758746586 | -1.9514173306315876 | 1.9640462753659296 | AMBIGUOUS |
| 1111 | BVM3 | -1.465601689238353 | 1.4724317758746586 | -1.9514173306315876 | 1.9640462753659296 | AMBIGUOUS |
| 1111 | BVM4 | -1.465601689238353 | 1.4724317758746586 | -1.9514173306315876 | 1.9640462753659296 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.260231e-05 | -2.808521e-07 | 0.115828032521402 | 0.11584161446853339 | 1 |
| 1111 | 0.0001425723 | -2.808521e-07 | 0.5192558376648642 | 0.5192694196119955 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11584161446853339, 0.5192694196119955]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.260231e-05, 0.0001425723]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.115828032521402, 0.5192558376648642]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
