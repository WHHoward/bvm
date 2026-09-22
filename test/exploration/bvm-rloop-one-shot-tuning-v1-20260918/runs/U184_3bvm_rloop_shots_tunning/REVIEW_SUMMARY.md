# U184_3bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.74, JS2_AREA=0.74, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0766113281097052 | 0.11569545771145007 | 2.0060321928747697 | -0.10934644872162817 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0766113281097052 | 0.11569545771145007 | 2.0060321928747697 | -0.10934644872162817 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0766113281097052 | 0.11569545771145007 | 2.0060321928747697 | -0.10934644872162817 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0766113281097052 | 0.11569545771145007 | 2.0060321928747697 | -0.10934644872162817 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0766113281097052 | 0.11569545771145007 | 2.0060321928747697 | -0.10934644872162817 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0766113281097052 | 0.11569545771145007 | 2.0060321928747697 | -0.10934644872162817 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0766113281097052 | 0.11569545771145007 | 2.0060321928747697 | -0.10934644872162817 | REVIEW_REQUIRED |

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
| 000 | BVM1 | 0.003406202261064121 | 0.06419130588733918 | 0.00376159524898833 | 0.061695337802157926 | AMBIGUOUS |
| 001 | BVM3 | -3.0004305584395468 | 3.0185735853322506 | -2.980723070287238 | 3.2261276102803675 | AMBIGUOUS |
| 011 | BVM2 | -3.373827153526304 | 3.389488652461813 | -3.0767332897074238 | 3.1177921296727535 | AMBIGUOUS |
| 011 | BVM3 | -3.373827153526304 | 3.389488652461813 | -3.0767332897074238 | 3.1177921296727535 | AMBIGUOUS |
| 111 | BVM1 | -7.392492649695523 | 7.405794135472888 | -7.374219147580473 | 7.396734510900786 | AMBIGUOUS |
| 111 | BVM2 | -7.392492649695523 | 7.405794135472888 | -7.374219147580473 | 7.396734510900786 | AMBIGUOUS |
| 111 | BVM3 | -7.392492649695523 | 7.405794135472888 | -7.374219147580473 | 7.396734510900786 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 3.829529e-06 | -4.378112e-06 | -0.000837586227575868 | 0.009318958393411488 | 10 |
| 001 | 3.356927e-05 | -3.089251e-05 | 0.03498451899796931 | 0.08481341480584947 | 2 |
| 011 | 7.515318e-05 | -5.536457e-06 | 0.16889708000707818 | 0.17030832936970106 | 3 |
| 111 | 0.0003124167 | -4.378112e-06 | 0.7446859175312226 | 0.7448976420856027 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.009318958393411488, 0.08481341480584947, 0.17030832936970106, 0.7448976420856027]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [3.829529e-06, 3.356927e-05, 7.515318e-05, 0.0003124167]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.000837586227575868, 0.03498451899796931, 0.16889708000707818, 0.7446859175312226]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
