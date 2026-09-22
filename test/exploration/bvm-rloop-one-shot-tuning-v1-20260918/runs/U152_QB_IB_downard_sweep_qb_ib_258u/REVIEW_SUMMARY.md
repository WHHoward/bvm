# U152_QB_IB_downard_sweep_qb_ib_258u review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780256992163229 | 0.11986165665676657 | 2.009284524136853 | -0.11123784606533216 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780256992163229 | 0.11986165665676657 | 2.009284524136853 | -0.11123784606533216 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780256992163229 | 0.11986165665676657 | 2.009284524136853 | -0.11123784606533216 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780256992163229 | 0.11986165665676657 | 2.009284524136853 | -0.11123784606533216 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.001923530726714335 | 0.0023162137178049692 | -0.002428943163996958 | 0.003448346489994861 | AMBIGUOUS |
| 0001 | BVM4 | -1.1663643584768997 | 1.1762961043906632 | -1.4411655804028296 | 1.4422136157030898 | AMBIGUOUS |
| 0011 | BVM3 | -1.524621976221813 | 1.5333705483731372 | -1.959484846950433 | 1.9799919613678236 | AMBIGUOUS |
| 0011 | BVM4 | -1.524621976221813 | 1.5333705483731372 | -1.959484846950433 | 1.9799919613678236 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -1.00851e-06 | -0.002061905872719808 | 0.002061905872719808 | 0 |
| 0001 | 1.834853e-05 | -1.144968e-05 | 0.039157126061319845 | 0.04382502398229429 | 2 |
| 0011 | 2.620535e-05 | -4.949093e-05 | -0.0018838612607911976 | 0.08659865621853385 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.002061905872719808, 0.04382502398229429, 0.08659865621853385]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.834853e-05, 2.620535e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.002061905872719808, 0.039157126061319845, -0.0018838612607911976]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
