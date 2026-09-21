# U133_QB_L1_screen_qb_l1_1p8p review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780311373139326 | 0.11313783777596317 | 2.009519277677913 | -0.11129880240853639 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780311373139326 | 0.11313783777596317 | 2.009519277677913 | -0.11129880240853639 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780311373139326 | 0.11313783777596317 | 2.009519277677913 | -0.11129880240853639 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780311373139326 | 0.11313783777596317 | 2.009519277677913 | -0.11129880240853639 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.001918405937546779 | 0.002346134847106249 | -0.0024980800712760777 | 0.0035369639623084232 | AMBIGUOUS |
| 0001 | BVM4 | -1.1385431831567552 | 1.1485546656970076 | -1.3494336050078972 | 1.368479199582875 | AMBIGUOUS |
| 0011 | BVM3 | -1.392043584964095 | 1.4008864245882127 | -1.9254414454681335 | 1.9254414454681335 | AMBIGUOUS |
| 0011 | BVM4 | -1.392043584964095 | 1.4008864245882127 | -1.9254414454681335 | 1.9254414454681335 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -7.996432e-07 | -0.001653833526957529 | 0.001653833526957529 | 0 |
| 0001 | 2.135906e-05 | -7.996432e-07 | 0.07309836178868849 | 0.07313703236179926 | 1 |
| 0011 | 3.999902e-05 | -3.590343e-05 | 0.04070264466432135 | 0.11091259023631173 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.001653833526957529, 0.07313703236179926, 0.11091259023631173]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.135906e-05, 3.999902e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.001653833526957529, 0.07309836178868849, 0.04070264466432135]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
