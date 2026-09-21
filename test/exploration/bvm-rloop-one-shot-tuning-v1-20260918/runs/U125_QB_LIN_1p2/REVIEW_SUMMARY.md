# U125_QB_LIN_1p2 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780343449407994 | 0.11308706734911697 | 2.009513707254905 | -0.11128893480206473 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780343449407994 | 0.11308706734911697 | 2.009513707254905 | -0.11128893480206473 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780343449407994 | 0.11308706734911697 | 2.009513707254905 | -0.11128893480206473 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780343449407994 | 0.11308706734911697 | 2.009513707254905 | -0.11128893480206473 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.00191835819106385 | 0.0023511641433079473 | -0.0024738248579488733 | 0.0034779174784213373 | AMBIGUOUS |
| 0001 | BVM4 | -1.1407382799628671 | 1.1507584523630126 | -1.3561316089569309 | 1.3737634301724235 | AMBIGUOUS |
| 0011 | BVM3 | -1.4351629880621417 | 1.4440349848718335 | -1.9429707390692859 | 1.945386711105421 | AMBIGUOUS |
| 0011 | BVM4 | -1.4351629880621417 | 1.4440349848718335 | -1.9429707390692859 | 1.945386711105421 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.239955e-07 | -0.0016006824352456381 | 0.0016006824352456381 | 0 |
| 0001 | 2.123987e-05 | -8.239955e-07 | 0.07052580435127877 | 0.07056565259637819 | 1 |
| 0011 | 3.803582e-05 | -4.199205e-05 | 0.027556880694314053 | 0.10879390083133972 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0016006824352456381, 0.07056565259637819, 0.10879390083133972]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.123987e-05, 3.803582e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0016006824352456381, 0.07052580435127877, 0.027556880694314053]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
