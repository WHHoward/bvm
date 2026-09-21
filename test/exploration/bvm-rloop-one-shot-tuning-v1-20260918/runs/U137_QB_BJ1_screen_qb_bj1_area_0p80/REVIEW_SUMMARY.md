# U137_QB_BJ1_screen_qb_bj1_area_0p80 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780274050582608 | 0.12025317781677265 | 2.0093644199182847 | -0.1112526474750398 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780274050582608 | 0.12025317781677265 | 2.0093644199182847 | -0.1112526474750398 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780274050582608 | 0.12025317781677265 | 2.0093644199182847 | -0.1112526474750398 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780274050582608 | 0.12025317781677265 | 2.0093644199182847 | -0.1112526474750398 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0019268093185420341 | 0.0023146380838683675 | -0.0023903480902971726 | 0.003407348176654389 | AMBIGUOUS |
| 0001 | BVM4 | -1.1572985268620162 | 1.1672312436209324 | -1.410137321570923 | 1.4156079544298208 | AMBIGUOUS |
| 0011 | BVM3 | -1.5093720201381509 | 1.5181266242618183 | -1.958675973783157 | 1.9742811159533171 | AMBIGUOUS |
| 0011 | BVM4 | -1.5093720201381509 | 1.5181266242618183 | -1.958675973783157 | 1.9742811159533171 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -1.025756e-06 | -0.002071398071534033 | 0.002071398071534033 | 0 |
| 0001 | 1.920816e-05 | -1.263496e-06 | 0.050068526296799455 | 0.05018401778477899 | 2 |
| 0011 | 2.931676e-05 | -4.990172e-05 | 0.0010927054860744453 | 0.0932523998465857 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.002071398071534033, 0.05018401778477899, 0.0932523998465857]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.920816e-05, 2.931676e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.002071398071534033, 0.050068526296799455, 0.0010927054860744453]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
