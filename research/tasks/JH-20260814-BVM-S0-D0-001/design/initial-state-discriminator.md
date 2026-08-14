# BVM-S0/D0 — Initial-state discriminator design

## Why D0 precedes S0

`BVM-S0` requires two observable, reproducibly prepared initial states before it
may call their subsequent read stimuli `read0` and `read1`.  The repository has
historical W1/W0-labelled PWL sequences and legacy phase traces, but neither is a
frozen, isolated demonstration that the two initialization procedures create
distinct, stable, observable initial states.  In particular, a filename or an
old `W1`/`W0` label is not such a demonstration.

Therefore D0 is an exploratory, bounded discriminator.  It does **not** run a
read pulse, characterize a source pulse, choose a receiver, or attach logical
bit/fluxoid meaning to a phase value.  Its only question is whether the two
specified write procedures yield two reproducible, stable *operational state
signatures* in the declared BVM instance.  An accepted D0 is a prerequisite for
a later S0 contract, not S0 evidence.

## Fixed closure and canonical load

| Item | Frozen choice |
|---|---|
| BVM cell | `circuits/bvm/bvm_cell.cir`, subcircuit `BVM` |
| JJ model | `circuits/models/jjmit.cir` |
| Instance | `XBVM1 WL1 BL1 SE1 SL1 BVM` |
| Only load | `R_LD SL1 0 12` (12 ohm); no stack, BQ, DCSFQ, JTL, or load sweep |
| Output voltage | `V(SL1)`, positive `SL1 -> 0` |
| Output current | `I(L_SL|XBVM1)`, positive in the BVM netlist direction `N8 -> SL`; it is the current delivered from the BVM output chain into the declared source port |
| Solver ladder | D0: nominal `0.1 ps` only.  A later S0 must separately preregister `0.1/0.05/0.025 ps`; D0 does not transfer a tolerance to it. |

The D0 execution copies the cell and model into its unique run directory before
running.  These copied inputs, rather than a mutable working-tree lookup, are
the run closure.

## Direct junction probes and direction

The BVM source file defines:

- `B_JM1 N1 n_jm1o ...`; register `P(B_JM1|XBVM1)` and
  `V(B_JM1|XBVM1)` with positive orientation `N1 -> n_jm1o`.
- `B_JM2 n_jm2i N2 ...`; register `P(B_JM2|XBVM1)` and
  `V(B_JM2|XBVM1)` with positive orientation `n_jm2i -> N2`.

These are direct JoSIM element probes.  `V(SL1)`, `V(WL1)`, `V(BL1)`, and
`V(SE1)` are never substitutes for either junction voltage.  D0 may report
same-run, same-window raw-time phase/area values descriptively; it sets no
phase-area acceptance tolerance and makes no local-event, fluxoid, or downstream
claim.

## Three predeclared cases

All cases have the same instance, closure, 12-ohm load, duration
`[0, 80 ps]`, output columns, zero SE/read source, and nominal timestep
`0.1 ps`.  The only difference is the initialization PWL.

| Case ID | WL/BL initialization | SE/read source |
|---|---|---|
| `init_positive` | both sources `0 -> +100 uA` over 10–11 ps, hold through 20 ps, return to `0` by 21 ps | identically zero |
| `init_negative` | both sources `0 -> -100 uA` over 10–11 ps, hold through 20 ps, return to `0` by 21 ps | identically zero |
| `no_init_control` | identically zero | identically zero |

No waveform may be changed after inspection.  These are operational names only:
they are **not** a claim that either signature is published logical 0/1, a BVM
fluxoid count, or a successfully readable state.

## Registered windows and discriminator

All windows are half-open and use actual CSV samples:

| Window | Interval | Purpose |
|---|---:|---|
| `pre_init` | `[4, 9) ps` | startup reference |
| `init_activity` | `[9, 31) ps` | allowed initialization activity / direct-JJ area window |
| `state_early` | `[35, 45) ps` | first post-initialization platform witness |
| `state_late` | `[65, 75) ps` | persistence witness |

For each state window, record the mean and peak-to-peak range of the ordered
signature vector `(P(B_JM1|XBVM1), P(B_JM2|XBVM1))` in raw radians.  The
predeclared exploratory discriminator is:

1. every state window contains at least two actual samples and neither P column
   has NaN/Inf;
2. each component's peak-to-peak range is at most `0.02 rad` in both state
   windows; and
3. the L-infinity separation between the `init_positive` and `init_negative`
   state-window means is at least `0.10 rad` in both windows.

These bands are D0-specific observability guards, not a global BVM stability,
integer-turn, phase-area-residual, or S0 acceptance tolerance.  If any guard is
not met, or direct P/V output is unavailable, D0 remains a valid exploratory
artifact only if the data are otherwise sound and its conclusion is
`INCONCLUSIVE`; it must not advance S0.

## What an accepted D0 enables — and what it does not

Only if D0's raw data meet the registered discriminator may a later, separately
issued S0 use these two procedures as *operationally distinguishable initial
states*.  That S0 must still define its read stimulus, matched zero controls,
readout windows, its full `0.1/0.05/0.025 ps` ladder, task-local bands, and stop
rule before execution.  It must keep read0/read1 identical apart from this
initialization and must not assign logical/published semantics without separate
provenance evidence.

