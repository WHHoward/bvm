# BVM QB L1/L3/BJ2 targeted closure - PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: bvm-qb-l1-l3-bj2-targeted-closure-v1-20260914
- Registration HEAD: 135ed25ddafb4ef7b47e1a1d4a2070c223fe45fe
- Sealed preflight HEAD: 135ed25ddafb4ef7b47e1a1d4a2070c223fe45fe
- Remote bvm/master: 135ed25ddafb4ef7b47e1a1d4a2070c223fe45fe
- Status: PASS
- Solver has not been invoked at preflight.

## Exact scope

The only new screening point is L1=1.2 pH plus L3=2.0 pH plus BJ2 area=2.2, with masks 0011 and 0111. Frozen parameters are Lin=1.5 pH, L2=2.0 pH, RJ1=32 ohm, RJ2=12 ohm, IBias=260 uA and BJS/BJ1 areas 4.0/0.9. Three reference pairs are immutable context and are not rerun.

## Source and topology

The resolved closure is inputs/jjmit.cir + inputs/bvm_jm2_connected.cir + the target BQ variant + inputs/jtl2.cir; topology is BVM1..4 -> COMMON_SL -> eight-JJ JSL -> QB -> six-stage JTL -> R_TERM. The BQ variant changes only L1 1.4 -> 1.2 pH, BJ2 area 2.0 -> 2.2 and L3 1.3 pH -> 2.0 pH.

## Exact probes and metrics

Raw preserves the full BVM boundary, COMMON_SL, P/V/I for B_JSL1..8, QBIN, LIN/L1/L2/L3, BJS/BJ1/BJ2, RJ1/RJ2, all P/V/I B01/B02 JTL probes, every JTL output and I(R_TERM). Metrics are raw SHA-256, 1999-point actual grid 0..199.9 ps, phase navigation from the 101-110 ps baseline at +0.5/+1.5/+2.5/+3.5/+4.5 turns, corrected 70-110 ps control windows, I(L1) samples/positive dwell/crossing, actual-grid integrals of V(BJ1)-V(BJ2) over 118-121/121-124/124-128/128-132 ps, and I(B_JSL8) signed areas over 110-112/110-121/121-124/121-126 ps.

## Conditional validation

No third solve is authorized before scientific review. Masks 0001 and 1111 are reserved for a separate later validation task only after a clean ordered 2/3 result and explicit scientific-review authorization. This experiment maximum is two new physical solves.

## Corrected history/control

Use actual stored samples in 70-81 ps ZERO_STATE_READ_CONTROL, 81-90 ps idle, 90-101 ps WRITE1 and 101-110 ps SETTLE. Only unintended complete QBOUT->JTL1..6 propagation before FINAL READ is contamination. FINAL/Tail rollback is separate.

## Interpretation ceiling

P values are raw radians; rad/(2*pi) is navigation only, not an SFQ count. The result is bounded to this source, receiver, load, history, solver and 0.1 ps grid. No additional parameter/scan, replay, source modification, timestep refinement or positional validation is authorized.

## Known UNKNOWNs

No timestep convergence, parameter sensitivity, hardware equivalence, exact continuous optimum or universal mechanism is established by this Quick experiment.

## Stop

After the two screening solves, stop at EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW. A clean 2/3 result is a candidate record only; it does not authorize a third solve in this experiment.
