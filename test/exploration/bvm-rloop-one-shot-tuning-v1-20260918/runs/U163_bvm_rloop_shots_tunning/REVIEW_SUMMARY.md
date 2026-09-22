# U163_bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 0001, 0011, 0111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.07483941416563 | 0.11022227837346288 | 2.007291585939456 | -0.11114362633902188 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.07483941416563 | 0.11022227837346288 | 2.007291585939456 | -0.11114362633902188 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.07483941416563 | 0.11022227837346288 | 2.007291585939456 | -0.11114362633902188 | REVIEW_REQUIRED |
| 0111 | BVM2 | -1.07483941416563 | 0.11022227837346288 | 2.007291585939456 | -0.11114362633902188 | REVIEW_REQUIRED |
| 0111 | BVM3 | -1.07483941416563 | 0.11022227837346288 | 2.007291585939456 | -0.11114362633902188 | REVIEW_REQUIRED |
| 0111 | BVM4 | -1.07483941416563 | 0.11022227837346288 | 2.007291585939456 | -0.11114362633902188 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.4138624055333 | 2.428996242170482 | -2.561781566685208 | 2.563283289066246 | AMBIGUOUS |
| 0011 | BVM3 | -2.235429024184683 | 2.339561525139632 | -3.0900056819611916 | 3.0913931947550672 | AMBIGUOUS |
| 0011 | BVM4 | -2.235429024184683 | 2.339561525139632 | -3.0900056819611916 | 3.0913931947550672 | AMBIGUOUS |
| 0111 | BVM2 | -2.524457583938427 | 2.5252420427374322 | -3.071602595891476 | 3.236122731692471 | AMBIGUOUS |
| 0111 | BVM3 | -2.524457583938427 | 2.5252420427374322 | -3.071602595891476 | 3.236122731692471 | AMBIGUOUS |
| 0111 | BVM4 | -2.524457583938427 | 2.5252420427374322 | -3.071602595891476 | 3.236122731692471 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.723127e-05 | -4.094284e-05 | 0.03782533161242668 | 0.07716849169208476 | 2 |
| 0011 | 5.680032e-05 | -2.831528e-05 | 0.05180290247865215 | 0.09496949441075214 | 5 |
| 0111 | 6.723552e-05 | -2.634569e-05 | 0.13355380209928733 | 0.15140325552403852 | 7 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.07716849169208476, 0.09496949441075214, 0.15140325552403852]}, "peak_positive_a": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [2.723127e-05, 5.680032e-05, 6.723552e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "0111"], "nondecreasing": true, "values": [0.03782533161242668, 0.05180290247865215, 0.13355380209928733]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
