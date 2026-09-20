# U099_b013_s1_rsl6_passive review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.74, JS2_AREA=0.90, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0771951914685987 | 0.11467336466691383 | 2.0094104156968386 | -0.11260673773086563 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0771951914685987 | 0.11467336466691383 | 2.0094104156968386 | -0.11260673773086563 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0771951914685987 | 0.11467336466691383 | 2.0094104156968386 | -0.11260673773086563 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0771951914685987 | 0.11467336466691383 | 2.0094104156968386 | -0.11260673773086563 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0771951914685987 | 0.11467336466691383 | 2.0094104156968386 | -0.11260673773086563 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -0.45260772378469627 | 0.4631636435542776 | -0.8988866035108602 | 0.9370352475952722 | AMBIGUOUS |
| 1111 | BVM1 | -1.0743834329199828 | 1.0978949947755907 | -1.186716408233236 | 1.232044531800523 | AMBIGUOUS |
| 1111 | BVM2 | -1.0743834329199828 | 1.0978949947755907 | -1.186716408233236 | 1.232044531800523 | AMBIGUOUS |
| 1111 | BVM3 | -1.0743834329199828 | 1.0978949947755907 | -1.186716408233236 | 1.232044531800523 | AMBIGUOUS |
| 1111 | BVM4 | -1.0743834329199828 | 1.0978949947755907 | -1.186716408233236 | 1.232044531800523 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.720343e-05 | -1.839329e-06 | 0.08986598397629085 | 0.08995493353100381 | 1 |
| 1111 | 0.0001700509 | -1.839329e-06 | 0.5534925616277075 | 0.5535815111824205 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.08995493353100381, 0.5535815111824205]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.720343e-05, 0.0001700509]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.08986598397629085, 0.5534925616277075]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
