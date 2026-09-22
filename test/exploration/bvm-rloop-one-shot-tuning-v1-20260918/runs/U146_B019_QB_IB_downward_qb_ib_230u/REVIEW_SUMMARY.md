# U146_B019_QB_IB_downward_qb_ib_230u review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.078026883827891 | 0.11314038425505271 | 2.009540763595231 | -0.11131869677642284 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.078026883827891 | 0.11314038425505271 | 2.009540763595231 | -0.11131869677642284 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.078026883827891 | 0.11314038425505271 | 2.009540763595231 | -0.11131869677642284 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.078026883827891 | 0.11314038425505271 | 2.009540763595231 | -0.11131869677642284 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0018796676243982109 | 0.0022842554052321168 | -0.0024990668319232493 | 0.0035398764977670047 | AMBIGUOUS |
| 0001 | BVM4 | -1.136562165664596 | 1.146500166367623 | -1.3433076675863127 | 1.3637699003097514 | AMBIGUOUS |
| 0011 | BVM3 | -1.2157909287302293 | 1.224550546234604 | -1.5930976902053513 | 1.5930976902053513 | AMBIGUOUS |
| 0011 | BVM4 | -1.2157909287302293 | 1.224550546234604 | -1.5930976902053513 | 1.5930976902053513 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.519068e-07 | -0.00167198776504407 | 0.00167198776504407 | 0 |
| 0001 | 2.168663e-05 | -8.519068e-07 | 0.07605968621324159 | 0.07610088424280398 | 1 |
| 0011 | 4.23645e-05 | -8.519068e-07 | 0.12716489055168995 | 0.12720608858125235 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.00167198776504407, 0.07610088424280398, 0.12720608858125235]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.168663e-05, 4.23645e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [-0.00167198776504407, 0.07605968621324159, 0.12716489055168995]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
