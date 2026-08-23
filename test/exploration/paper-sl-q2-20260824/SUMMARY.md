# PAPER-SL-Q2 summary

## Verdict

`BIAS_BRANCH_SUBTHRESHOLD`

Under the frozen PAPER-SL-Q1 ideal-current replay, neither 37.5 µA nor 40 µA
produced a complete BJL2 event. Both logical0 and both READ=0 controls remained
zero-event and bounded. The accepted 35 µA Q1 baseline was not rerun.

## Main results

| IBIAS | case | BJs largest segment / area | BJL1 largest segment / area | BJL2 largest segment / area | complete BJL2 | post complete |
|---:|---|---:|---:|---:|---:|---:|
| 37.5 µA | logical1 + READ | 14.09212 / 14.09214 | 0.79726 / 0.79728 | 0.88033 / 0.88033 | 0 | 0 |
| 37.5 µA | logical0 + READ | 0.02368 / 0.02368 | 0.01927 / 0.01927 | 0.00659 / 0.00659 | 0 | 0 |
| 37.5 µA | controls | ~0.00018 / ~0.00018 | ~0.000072 / ~0.000072 | ~0.000025 / ~0.000025 | 0 | 0 |
| 40 µA | logical1 + READ | 14.09212 / 14.09214 | 0.81541 / 0.81545 | 0.94432 / 0.94433 | 0 | 0 |
| 40 µA | logical0 + READ | 0.02368 / 0.02368 | 0.01931 / 0.01931 | 0.00662 / 0.00662 | 0 | 0 |
| 40 µA | controls | ~0.00018 / ~0.00018 | ~0.000072 / ~0.000072 | ~0.000025 / ~0.000025 | 0 | 0 |

The largest 40 µA BJL2 segment reaches `0.944323 turn` with
`0.944333 Phi0` same-segment area, still below the registered one-turn
criterion. This is a near-threshold operating-point observation, not a local
pass and not a universal bias threshold.

## Settled load-line

| IBIAS | P(BJL1) | P(BJL2) | I(RB) | I(BJL1) | I(BJL2) |
|---:|---:|---:|---:|---:|---:|
| 37.5 µA | 0.466471 rad | 0.405654 rad | 37.5 µA | 16.1905 µA | 21.3095 µA |
| 40 µA | 0.499919 rad | 0.434736 rad | 40 µA | 17.2568 µA | 22.7432 µA |

The bias increase changes the settled load-line, but the read1 response does
not scale into a complete BJL2 segment within the two registered points.

## Boundary

Observed: Q1 replay source trajectories are byte-identical; only IBIAS is
changed. Direct P/V phase-area evidence is used for BJs/BJL1/BJL2 with the
registered [94,130) ps activity and [140,170) ps post windows.

Derived: 40 µA is closer to a BJL2 complete segment than 37.5 µA, but remains
subthreshold. Current/Ic and voltage peaks were not used as event evidence.

Inference: this two-point local central-bias bracket does not close the frozen
QB replay one-shot window. It does not distinguish all possible internal QB
ratio/load-line mechanisms.

Unknown: transfer to a physical BVM/JSL/QB network and behavior outside the
registered bias bracket.

