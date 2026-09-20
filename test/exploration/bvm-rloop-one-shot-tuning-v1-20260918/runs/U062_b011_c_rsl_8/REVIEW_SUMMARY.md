# U062_b011_c_rsl_8 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.078094735206954 | 0.11339184906513786 | 2.00977854108021 | -0.11157732355894727 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.078094735206954 | 0.11339184906513786 | 2.00977854108021 | -0.11157732355894727 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.078094735206954 | 0.11339184906513786 | 2.00977854108021 | -0.11157732355894727 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.078094735206954 | 0.11339184906513786 | 2.00977854108021 | -0.11157732355894727 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.078094735206954 | 0.11339184906513786 | 2.00977854108021 | -0.11157732355894727 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.072763076444364 | 1.084286037563666 | -1.1841460240713133 | 1.2127114715673328 | AMBIGUOUS |
| 1111 | BVM1 | -1.0701397255173803 | 1.0811097027869097 | -1.154441504647585 | 1.2488495112556646 | AMBIGUOUS |
| 1111 | BVM2 | -1.0701397255173803 | 1.0811097027869097 | -1.154441504647585 | 1.2488495112556646 | AMBIGUOUS |
| 1111 | BVM3 | -1.0701397255173803 | 1.0811097027869097 | -1.154441504647585 | 1.2488495112556646 | AMBIGUOUS |
| 1111 | BVM4 | -1.0701397255173803 | 1.0811097027869097 | -1.154441504647585 | 1.2488495112556646 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.589225e-05 | -1.06473e-06 | 0.11445598945433257 | 0.11450747956805855 | 1 |
| 1111 | 0.0001607235 | -1.06473e-06 | 0.5335438315399894 | 0.5335953216537154 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11450747956805855, 0.5335953216537154]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.589225e-05, 0.0001607235]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.11445598945433257, 0.5335438315399894]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
