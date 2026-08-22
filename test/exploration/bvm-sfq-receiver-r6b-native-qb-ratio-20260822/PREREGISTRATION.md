# R6-B native-QB matched-ratio transfer Exploration

## Status

`PREREGISTERED` before netlist generation and execution.

- Run ID: `bvm-sfq-receiver-r6b-native-qb-ratio-20260822`
- Created: `2026-08-22T23:33:37+08:00`
- Git HEAD at preregistration: `c6cdd5672e1ba457cf4c7da8e05c2757def7ccdd`
- Worktree at preregistration: clean
- Study phase: `EXPLORATORY`
- JoSIM: `build/josim-cli`, `v2.7.2837d13`
- JoSIM SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Metric contract: `docs/research/METRIC_SPEC_V2.md`, v2.0.0
- Metric contract SHA-256: `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`

## Single research question

With the native paper-QB topology and all native QB parameters frozen, does
the R6-B matched-ratio interface

```text
canonical SL-derived primary -> R_PRI 12 ohm -> L_PRI 0.20 pH
L_PRI -- K=0.70710678 -- L_SEC 1.00 pH -> native QB IN
```

increase the native-QB drive relative to accepted R6-A while preserving the
canonical BVM source/storage behavior sufficiently to justify the resulting
reflected-load risk?

## Frozen conditions

- Canonical BVM topology and parameters: unchanged.
- Native `BQ_PAPER` topology and parameters: unchanged.
- BJs/BJL1/BJL2 AREA, Lin/L0/L1/L2, RJ1/RJ2, RB/IB, and OUT passive load:
  unchanged from R6-A.
- Primary return: `R_PRI SL1 N_PRI 12.0`, `L_PRI N_PRI 0 0.20p`.
- Canonical BVM SL termination: retained; not replaced or deleted.
- Mutual interface: the only changed receiver parameter is `L_SEC=1.00p` and
  `K=0.70710678`; `M=0.316227766 pH` is the R6-A-matched value.
- Requested timestep: `0.0125 ps`.
- Stop time: `170 ps`.
- One run for each case; no parameter sweep and no convergence ladder in this
  Exploration.

## Matched cases

1. `read1`: logical1 write plus canonical positive READ.
2. `read0`: logical0 write plus canonical positive READ.
3. `logical1-read0-control`: logical1 write, READ=0.
4. `logical0-read0-control`: logical0 write, READ=0.

The four PWL inputs, initial conditions, bias ramp, load, timestep, stop time,
and measurement probes are identical to R6-A except for the declared R6-B
secondary/mutual values.

## Hypothesis and alternatives

Primary hypothesis: reducing the secondary source/leakage impedance at fixed
first-order M increases the native-QB input current and/or voltage transient,
with read1 activity increasing more than read0/control activity, while the
source guard remains close to the canonical no-receiver and R6-A baselines.

Alternatives:

- drive gain is negligible because the native QB nonlinear network remains the
  limiting impedance;
- drive gain occurs but reflected loading increases SL/N6 disturbance, JM drift,
  or JS post-window p2p;
- activity becomes nonselective or free-running;
- BJL2 still does not complete a phase/voltage-area-consistent local event.

## Predeclared measurements

For each case, report raw columns and derived quantities for:

- BJs, BJL1, BJL2: continuous/unwrapped phase, raw phase deltas in radians,
  phase deltas in turns, activity range, largest monotonic segment, direct
  same-JJ voltage area, and residual;
- `I(R_PRI)`, `I(L_PRI)`, `V(L_SEC)`, `I(L_SEC)`, `V(QB_IN)`;
- `V(SL1)`, `V(N6|XBVM1)`, `I(L_SL|XBVM1)`;
- `P(B_JM1|XBVM1)`, `P(B_JM2|XBVM1)`, `P(B_JS1|XBVM1)`,
  `P(B_JS2|XBVM1)` and their pre/post drift/p2p;
- native QB branch currents including `I(Lin|XBQ)`, `I(RB|XBQ)`,
  `I(RJ1|XBQ)`, and `I(RJ2|XBQ)`.

The principal R6-B/R6-A comparison is made using the same `[94,130) ps`
activity, `[80,90) ps` pre, and `[150,170) ps` post windows, against the
actual CSV time column. The windows are inherited from R6-A and frozen before
R6-B execution.

## Local-event rule

A BJL2 local event is recognized only if one continuous unwrapped BJL2 phase
trajectory contains a monotonic segment of at least 1.0 turn in the activity
window and the same segment's direct `V(BJL2|XBQ)` integral divided by Phi0 is
consistent with the phase delta. Current above Ic, a voltage peak, or a phase
excursion alone is insufficient. A local BJL2 event is not downstream SFQ
delivery.

## Predeclared interpretation classes

- `DRIVE_GAIN_WITH_ISOLATION_PRESERVED`: R6-B has a meaningful increase in
  native-QB drive/activity over R6-A, while source/storage comparison remains
  consistent with the canonical no-receiver and R6-A guards; no complete-event
  claim is made unless the local-event rule is satisfied.
- `DRIVE_GAIN_WITH_REFLECTED_BACK_ACTION`: drive increases, but the comparative
  SL/N6/JM/JS guard shows additional receiver-reflected disturbance.
- `NO_MEANINGFUL_DRIVE_GAIN`: no material R6-B increase in secondary/QB drive
  or BJL2 activity over R6-A.
- `ISOLATED_NATIVE_QB_LOCAL_PASS`: read1 has exactly one complete BJL2 local
  phase/area-consistent event, read0 and both controls have zero, and no
  free-running behavior is observed. This remains an Exploration result and
  does not establish JTL/T1 delivery.
- `NONSELECTIVE_OR_FREE_RUNNING`: read0/control has complete activity or
  sustained running comparable to read1.
- `INCONCLUSIVE`: artifact QA, signs/endpoints, windows, or source/storage
  comparison cannot be resolved.

No post-result threshold will be invented for “meaningful” drive gain. The
report must show the measured R6-B/R6-A values and state where the comparison
is descriptive rather than a frozen physical Gate.

## Execution boundary

No QB AREA/bias/RJ/L changes, no secondary sweep, no JTL/T1, and no canonical
BVM modification are authorized by this preregistration.
