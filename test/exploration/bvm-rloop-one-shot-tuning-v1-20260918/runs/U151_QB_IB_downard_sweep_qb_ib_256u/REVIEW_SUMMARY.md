# U151_QB_IB_downard_sweep_qb_ib_256u review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780261518348375 | 0.12009290878907919 | 2.0093617142842524 | -0.1112403925444217 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780261518348375 | 0.12009290878907919 | 2.0093617142842524 | -0.1112403925444217 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780261518348375 | 0.12009290878907919 | 2.0093617142842524 | -0.1112403925444217 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780261518348375 | 0.12009290878907919 | 2.0093617142842524 | -0.1112403925444217 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0019158435429630053 | 0.002297178786611179 | -0.0023788252724173237 | 0.003399263105545318 | AMBIGUOUS |
| 0001 | BVM4 | -1.1581348224259869 | 1.168052435380804 | -1.412737197143801 | 1.417785591938676 | AMBIGUOUS |
| 0011 | BVM3 | -1.5045516307147493 | 1.5132865473719563 | -1.9583809800961363 | 1.9729277418947355 | AMBIGUOUS |
| 0011 | BVM4 | -1.5045516307147493 | 1.5132865473719563 | -1.9583809800961363 | 1.9729277418947355 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -1.051017e-06 | -0.002149867661901237 | 0.002149867661901237 | 0 |
| 0001 | 1.888546e-05 | -1.190745e-06 | 0.04896106492546398 | 0.049069476053474476 | 2 |
| 0011 | 2.886369e-05 | -4.791078e-05 | 0.0027269083323371726 | 0.09191594161872907 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.002149867661901237, 0.049069476053474476, 0.09191594161872907]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.888546e-05, 2.886369e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.002149867661901237, 0.04896106492546398, 0.0027269083323371726]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
