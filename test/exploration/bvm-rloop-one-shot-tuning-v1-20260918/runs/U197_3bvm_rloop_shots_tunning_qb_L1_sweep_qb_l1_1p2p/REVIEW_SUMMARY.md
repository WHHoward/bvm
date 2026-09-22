# U197_3bvm_rloop_shots_tunning_qb_L1_sweep_qb_l1_1p2p review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.87, JS2_AREA=0.87, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.07509591684814 | 0.11118675732859973 | 2.0070757718366234 | -0.11107996436178498 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.07509591684814 | 0.11118675732859973 | 2.0070757718366234 | -0.11107996436178498 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.07509591684814 | 0.11118675732859973 | 2.0070757718366234 | -0.11107996436178498 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.07509591684814 | 0.11118675732859973 | 2.0070757718366234 | -0.11107996436178498 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.07509591684814 | 0.11118675732859973 | 2.0070757718366234 | -0.11107996436178498 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.07509591684814 | 0.11118675732859973 | 2.0070757718366234 | -0.11107996436178498 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.07509591684814 | 0.11118675732859973 | 2.0070757718366234 | -0.11107996436178498 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02830865099534079 | 0.039359510806949306 | -0.00844624142142672 | 0.040228576373702606 | AMBIGUOUS |
| 001 | BVM3 | -2.369591516421983 | 2.419100306118914 | -3.048916952697549 | 3.0517192096960626 | AMBIGUOUS |
| 011 | BVM2 | -2.4611024256009615 | 2.4614197805574864 | -3.0125389073550344 | 3.1662595367460464 | AMBIGUOUS |
| 011 | BVM3 | -2.4611024256009615 | 2.4614197805574864 | -3.0125389073550344 | 3.1662595367460464 | AMBIGUOUS |
| 111 | BVM1 | -3.1838711771147543 | 3.184185524042855 | -2.8937536155783983 | 3.3080074013175893 | AMBIGUOUS |
| 111 | BVM2 | -3.1838711771147543 | 3.184185524042855 | -2.8937536155783983 | 3.3080074013175893 | AMBIGUOUS |
| 111 | BVM3 | -3.1838711771147543 | 3.184185524042855 | -2.8937536155783983 | 3.3080074013175893 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.463559e-06 | -3.900306e-06 | -0.0011346093634501807 | 0.006738913472897182 | 9 |
| 001 | 2.655974e-05 | -4.236149e-05 | 0.026479577753773298 | 0.08387285540748132 | 3 |
| 011 | 8.080594e-05 | -1.230947e-05 | 0.12213939325167673 | 0.13101698980410523 | 8 |
| 111 | 0.0001000017 | -4.271867e-06 | 0.21327459176497593 | 0.2142347060710263 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.006738913472897182, 0.08387285540748132, 0.13101698980410523, 0.2142347060710263]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.463559e-06, 2.655974e-05, 8.080594e-05, 0.0001000017]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011346093634501807, 0.026479577753773298, 0.12213939325167673, 0.21327459176497593]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
