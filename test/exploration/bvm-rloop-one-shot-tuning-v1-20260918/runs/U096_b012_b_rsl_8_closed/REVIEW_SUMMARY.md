# U096_b012_b_rsl_8_closed review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0780266353669397 | 0.1123554320757236 | 2.009468348096124 | -0.11127747564616207 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0780266353669397 | 0.1123554320757236 | 2.009468348096124 | -0.11127747564616207 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0780266353669397 | 0.1123554320757236 | 2.009468348096124 | -0.11127747564616207 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0780266353669397 | 0.1123554320757236 | 2.009468348096124 | -0.11127747564616207 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0780266353669397 | 0.1123554320757236 | 2.009468348096124 | -0.11127747564616207 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0780266353669397 | 0.1123554320757236 | 2.009468348096124 | -0.11127747564616207 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0780266353669397 | 0.1123554320757236 | 2.009468348096124 | -0.11127747564616207 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.0808019130424642 | 1.0919684148357234 | -1.2071178437684138 | 1.2449249413449506 | AMBIGUOUS |
| 0011 | BVM3 | -1.198500494867669 | 1.2081374062493546 | -1.554391701425726 | 1.554391701425726 | AMBIGUOUS |
| 0011 | BVM4 | -1.198500494867669 | 1.2081374062493546 | -1.554391701425726 | 1.554391701425726 | AMBIGUOUS |
| 1111 | BVM1 | -1.962576479466476 | 1.9697427490890749 | -2.0064305736128234 | 2.0424393794873645 | AMBIGUOUS |
| 1111 | BVM2 | -1.962576479466476 | 1.9697427490890749 | -2.0064305736128234 | 2.0424393794873645 | AMBIGUOUS |
| 1111 | BVM3 | -1.962576479466476 | 1.9697427490890749 | -2.0064305736128234 | 2.0424393794873645 | AMBIGUOUS |
| 1111 | BVM4 | -1.962576479466476 | 1.9697427490890749 | -2.0064305736128234 | 2.0424393794873645 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.188689e-05 | -8.280074e-07 | 0.06970031578668688 | 0.06974035804640716 | 1 |
| 0011 | 4.131337e-05 | -5.454641e-05 | 0.029058651041096808 | 0.12316902607351053 | 2 |
| 1111 | 0.0001001552 | -8.280074e-07 | 0.1870577995708484 | 0.18709784183056868 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.06974035804640716, 0.12316902607351053, 0.18709784183056868]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [2.188689e-05, 4.131337e-05, 0.0001001552]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": false, "values": [0.06970031578668688, 0.029058651041096808, 0.1870577995708484]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
