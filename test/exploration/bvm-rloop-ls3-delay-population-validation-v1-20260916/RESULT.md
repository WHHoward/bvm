# LS3-only delay population validation (bvm-rloop-ls3-delay-population-validation-v1-20260916)

- Status: `ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW`
- Artifact status: `VALID`
- Scientific interpretation: `NOT_PERFORMED`; final classification: `SCIENTIFIC_REVIEW_REQUIRED`.
- HEAD: `2099471a24f7938056ac762ff60c89636dcafa7d`; four authorized solves only; 0.3 ps = 3 actual stored samples.
- Fixture: canonical BVM → COMMON_SL → JSL1..8 → canonical QB → JTL1..6 → terminal; per-instance ideal LS3 current replay with physical R_S retained.
- The source is a causal replay counterfactual, not a physical delay or passive-realizability proof.

## Exact fidelity gates

| mask | exact gate | max landmark timing drift (ps) | max active JS1/JS2 p2p drift (turns) | max normalized RMS |
|---|---|---:|---:|---:|
| `0001` | `PASS` | 0 | 0 | 5.5015551e-08 |
| `1111` | `PASS` | 0 | 0 | 5.6641852e-08 |

## Population comparison

| population | canonical | LS3 delay 0.3 ps |
|---|---:|---:|
| `N1 0001` | `1-like` | `ONE_RESPONSE_LIKE_WITH_TERMINAL_CORROBORATION` |
| `N2 0011` | `2` | `2` |
| `N3 0111` | `4` | `3` |
| `N4 1111` | `4-like` | `N4_FOUR_RESPONSE_LIKE_PRESERVED` |

- Mechanical candidate label: `POPULATION_MAPPING_1_2_3_4_SUPPORTED_BY_CURRENT_REPLAY`.
- Final scientific assignment: `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED`.
- N2/N3 are reused read-only raw evidence; no N2/N3 solve was executed in this experiment.

## N1/N4 multi-evidence record

| case | old strict count | ordered phase chains | JTL6 clusters | terminal clusters | terminal area / Φ0 | descriptive candidate |
|---|---:|---:|---:|---:|---:|---|
| `LS3_EXACT_0001` | 1 | 1 | 1 | 1 | 1 | `ONE_RESPONSE_LIKE_WITH_TERMINAL_CORROBORATION` |
| `LS3_DELAY0P3_0001` | 1 | 1 | 1 | 1 | 0.99999994 | `ONE_RESPONSE_LIKE_WITH_TERMINAL_CORROBORATION` |
| `LS3_EXACT_1111` | 0 | 4 | 4 | 4 | 3.9999999 | `N4_FOUR_RESPONSE_LIKE_PRESERVED` |
| `LS3_DELAY0P3_1111` | 0 | 4 | 4 | 4 | 4 | `N4_FOUR_RESPONSE_LIKE_PRESERVED` |

For N4 the old strict field is deliberately shown beside the primary multi-evidence result: the strict count may be zero even when four phase chains, four JTL6/terminal clusters and near-four terminal area are present. It is contextual, not the sole oracle.

### N4 round-by-round timing drift

| response index | canonical BJ1 (ps) | delayed BJ1 (ps) | ΔBJ1 (ps) | canonical BJ2 (ps) | delayed BJ2 (ps) | ΔBJ2 (ps) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 113.2 | 113.3 | 0.1 | 114.2 | 114.2 | 0 |
| 2 | 115.8 | 116 | 0.2 | 116.9 | 117.1 | 0.2 |
| 3 | 118.1 | 118.3 | 0.2 | 119.4 | 119.6 | 0.2 |
| 4 | 120.5 | 120.7 | 0.2 | 122 | 122.2 | 0.2 |

## Evidence retained

- Per-run active BVM JS1/JS2 phase navigation and same-JJ voltage-area cross-checks.
- BJ1/BJ2 landmarks, ordered JTL phase chains, JTL6/terminal cluster peaks/valleys/areas, terminal area/Φ0.
- I(B_JSL8), COMMON_SL, QBIN/QB, all JSL/JTL stages, JM1/JM2, R_S, imposed LS3, I_TOTAL and Vbridge.
- Ideal-source P_absorb = V(node6−node10) × I_source(node6→node10), signed and absolute exchanged energy; per-instance extrema and [110,121)/[110,130) records are in `analysis/mechanical_analysis.json`.
- Phase is raw radians; turns are navigation only. Areas are same-JJ actual-grid arithmetic, not SFQ counts.

Stop marker: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
