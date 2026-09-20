# U072_b012_a1_se120_a0p74 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.740, JS2_AREA=0.740, RSH_JS1=12, RSH_JS2=20
- Mode: passive
- Masks: 0001, 1111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0001 | BVM4 | -1.0775653858662304 | 0.12307642735227974 | 2.0096370523358016 | -0.11230752643785274 | REVIEW_REQUIRED |
| 1111 | BVM1 | -1.0775653858662304 | 0.12307642735227974 | 2.0096370523358016 | -0.11230752643785274 | REVIEW_REQUIRED |
| 1111 | BVM2 | -1.0775653858662304 | 0.12307642735227974 | 2.0096370523358016 | -0.11230752643785274 | REVIEW_REQUIRED |
| 1111 | BVM3 | -1.0775653858662304 | 0.12307642735227974 | 2.0096370523358016 | -0.11230752643785274 | REVIEW_REQUIRED |
| 1111 | BVM4 | -1.0775653858662304 | 0.12307642735227974 | 2.0096370523358016 | -0.11230752643785274 | REVIEW_REQUIRED |

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
| 0001 | BVM4 | -1.5022825905220767 | 1.5085422340113526 | -1.9212123325738126 | 1.9751212948978996 | AMBIGUOUS |
| 1111 | BVM1 | -1.8787317774173369 | 1.8835681459970248 | -1.9675534773538796 | 1.9980332405054086 | AMBIGUOUS |
| 1111 | BVM2 | -1.8787317774173369 | 1.8835681459970248 | -1.9675534773538796 | 1.9980332405054086 | AMBIGUOUS |
| 1111 | BVM3 | -1.8787317774173369 | 1.8835681459970248 | -1.9675534773538796 | 1.9980332405054086 | AMBIGUOUS |
| 1111 | BVM4 | -1.8787317774173369 | 1.8835681459970248 | -1.9675534773538796 | 1.9980332405054086 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0001 | 3.928406e-05 | -3.566878e-07 | 0.13551498660350772 | 0.13553223594877523 | 1 |
| 1111 | 0.0001683173 | -3.566878e-07 | 0.5979383956819724 | 0.5979556450272399 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.13553223594877523, 0.5979556450272399]}, "peak_positive_a": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [3.928406e-05, 0.0001683173]}, "signed_area_phi0": {"masks": ["0001", "1111"], "nondecreasing": true, "values": [0.13551498660350772, 0.5979383956819724]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
