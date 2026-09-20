# U067_b012_a1_se100_a1 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=1.000, JS2_AREA=1.000, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0763153829431866 | 0.11232376024204813 | 2.0091420804627855 | -0.11313592791664623 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0763153829431866 | 0.11232376024204813 | 2.0091420804627855 | -0.11313592791664623 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0763153829431866 | 0.11232376024204813 | 2.0091420804627855 | -0.11313592791664623 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0763153829431866 | 0.11232376024204813 | 2.0091420804627855 | -0.11313592791664623 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0763153829431866 | 0.11232376024204813 | 2.0091420804627855 | -0.11313592791664623 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -0.040067785317795715 | 0.06009500938457803 | -0.14588885337387367 | 0.2113219068173584 | AMBIGUOUS |
| 1111 | BVM1 | -0.03843700578495404 | 0.06819964381925116 | -0.13640178637110886 | 0.24140028120240956 | AMBIGUOUS |
| 1111 | BVM2 | -0.03843700578495404 | 0.06819964381925116 | -0.13640178637110886 | 0.24140028120240956 | AMBIGUOUS |
| 1111 | BVM3 | -0.03843700578495404 | 0.06819964381925116 | -0.13640178637110886 | 0.24140028120240956 | AMBIGUOUS |
| 1111 | BVM4 | -0.03843700578495404 | 0.06819964381925116 | -0.13640178637110886 | 0.24140028120240956 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 1.120151e-05 | -1.114173e-05 | 0.01763131397634427 | 0.022957035092985793 | 2 |
| 1111 | 4.972975e-05 | -4.520871e-05 | 0.07073473859926903 | 0.09241074648227704 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.022957035092985793, 0.09241074648227704]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [1.120151e-05, 4.972975e-05]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.01763131397634427, 0.07073473859926903]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
