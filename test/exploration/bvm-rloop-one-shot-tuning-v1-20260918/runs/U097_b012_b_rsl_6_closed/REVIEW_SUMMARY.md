# U097_b012_b_rsl_6_closed review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.078018694686638 | 0.11438131534634023 | 2.0096434185335252 | -0.11128304606917035 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.078018694686638 | 0.11438131534634023 | 2.0096434185335252 | -0.11128304606917035 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.078018694686638 | 0.11438131534634023 | 2.0096434185335252 | -0.11128304606917035 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.078018694686638 | 0.11438131534634023 | 2.0096434185335252 | -0.11128304606917035 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.078018694686638 | 0.11438131534634023 | 2.0096434185335252 | -0.11128304606917035 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.078018694686638 | 0.11438131534634023 | 2.0096434185335252 | -0.11128304606917035 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.078018694686638 | 0.11438131534634023 | 2.0096434185335252 | -0.11128304606917035 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0638945173814431 | 1.0759855661546174 | -1.1094631240677422 | 1.1125260609475458 | AMBIGUOUS |
| 0011 | BVM3 | -1.1130557285981555 | 1.1231947260788133 | -1.304576898382048 | 1.3160621556953316 | AMBIGUOUS |
| 0011 | BVM4 | -1.1130557285981555 | 1.1231947260788133 | -1.304576898382048 | 1.3160621556953316 | AMBIGUOUS |
| 1111 | BVM1 | -1.9147627854064397 | 1.9219071393933747 | -1.9838298236655416 | 2.0461835472700844 | AMBIGUOUS |
| 1111 | BVM2 | -1.9147627854064397 | 1.9219071393933747 | -1.9838298236655416 | 2.0461835472700844 | AMBIGUOUS |
| 1111 | BVM3 | -1.9147627854064397 | 1.9219071393933747 | -1.9838298236655416 | 2.0461835472700844 | AMBIGUOUS |
| 1111 | BVM4 | -1.9147627854064397 | 1.9219071393933747 | -1.9838298236655416 | 2.0461835472700844 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.268478e-05 | 0.0 | 0.0713831528063854 | 0.0713831528063854 | 0 |
| 0011 | 4.222042e-05 | -7.052808e-05 | 0.041742736793619055 | 0.12856051742605945 | 1 |
| 1111 | 9.985539e-05 | 0.0 | 0.20208743485564623 | 0.20208743485564623 | 0 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.0713831528063854, 0.12856051742605945, 0.20208743485564623]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [2.268478e-05, 4.222042e-05, 9.985539e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": false, "values": [0.0713831528063854, 0.041742736793619055, 0.20208743485564623]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
