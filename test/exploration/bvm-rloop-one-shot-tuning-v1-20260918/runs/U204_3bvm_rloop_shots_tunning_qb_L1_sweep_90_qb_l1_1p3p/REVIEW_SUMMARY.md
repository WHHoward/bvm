# U204_3bvm_rloop_shots_tunning_qb_L1_sweep_90_qb_l1_1p3p review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.074869868315499 | 0.11047310656377557 | 2.0075729718788424 | -0.11130485029637402 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.074869868315499 | 0.11047310656377557 | 2.0075729718788424 | -0.11130485029637402 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.074869868315499 | 0.11047310656377557 | 2.0075729718788424 | -0.11130485029637402 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.074869868315499 | 0.11047310656377557 | 2.0075729718788424 | -0.11130485029637402 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.074869868315499 | 0.11047310656377557 | 2.0075729718788424 | -0.11130485029637402 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.074869868315499 | 0.11047310656377557 | 2.0075729718788424 | -0.11130485029637402 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.074869868315499 | 0.11047310656377557 | 2.0075729718788424 | -0.11130485029637402 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.026441874921333017 | 0.03654501479331223 | -0.006243616586506433 | 0.033926661331541604 | AMBIGUOUS |
| 001 | BVM3 | -2.3948328060301023 | 2.4247166453282123 | -2.7208922487874294 | 2.721596095607759 | AMBIGUOUS |
| 011 | BVM2 | -2.28698305039331 | 2.3236837823829437 | -3.107780408400087 | 3.139759649847956 | AMBIGUOUS |
| 011 | BVM3 | -2.28698305039331 | 2.3236837823829437 | -3.107780408400087 | 3.139759649847956 | AMBIGUOUS |
| 111 | BVM1 | -2.873446733994912 | 2.8742996930814244 | -2.9833164682539324 | 3.3171606408272187 | AMBIGUOUS |
| 111 | BVM2 | -2.873446733994912 | 2.8742996930814244 | -2.9833164682539324 | 3.3171606408272187 | AMBIGUOUS |
| 111 | BVM3 | -2.873446733994912 | 2.8742996930814244 | -2.9833164682539324 | 3.3171606408272187 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.02525e-06 | -3.345662e-06 | -0.0012081432051304802 | 0.005833758934968361 | 9 |
| 001 | 2.632165e-05 | -4.295539e-05 | 0.03407493497997915 | 0.08707285926001526 | 2 |
| 011 | 7.514455e-05 | -1.380948e-05 | 0.1209284234813436 | 0.1294089548243048 | 7 |
| 111 | 9.472345e-05 | -5.142104e-06 | 0.2096153215932846 | 0.21071943868770604 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005833758934968361, 0.08707285926001526, 0.1294089548243048, 0.21071943868770604]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.02525e-06, 2.632165e-05, 7.514455e-05, 9.472345e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0012081432051304802, 0.03407493497997915, 0.1209284234813436, 0.2096153215932846]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
