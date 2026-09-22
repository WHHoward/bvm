# U191_3bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.84, JS2_AREA=0.84, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0753732938196594 | 0.11224036305186819 | 2.0065860520767296 | -0.11083900377794381 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0753732938196594 | 0.11224036305186819 | 2.0065860520767296 | -0.11083900377794381 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0753732938196594 | 0.11224036305186819 | 2.0065860520767296 | -0.11083900377794381 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0753732938196594 | 0.11224036305186819 | 2.0065860520767296 | -0.11083900377794381 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0753732938196594 | 0.11224036305186819 | 2.0065860520767296 | -0.11083900377794381 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0753732938196594 | 0.11224036305186819 | 2.0065860520767296 | -0.11083900377794381 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0753732938196594 | 0.11224036305186819 | 2.0065860520767296 | -0.11083900377794381 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.0278100663051168 | 0.04273873630515935 | -0.010454187929957002 | 0.047615975874233246 | AMBIGUOUS |
| 001 | BVM3 | -2.396763450982773 | 2.417340593575124 | -3.144577349552819 | 3.1516990717068465 | AMBIGUOUS |
| 011 | BVM2 | -2.691405405579368 | 2.691405405579368 | -2.885687961372388 | 3.1766232450908554 | AMBIGUOUS |
| 011 | BVM3 | -2.691405405579368 | 2.691405405579368 | -2.885687961372388 | 3.1766232450908554 | AMBIGUOUS |
| 111 | BVM1 | -4.396242916540563 | 4.396242916540563 | -4.432508487084795 | 4.438876833400203 | AMBIGUOUS |
| 111 | BVM2 | -4.396242916540563 | 4.396242916540563 | -4.432508487084795 | 4.438876833400203 | AMBIGUOUS |
| 111 | BVM3 | -4.396242916540563 | 4.396242916540563 | -4.432508487084795 | 4.438876833400203 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.784747e-06 | -4.312914e-06 | -0.0010148314721851 | 0.0073285665898433485 | 10 |
| 001 | 2.860561e-05 | -3.830584e-05 | 0.03170157047356757 | 0.08412373352348748 | 2 |
| 011 | 8.615972e-05 | -6.097015e-06 | 0.1274591771330747 | 0.13156415541274163 | 9 |
| 111 | 0.000178919 | -4.312914e-06 | 0.30445262484648083 | 0.30466119643960815 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.0073285665898433485, 0.08412373352348748, 0.13156415541274163, 0.30466119643960815]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.784747e-06, 2.860561e-05, 8.615972e-05, 0.000178919]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0010148314721851, 0.03170157047356757, 0.1274591771330747, 0.30445262484648083]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
