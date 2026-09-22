# U155_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.85, JS2_AREA=0.85, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: passive
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0751344532654448 | 0.11199812922848225 | 2.006893539426783 | -0.11114489957856664 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0751344532654448 | 0.11199812922848225 | 2.006893539426783 | -0.11114489957856664 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0751344532654448 | 0.11199812922848225 | 2.006893539426783 | -0.11114489957856664 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0751344532654448 | 0.11199812922848225 | 2.006893539426783 | -0.11114489957856664 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0751344532654448 | 0.11199812922848225 | 2.006893539426783 | -0.11114489957856664 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0751344532654448 | 0.11199812922848225 | 2.006893539426783 | -0.11114489957856664 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0751344532654448 | 0.11199812922848225 | 2.006893539426783 | -0.11114489957856664 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.2765961372577985 | 2.406709218447023 | -2.756350728699747 | 2.761917570721744 | AMBIGUOUS |
| 0011 | BVM3 | -2.2042681733696865 | 2.3809781772480214 | -3.0067030457327295 | 3.0121614236610093 | AMBIGUOUS |
| 0011 | BVM4 | -2.2042681733696865 | 2.3809781772480214 | -3.0067030457327295 | 3.0121614236610093 | AMBIGUOUS |
| 1111 | BVM1 | -2.5765204444156136 | 2.5768524257114085 | -2.7753060824219924 | 3.1198563374536676 | AMBIGUOUS |
| 1111 | BVM2 | -2.5765204444156136 | 2.5768524257114085 | -2.7753060824219924 | 3.1198563374536676 | AMBIGUOUS |
| 1111 | BVM3 | -2.5765204444156136 | 2.5768524257114085 | -2.7753060824219924 | 3.1198563374536676 | AMBIGUOUS |
| 1111 | BVM4 | -2.5765204444156136 | 2.5768524257114085 | -2.7753060824219924 | 3.1198563374536676 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 5.634831e-05 | -5.366532e-06 | 0.17466332635444878 | 0.17500759623894094 | 1 |
| 0011 | 0.0001265147 | -5.366532e-06 | 0.37198042717211577 | 0.3722399515050398 | 1 |
| 1111 | 0.0002725664 | -5.366532e-06 | 0.8000931075773733 | 0.8003526319102974 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.17500759623894094, 0.3722399515050398, 0.8003526319102974]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [5.634831e-05, 0.0001265147, 0.0002725664]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.17466332635444878, 0.37198042717211577, 0.8000931075773733]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
