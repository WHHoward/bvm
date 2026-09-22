# U177_3bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: passive
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0747648954875852 | 0.11039273331751424 | 2.008358560677944 | -0.11163748412743607 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0747648954875852 | 0.11039273331751424 | 2.008358560677944 | -0.11163748412743607 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0747648954875852 | 0.11039273331751424 | 2.008358560677944 | -0.11163748412743607 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0747648954875852 | 0.11039273331751424 | 2.008358560677944 | -0.11163748412743607 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0747648954875852 | 0.11039273331751424 | 2.008358560677944 | -0.11163748412743607 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0747648954875852 | 0.11039273331751424 | 2.008358560677944 | -0.11163748412743607 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0747648954875852 | 0.11039273331751424 | 2.008358560677944 | -0.11163748412743607 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.02745994134580895 | 0.03765486587346925 | -0.006447732801021787 | 0.03357391031567272 | AMBIGUOUS |
| 001 | BVM3 | -2.417822498827312 | 2.41955852911557 | -2.2928343500450956 | 2.2928343500450956 | AMBIGUOUS |
| 011 | BVM2 | -2.210588438976786 | 2.3775833227343997 | -2.776800658746085 | 2.776800658746085 | AMBIGUOUS |
| 011 | BVM3 | -2.210588438976786 | 2.3775833227343997 | -2.776800658746085 | 2.776800658746085 | AMBIGUOUS |
| 111 | BVM1 | -2.1921742120610537 | 2.344091074820027 | -3.0449831040536526 | 3.0546438090993306 | AMBIGUOUS |
| 111 | BVM2 | -2.1921742120610537 | 2.344091074820027 | -3.0449831040536526 | 3.0546438090993306 | AMBIGUOUS |
| 111 | BVM3 | -2.1921742120610537 | 2.344091074820027 | -3.0449831040536526 | 3.0546438090993306 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.751764e-06 | -3.196283e-06 | -0.00015095376865115385 | 0.006775740152358704 | 9 |
| 001 | 5.840885e-05 | -2.975979e-06 | 0.16296929933511742 | 0.16311321703928297 | 1 |
| 011 | 0.0001216609 | -2.975979e-06 | 0.36447004602373595 | 0.3646139637279015 | 1 |
| 111 | 0.0001980942 | -2.975979e-06 | 0.5904338011638931 | 0.5905777188680588 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.006775740152358704, 0.16311321703928297, 0.3646139637279015, 0.5905777188680588]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.751764e-06, 5.840885e-05, 0.0001216609, 0.0001980942]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.00015095376865115385, 0.16296929933511742, 0.36447004602373595, 0.5904338011638931]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
