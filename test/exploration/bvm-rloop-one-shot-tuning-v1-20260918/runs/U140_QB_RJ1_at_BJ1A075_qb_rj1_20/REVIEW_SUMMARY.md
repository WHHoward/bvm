# U140_QB_RJ1_at_BJ1A075_qb_rj1_20 review summary

No scientific interpretation performed.

## CASE

- Parameters: JS1_AREA=0.52, JS2_AREA=0.74, RSH_JS1=12, RSH_JS2=20
- Mode: closed
- Masks: 0000, 0001, 0011
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 0000 | BVM1 | -1.07802185985017 | 0.11999009469584172 | 2.0092830917423647 | -0.11123864184004773 | REVIEW_REQUIRED |
| 0001 | BVM4 | -1.07802185985017 | 0.11999009469584172 | 2.0092830917423647 | -0.11123864184004773 | REVIEW_REQUIRED |
| 0011 | BVM3 | -1.07802185985017 | 0.11999009469584172 | 2.0092830917423647 | -0.11123864184004773 | REVIEW_REQUIRED |
| 0011 | BVM4 | -1.07802185985017 | 0.11999009469584172 | 2.0092830917423647 | -0.11123864184004773 | REVIEW_REQUIRED |

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
| 0000 | BVM1 | 0.0018882301603365538 | 0.0022713638548416733 | -0.002450779222189167 | 0.003482246492873433 | AMBIGUOUS |
| 0001 | BVM4 | -1.1697733141184794 | 1.1796679769305025 | -1.4529319690075906 | 1.4529319690075906 | AMBIGUOUS |
| 0011 | BVM3 | -1.5141096489911448 | 1.5228261355059414 | -1.958771419002529 | 1.976658843056627 | AMBIGUOUS |
| 0011 | BVM4 | -1.5141096489911448 | 1.5228261355059414 | -1.958771419002529 | 1.976658843056627 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 0000 | 0.0 | -9.765601e-07 | -0.0021018735350539627 | 0.0021018735350539627 | 0 |
| 0001 | 1.804609e-05 | -1.598316e-05 | 0.035134031085364135 | 0.0431476727258794 | 2 |
| 0011 | 2.65827e-05 | -4.712139e-05 | 0.0008972550512191983 | 0.08693542201597618 | 2 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0021018735350539627, 0.0431476727258794, 0.08693542201597618]}, "peak_positive_a": {"masks": ["0000", "0001", "0011"], "nondecreasing": true, "values": [0.0, 1.804609e-05, 2.65827e-05]}, "signed_area_phi0": {"masks": ["0000", "0001", "0011"], "nondecreasing": false, "values": [-0.0021018735350539627, 0.035134031085364135, 0.0008972550512191983]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
