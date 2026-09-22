# U149_QB_IB_downard_sweep_qb_ib_252u review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780269174608321 | 0.11265241519953303 | 2.0094777382377664 | -0.11124994184100713 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780269174608321 | 0.11265241519953303 | 2.0094777382377664 | -0.11124994184100713 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780269174608321 | 0.11265241519953303 | 2.0094777382377664 | -0.11124994184100713 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780269174608321 | 0.11265241519953303 | 2.0094777382377664 | -0.11124994184100713 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0018878959349560688 | 0.0023221183661936806 | -0.0025176720447706922 | 0.0034959179024850314 | AMBIGUOUS |
| 0001 | BVM4 | -1.1483006862388216 | 1.1582603001831207 | -1.380054522678454 | 1.3920301363714038 | AMBIGUOUS |
| 0011 | BVM3 | -1.461086781812722 | 1.4698644634031375 | -1.948702561105292 | 1.9540644911380578 | AMBIGUOUS |
| 0011 | BVM4 | -1.461086781812722 | 1.4698644634031375 | -1.948702561105292 | 1.9540644911380578 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -7.829996e-07 | -0.001528852829040256 | 0.001528852829040256 | 0 |
| 0001 | 1.980272e-05 | -7.829996e-07 | 0.06076632531744878 | 0.06080419100964437 | 1 |
| 0011 | 3.288561e-05 | -4.284735e-05 | 0.016808585029023198 | 0.096867956646389 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.001528852829040256, 0.06080419100964437, 0.096867956646389]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.980272e-05, 3.288561e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.001528852829040256, 0.06076632531744878, 0.016808585029023198]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
