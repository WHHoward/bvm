# R8 BJL2 output-stage current-class single-point Exploration

## Status

`PREREGISTERED` before execution.

- Run ID: `bvm-sfq-receiver-r8-bjl2-area070-20260823`
- Created: `2026-08-23T01:18:02+08:00`
- Git HEAD before this Exploration: `3d8414c7410e2b23a059ba7e711d62bdce1c8969`
- Study phase: `EXPLORATORY`
- Execution mode: one point, four matched runs, no sweep
- JoSIM: `build/josim-cli`, `v2.7.2837d13`
- JoSIM SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Requested timestep: `0.0125 ps`
- Stop time: `170 ps`

## Primary research question

Does reducing only the native-QB BJL2 output-stage `AREA` from `1.89` to
`0.70`, with the R7-A isolated source and routing point frozen, move the
state-selective response into a substantially more nonlinear or quantizing
BJL2 regime without collapsing read0 margin or disturbing the canonical BVM
source/storage guard?

## Physics boundary

This is not a pure `Ic` experiment. Under the frozen `jjmit.cir` model:

```text
Ic, C  ∝ AREA
RN, R0 ∝ 1/AREA
```

The intrinsic `beta_c` remains approximately constant, while the BJL2
capacitance, intrinsic resistance, and loading relative to `RJ2=22 ohm` and
the fixed output network change. The point therefore tests an output-stage
current-class/AREA change as a combined nonlinear dynamic perturbation.

## Frozen conditions

- Canonical BVM topology and parameters: unchanged.
- R7-A isolated transformer and passive return: unchanged.
- `L1=2.50 pH`, `L2=3.91 pH`, `Lin=0.8 pH`, `L0=1.323 pH`.
- BJs `AREA=1.33`, BJL1 `AREA=1.12`.
- **Only changed receiver parameter:** BJL2 `AREA=0.70`.
- `IB=90 uA`, `RB=8.5 ohm`, `RJ1=33 ohm`, `RJ2=22 ohm`.
- R7-A transformer: `R_PRI=12 ohm`, `L_PRI=0.20 pH`, `L_SEC=1.00 pH`,
  `K=0.70710678`.
- Output passive load: `10 ohm`.
- Four cases: `read1`, `read0`, `logical1-read0-control`,
  `logical0-read0-control`.
- One run per case; no AREA sweep, bias change, transformer change, JTL, or
  T1.

The actual BJL2 model point is expected to be approximately:

```text
Ic = 70 uA
C  = 49 fF
RN = 22.86 ohm
R0 = 228.57 ohm
```

## Windows and probes

The R7-A windows and source PWLs are frozen:

- pre: `[80,90) ps`
- activity: `[94,130) ps`
- post: `[150,170) ps`
- read-state: `[20,90) ps`

The same probes are retained for BJs/BJL1/BJL2 `P/V/I`, `Lin/L1/L2/L0/RB`,
`RJ1/RJ2`, transformer branches, `SL/N6/OUT`, and `JM1/JM2/JS1/JS2`.

## Required measurements

Settled operating points must be recomputed from the new READ=0 controls:

```text
P(BJs), P(BJL1), P(BJL2)
I(Lin), I(BJL1), I(BJL2), I(L1), I(L2), I(RB)
```

Also report actual `BJL2 settled I/Ic`, read1 peak `I/Ic`, and read0 peak
`I/Ic`. These ratios are local diagnostics only and are not event criteria.

Compare R8 against R7-A for read1 and read0:

- BJL2 activity-range gain;
- largest monotonic phase-segment gain;
- same-JJ voltage-area gain;
- current-excursion gain;
- read1/read0 separation and control activity;
- BJs/BJL1 redistribution.

## Event rule

Raw `P(...)` remains radians. A BJL2 local event requires one continuous
unwrapped same-JJ phase trajectory with a monotonic segment of at least
`1.0 turn`, a same-segment direct `V(BJL2|XBQ)` area consistent with that
phase evolution, and bounded post-event retrap without a second complete
transition or free-running. Current above `Ic`, voltage peak, or activity
range alone is insufficient. A local event is not downstream SFQ delivery.

## Source/storage guard

Compare canonical no-receiver and R7-A baselines using `I(L_SL)`, `V(SL)`,
`V(N6)`, JM1/JM2 drift, and JS1/JS2 post-window p2p. Absolute canonical
read1 JS running is expected source behavior and is not itself receiver
back-action.

## Allowed outcomes

- `BJL2_OUTPUT_CLASS_NONLINEAR_GAIN_WITH_SELECTIVITY_PRESERVED`
- `BJL2_OUTPUT_CLASS_LOCAL_PASS`
- `OUTPUT_CLASS_GAIN_WITH_READ0_MARGIN_COLLAPSE`
- `OUTPUT_CLASS_CHANGE_WITHOUT_MEANINGFUL_BJL2_GAIN`
- `BACK_ACTION_OR_FREE_RUNNING_FAILURE`
- `INCONCLUSIVE`

If the point remains a roughly `1e-3 turn` response, do not append an AREA
sweep. If a large nonlinear jump occurs, do not automatically lower AREA;
first assess read0 margin, retrap, load-line, and event evidence.

