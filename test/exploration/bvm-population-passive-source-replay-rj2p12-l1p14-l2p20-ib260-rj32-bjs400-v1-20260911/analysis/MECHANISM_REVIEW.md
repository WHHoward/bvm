# Mechanism diagnostic raw review navigation

Scientific interpretation: `NOT_PERFORMED`.

This document records direct raw-oriented arithmetic and navigation only. The passive waveform is a counterfactual source fixture and the replay is ideal current forcing. No phase, activity segment, voltage area, terminal area or phase landmark is an SFQ count.

## Passive source windows

| population | window (ps) | samples | max (uA) | min (uA) | signed area (A s) | abs area (A s) | positive support (ps) |
|---|---:|---:|---:|---:|---:|---:|---:|
| N2 | 110–121 | 110 | 141.484 | -4.56273 | 8.47992e-16 | 8.48448e-16 | 10.8 |
| N2 | 121–124 | 30 | 82.9445 | 27.8543 | 1.42809e-16 | 1.42809e-16 | 2.9 |
| N2 | 121–126 | 50 | 82.9445 | -15.3201 | 1.55697e-16 | 1.73433e-16 | 3.9 |
| N2 | 121–130 | 90 | 82.9445 | -17.3061 | 1.77695e-16 | 2.22671e-16 | 6 |
| N2 | 110–200 | 900 | 141.484 | -17.3061 | 1.03501e-15 | 1.17844e-15 | 49.2 |
| N3 | 110–121 | 110 | 212.326 | -4.56273 | 1.33344e-15 | 1.3339e-15 | 10.8 |
| N3 | 121–124 | 30 | 127.882 | 28.8773 | 1.70899e-16 | 1.70899e-16 | 2.9 |
| N3 | 121–126 | 50 | 127.882 | -16.6851 | 1.90777e-16 | 2.072e-16 | 4 |
| N3 | 121–130 | 90 | 127.882 | -22.2636 | 1.99486e-16 | 2.60129e-16 | 5.7 |
| N3 | 110–200 | 900 | 212.326 | -22.2636 | 1.55195e-15 | 1.73878e-15 | 48.3 |
| N4 | 110–121 | 110 | 283.817 | -4.56273 | 1.84261e-15 | 1.84306e-15 | 10.8 |
| N4 | 121–124 | 30 | 156.596 | 1.47561 | 1.69095e-16 | 1.69095e-16 | 2.9 |
| N4 | 121–126 | 50 | 156.596 | -20.6544 | 2.06915e-16 | 2.24071e-16 | 4.2 |
| N4 | 121–130 | 90 | 156.596 | -37.6576 | 2.05952e-16 | 2.9047e-16 | 5.7 |
| N4 | 110–200 | 900 | 283.817 | -37.6576 | 2.06891e-15 | 2.32916e-15 | 48.4 |

Zero crossings are retained as exact-zero samples or sign-change brackets; no crossing interpolation was performed.

## Replay navigation

| replay | BJ1 delta at 130 ps (turn display) | BJ2 delta at 130 ps (turn display) | QBOUT first activity (ps) | JTL1 first activity (ps) | JTL6 first activity (ps) | terminal first activity (ps) |
|---|---:|---:|---:|---:|---:|---:|
| N2 | 2.99594 | 2.99415 | 110.0 | 113.3 | 127.5 | 129.6 |
| N3 | 3.97418 | 3.9717 | 110.0 | 112.8 | 126.70000000000002 | 128.8 |
| N4 | 3.94126 | 3.96212 | 110.0 | 112.60000000000001 | 126.19999999999999 | 128.3 |

The four registered cumulative-phase landmarks (`+0.5`, `+1.5`, `+2.5`, `+3.5` turns) are navigation only. Activity segments use the preregistered absolute-voltage threshold and are not response counts.

## Closed-loop versus replay

The following descriptive comparisons use identical stored time grids and unwrap each phase trace before subtraction. They are not causal conclusions.

| population | source current max abs delta (A) | BJ1 phase max abs delta (rad) | BJ2 phase max abs delta (rad) | QBOUT max abs delta (V) | JTL6 max abs delta (V) | terminal max abs delta (A) |
|---|---:|---:|---:|---:|---:|---:|
| N2 | 0.000132001 | 17.5826 | 17.9715 | 0.000925462 | 0.0012833 | 0.00012833 |
| N3 | 0.000113889 | 10.7291 | 11.6821 | 0.000925462 | 0.00131399 | 0.000131399 |
| N4 | 0.000339069 | 10.0919 | 9.76149 | 0.000925462 | 0.00124508 | 0.000124508 |

## Review boundary

- response multiplicity classification: `UNASSESSED_PENDING_SCIENTIFIC_REVIEW`
- no automatic upgrade to 2/3/4 was made
- no causal statement about QB-to-source back-action was made
- raw CSV, decks, logs, metadata and source/reference hashes remain the authority.
