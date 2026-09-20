# U104_b013_s2_rsl6_closed review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=1.00, JS2_AREA=1.00, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.076218246928544 | 0.11621812254456383 | 2.00879225789787 | -0.11288382648678862 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.076218246928544 | 0.11621812254456383 | 2.00879225789787 | -0.11288382648678862 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.076218246928544 | 0.11621812254456383 | 2.00879225789787 | -0.11288382648678862 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.076218246928544 | 0.11621812254456383 | 2.00879225789787 | -0.11288382648678862 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.076218246928544 | 0.11621812254456383 | 2.00879225789787 | -0.11288382648678862 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.076218246928544 | 0.11621812254456383 | 2.00879225789787 | -0.11288382648678862 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.076218246928544 | 0.11621812254456383 | 2.00879225789787 | -0.11288382648678862 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -0.39902679571381616 | 0.407117453161387 | -0.9002852094042689 | 0.9624442865134104 | AMBIGUOUS |
| 0011 | BVM3 | -0.7182128298593278 | 0.7250151917045469 | -1.0015080715206006 | 1.0045749872739813 | AMBIGUOUS |
| 0011 | BVM4 | -0.7182128298593278 | 0.7250151917045469 | -1.0015080715206006 | 1.0045749872739813 | AMBIGUOUS |
| 1111 | BVM1 | -1.5198245528566996 | 1.5246805770718594 | -1.9128103362265654 | 2.068116912794499 | AMBIGUOUS |
| 1111 | BVM2 | -1.5198245528566996 | 1.5246805770718594 | -1.9128103362265654 | 2.068116912794499 | AMBIGUOUS |
| 1111 | BVM3 | -1.5198245528566996 | 1.5246805770718594 | -1.9128103362265654 | 2.068116912794499 | AMBIGUOUS |
| 1111 | BVM4 | -1.5198245528566996 | 1.5246805770718594 | -1.9128103362265654 | 2.068116912794499 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.358386e-05 | -4.849313e-07 | 0.05700954921935291 | 0.057033000392689145 | 1 |
| 0011 | 4.382312e-05 | -5.24844e-05 | 0.07354294503984754 | 0.10801715997686849 | 2 |
| 1111 | 0.0001048711 | -6.418444e-06 | 0.1819882188140873 | 0.18407067118431275 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.057033000392689145, 0.10801715997686849, 0.18407067118431275]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [2.358386e-05, 4.382312e-05, 0.0001048711]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.05700954921935291, 0.07354294503984754, 0.1819882188140873]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
