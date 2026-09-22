# U158_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 0001, 0011, 0111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.074845800204723 | 0.11364506457959711 | 2.0084042381466114 | -0.11129418691518679 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.074845800204723 | 0.11364506457959711 | 2.0084042381466114 | -0.11129418691518679 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.074845800204723 | 0.11364506457959711 | 2.0084042381466114 | -0.11129418691518679 | REVIEW_REQUIRED |
| 0111 | BVM2 | -1.074845800204723 | 0.11364506457959711 | 2.0084042381466114 | -0.11129418691518679 | REVIEW_REQUIRED |
| 0111 | BVM3 | -1.074845800204723 | 0.11364506457959711 | 2.0084042381466114 | -0.11129418691518679 | REVIEW_REQUIRED |
| 0111 | BVM4 | -1.074845800204723 | 0.11364506457959711 | 2.0084042381466114 | -0.11129418691518679 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.3811896464209075 | 2.4371138922964013 | -2.8291639560093467 | 2.8353262603354277 | AMBIGUOUS |
| 0011 | BVM3 | -2.2775447643806035 | 2.3431773026297598 | -3.1158688535939487 | 3.1306515625956814 | AMBIGUOUS |
| 0011 | BVM4 | -2.2775447643806035 | 2.3431773026297598 | -3.1158688535939487 | 3.1306515625956814 | AMBIGUOUS |
| 0111 | BVM2 | -2.6339595270394556 | 2.639200562977449 | -3.0018391115168983 | 3.2574843012528394 | AMBIGUOUS |
| 0111 | BVM3 | -2.6339595270394556 | 2.639200562977449 | -3.0018391115168983 | 3.2574843012528394 | AMBIGUOUS |
| 0111 | BVM4 | -2.6339595270394556 | 2.639200562977449 | -3.0018391115168983 | 3.2574843012528394 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 1.596752e-05 | -5.572993e-05 | -0.0371173713575849 | 0.08013336133281042 | 2 |
| 0011 | 4.417036e-05 | -2.964149e-05 | 0.046886819191867865 | 0.09441345376894128 | 6 |
| 0111 | 7.489127e-05 | -1.729039e-05 | 0.13853616955592052 | 0.14918493504609648 | 5 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.08013336133281042, 0.09441345376894128, 0.14918493504609648]}, "peak_positive_a": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [1.596752e-05, 4.417036e-05, 7.489127e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [-0.0371173713575849, 0.046886819191867865, 0.13853616955592052]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
