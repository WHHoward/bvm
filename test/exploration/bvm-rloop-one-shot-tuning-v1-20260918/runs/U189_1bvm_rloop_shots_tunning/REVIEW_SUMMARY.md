# U189_1bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=1; bit order: mask left-to-right: b0=BVM1 (rightmost bit is highest-index BVM)
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 0, 1
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0 | BVM1 | -1.0752973675549262 | 0.11085698828651344 | 2.008951253686018 | -0.11203887289391368 | REVIEW_REQUIRED |
| 1 | BVM1 | -1.0752973675549262 | 0.11085698828651344 | 2.008951253686018 | -0.11203887289391368 | REVIEW_REQUIRED |

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
| 0 | BVM1 | -0.019196043742682606 | 0.025554681606561564 | -0.008520964667208366 | 0.022935771102490107 | AMBIGUOUS |
| 1 | BVM1 | -2.278161967249914 | 2.381932406624823 | -3.187546765032496 | 3.188018341128877 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0 | 1.075068e-06 | -1.226802e-06 | -0.00014516385989635127 | 0.0022827172268049625 | 9 |
| 1 | 6.076777e-05 | -1.94936e-06 | 0.13456563864361318 | 0.13508797469640807 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0", "1"], "nondecreasing": true, "values": [0.0022827172268049625, 0.13508797469640807]}, "peak_positive_a": {"masks": ["0", "1"], "nondecreasing": true, "values": [1.075068e-06, 6.076777e-05]}, "signed_area_phi0": {"masks": ["0", "1"], "nondecreasing": true, "values": [-0.00014516385989635127, 0.13456563864361318]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
