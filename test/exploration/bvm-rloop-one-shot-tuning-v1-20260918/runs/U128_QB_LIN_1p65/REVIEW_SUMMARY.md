# U128_QB_LIN_1p65 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.0780284643340379 | 0.11307783636241762 | 2.0095055903528074 | -0.11128240944939803 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.0780284643340379 | 0.11307783636241762 | 2.0095055903528074 | -0.11128240944939803 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780284643340379 | 0.11307783636241762 | 2.0095055903528074 | -0.11128240944939803 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780284643340379 | 0.11307783636241762 | 2.0095055903528074 | -0.11128240944939803 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.001911419035545047 | 0.00233902062115004 | -0.002483135422119752 | 0.0034910795922150355 | AMBIGUOUS |
| 0001 | BVM4 | -1.1411533878854394 | 1.1511341694371695 | -1.3573458815952502 | 1.374738811241162 | AMBIGUOUS |
| 0011 | BVM3 | -1.4296279292822802 | 1.4384301048184378 | -1.9407827564891302 | 1.942414094655822 | AMBIGUOUS |
| 0011 | BVM4 | -1.4296279292822802 | 1.4384301048184378 | -1.9407827564891302 | 1.942414094655822 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -8.358008e-07 | -0.001647786804919347 | 0.001647786804919347 | 0 |
| 0001 | 2.103275e-05 | -8.358008e-07 | 0.06980210816241553 | 0.06984252730928307 | 1 |
| 0011 | 3.810598e-05 | -4.067262e-05 | 0.02982779540999193 | 0.10693060085744353 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.001647786804919347, 0.06984252730928307, 0.10693060085744353]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 2.103275e-05, 3.810598e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.001647786804919347, 0.06980210816241553, 0.02982779540999193]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
