# U101_b013_s1_rsl12_closed review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.74, JS2_AREA=0.90, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0771893919748357 | 0.11467049987793834 | 2.009224841033193 | -0.11236100249873175 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0771893919748357 | 0.11467049987793834 | 2.009224841033193 | -0.11236100249873175 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0771893919748357 | 0.11467049987793834 | 2.009224841033193 | -0.11236100249873175 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0771893919748357 | 0.11467049987793834 | 2.009224841033193 | -0.11236100249873175 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0771893919748357 | 0.11467049987793834 | 2.009224841033193 | -0.11236100249873175 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0771893919748357 | 0.11467049987793834 | 2.009224841033193 | -0.11236100249873175 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0771893919748357 | 0.11467049987793834 | 2.009224841033193 | -0.11236100249873175 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0787244476547915 | 1.113091888601226 | -1.2731967479709654 | 1.3136749429574133 | AMBIGUOUS |
| 0011 | BVM3 | -1.2154831071547951 | 1.22301072216019 | -1.7535158619960611 | 1.7535158619960611 | AMBIGUOUS |
| 0011 | BVM4 | -1.2154831071547951 | 1.22301072216019 | -1.7535158619960611 | 1.7535158619960611 | AMBIGUOUS |
| 1111 | BVM1 | -1.7751197927037698 | 1.7811736011051449 | -1.9401934693968381 | 2.060646704977077 | AMBIGUOUS |
| 1111 | BVM2 | -1.7751197927037698 | 1.7811736011051449 | -1.9401934693968381 | 2.060646704977077 | AMBIGUOUS |
| 1111 | BVM3 | -1.7751197927037698 | 1.7811736011051449 | -1.9401934693968381 | 2.060646704977077 | AMBIGUOUS |
| 1111 | BVM4 | -1.7751197927037698 | 1.7811736011051449 | -1.9401934693968381 | 2.060646704977077 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.143184e-05 | -8.673845e-07 | 0.06519177334067892 | 0.06523371986848332 | 1 |
| 0011 | 4.109065e-05 | -4.516361e-05 | 0.032323448075698695 | 0.10996894740113558 | 2 |
| 1111 | 9.918004e-05 | -1.147756e-05 | 0.15181549287368098 | 0.15795644991540927 | 4 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.06523371986848332, 0.10996894740113558, 0.15795644991540927]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [2.143184e-05, 4.109065e-05, 9.918004e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": false, "values": [0.06519177334067892, 0.032323448075698695, 0.15181549287368098]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
