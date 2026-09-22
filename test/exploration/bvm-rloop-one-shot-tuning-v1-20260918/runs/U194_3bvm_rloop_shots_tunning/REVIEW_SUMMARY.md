# U194_3bvm_rloop_shots_tunning review summary

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
| 000 | BVM1 | -1.075098724869094 | 0.1112860700130891 | 2.0070398028194845 | -0.11108728548916738 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.075098724869094 | 0.1112860700130891 | 2.0070398028194845 | -0.11108728548916738 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.075098724869094 | 0.1112860700130891 | 2.0070398028194845 | -0.11108728548916738 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.075098724869094 | 0.1112860700130891 | 2.0070398028194845 | -0.11108728548916738 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.075098724869094 | 0.1112860700130891 | 2.0070398028194845 | -0.11108728548916738 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.075098724869094 | 0.1112860700130891 | 2.0070398028194845 | -0.11108728548916738 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.075098724869094 | 0.1112860700130891 | 2.0070398028194845 | -0.11108728548916738 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.028084210694592597 | 0.039325769959013816 | -0.008089400123520385 | 0.04045261878709307 | AMBIGUOUS |
| 001 | BVM3 | -2.3561281859829877 | 2.417901153200188 | -3.0315450633351144 | 3.03449011414857 | AMBIGUOUS |
| 011 | BVM2 | -2.458826096111895 | 2.459076319513424 | -3.0097758502190053 | 3.165931979957669 | AMBIGUOUS |
| 011 | BVM3 | -2.458826096111895 | 2.459076319513424 | -3.0097758502190053 | 3.165931979957669 | AMBIGUOUS |
| 111 | BVM1 | -3.1768042838386226 | 3.1770514992117267 | -2.8934256290716753 | 3.3091122390170384 | AMBIGUOUS |
| 111 | BVM2 | -3.1768042838386226 | 3.1770514992117267 | -2.8934256290716753 | 3.3091122390170384 | AMBIGUOUS |
| 111 | BVM3 | -3.1768042838386226 | 3.1770514992117267 | -2.8934256290716753 | 3.3091122390170384 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.385753e-06 | -3.804115e-06 | -0.00111934702453909 | 0.006584365809742768 | 9 |
| 001 | 2.717507e-05 | -3.739533e-05 | 0.03505062522798988 | 0.08615298844842191 | 2 |
| 011 | 8.53821e-05 | -1.014755e-05 | 0.12390071209435001 | 0.13120941501292208 | 8 |
| 111 | 0.0001020104 | -4.920227e-06 | 0.21322113035166806 | 0.21434804202411878 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.006584365809742768, 0.08615298844842191, 0.13120941501292208, 0.21434804202411878]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.385753e-06, 2.717507e-05, 8.53821e-05, 0.0001020104]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.00111934702453909, 0.03505062522798988, 0.12390071209435001, 0.21322113035166806]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
