# U150_QB_IB_downard_sweep_qb_ib_254u review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780266118274777 | 0.11504960695238307 | 2.009061707216524 | -0.11125774043321873 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780266118274777 | 0.11504960695238307 | 2.009061707216524 | -0.11125774043321873 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780266118274777 | 0.11504960695238307 | 2.009061707216524 | -0.11125774043321873 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780266118274777 | 0.11504960695238307 | 2.009061707216524 | -0.11125774043321873 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0019872245349397146 | 0.0023580396368495207 | -0.0023681778067244745 | 0.003465885364723584 | AMBIGUOUS |
| 0001 | BVM4 | -1.152486699974553 | 1.1624655875824605 | -1.3939356985050433 | 1.4027122978418456 | AMBIGUOUS |
| 0011 | BVM3 | -1.4833389506036434 | 1.49213561937877 | -1.954350492570794 | 1.9638106623881764 | AMBIGUOUS |
| 0011 | BVM4 | -1.4833389506036434 | 1.49213561937877 | -1.954350492570794 | 1.9638106623881764 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -1.231785e-06 | -0.002561698632181398 | 0.002561698632181398 | 0 |
| 0001 | 1.929243e-05 | -1.231785e-06 | 0.05549342527253184 | 0.05555299413011637 | 1 |
| 0011 | 3.114394e-05 | -4.545326e-05 | 0.009103425890918164 | 0.09495785953978629 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.002561698632181398, 0.05555299413011637, 0.09495785953978629]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.929243e-05, 3.114394e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.002561698632181398, 0.05549342527253184, 0.009103425890918164]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
