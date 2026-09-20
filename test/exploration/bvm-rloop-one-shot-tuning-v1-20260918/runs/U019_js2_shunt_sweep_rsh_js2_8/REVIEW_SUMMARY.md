# U019_js2_shunt_sweep_rsh_js2_8 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=8
- Mode: passive
- Masks: 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 1111 | BVM1 | -1.0779904887192289 | 0.11377095613958288 | 2.0095765734574265 | -0.11131630945227654 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0779904887192289 | 0.11377095613958288 | 2.0095765734574265 | -0.11131630945227654 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0779904887192289 | 0.11377095613958288 | 2.0095765734574265 | -0.11131630945227654 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0779904887192289 | 0.11377095613958288 | 2.0095765734574265 | -0.11131630945227654 | REVIEW_REQUIRED |

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
| 1111 | BVM1 | -1.0433510519750502 | 1.0535060604429831 | -1.0704056575117926 | 1.0718512618598963 | AMBIGUOUS |
| 1111 | BVM2 | -1.0433510519750502 | 1.0535060604429831 | -1.0704056575117926 | 1.0718512618598963 | AMBIGUOUS |
| 1111 | BVM3 | -1.0433510519750502 | 1.0535060604429831 | -1.0704056575117926 | 1.0718512618598963 | AMBIGUOUS |
| 1111 | BVM4 | -1.0433510519750502 | 1.0535060604429831 | -1.0704056575117926 | 1.0718512618598963 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 1111 | 0.0001018323 | -3.320834e-07 | 0.30090488456401343 | 0.30092094404579056 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.30092094404579056]}, "peak_positive_a": {"masks": ["1111"], "nondecreasing": true, "values": [0.0001018323]}, "signed_area_phi0": {"masks": ["1111"], "nondecreasing": true, "values": [0.30090488456401343]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
