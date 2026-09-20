# U045_b010_g5_se_110 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0780700661907747 | 0.11678073526839372 | 2.009738752344437 | -0.11149822355223056 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0780700661907747 | 0.11678073526839372 | 2.009738752344437 | -0.11149822355223056 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0780700661907747 | 0.11678073526839372 | 2.009738752344437 | -0.11149822355223056 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0780700661907747 | 0.11678073526839372 | 2.009738752344437 | -0.11149822355223056 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0780700661907747 | 0.11678073526839372 | 2.009738752344437 | -0.11149822355223056 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.351822043238877 | 1.360329750299326 | -1.8565623373658344 | 1.8565623373658344 | AMBIGUOUS |
| 1111 | BVM1 | -1.617468354528275 | 1.6241070414300185 | -1.9435277813701077 | 2.0029339554285888 | AMBIGUOUS |
| 1111 | BVM2 | -1.617468354528275 | 1.6241070414300185 | -1.9435277813701077 | 2.0029339554285888 | AMBIGUOUS |
| 1111 | BVM3 | -1.617468354528275 | 1.6241070414300185 | -1.9435277813701077 | 2.0029339554285888 | AMBIGUOUS |
| 1111 | BVM4 | -1.617468354528275 | 1.6241070414300185 | -1.9435277813701077 | 2.0029339554285888 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.289599e-05 | -2.882455e-07 | 0.12313924688450106 | 0.12315318637486578 | 1 |
| 1111 | 0.0001454673 | -2.882455e-07 | 0.5408177781336904 | 0.540831717624055 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.12315318637486578, 0.540831717624055]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.289599e-05, 0.0001454673]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.12313924688450106, 0.5408177781336904]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
