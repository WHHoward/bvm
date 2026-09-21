# U138_QB_BJ1_screen_qb_bj1_area_0p85 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780292780281677 | 0.11257554336201964 | 2.0094891973936693 | -0.11125965029253583 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780292780281677 | 0.11257554336201964 | 2.0094891973936693 | -0.11125965029253583 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780292780281677 | 0.11257554336201964 | 2.0094891973936693 | -0.11125965029253583 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780292780281677 | 0.11257554336201964 | 2.0094891973936693 | -0.11125965029253583 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0019050846688099842 | 0.0023403256916833958 | -0.0024944672540678937 | 0.003481689450572613 | AMBIGUOUS |
| 0001 | BVM4 | -1.1463412342414514 | 1.1563246259342483 | -1.373817144965717 | 1.3873079137169015 | AMBIGUOUS |
| 0011 | BVM3 | -1.4717756914527507 | 1.4805859202290286 | -1.9508117460731231 | 1.9581519720485212 | AMBIGUOUS |
| 0011 | BVM4 | -1.4717756914527507 | 1.4805859202290286 | -1.9508117460731231 | 1.9581519720485212 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.006083e-07 | -0.0015559268872650735 | 0.0015559268872650735 | 0 |
| 0001 | 2.036463e-05 | -8.006083e-07 | 0.06344841020563463 | 0.06348712745077376 | 1 |
| 0011 | 3.421432e-05 | -4.654968e-05 | 0.01427289749780718 | 0.10138938853708122 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0015559268872650735, 0.06348712745077376, 0.10138938853708122]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.036463e-05, 3.421432e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0015559268872650735, 0.06344841020563463, 0.01427289749780718]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
