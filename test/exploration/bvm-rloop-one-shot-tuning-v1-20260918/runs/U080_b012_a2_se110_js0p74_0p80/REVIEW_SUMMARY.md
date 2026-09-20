# U080_b012_a2_se110_js0p74_0p80 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.740, JS2_AREA=0.800, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0774289900800007 | 0.1172413296737016 | 2.009574345288223 | -0.11241543348926915 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0774289900800007 | 0.1172413296737016 | 2.009574345288223 | -0.11241543348926915 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0774289900800007 | 0.1172413296737016 | 2.009574345288223 | -0.11241543348926915 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0774289900800007 | 0.1172413296737016 | 2.009574345288223 | -0.11241543348926915 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0774289900800007 | 0.1172413296737016 | 2.009574345288223 | -0.11241543348926915 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.152221340937936 | 1.1601169540027476 | -1.483498487518599 | 1.483498487518599 | AMBIGUOUS |
| 1111 | BVM1 | -1.349540525298666 | 1.3557458173748762 | -1.9217913064257923 | 1.9275367998714097 | AMBIGUOUS |
| 1111 | BVM2 | -1.349540525298666 | 1.3557458173748762 | -1.9217913064257923 | 1.9275367998714097 | AMBIGUOUS |
| 1111 | BVM3 | -1.349540525298666 | 1.3557458173748762 | -1.9217913064257923 | 1.9275367998714097 | AMBIGUOUS |
| 1111 | BVM4 | -1.349540525298666 | 1.3557458173748762 | -1.9217913064257923 | 1.9275367998714097 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.145704e-05 | -3.317265e-07 | 0.10693545900163635 | 0.10695150122380623 | 1 |
| 1111 | 0.0001444411 | -3.317265e-07 | 0.5078461483695568 | 0.5078621905917265 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10695150122380623, 0.5078621905917265]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.145704e-05, 0.0001444411]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10693545900163635, 0.5078461483695568]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
