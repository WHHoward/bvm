# U054_b011_a130_0 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0780700661907747 | 0.15980143047073467 | 2.0105434397367095 | -0.11181366864943869 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0780700661907747 | 0.15980143047073467 | 2.0105434397367095 | -0.11181366864943869 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0780700661907747 | 0.15980143047073467 | 2.0105434397367095 | -0.11181366864943869 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0780700661907747 | 0.15980143047073467 | 2.0105434397367095 | -0.11181366864943869 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0780700661907747 | 0.15980143047073467 | 2.0105434397367095 | -0.11181366864943869 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -2.0883746632470532 | 2.094147053878053 | -2.138184271701922 | 2.1387811027385166 | AMBIGUOUS |
| 1111 | BVM1 | -2.0910962127739245 | 2.0954387553961866 | -2.2268733637398808 | 2.235727153224083 | AMBIGUOUS |
| 1111 | BVM2 | -2.0910962127739245 | 2.0954387553961866 | -2.2268733637398808 | 2.235727153224083 | AMBIGUOUS |
| 1111 | BVM3 | -2.0910962127739245 | 2.0954387553961866 | -2.2268733637398808 | 2.235727153224083 | AMBIGUOUS |
| 1111 | BVM4 | -2.0910962127739245 | 2.0954387553961866 | -2.2268733637398808 | 2.235727153224083 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 4.449391e-05 | -2.859863e-07 | 0.1566918326626598 | 0.15670566289859852 | 1 |
| 1111 | 0.0001788349 | -2.859863e-07 | 0.6566522525483873 | 0.656666082784326 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.15670566289859852, 0.656666082784326]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [4.449391e-05, 0.0001788349]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.1566918326626598, 0.6566522525483873]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
