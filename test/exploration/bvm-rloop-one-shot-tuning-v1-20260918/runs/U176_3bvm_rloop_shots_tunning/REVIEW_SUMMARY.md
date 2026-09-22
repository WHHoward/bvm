# U176_3bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0748663324083256 | 0.11048647557899546 | 2.0076075085014935 | -0.11133747705970776 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0748663324083256 | 0.11048647557899546 | 2.0076075085014935 | -0.11133747705970776 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0748663324083256 | 0.11048647557899546 | 2.0076075085014935 | -0.11133747705970776 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0748663324083256 | 0.11048647557899546 | 2.0076075085014935 | -0.11133747705970776 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0748663324083256 | 0.11048647557899546 | 2.0076075085014935 | -0.11133747705970776 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0748663324083256 | 0.11048647557899546 | 2.0076075085014935 | -0.11133747705970776 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0748663324083256 | 0.11048647557899546 | 2.0076075085014935 | -0.11133747705970776 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02630551096609188 | 0.03645012661624084 | -0.005945041913266039 | 0.03395376541835016 | AMBIGUOUS |
| 001 | BVM3 | -2.390323405365503 | 2.421486436603219 | -2.6581529564177524 | 2.6589019873264257 | AMBIGUOUS |
| 011 | BVM2 | -2.2773138464736715 | 2.328478165888644 | -3.106544952238842 | 3.136763144241399 | AMBIGUOUS |
| 011 | BVM3 | -2.2773138464736715 | 2.328478165888644 | -3.106544952238842 | 3.136763144241399 | AMBIGUOUS |
| 111 | BVM1 | -2.8498005429729423 | 2.85068332769579 | -2.9804592232225806 | 3.3120468651817214 | AMBIGUOUS |
| 111 | BVM2 | -2.8498005429729423 | 2.85068332769579 | -2.9804592232225806 | 3.3120468651817214 | AMBIGUOUS |
| 111 | BVM3 | -2.8498005429729423 | 2.85068332769579 | -2.9804592232225806 | 3.3120468651817214 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 1.992156e-06 | -3.27544e-06 | -0.0011414170569278804 | 0.005776053056947547 | 9 |
| 001 | 3.694316e-05 | -1.889352e-05 | 0.06913844029987076 | 0.0853478758657015 | 2 |
| 011 | 8.58707e-05 | -6.057825e-06 | 0.12799230956055044 | 0.13072175500388664 | 5 |
| 111 | 0.0001004561 | -3.042869e-06 | 0.21499661785205437 | 0.21571666109993917 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005776053056947547, 0.0853478758657015, 0.13072175500388664, 0.21571666109993917]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [1.992156e-06, 3.694316e-05, 8.58707e-05, 0.0001004561]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011414170569278804, 0.06913844029987076, 0.12799230956055044, 0.21499661785205437]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
