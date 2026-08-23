# PAPER-SL-Q2 analysis report

## Verdict: `BIAS_BRANCH_SUBTHRESHOLD`

Executed bias directories: `37p5u, 40u`.
Q1 replay source trajectories remain byte-identical; only IBIAS differs.

## Case summary

| bias | case | BJs units | BJL1 units | BJL2 units | BJs largest delta / area | BJL1 largest delta / area | BJL2 largest delta / area | post units | classification |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 37p5u | paper-j1-logical1-read0-control | 0 | 0 | 0 | 0.000180388 / 0.000180427 | -7.1938e-05 / -7.19621e-05 | -2.5051e-05 / -2.50551e-05 | 0 | `NO_COMPLETE_EVENT` |
| 37p5u | paper-j0-logical0-read0-control | 0 | 0 | 0 | -0.000180388 / -0.000180427 | 7.1938e-05 / 7.19615e-05 | 2.5051e-05 / 2.50496e-05 | 0 | `NO_COMPLETE_EVENT` |
| 37p5u | paper-j0-logical0-read | 0 | 0 | 0 | 0.0236757 / 0.0236817 | 0.0192651 / 0.0192704 | 0.00658881 / 0.00659052 | 0 | `NO_COMPLETE_EVENT` |
| 37p5u | paper-j1-logical1-read | 14 | 0 | 0 | 14.0921 / 14.0921 | 0.797259 / 0.797281 | 0.880329 / 0.880334 | 0 | `NO_COMPLETE_EVENT` |
| 40u | paper-j1-logical1-read0-control | 0 | 0 | 0 | 0.000180388 / 0.000180427 | -7.21768e-05 / -7.21952e-05 | -2.5051e-05 / -2.50475e-05 | 0 | `NO_COMPLETE_EVENT` |
| 40u | paper-j0-logical0-read0-control | 0 | 0 | 0 | -0.000180388 / -0.000180427 | 7.21768e-05 / 7.22008e-05 | 2.50669e-05 / 2.50616e-05 | 0 | `NO_COMPLETE_EVENT` |
| 40u | paper-j0-logical0-read | 0 | 0 | 0 | 0.0236757 / 0.0236817 | 0.0193068 / 0.0193122 | 0.00662115 / 0.00662284 | 0 | `NO_COMPLETE_EVENT` |
| 40u | paper-j1-logical1-read | 14 | 0 | 0 | 14.0921 / 14.0921 | 0.815414 / 0.815445 | 0.944323 / 0.944333 | 0 | `NO_COMPLETE_EVENT` |

## Settled operating points

| bias | P(BJs) rad | P(BJL1) rad | P(BJL2) rad | I(RB) µA | I(BJL1) µA | I(BJL2) µA | I(L1) µA | I(L2) µA |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 37p5u | -4.48513e-07 | 0.466471 | 0.405654 | 37.5 | 16.1905 | 21.3095 | -16.1905 | 21.3095 |
| 40u | -4.48513e-07 | 0.499919 | 0.434736 | 40 | 17.2568 | 22.7432 | -17.2568 | 22.7432 |

## Evidence boundary

- Observed: phase and voltage-area results use the same JJ, same monotonic segment, actual CSV time, and the registered [94,130) ps window; post checks use [140,170) ps.
- Derived: a BJL2 complete-unit count requires a segment of at least one turn with area consistency; current/Ic and voltage peaks are not used as event criteria.
- Inference: any high-side bias effect is a local QB operating-point result under ideal paper-JSL replay, not physical BVM interface evidence.
- Unknown: physical BVM/JSL source loading and whether this replay result transfers to a connected BVM.
