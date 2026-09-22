# U192_3bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.86, JS2_AREA=0.86, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0751847906641585 | 0.11158766863024813 | 2.0068768281577585 | -0.11100898125716596 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0751847906641585 | 0.11158766863024813 | 2.0068768281577585 | -0.11100898125716596 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0751847906641585 | 0.11158766863024813 | 2.0068768281577585 | -0.11100898125716596 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0751847906641585 | 0.11158766863024813 | 2.0068768281577585 | -0.11100898125716596 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0751847906641585 | 0.11158766863024813 | 2.0068768281577585 | -0.11100898125716596 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0751847906641585 | 0.11158766863024813 | 2.0068768281577585 | -0.11100898125716596 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0751847906641585 | 0.11158766863024813 | 2.0068768281577585 | -0.11100898125716596 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02826179578009453 | 0.03966578857943535 | -0.008875609626900038 | 0.04298141576238587 | AMBIGUOUS |
| 001 | BVM3 | -2.360287604927729 | 2.4172362515944332 | -3.0907007911751463 | 3.094929012801786 | AMBIGUOUS |
| 011 | BVM2 | -2.5292910558981507 | 2.5293069236459766 | -2.9664087383675306 | 3.1717245832664416 | AMBIGUOUS |
| 011 | BVM3 | -2.5292910558981507 | 2.5293069236459766 | -2.9664087383675306 | 3.1717245832664416 | AMBIGUOUS |
| 111 | BVM1 | -3.2512926805862405 | 3.251305508474654 | -2.8654137861297064 | 3.2920318260173818 | AMBIGUOUS |
| 111 | BVM2 | -3.2512926805862405 | 3.251305508474654 | -2.8654137861297064 | 3.2920318260173818 | AMBIGUOUS |
| 111 | BVM3 | -3.2512926805862405 | 3.251305508474654 | -2.8654137861297064 | 3.2920318260173818 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.497507e-06 | -3.98536e-06 | -0.0010862809587784726 | 0.006839849529825486 | 9 |
| 001 | 2.760857e-05 | -3.698064e-05 | 0.033967949039008224 | 0.08542337649654322 | 2 |
| 011 | 8.560373e-05 | -8.970182e-06 | 0.12473706251567254 | 0.13157106966458731 | 8 |
| 111 | 0.0001053728 | -3.869349e-06 | 0.21212427853632823 | 0.21250159216854034 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.006839849529825486, 0.08542337649654322, 0.13157106966458731, 0.21250159216854034]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.497507e-06, 2.760857e-05, 8.560373e-05, 0.0001053728]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0010862809587784726, 0.033967949039008224, 0.12473706251567254, 0.21212427853632823]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
