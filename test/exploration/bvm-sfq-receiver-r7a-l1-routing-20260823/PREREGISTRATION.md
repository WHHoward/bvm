# R7-A native-QB L1 single-point routing Exploration

## Status

`PREREGISTERED` before execution.

- Run ID: `bvm-sfq-receiver-r7a-l1-routing-20260823`
- Created: `2026-08-23T00:39:08+08:00`
- Git HEAD before this Exploration: `a32c341766150e532a2e097f8c2573eb532748ce`
- Worktree was clean before the new R7-A directory was created.
- Study phase: `EXPLORATORY`
- Execution mode: one point, four matched runs, no sweep
- JoSIM: `build/josim-cli`, `v2.7.2837d13`
- JoSIM SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Requested timestep: `0.0125 ps`
- Stop time: `170 ps`

## Primary research question

Does reducing native-QB `L1` from `3.91 pH` to `2.50 pH`, with `L2` and all
other receiver/source parameters frozen at R6-B, increase the fraction of the
read1 front-stage perturbation routed into `L2`/BJL2 while preserving read0
selectivity and the canonical BVM source/storage guard?

## Physics-informed hypothesis

At the R6-B read1 transient's approximately `1.5 ps` dominant oscillation
period, lowering `L1` reduces the node2-to-node3 inductive reactance and moves
some dynamic current from BJL1/RJ1 into the L1/L2 path. The actual gain is
not assumed to equal the ideal `1/L1` ratio because the QB network is
nonlinear and load-coupled.

## Alternatives

- L1 changes the settled phase/current branch but does not increase L2/BJL2
  routing.
- L1 produces no meaningful routing change at this point.
- L1 causes reflected-load source disturbance or nonselective activity.
- BJL2 produces exactly one local phase/voltage-area-consistent event.

## Frozen conditions

- Canonical BVM topology and parameters: unchanged.
- SL route, R6-B transformer and passive return: unchanged.
- `R_PRI=12 ohm`, `L_PRI=0.20 pH`, `L_SEC=1.00 pH`,
  `K=0.70710678`.
- Native QB BJs/BJL1/BJL2 AREA: unchanged.
- `L1=2.50 pH` is the only receiver parameter change.
- `L2=3.91 pH`, `Lin=0.8 pH`, `L0=1.323 pH` unchanged.
- `RB=8.5 ohm`, `IB=90 uA`, `RJ1=33 ohm`, `RJ2=22 ohm` unchanged.
- Output passive load: `10 ohm`.
- Four cases: `read1`, `read0`, `logical1-read0-control`,
  `logical0-read0-control`.
- One run per case; no sweep; no JTL/T1; no convergence ladder in this
  Exploration.

## Windows and routing metrics

All windows are half-open and applied to the actual CSV time column:

- pre: `[80,90) ps`
- activity: `[94,130) ps`
- post: `[150,170) ps`
- read-state: `[20,90) ps`

For each state, the control-subtracted signal is preregistered as

```text
delta_I_x(t) = I_read(t) - I_matching_READ0_control(t)
```

The primary routing metrics are

```text
G_L2   = RMS(delta_I_L2)   / RMS(delta_I_Lin)
G_BJL2 = RMS(delta_I_BJL2) / RMS(delta_I_Lin)
```

The RMS is computed over the same `[94,130) ps` samples using the actual time
axis for alignment. R6-B descriptive references are `G_L2≈0.194` and
`G_BJL2≈0.175`; no new universal threshold is introduced here.

Also report BJL1/RJ1 redistribution, L1/L2 currents, BJs/BJL1/BJL2 phase and
current operating points, read1/read0 absolute separation, source/storage
guards, and BJL2 same-JJ phase/voltage-area segments.

## Local-event rule

Raw `P(...)` remains radians. A local BJL2 event requires one continuous
same-JJ phase trajectory with a monotonic segment of at least `1.0 turn` in
the activity window and a consistent direct same-JJ `V(BJL2|XBQ)` area over
the same endpoints, direction, run, and window. Current or voltage peaks alone
are insufficient. A local BJL2 event is not downstream SFQ delivery.

## Allowed outcomes

- `ROUTING_GAIN_WITH_SELECTIVITY_PRESERVED`
- `STATIC_OP_SHIFT_WITHOUT_CLEAR_ROUTING_GAIN`
- `L1_ROUTING_HYPOTHESIS_NOT_SUPPORTED_AT_THIS_POINT`
- `ISOLATED_NATIVE_QB_LOCAL_PASS`
- `BACK_ACTION_OR_NONSELECTIVE_FAILURE`
- `INCONCLUSIVE`

If no complete event occurs, do not add an L1 sweep. The conclusion remains
bounded to this model, source, load, timestep, window, and single point.
