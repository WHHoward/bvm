# U040_b010_b0_baseline review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0780700661907747 | 0.11364188148073526 | 2.0097510072750553 | -0.11149583622808414 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0780700661907747 | 0.11364188148073526 | 2.0097510072750553 | -0.11149583622808414 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0780700661907747 | 0.11364188148073526 | 2.0097510072750553 | -0.11149583622808414 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0780700661907747 | 0.11364188148073526 | 2.0097510072750553 | -0.11149583622808414 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0780700661907747 | 0.11364188148073526 | 2.0097510072750553 | -0.11149583622808414 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.125971120399074 | 1.1362100990149824 | -1.3131002344579086 | 1.3398977888460633 | AMBIGUOUS |
| 1111 | BVM1 | -1.1504610872673398 | 1.1585567103491348 | -1.37451446643338 | 1.3951864653718136 | AMBIGUOUS |
| 1111 | BVM2 | -1.1504610872673398 | 1.1585567103491348 | -1.37451446643338 | 1.3951864653718136 | AMBIGUOUS |
| 1111 | BVM3 | -1.1504610872673398 | 1.1585567103491348 | -1.37451446643338 | 1.3951864653718136 | AMBIGUOUS |
| 1111 | BVM4 | -1.1504610872673398 | 1.1585567103491348 | -1.37451446643338 | 1.3951864653718136 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.009441e-05 | -2.88348e-07 | 0.09929469398549086 | 0.0993086384327335 | 1 |
| 1111 | 0.0001273275 | -2.88348e-07 | 0.42663677696023483 | 0.4266507214074775 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.0993086384327335, 0.4266507214074775]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.009441e-05, 0.0001273275]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.09929469398549086, 0.42663677696023483]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
