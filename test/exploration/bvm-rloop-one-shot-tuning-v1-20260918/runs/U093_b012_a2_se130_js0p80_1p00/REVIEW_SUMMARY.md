# U093_b012_a2_se130_js0p80_1p00 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.800, JS2_AREA=1.000, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.076858260454073 | 0.11948239042737857 | 2.009279112868788 | -0.11280424901524272 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.076858260454073 | 0.11948239042737857 | 2.009279112868788 | -0.11280424901524272 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.076858260454073 | 0.11948239042737857 | 2.009279112868788 | -0.11280424901524272 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.076858260454073 | 0.11948239042737857 | 2.009279112868788 | -0.11280424901524272 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.076858260454073 | 0.11948239042737857 | 2.009279112868788 | -0.11280424901524272 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.25030095659018 | 1.256591555715887 | -1.8508878906868131 | 1.8508878906868131 | AMBIGUOUS |
| 1111 | BVM1 | -1.6400017023571574 | 1.644953426439598 | -1.918025811880698 | 2.067370444280409 | AMBIGUOUS |
| 1111 | BVM2 | -1.6400017023571574 | 1.644953426439598 | -1.918025811880698 | 2.067370444280409 | AMBIGUOUS |
| 1111 | BVM3 | -1.6400017023571574 | 1.644953426439598 | -1.918025811880698 | 2.067370444280409 | AMBIGUOUS |
| 1111 | BVM4 | -1.6400017023571574 | 1.644953426439598 | -1.918025811880698 | 2.067370444280409 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.540615e-05 | -2.714945e-07 | 0.12126753772675447 | 0.12128066714236312 | 1 |
| 1111 | 0.0001727929 | -2.714945e-07 | 0.5642819827635394 | 0.5642951121791481 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.12128066714236312, 0.5642951121791481]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.540615e-05, 0.0001727929]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.12126753772675447, 0.5642819827635394]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
