# RJ2=12 local timestep robustness handoff

This is a bounded numerical spot-check, not a change to the project standard.

- Canonical timestep: `.tran=0.1p`; the two 0.1ps cases are exact immutable reuse.
- New physical solves: exactly four, at 0.05ps and 0.025ps, masks `0001` and `0011`.
- All circuit parameters, history, controls, topology, load and stop time remain fixed.
- The repaired second-response oracle uses common FINAL-origin cumulative phase
  history plus independent voltage clusters and valley-gated terminal pulses.
- A stable result is `TIMESTEP_ROBUST_CANDIDATE_WITHIN_TESTED_DT` only; it is
  not full convergence or final SFQ proof.

Raw `P(...)` is radians. Phase turns and voltage-area-over-Phi0 values are
derived diagnostics and are never event or SFQ counts.
