# U126_QB_LIN_1p35 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780324376044064 | 0.11308404340519822 | 2.009510842465929 | -0.11128670663286142 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780324376044064 | 0.11308404340519822 | 2.009510842465929 | -0.11128670663286142 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780324376044064 | 0.11308404340519822 | 2.009510842465929 | -0.11128670663286142 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780324376044064 | 0.11308404340519822 | 2.009510842465929 | -0.11128670663286142 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.001916145937354871 | 0.0023471852697306505 | -0.0024767214779131495 | 0.0034821828308961946 | AMBIGUOUS |
| 0001 | BVM4 | -1.1408765060309425 | 1.150883404908834 | -1.3565369447659972 | 1.3740882335802853 | AMBIGUOUS |
| 0011 | BVM3 | -1.433318621004121 | 1.4421670469667411 | -1.942242255063766 | 1.944398804542661 | AMBIGUOUS |
| 0011 | BVM4 | -1.433318621004121 | 1.4421670469667411 | -1.942242255063766 | 1.944398804542661 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.278042e-07 | -0.001617029529830967 | 0.001617029529830967 | 0 |
| 0001 | 2.117727e-05 | -8.278042e-07 | 0.0702833987027375 | 0.0703234311357495 | 1 |
| 0011 | 3.805077e-05 | -4.153928e-05 | 0.02832119754043234 | 0.10816737076159882 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.001617029529830967, 0.0703234311357495, 0.10816737076159882]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.117727e-05, 3.805077e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.001617029529830967, 0.0702833987027375, 0.02832119754043234]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
