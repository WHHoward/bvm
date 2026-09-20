# U022_js2_shunt_sweep_rsh_js2_16 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=16
- Mode: passive
- Masks: 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 1111 | BVM1 | -1.0780500126679453 | 0.11367562232867079 | 2.0096943481153144 | -0.11143710805408322 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0780500126679453 | 0.11367562232867079 | 2.0096943481153144 | -0.11143710805408322 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0780500126679453 | 0.11367562232867079 | 2.0096943481153144 | -0.11143710805408322 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0780500126679453 | 0.11367562232867079 | 2.0096943481153144 | -0.11143710805408322 | REVIEW_REQUIRED |

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
| 1111 | BVM1 | -1.1067892255308325 | 1.1152303899095746 | -1.250422503220219 | 1.305474516345592 | AMBIGUOUS |
| 1111 | BVM2 | -1.1067892255308325 | 1.1152303899095746 | -1.250422503220219 | 1.305474516345592 | AMBIGUOUS |
| 1111 | BVM3 | -1.1067892255308325 | 1.1152303899095746 | -1.250422503220219 | 1.305474516345592 | AMBIGUOUS |
| 1111 | BVM4 | -1.1067892255308325 | 1.1152303899095746 | -1.250422503220219 | 1.305474516345592 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 1111 | 0.0001217473 | -5.037417e-06 | 0.3991353917232136 | 0.39939328571238286 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.39939328571238286]}, "peak_positive_a": {"masks": ["1111"], "nondecreasing": true, "values": [0.0001217473]}, "signed_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.3991353917232136]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
