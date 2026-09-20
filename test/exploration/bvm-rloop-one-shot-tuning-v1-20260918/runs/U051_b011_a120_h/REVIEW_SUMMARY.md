# U051_b011_a120_h review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.572, JS2_AREA=0.814, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0778532971582835 | 0.11875775797148123 | 2.0096529678301107 | -0.11188528837383002 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0778532971582835 | 0.11875775797148123 | 2.0096529678301107 | -0.11188528837383002 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0778532971582835 | 0.11875775797148123 | 2.0096529678301107 | -0.11188528837383002 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0778532971582835 | 0.11875775797148123 | 2.0096529678301107 | -0.11188528837383002 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0778532971582835 | 0.11875775797148123 | 2.0096529678301107 | -0.11188528837383002 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.5139578470064234 | 1.5213864517217206 | -1.9563255735835758 | 1.9816773644686838 | AMBIGUOUS |
| 1111 | BVM1 | -1.8737457395291655 | 1.8795233504422988 | -1.9480479249933664 | 2.0471202855186403 | AMBIGUOUS |
| 1111 | BVM2 | -1.8737457395291655 | 1.8795233504422988 | -1.9480479249933664 | 2.0471202855186403 | AMBIGUOUS |
| 1111 | BVM3 | -1.8737457395291655 | 1.8795233504422988 | -1.9480479249933664 | 2.0471202855186403 | AMBIGUOUS |
| 1111 | BVM4 | -1.8737457395291655 | 1.8795233504422988 | -1.9480479249933664 | 2.0471202855186403 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.86744e-05 | -2.738634e-07 | 0.13225573292288995 | 0.13226897689799294 | 1 |
| 1111 | 0.0001599803 | -2.738634e-07 | 0.5822427587663704 | 0.5822560027414734 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.13226897689799294, 0.5822560027414734]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.86744e-05, 0.0001599803]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.13225573292288995, 0.5822427587663704]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
