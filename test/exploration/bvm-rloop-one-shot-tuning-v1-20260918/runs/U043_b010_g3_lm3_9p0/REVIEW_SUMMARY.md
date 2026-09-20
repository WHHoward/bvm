# U043_b010_g3_lm3_9p0 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0782623253620298 | 0.11446614493100819 | 2.009839179113528 | -0.11112627845022484 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0782623253620298 | 0.11446614493100819 | 2.009839179113528 | -0.11112627845022484 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0782623253620298 | 0.11446614493100819 | 2.009839179113528 | -0.11112627845022484 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0782623253620298 | 0.11446614493100819 | 2.009839179113528 | -0.11112627845022484 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0782623253620298 | 0.11446614493100819 | 2.009839179113528 | -0.11112627845022484 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.1379331263443895 | 1.149142934197664 | -1.3667508564783684 | 1.379976473094362 | AMBIGUOUS |
| 1111 | BVM1 | -1.2019428571318036 | 1.2108101747861684 | -1.5678695467955315 | 1.5678695467955315 | AMBIGUOUS |
| 1111 | BVM2 | -1.2019428571318036 | 1.2108101747861684 | -1.5678695467955315 | 1.5678695467955315 | AMBIGUOUS |
| 1111 | BVM3 | -1.2019428571318036 | 1.2108101747861684 | -1.5678695467955315 | 1.5678695467955315 | AMBIGUOUS |
| 1111 | BVM4 | -1.2019428571318036 | 1.2108101747861684 | -1.5678695467955315 | 1.5678695467955315 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.101261e-05 | -2.973829e-07 | 0.10215086120642707 | 0.10216524257948988 | 1 |
| 1111 | 0.0001324595 | -2.973829e-07 | 0.45285548679876325 | 0.45286986817182606 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10216524257948988, 0.45286986817182606]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.101261e-05, 0.0001324595]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.10215086120642707, 0.45285548679876325]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
