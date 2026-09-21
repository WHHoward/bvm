# U134_QB_BJ1_screen_qb_bj1_area_0p65 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780181518084904 | 0.11679187611441016 | 2.0092768846995845 | -0.11120108127347803 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780181518084904 | 0.11679187611441016 | 2.0092768846995845 | -0.11120108127347803 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780181518084904 | 0.11679187611441016 | 2.0092768846995845 | -0.11120108127347803 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780181518084904 | 0.11679187611441016 | 2.0092768846995845 | -0.11120108127347803 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0017292821186706837 | 0.002160926239830212 | -0.002753587416915812 | 0.0037189098932510797 | AMBIGUOUS |
| 0001 | BVM4 | -1.2719234288487586 | 1.2817373523581512 | -1.752309785837311 | 1.752309785837311 | AMBIGUOUS |
| 0011 | BVM3 | -1.5610497097375606 | 1.5696762418785222 | -1.9480433095000167 | 1.9781506500847104 | AMBIGUOUS |
| 0011 | BVM4 | -1.5610497097375606 | 1.5696762418785222 | -1.9480433095000167 | 1.9781506500847104 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -4.262445e-07 | -0.0009209950310282371 | 0.0009209950310282371 | 0 |
| 0001 | 1.074189e-05 | -6.129393e-05 | -0.04919379092057475 | 0.08288670298088645 | 2 |
| 0011 | 2.85752e-05 | -4.264263e-05 | -0.016722749580893856 | 0.07894396436777934 | 4 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [0.0009209950310282371, 0.08288670298088645, 0.07894396436777934]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.074189e-05, 2.85752e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0009209950310282371, -0.04919379092057475, -0.016722749580893856]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
