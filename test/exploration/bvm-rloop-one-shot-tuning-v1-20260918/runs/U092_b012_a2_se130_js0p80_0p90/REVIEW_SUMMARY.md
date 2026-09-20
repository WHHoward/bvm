# U092_b012_a2_se130_js0p80_0p90 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.800, JS2_AREA=0.900, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0770567266681086 | 0.12206579346364616 | 2.009397524146448 | -0.11269299971002147 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0770567266681086 | 0.12206579346364616 | 2.009397524146448 | -0.11269299971002147 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0770567266681086 | 0.12206579346364616 | 2.009397524146448 | -0.11269299971002147 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0770567266681086 | 0.12206579346364616 | 2.009397524146448 | -0.11269299971002147 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0770567266681086 | 0.12206579346364616 | 2.009397524146448 | -0.11269299971002147 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.4642539651802506 | 1.4700943308874452 | -1.9563827738701232 | 2.0075701866673383 | AMBIGUOUS |
| 1111 | BVM1 | -1.8858867629544704 | 1.8904058084086217 | -1.9531710271185285 | 2.0452724011363776 | AMBIGUOUS |
| 1111 | BVM2 | -1.8858867629544704 | 1.8904058084086217 | -1.9531710271185285 | 2.0452724011363776 | AMBIGUOUS |
| 1111 | BVM3 | -1.8858867629544704 | 1.8904058084086217 | -1.9531710271185285 | 2.0452724011363776 | AMBIGUOUS |
| 1111 | BVM4 | -1.8858867629544704 | 1.8904058084086217 | -1.9531710271185285 | 2.0452724011363776 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 4.083225e-05 | -3.10611e-07 | 0.13431065233728576 | 0.13432567341841858 | 1 |
| 1111 | 0.0001777288 | -3.10611e-07 | 0.6002519949320413 | 0.6002670160131741 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.13432567341841858, 0.6002670160131741]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [4.083225e-05, 0.0001777288]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.13431065233728576, 0.6002519949320413]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
