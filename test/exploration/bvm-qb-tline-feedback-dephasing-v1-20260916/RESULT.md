# BVM -> QB TLINE feedback dephasing (bvm-qb-tline-feedback-dephasing-v1-20260916)

- Status: `ANALYSIS_COMPLETE`
- Outcome: `N2_FUNCTIONAL_FAIL` (FAIL)
- Bounded answer: At least one N2 TLINE case does not retain the canonical two ordered navigation candidates.
- Formal solves: exactly TLINE_TD_0P3/TLINE_TD_0P6 × masks 0011/0111.
- TLINE: ideal lossless four-node element, `Z0=6 ohm`; no current-to-SFQ conversion.
- Canonical QB/JTL/terminal and BVM parameters are unchanged.

## N2/N3 timing summary

Phase is raw radians. Turns are only independent continuous-unwrapped navigation values, not SFQ counts.

| run | mask | TD (ps) | JS1 [110,121) p2p (turns) | JS2 [110,121) p2p (turns) | ordered QB/JTL navigation candidates |
|---|---:|---:|---:|---:|---:|
| `TLINE_TD_0P3_0011` | 0011 | 0.3 | 3.1940761 | 3.1874314 | 1 |
| `TLINE_TD_0P3_0111` | 0111 | 0.3 | 6.5527882 | 6.5098847 | 4 |
| `TLINE_TD_0P6_0011` | 0011 | 0.6 | 3.2760322 | 3.2095419 | 1 |
| `TLINE_TD_0P6_0111` | 0111 | 0.6 | 6.2927921 | 6.3050498 | 4 |

## N2 reference and TLINE forward timing

The canonical N2 ordered phase-navigation candidate count is `2`; the TLINE runs report `{'TLINE_TD_0P3_0011': 1, 'TLINE_TD_0P6_0011': 1}`. This navigation oracle is not a terminal pulse count.

| run | specified TD (ps) | first BJ1 +0.5 (ps) | first BJ2 +0.5 (ps) | first BJ1 shift vs canonical (ps) | first BJ2 shift vs canonical (ps) | port V peak delta (ps) | same-grid V lag (ps) |
|---|---:|---:|---:|---:|---:|---:|---:|
| `TLINE_TD_0P3_0011` | 0.3 | 115.5 | 116.4 | 0.3 | 0.3 | 0 | 0.1 |
| `TLINE_TD_0P3_0111` | 0.3 | 114.1 | 115.1 | 0.3 | 0.3 | 0 | 0 |
| `TLINE_TD_0P6_0011` | 0.6 | 115.8 | 116.6 | 0.6 | 0.5 | 0 | 0 |
| `TLINE_TD_0P6_0111` | 0.6 | 114.4 | 115.3 | 0.6 | 0.5 | 0.7 | 1.1 |

## Same-JJ phase / voltage-area cross-check

All JS1/JS2 phase-area values use the same JJ, endpoints, direction and actual stored timestamps in `[110,121) ps`.

| run | JS1 phase delta (turns) | JS1 V-area/Phi0 (turns) | JS2 phase delta (turns) | JS2 V-area/Phi0 (turns) |
|---|---:|---:|---:|---:|
| `TLINE_TD_0P3_0011` | -3.1662428 | -3.1691323 | -2.8508739 | -2.8475883 |
| `TLINE_TD_0P3_0111` | -6.5274552 | -6.5292781 | -6.4820639 | -6.4825259 |
| `TLINE_TD_0P6_0011` | -3.2520417 | -3.2558797 | -2.8956335 | -2.8926119 |
| `TLINE_TD_0P6_0111` | -6.2710645 | -6.2730903 | -6.279075 | -6.2810974 |

## TLINE port and distortion evidence

Port features are described directly from `V(TLINE_IN,0)`, `I(T_BVM_QB)`, `V(QBIN)` and `I(LIN|XBQ1)`. No incident/reflected-wave decomposition is asserted.

Detailed peak amplitudes, signed areas, zero crossings, half-peak widths, local features, COMMON_SL, JSL1..8, LS3/RS, QB, JTL and JM1/JM2 timing are in `provenance.json.analysis.runs` and `result.json.analysis_summary`.

## Interpretation boundary

Outcome disposition: `N2_FUNCTIONAL_FAIL` (FAIL). At least one N2 TLINE case does not retain the canonical two ordered navigation candidates.

For N3, the TLINE cases remain multi-turn phase-navigation trajectories in the registered window and the source current remains positive-dominant; the result therefore does not satisfy the stated selective-dephasing outcome. The N2 two-response requirement is already lost in both TLINE cases.

The outcome is bounded to this fixed N2/N3 simulation, ideal lossless TLINE model, `Z0=6 ohm`, two registered TD values, canonical QB/JTL/terminal, `dt=0.1 ps`, and `0–200 ps`. It is not a hardware measurement, universal impedance result, SFQ count, or proof of physical-equivalent QB feedback.

## Evidence

- Preflight and syntax basis: `PREFLIGHT.md` and `experiment.yaml`.
- Raw/deck/log: `runs/TLINE_TD_0P3/0011`, `runs/TLINE_TD_0P3/0111`, `runs/TLINE_TD_0P6/0011`, `runs/TLINE_TD_0P6/0111`.
- Smoke evidence: `smoke/tline_syntax/`.
- Full-window plots and comparisons: `plots/`.
- Machine evidence: `provenance.json` and `result.json`.
- Delivery manifest: `delivery_manifest.json`; raw ZIP is Drive-only.

Stop marker: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
