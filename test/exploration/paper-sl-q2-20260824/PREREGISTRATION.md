# PAPER-SL-Q2 — local QB bias closure under frozen paper-JSL replay

## Scope

This is a bounded Exploration. It uses the accepted PAPER-SL-Q1 ideal-current
replay fixture and does not connect the physical BVM, paper-JSL load, or any
downstream JTL/T1. The Q1 replay source trajectories are copied byte-for-byte;
only the QB central bias source `IBIAS` changes.

Registration time: `2026-08-24T03:54:53+08:00`  
Parent HEAD: `5627a6386a143784db109138e953368f7ab8a4c2`

## Scientific question

Can a small, local high-side bias increase move the already state-selective
paper-JSL logical1 replay from the Q1 near-threshold regime into one complete
BJL2 event, while logical0 and both READ=0 controls remain event-free and
bounded?

## Frozen conditions

The QB cell, model, topology, inductors, resistors, output load, replay source
PWL knots, polarity, timestep, stop time, and analysis windows are inherited
from Q1:

| item | frozen value |
|---|---:|
| BJs AREA | 0.50 |
| BJL1 AREA | 0.36 |
| BJL2 AREA | 0.54 |
| Lin / L0 | 0.8 pH / 1.323 pH |
| L1 / L2 | 3.91 pH / 3.91 pH |
| RJ1 / RJ2 | 33 Ω / 22 Ω |
| RB | 6 Ω |
| output load | 10 Ω |
| jjmit model | Q1 snapshot, unchanged |
| replay grid / stop | 0.0125 ps / 170 ps |
| activity window | [94, 130) ps |
| post window | [140, 170) ps |

The accepted Q1 35 µA result is the baseline and is not rerun. The only new
registered points are 37.5 µA and, conditionally, 40 µA.

## Analytic point selection

Q1 logical1 READ=0 settled data are used only for a first-order load-line
review. At 35 µA, the measured settled branch currents are approximately:

```text
I(RB)   = 35.000 µA
I(BJL1) = 15.12166 µA
I(BJL2) = 19.87834 µA
I(RJ1), I(RJ2) ≈ 0
```

Thus the static bias split is approximately 43.2% through BJL1 and 56.8%
through BJL2. Holding that split only as a local first-order estimate gives:

| IBIAS | projected BJL1 | projected BJL2 | BJL1/Ic | BJL2/Ic |
|---:|---:|---:|---:|---:|
| 35.0 µA baseline | 15.122 µA | 19.878 µA | 0.420 | 0.368 |
| 37.5 µA | 16.202 µA | 21.298 µA | 0.450 | 0.394 |
| 40.0 µA | 17.282 µA | 22.718 µA | 0.480 | 0.421 |

These projections are not event criteria and do not assume that a nonlinear
read transient preserves the DC split. The first point is 37.5 µA because it
is the smallest registered perturbation and therefore gives the cleanest
causal test. The 40 µA point is run only if 37.5 µA remains bounded and does
not establish a qualifying result or a BJL1-only stop condition.

## Matched cases and stop order

For each executed bias, use the same four Q1 replay cases:

1. logical1 + READ=0 control;
2. logical0 + READ=0 control;
3. logical0 + READ;
4. logical1 + READ.

The first three are checked before the logical1 READ result is interpreted.
If a control or logical0 has a complete BJL1/BJL2 event, free-running, or
multifire behavior, stop that bias direction immediately. If logical1 has a
complete BJL1 event while BJL2 remains subthreshold, record the BJL1-only
closure and stop the bias branch without changing BJL2.

If 37.5 µA produces a selective exactly-one BJL2 result with bounded post
behavior, do not run 40 µA. Otherwise, if no stop condition occurs, run 40 µA
using the same order. At the end of the registered bracket, a no-event result
is limited to these two tested bias points.

## Evidence rule

For BJs, BJL1, and BJL2 record direct continuous unwrapped phase, monotonic
segments, and same-JJ/same-segment `integral(V dt)/Phi0`. A complete event
requires at least one monotonic segment of one turn with consistent voltage
area. Current over `Ic`, voltage peaks, total phase range, or a plot alone
cannot establish an event. Post boundedness/retrap and additional complete
segments are checked separately.

## Verdict classes

- `PAPER_SL_QB_BIAS_ONE_SHOT`: logical1 BJL2 exactly one; logical0/control
  zero; bounded post/retrap.
- `BJL1_ONE_SHOT_BJL2_SUBTHRESHOLD`: selective BJL1 complete event but no
  qualifying BJL2 event.
- `BIAS_BRANCH_SUBTHRESHOLD`: both registered points remain below complete
  BJL2 event and negatives remain zero.
- `NONSELECTIVE_OR_FREE_RUNNING`: control/logical0 event, multifire, or
  free-running behavior.
- `INCONCLUSIVE`: invalid artifact or insufficient phase/area/post evidence.

This Exploration does not establish physical BVM-to-QB operation, downstream
SFQ delivery, or a universal bias threshold.

