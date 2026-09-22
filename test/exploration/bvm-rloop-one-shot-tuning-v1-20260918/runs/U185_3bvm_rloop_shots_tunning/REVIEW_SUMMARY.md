# U185_3bvm_rloop_shots_tunning review summary

No scientific interpretation performed.

## CASE

- ARRAY_SIZE=3; bit order: mask left-to-right: b2=BVM1, b1=BVM2, b0=BVM3; rightmost bit is highest-index BVM
- Parameters: JS1_AREA=0.74, JS2_AREA=0.74, RSH_JS1=OPEN, RSH_JS2=OPEN
- Mode: closed
- Masks: 000, 001, 011, 111
- Phase output: raw radians; turns are navigation only.

## S-LOOP

| mask | BVM | WRITE0 JM1 turns | control JM1 turns | WRITE1 JM1 turns | pre-read JM1 turns | Gate-S |
|---|---:|---:|---:|---:|---:|---|
| 000 | BVM1 | -1.0766464104514193 | 0.11517661259697035 | 2.0059831731522975 | -0.1092259684297076 | REVIEW_REQUIRED |
| 001 | BVM3 | -1.0766464104514193 | 0.11517661259697035 | 2.0059831731522975 | -0.1092259684297076 | REVIEW_REQUIRED |
| 011 | BVM2 | -1.0766464104514193 | 0.11517661259697035 | 2.0059831731522975 | -0.1092259684297076 | REVIEW_REQUIRED |
| 011 | BVM3 | -1.0766464104514193 | 0.11517661259697035 | 2.0059831731522975 | -0.1092259684297076 | REVIEW_REQUIRED |
| 111 | BVM1 | -1.0766464104514193 | 0.11517661259697035 | 2.0059831731522975 | -0.1092259684297076 | REVIEW_REQUIRED |
| 111 | BVM2 | -1.0766464104514193 | 0.11517661259697035 | 2.0059831731522975 | -0.1092259684297076 | REVIEW_REQUIRED |
| 111 | BVM3 | -1.0766464104514193 | 0.11517661259697035 | 2.0059831731522975 | -0.1092259684297076 | REVIEW_REQUIRED |

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
| 000 | BVM1 | 0.005761233869489216 | 0.06604364183336021 | 0.0057033014702037605 | 0.06119692181617362 | AMBIGUOUS |
| 001 | BVM3 | -3.063130889679155 | 3.0848256978593693 | -2.975873666917711 | 3.2220403999333085 | AMBIGUOUS |
| 011 | BVM2 | -3.441279851366636 | 3.460129367051725 | -3.057311659748403 | 3.3144391072158417 | AMBIGUOUS |
| 011 | BVM3 | -3.441279851366636 | 3.460129367051725 | -3.057311659748403 | 3.3144391072158417 | AMBIGUOUS |
| 111 | BVM1 | -7.470728094930332 | 7.487202573230649 | -7.468674470953133 | 7.492068226319865 | AMBIGUOUS |
| 111 | BVM2 | -7.470728094930332 | 7.487202573230649 | -7.468674470953133 | 7.492068226319865 | AMBIGUOUS |
| 111 | BVM3 | -7.470728094930332 | 7.487202573230649 | -7.468674470953133 | 7.492068226319865 | AMBIGUOUS |

JS1: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
JS2: raw P/V/I and navigation/activity metrics are in `analysis/case_metrics.json`.
LS3: I/V window metrics are retained in `analysis/per_signal_window_metrics.csv`.
settling: descriptive post-first-activity timing only.
Gate-R: AMBIGUOUS

## OUTPUT

| mask | peak positive I(B_JSL8) [A] | peak negative [A] | signed area [Phi0] | absolute area [Phi0] | zero crossings |
|---|---:|---:|---:|---:|---:|
| 000 | 3.54758e-06 | -4.046453e-06 | -0.0008290058042419707 | 0.0086950192432482 | 10 |
| 001 | 3.218209e-05 | -4.20918e-05 | 0.018915398279136707 | 0.0873630148982839 | 4 |
| 011 | 8.495461e-05 | -4.046453e-06 | 0.1536829981467642 | 0.15387868374325994 | 1 |
| 111 | 0.0003121946 | -4.046453e-06 | 0.7303184347285137 | 0.7305141203250094 | 1 |

population monotonicity (mechanical nondecreasing check): {"absolute_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [0.0086950192432482, 0.0873630148982839, 0.15387868374325994, 0.7305141203250094]}, "peak_positive_a": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [3.54758e-06, 3.218209e-05, 8.495461e-05, 0.0003121946]}, "signed_area_phi0": {"masks": ["000", "001", "011", "111"], "nondecreasing": true, "values": [-0.0008290058042419707, 0.018915398279136707, 0.1536829981467642, 0.7303184347285137]}}
No strict 1:2:3:4 requirement or automatic verdict.

No scientific interpretation performed.
