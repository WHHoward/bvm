# BVM QB L3 highside selective-window search - PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: bvm-qb-l3-highside-selective-window-v1-20260911
- Registration HEAD: ccde33f50f2bf72a284ecad689fc0f00aed57649
- Sealed preflight HEAD: 512c23a7c93cff7821f0f50024623eb7cf2f5e80
- Remote bvm/master: ccde33f50f2bf72a284ecad689fc0f00aed57649
- Status: PASS
- Solver has not been invoked at preflight.

## Exact scope

Only H1 L3=1.8 pH and H2 L3=2.0 pH are new registered points, each with 0011 and 0111. L3=1.6 pH is an immutable reference. H2 runs only when H1 is not a clean 2/3 point.

## Corrected history/control

Use actual stored samples in 70-81 ps ZERO_STATE_READ_CONTROL, 81-90 ps idle, 90-101 ps WRITE1 and 101-110 ps SETTLE. Only unintended complete QBOUT->JTL1..6 propagation before FINAL READ is contamination. FINAL/Tail rollback is separate.

## Interpretation ceiling

P values are raw radians; rad/(2*pi) is navigation only, not an SFQ count. The result is bounded to this source, receiver, load, history, solver and 0.1 ps grid. No extra L3, third parameter, replay, source modification, timestep refinement or N1/N4 validation is authorized.

## Stop

After H1 alone if clean 2/3, otherwise after H1 and H2, stop at EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW. Population validation requires later scientific authorization.
