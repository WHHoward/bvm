# U188_3bvm_rloop_shots_tunning review summary

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
| 000 | BVM1 | -1.074865262177277 | 0.11044859670253952 | 2.0076121239948432 | -0.11132904184772384 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.074865262177277 | 0.11044859670253952 | 2.0076121239948432 | -0.11132904184772384 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.074865262177277 | 0.11044859670253952 | 2.0076121239948432 | -0.11132904184772384 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.074865262177277 | 0.11044859670253952 | 2.0076121239948432 | -0.11132904184772384 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.074865262177277 | 0.11044859670253952 | 2.0076121239948432 | -0.11132904184772384 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.074865262177277 | 0.11044859670253952 | 2.0076121239948432 | -0.11132904184772384 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.074865262177277 | 0.11044859670253952 | 2.0076121239948432 | -0.11132904184772384 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.0266262877538936 | 0.03686610989100012 | -0.0061994829207870535 | 0.034303715307220616 | AMBIGUOUS |
| 001 | BVM3 | -2.3858741652693913 | 2.4200297709865706 | -2.6623572093099623 | 2.662994688519023 | AMBIGUOUS |
| 011 | BVM2 | -2.2804531140641817 | 2.337859951896554 | -3.115495205534052 | 3.1469955975046404 | AMBIGUOUS |
| 011 | BVM3 | -2.2804531140641817 | 2.337859951896554 | -3.115495205534052 | 3.1469955975046404 | AMBIGUOUS |
| 111 | BVM1 | -2.8219793994837867 | 2.8229024344917426 | -2.9413876555386733 | 3.2979417424347077 | AMBIGUOUS |
| 111 | BVM2 | -2.8219793994837867 | 2.8229024344917426 | -2.9413876555386733 | 3.2979417424347077 | AMBIGUOUS |
| 111 | BVM3 | -2.8219793994837867 | 2.8229024344917426 | -2.9413876555386733 | 3.2979417424347077 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 1.947597e-06 | -3.30843e-06 | -0.001213485952184691 | 0.005759647561393438 | 9 |
| 001 | 3.297797e-05 | -1.845125e-05 | 0.062156913880829404 | 0.07882152401540524 | 4 |
| 011 | 8.58311e-05 | -2.971832e-06 | 0.13464804424170554 | 0.1347917613978433 | 1 |
| 111 | 0.0001155848 | -2.971832e-06 | 0.24433411441091715 | 0.24447783156705494 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.005759647561393438, 0.07882152401540524, 0.1347917613978433, 0.24447783156705494]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [1.947597e-06, 3.297797e-05, 8.58311e-05, 0.0001155848]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.001213485952184691, 0.062156913880829404, 0.13464804424170554, 0.24433411441091715]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
