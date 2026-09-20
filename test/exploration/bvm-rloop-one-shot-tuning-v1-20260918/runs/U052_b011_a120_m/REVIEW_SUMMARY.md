# U052_b011_a120_m review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.624, JS2_AREA=0.888, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0775981717845073 | 0.11734700855591454 | 2.0095608171180603 | -0.11220407572484312 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0775981717845073 | 0.11734700855591454 | 2.0095608171180603 | -0.11220407572484312 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0775981717845073 | 0.11734700855591454 | 2.0095608171180603 | -0.11220407572484312 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0775981717845073 | 0.11734700855591454 | 2.0095608171180603 | -0.11220407572484312 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0775981717845073 | 0.11734700855591454 | 2.0095608171180603 | -0.11220407572484312 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.268622300681124 | 1.276213514001778 | -1.8034929810285345 | 1.8034929810285345 | AMBIGUOUS |
| 1111 | BVM1 | -1.5860676572140393 | 1.5920509599756245 | -1.9649270229055058 | 2.0378072544461463 | AMBIGUOUS |
| 1111 | BVM2 | -1.5860676572140393 | 1.5920509599756245 | -1.9649270229055058 | 2.0378072544461463 | AMBIGUOUS |
| 1111 | BVM3 | -1.5860676572140393 | 1.5920509599756245 | -1.9649270229055058 | 2.0378072544461463 | AMBIGUOUS |
| 1111 | BVM4 | -1.5860676572140393 | 1.5920509599756245 | -1.9649270229055058 | 2.0378072544461463 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.435833e-05 | -2.612502e-07 | 0.11993633880684976 | 0.11994897281031444 | 1 |
| 1111 | 0.0001557065 | -2.612502e-07 | 0.5431573837889896 | 0.5431700177924542 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11994897281031444, 0.5431700177924542]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.435833e-05, 0.0001557065]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11993633880684976, 0.5431573837889896]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
