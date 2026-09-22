# U160_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 0001, 0011, 0111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0748295270606087 | 0.11041008120631128 | 2.0072400197378943 | -0.11116511225633917 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0748295270606087 | 0.11041008120631128 | 2.0072400197378943 | -0.11116511225633917 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0748295270606087 | 0.11041008120631128 | 2.0072400197378943 | -0.11116511225633917 | REVIEW_REQUIRED |
| 0111 | BVM2 | -1.0748295270606087 | 0.11041008120631128 | 2.0072400197378943 | -0.11116511225633917 | REVIEW_REQUIRED |
| 0111 | BVM3 | -1.0748295270606087 | 0.11041008120631128 | 2.0072400197378943 | -0.11116511225633917 | REVIEW_REQUIRED |
| 0111 | BVM4 | -1.0748295270606087 | 0.11041008120631128 | 2.0072400197378943 | -0.11116511225633917 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.4083657030947236 | 2.424589591937142 | -2.5352748520400596 | 2.536593673560496 | AMBIGUOUS |
| 0011 | BVM3 | -2.23691763219841 | 2.3530422830448963 | -3.0927023078239753 | 3.093906951588238 | AMBIGUOUS |
| 0011 | BVM4 | -2.23691763219841 | 2.3530422830448963 | -3.0927023078239753 | 3.093906951588238 | AMBIGUOUS |
| 0111 | BVM2 | -2.4930584145116446 | 2.493879303877124 | -3.0555889666443763 | 3.2192641647679903 | AMBIGUOUS |
| 0111 | BVM3 | -2.4930584145116446 | 2.493879303877124 | -3.0555889666443763 | 3.2192641647679903 | AMBIGUOUS |
| 0111 | BVM4 | -2.4930584145116446 | 2.493879303877124 | -3.0555889666443763 | 3.2192641647679903 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.998716e-05 | -2.261746e-05 | 0.05246321630963075 | 0.0723097802681871 | 2 |
| 0011 | 6.836817e-05 | -2.557624e-05 | 0.06487593326695566 | 0.08718364623171597 | 5 |
| 0111 | 8.480361e-05 | -1.04689e-05 | 0.15778453299599898 | 0.1635747942452674 | 5 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.0723097802681871, 0.08718364623171597, 0.1635747942452674]}, "peak_positive_a": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [2.998716e-05, 6.836817e-05, 8.480361e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.05246321630963075, 0.06487593326695566, 0.15778453299599898]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
