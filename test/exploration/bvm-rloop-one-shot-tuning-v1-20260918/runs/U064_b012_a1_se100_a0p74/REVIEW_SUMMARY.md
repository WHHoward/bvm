# U064_b012_a1_se100_a0p74 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.740, JS2_AREA=0.740, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0775653858662304 | 0.11544797177494208 | 2.0096599706476064 | -0.11231230108614561 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0775653858662304 | 0.11544797177494208 | 2.0096599706476064 | -0.11231230108614561 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0775653858662304 | 0.11544797177494208 | 2.0096599706476064 | -0.11231230108614561 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0775653858662304 | 0.11544797177494208 | 2.0096599706476064 | -0.11231230108614561 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0775653858662304 | 0.11544797177494208 | 2.0096599706476064 | -0.11231230108614561 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.082350872610612 | 1.1117645682068282 | -1.2883218629172664 | 1.3243554969629299 | AMBIGUOUS |
| 1111 | BVM1 | -1.1445405074688269 | 1.151539250598327 | -1.4404967476699801 | 1.4496763273226916 | AMBIGUOUS |
| 1111 | BVM2 | -1.1445405074688269 | 1.151539250598327 | -1.4404967476699801 | 1.4496763273226916 | AMBIGUOUS |
| 1111 | BVM3 | -1.1445405074688269 | 1.151539250598327 | -1.4404967476699801 | 1.4496763273226916 | AMBIGUOUS |
| 1111 | BVM4 | -1.1445405074688269 | 1.151539250598327 | -1.4404967476699801 | 1.4496763273226916 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.867026e-05 | -3.568929e-07 | 0.09534945331594166 | 0.09536671257980105 | 1 |
| 1111 | 0.000121729 | -3.568929e-07 | 0.4296686400671588 | 0.4296858993310182 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09536671257980105, 0.4296858993310182]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [2.867026e-05, 0.000121729]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09534945331594166, 0.4296686400671588]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
