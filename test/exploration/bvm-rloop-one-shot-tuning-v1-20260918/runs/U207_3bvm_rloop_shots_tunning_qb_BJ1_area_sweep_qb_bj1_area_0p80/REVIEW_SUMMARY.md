# U207_3bvm_rloop_shots_tunning_qb_BJ1_area_sweep_qb_bj1_area_0p80 review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.9, JS2_AREA=0.9, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0748745037684702 | 0.11022832626130037 | 2.0075368437067604 | -0.111265061560601 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0748745037684702 | 0.11022832626130037 | 2.0075368437067604 | -0.111265061560601 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0748745037684702 | 0.11022832626130037 | 2.0075368437067604 | -0.111265061560601 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0748745037684702 | 0.11022832626130037 | 2.0075368437067604 | -0.111265061560601 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0748745037684702 | 0.11022832626130037 | 2.0075368437067604 | -0.111265061560601 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0748745037684702 | 0.11022832626130037 | 2.0075368437067604 | -0.111265061560601 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0748745037684702 | 0.11022832626130037 | 2.0075368437067604 | -0.111265061560601 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.026575087608700934 | 0.036710647342587964 | -0.006427058573914157 | 0.03426130051488662 | AMBIGUOUS |
| 001 | BVM3 | -2.3966716981580807 | 2.424129490912158 | -2.7680734451881244 | 2.7688822387779286 | AMBIGUOUS |
| 011 | BVM2 | -2.2979383376615923 | 2.321194726396941 | -3.1089785586426717 | 3.1454663890649304 | AMBIGUOUS |
| 011 | BVM3 | -2.2979383376615923 | 2.321194726396941 | -3.1089785586426717 | 3.1454663890649304 | AMBIGUOUS |
| 111 | BVM1 | -2.8960330645043495 | 2.8968934561267043 | -2.9809033928377615 | 3.3225580464967996 | AMBIGUOUS |
| 111 | BVM2 | -2.8960330645043495 | 2.8968934561267043 | -2.9809033928377615 | 3.3225580464967996 | AMBIGUOUS |
| 111 | BVM3 | -2.8960330645043495 | 2.8968934561267043 | -2.9809033928377615 | 3.3225580464967996 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 1.989632e-06 | -3.29903e-06 | -0.0012297358935581236 | 0.005726131035262949 | 9 |
| 001 | 2.476795e-05 | -4.163485e-05 | 0.018253997523789468 | 0.0805849570651771 | 2 |
| 011 | 7.065796e-05 | -1.469401e-05 | 0.11605308991440803 | 0.12688603951607252 | 8 |
| 111 | 8.988795e-05 | -6.507437e-06 | 0.20515476792794973 | 0.20669375676067336 | 3 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005726131035262949, 0.0805849570651771, 0.12688603951607252, 0.20669375676067336]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [1.989632e-06, 2.476795e-05, 7.065796e-05, 8.988795e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0012297358935581236, 0.018253997523789468, 0.11605308991440803, 0.20515476792794973]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
