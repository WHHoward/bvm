# U199_3bvm_rloop_shots_tunning_qb_L1_sweep_qb_l1_1p5p review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.87, JS2_AREA=0.87, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.075099730253416 | 0.11130055311291051 | 2.0070256380295497 | -0.11108967281331367 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.075099730253416 | 0.11130055311291051 | 2.0070256380295497 | -0.11108967281331367 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.075099730253416 | 0.11130055311291051 | 2.0070256380295497 | -0.11108967281331367 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.075099730253416 | 0.11130055311291051 | 2.0070256380295497 | -0.11108967281331367 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.075099730253416 | 0.11130055311291051 | 2.0070256380295497 | -0.11108967281331367 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.075099730253416 | 0.11130055311291051 | 2.0070256380295497 | -0.11108967281331367 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.075099730253416 | 0.11130055311291051 | 2.0070256380295497 | -0.11108967281331367 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.027984436460768286 | 0.039309233760426575 | -0.007920759545820206 | 0.04058966710858949 | AMBIGUOUS |
| 001 | BVM3 | -2.351496681646048 | 2.417833862490249 | -3.020895130740649 | 3.023937791280703 | AMBIGUOUS |
| 011 | BVM2 | -2.457707141368993 | 2.457937900120982 | -3.0086624818146057 | 3.1659411631978847 | AMBIGUOUS |
| 011 | BVM3 | -2.457707141368993 | 2.457937900120982 | -3.0086624818146057 | 3.1659411631978847 | AMBIGUOUS |
| 111 | BVM1 | -3.1737786528774796 | 3.1740064195165387 | -2.893431119917212 | 3.3097962392159648 | AMBIGUOUS |
| 111 | BVM2 | -3.1737786528774796 | 3.1740064195165387 | -2.893431119917212 | 3.3097962392159648 | AMBIGUOUS |
| 111 | BVM3 | -3.1737786528774796 | 3.1740064195165387 | -2.893431119917212 | 3.3097962392159648 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.347532e-06 | -3.757586e-06 | -0.001110158371389623 | 0.006508090259774113 | 9 |
| 001 | 2.881134e-05 | -3.304082e-05 | 0.04030358289695634 | 0.08641301067918286 | 2 |
| 011 | 8.764917e-05 | -1.000868e-05 | 0.12484827841448502 | 0.1312722222303035 | 8 |
| 111 | 0.0001028807 | -5.169455e-06 | 0.21327862612199552 | 0.2144657658442581 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.006508090259774113, 0.08641301067918286, 0.1312722222303035, 0.2144657658442581]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.347532e-06, 2.881134e-05, 8.764917e-05, 0.0001028807]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.001110158371389623, 0.04030358289695634, 0.12484827841448502, 0.21327862612199552]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
