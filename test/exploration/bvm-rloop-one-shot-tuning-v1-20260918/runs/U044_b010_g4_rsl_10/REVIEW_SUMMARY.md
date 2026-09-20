# U044_b010_g4_rsl_10 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0780831168961083 | 0.11356007583998604 | 2.0097744030516895 | -0.11153753482317424 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0780831168961083 | 0.11356007583998604 | 2.0097744030516895 | -0.11153753482317424 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0780831168961083 | 0.11356007583998604 | 2.0097744030516895 | -0.11153753482317424 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0780831168961083 | 0.11356007583998604 | 2.0097744030516895 | -0.11153753482317424 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0780831168961083 | 0.11356007583998604 | 2.0097744030516895 | -0.11153753482317424 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0973588813497857 | 1.1081743191695725 | -1.2402382739047346 | 1.2810233196214638 | AMBIGUOUS |
| 1111 | BVM1 | -1.1011189168803317 | 1.1093541347627127 | -1.2292311180404991 | 1.2948713912198895 | AMBIGUOUS |
| 1111 | BVM2 | -1.1011189168803317 | 1.1093541347627127 | -1.2292311180404991 | 1.2948713912198895 | AMBIGUOUS |
| 1111 | BVM3 | -1.1011189168803317 | 1.1093541347627127 | -1.2292311180404991 | 1.2948713912198895 | AMBIGUOUS |
| 1111 | BVM4 | -1.1011189168803317 | 1.1093541347627127 | -1.2292311180404991 | 1.2948713912198895 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.24243e-05 | -5.730397e-07 | 0.10748066926651836 | 0.1075083813431223 | 1 |
| 1111 | 0.0001423961 | -6.729676e-06 | 0.46951273138024396 | 0.4698658891403349 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1075083813431223, 0.4698658891403349]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.24243e-05, 0.0001423961]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10748066926651836, 0.46951273138024396]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
