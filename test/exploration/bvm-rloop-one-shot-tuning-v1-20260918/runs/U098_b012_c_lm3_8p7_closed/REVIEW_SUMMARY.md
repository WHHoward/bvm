# U098_b012_c_lm3_8p7_closed review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0001, 0011, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0781161526258938 | 0.11339630540354449 | 2.009537898806255 | -0.11113073478863132 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.0781161526258938 | 0.11339630540354449 | 2.009537898806255 | -0.11113073478863132 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.0781161526258938 | 0.11339630540354449 | 2.009537898806255 | -0.11113073478863132 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0781161526258938 | 0.11339630540354449 | 2.009537898806255 | -0.11113073478863132 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0781161526258938 | 0.11339630540354449 | 2.009537898806255 | -0.11113073478863132 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0781161526258938 | 0.11339630540354449 | 2.009537898806255 | -0.11113073478863132 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0781161526258938 | 0.11339630540354449 | 2.009537898806255 | -0.11113073478863132 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.14727975502537 | 1.157677824922393 | -1.3840640176668024 | 1.3950581228257044 | AMBIGUOUS |
| 0011 | BVM3 | -1.4658909215164337 | 1.4751317758222353 | -1.9555984901415548 | 1.9653101247690223 | AMBIGUOUS |
| 0011 | BVM4 | -1.4658909215164337 | 1.4751317758222353 | -1.9555984901415548 | 1.9653101247690223 | AMBIGUOUS |
| 1111 | BVM1 | -2.017089211982676 | 2.024522448106817 | -2.05162462505605 | 2.05162462505605 | AMBIGUOUS |
| 1111 | BVM2 | -2.017089211982676 | 2.024522448106817 | -2.05162462505605 | 2.05162462505605 | AMBIGUOUS |
| 1111 | BVM3 | -2.017089211982676 | 2.024522448106817 | -2.05162462505605 | 2.05162462505605 | AMBIGUOUS |
| 1111 | BVM4 | -2.017089211982676 | 2.024522448106817 | -2.05162462505605 | 2.05162462505605 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 2.125556e-05 | -8.368448e-07 | 0.07108440837360734 | 0.07112487800809027 | 1 |
| 0011 | 3.802033e-05 | -4.096483e-05 | 0.02695144598484216 | 0.10696260473438178 | 2 |
| 1111 | 9.202909e-05 | -1.538516e-05 | 0.1643034592303473 | 0.16933058069373463 | 4 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [0.07112487800809027, 0.10696260473438178, 0.16933058069373463]}, "peak_positive_a": {"masks": ["0001", "0011", "1111"], "nondecreasing": true, "values": [2.125556e-05, 3.802033e-05, 9.202909e-05]}, "signed_area_phi0": {"masks": ["0001", "0011", "1111"], "nondecreasing": false, "values": [0.07108440837360734, 0.02695144598484216, 0.1643034592303473]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
