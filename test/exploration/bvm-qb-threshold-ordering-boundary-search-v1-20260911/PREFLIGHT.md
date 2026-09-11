# QB threshold-ordering boundary search - PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: bvm-qb-threshold-ordering-boundary-search-v1-20260911
- Registration HEAD: 0063d54c64ddefb8e10fe5f96af79b1ed9f55dc4
- Sealed preflight HEAD: 0063d54c64ddefb8e10fe5f96af79b1ed9f55dc4
- Remote bvm/master: 0063d54c64ddefb8e10fe5f96af79b1ed9f55dc4
- Status: PASS
- Solver has not been invoked at preflight.

## Exact scope

Only two midpoint points are registered: Stage A L2=1.8 pH, L3=1.6 pH and Stage B IBias=250 uA, L3=1.6 pH; each uses masks 0011 and 0111, for exactly four new physical solves. L3=1.6 is fixed and all other parameters remain canonical.

## Corrected history/control

Use only actual stored samples in 70-81 ps ZERO_STATE_READ_CONTROL, 81-90 ps idle, 90-101 ps WRITE1 and 101-110 ps SETTLE. CONTROL contamination requires an unintended complete QBOUT->JTL1->...->JTL6 chain in those windows. FINAL/Tail rollback is separate and cannot mark CONTROL.

## Interpretation ceiling

Phase is raw radians; rad/(2*pi) is navigation only and not an SFQ count. The midpoint result can only establish bounded threshold ordering under this model, history, load, solver and 0.1 ps grid. No L2=1.7/1.9, IB=245/255, N1/N4, positional validation, timestep refinement or third-parameter solve is authorized.

## Stop

After the four midpoint solves, or earlier if a clean N2=2/N3=3 is observed, stop at EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW. Any population validation requires later scientific authorization.
