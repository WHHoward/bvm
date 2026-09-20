# U057_b011_a130_j2 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.676, JS2_AREA=1.010, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.07725137316351 | 0.11819944243111485 | 2.009398797385993 | -0.11252238561102687 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.07725137316351 | 0.11819944243111485 | 2.009398797385993 | -0.11252238561102687 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.07725137316351 | 0.11819944243111485 | 2.009398797385993 | -0.11252238561102687 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.07725137316351 | 0.11819944243111485 | 2.009398797385993 | -0.11252238561102687 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.07725137316351 | 0.11819944243111485 | 2.009398797385993 | -0.11252238561102687 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.265546997462242 | 1.2724005753681482 | -1.8403775051464504 | 1.8403775051464504 | AMBIGUOUS |
| 1111 | BVM1 | -1.6351007964480455 | 1.640453224930709 | -1.9750400940459338 | 2.078724764822011 | AMBIGUOUS |
| 1111 | BVM2 | -1.6351007964480455 | 1.640453224930709 | -1.9750400940459338 | 2.078724764822011 | AMBIGUOUS |
| 1111 | BVM3 | -1.6351007964480455 | 1.640453224930709 | -1.9750400940459338 | 2.078724764822011 | AMBIGUOUS |
| 1111 | BVM4 | -1.6351007964480455 | 1.640453224930709 | -1.9750400940459338 | 2.078724764822011 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.591596e-05 | -2.310794e-07 | 0.1211935285189315 | 0.12120470346899935 | 1 |
| 1111 | 0.000165243 | -2.310794e-07 | 0.5535617719659259 | 0.5535729469159938 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.12120470346899935, 0.5535729469159938]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.591596e-05, 0.000165243]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1211935285189315, 0.5535617719659259]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
