# Two-parameter full closed-loop QB combination — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-qb-two-parameter-combination-v1-20260911`
- Registration HEAD: `a669c32fd22317742ccb839983b3618664360ae1`
- Sealed preflight HEAD: `188241f3c42d075aadda8d5699c19561e536c6e6`
- Remote `bvm/master`: `a669c32fd22317742ccb839983b3618664360ae1`
- Status: **PASS**
- Solver has not been invoked at preflight.

## Exact scope

Nine registered two-parameter points run in order `C01 → C02 → C04 → C03 → C05 → C07 → C06 → C08 → C09`; each has exactly masks `0011` and `0111`. C01 is `L2=1.6pH + L3=1.6pH`; the other eight combinations are recorded in `screening/COMBINATION_MATRIX.json`. No third parameter, replay, passive capture, source scaling, read extension, JTL change or timestep change is registered.

## Corrected CONTROL/history rule

CONTROL/history is evaluated only on actual stored samples in `70≤t<81 ps` ZERO_STATE_READ_CONTROL, `81≤t<90 ps` post-control idle, `90≤t<101 ps` WRITE1 and `101≤t<110 ps` SETTLE. `CONTROL_CONTAMINATED` requires an unintended complete downstream `V(QBOUT) → V(JTL1_OUT) → ... → V(JTL6_OUT)` chain inside this history interval. Phase rollback after FINAL READ or TAIL is recorded separately and is never a CONTROL criterion.

## Evidence ceiling

Raw CSV is authoritative. P values remain radians; `rad/(2*pi)` is navigation/display only and never an SFQ count. Terminal area and voltage peaks are diagnostics, not event counts. No timestep convergence or parameter robustness is claimed in this experiment.

## Stop

A clean raw-supported N2=2/N3=3 pair is `DIRECT_2_TO_3_COMBINATION_CANDIDATE`, stops all not-yet-started combinations and permits only 0001/1111 validation. Otherwise the nine-point matrix ends at `NO_DIRECT_2_TO_3_TWO_PARAMETER_COMBINATION`; no third-parameter search starts automatically.
