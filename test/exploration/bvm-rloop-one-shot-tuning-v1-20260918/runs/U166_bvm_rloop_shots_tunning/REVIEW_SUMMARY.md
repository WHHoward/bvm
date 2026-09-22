# U166_bvm_rloop_shots_tunning review summary

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
| 000 | BVM1 | -1.0748844027919684 | 0.11059597417984258 | 2.0075664465261758 | -0.11129259536575578 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0748844027919684 | 0.11059597417984258 | 2.0075664465261758 | -0.11129259536575578 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0748844027919684 | 0.11059597417984258 | 2.0075664465261758 | -0.11129259536575578 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0748844027919684 | 0.11059597417984258 | 2.0075664465261758 | -0.11129259536575578 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0748844027919684 | 0.11059597417984258 | 2.0075664465261758 | -0.11129259536575578 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0748844027919684 | 0.11059597417984258 | 2.0075664465261758 | -0.11129259536575578 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0748844027919684 | 0.11059597417984258 | 2.0075664465261758 | -0.11129259536575578 | REVIEW_REQUIRED |

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
| 000 | BVM1 | -0.026020575871474466 | 0.035613337671946584 | -0.006626861689471725 | 0.032831468421643334 | AMBIGUOUS |
| 001 | BVM3 | -2.407593355986887 | 2.430749588516548 | -2.768097557162003 | 2.7689993290695614 | AMBIGUOUS |
| 011 | BVM2 | -2.2964554592258164 | 2.3072902025402007 | -3.110008529856891 | 3.139371773336147 | AMBIGUOUS |
| 011 | BVM3 | -2.2964554592258164 | 2.3072902025402007 | -3.110008529856891 | 3.139371773336147 | AMBIGUOUS |
| 111 | BVM1 | -2.929760034128794 | 2.9304632602448453 | -3.0201862546241176 | 3.3516651778416326 | AMBIGUOUS |
| 111 | BVM2 | -2.929760034128794 | 2.9304632602448453 | -3.0201862546241176 | 3.3516651778416326 | AMBIGUOUS |
| 111 | BVM3 | -2.929760034128794 | 2.9304632602448453 | -3.0201862546241176 | 3.3516651778416326 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 2.268984e-06 | -3.408486e-06 | -0.0011801556800902187 | 0.006194873597407138 | 9 |
| 001 | 2.616085e-05 | -5.541913e-05 | 0.018603589305401482 | 0.0929444236759587 | 2 |
| 011 | 6.344409e-05 | -2.852883e-05 | 0.10682447310921496 | 0.13315940575995464 | 8 |
| 111 | 8.917291e-05 | -2.124843e-05 | 0.17283851999312047 | 0.18817001728467647 | 7 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.006194873597407138, 0.0929444236759587, 0.13315940575995464, 0.18817001728467647]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [2.268984e-06, 2.616085e-05, 6.344409e-05, 8.917291e-05]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0011801556800902187, 0.018603589305401482, 0.10682447310921496, 0.17283851999312047]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
