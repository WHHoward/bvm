# BVM -> QB TLINE Z0 rescue gate — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration and scope

- Experiment: `bvm-qb-tline-z0-rescue-gate-v1-20260916`
- Study phase: `EXPLORATORY`
- Role: `Experimental Operator + Evidence Packager`
- Registration HEAD: `ad15dc5abd26d12b618451f9358211ef90b3fa80`
- Remote `bvm/master` at registration: `ad15dc5abd26d12b618451f9358211ef90b3fa80`
- The prior TLINE experiment and canonical raws are read-only references. No
  existing experiment is overwritten, rerun, modified, or repackaged.

The single question is whether the N2 loss observed with the prior
`Z0=6 ohm, TD=0.3 ps` TLINE is mainly caused by that near-end interface
condition. `Z0=12 ohm` and `Z0=24 ohm` are discrete engineering diagnostic
values only. They are not matching values, measured characteristic
impedances, or linear load resistances.

## Frozen source fixture

The previous TLINE topology is retained exactly:

```text
B_JSL8 -> TLINE_IN -> ideal lossless four-node TLINE -> QBIN -> canonical QB
```

The BVM array, COMMON_SL, eight JSL elements, canonical QB, six-stage JTL,
10-ohm terminal, stimulus, solver, `.tran 0.1p 200p`, and printed probe set
are unchanged. The only new deck-line change is the registered replacement of
the prior TLINE token:

```text
T_BVM_QB TLINE_IN 0 QBIN 0 TD=0.3p Z0=6
```

with either `Z0=12` or `Z0=24`. Every other line is byte-identical to the
corresponding prior TLINE deck. There is no QB/BVM/JTL/terminal modification,
amplitude scaling, matching network, transformer, READ extension, sentinel,
extra delay point, extra Z0 point, or timestep sweep.

The prior TLINE smoke result is the syntax authority for this experiment:
`Tlabel Vi+ Vi- Vo+ Vo- TD=value Z0=value`, `TD=0.3 ps` measured as three
stored samples on the 0.1-ps grid. It is referenced by hash and is not rerun.

## Exactly authorized solves

### Stage 1 — automatic preflight PASS required

Exactly two new physical solves are authorized:

| run | mask | TD | Z0 | purpose |
|---|---|---:|---:|---|
| `Z0_12_0011` | `0011` | 0.3 ps | 12 ohm | N2 rescue gate |
| `Z0_24_0011` | `0011` | 0.3 ps | 24 ohm | N2 rescue gate |

The maximum Stage 1 solve count is two. No `0111`, `0001`, `1111`, `TD=0.6`
or other Z0 case may be run at this stage.

### Stage 2 — conditional gate only

Only if one of the Stage 1 cases passes the rescue gate may one and only one
`0111` deck be materialized and solved. The selected Z0 is the one with the
smallest registered normalized actual-grid recovery/re-arm distance to the
canonical N2 trajectory. The maximum total new physical solve count is three.
If neither Stage 1 case passes, record `TLINE_Z0_RESCUE_FAILED` and stop.

## Raw grid, probes, and windows

- Raw is the immutable JoSIM output; expected grid is 1999 samples from 0 to
  199.9 ps with `.tran 0.1p 200p`.
- All windows are half-open and select actual stored timestamps. No
  interpolation, resampling, smoothing, time shift, sign correction, or
  amplitude scaling is allowed.
- Registered windows: full `[0,200) ps`, control `[70,110) ps`, focus
  `[110,121) ps`, and recovery `[121,130) ps`.
- Required raw probes include all BVM storage/R-loop/output branches, active
  JS1/JS2 and JM1/JM2 P/V/I, COMMON_SL, P/V/I JSL1..JSL8, TLINE near-port
  `V(TLINE_IN,0)`/`I(T_BVM_QB)`, QBIN, receiver-side `I(LIN|XBQ1)` and
  `V(LIN|XBQ1)`, QB internal BJS/BJ1/BJ2 P/V/I, L1/L2/L3/RJ1/RJ2 I/V,
  all JTL1..6 B01/B02 P/V/I and stage outputs, and terminal probes.
- `I(IB|XBQ1)` and `V(IB|XBQ1)` remain inherited public print requests but
  are known unavailable in JoSIM's public lookup. They are recorded as
  `UNKNOWN/NOT_SUPPORTED`; no metric uses them and their two known solver
  warning lines are nonfatal.
- `I(T_BVM_QB)` is the exposed first-port TLINE branch current. `I(LIN|XBQ1)`
  is the receiver-side QBIN KCL current, not a silently invented second
  TLINE branch label.

## Rescue gate and metric semantics

The N2 oracle is internal ordered phase navigation:
`BJ1 -> BJ2 -> JTL1 -> ... -> JTL6`. The first and second candidates use
`+0.5` and `+1.5` turns after independent continuous unwrapping of raw phase
radians. Terminal traces are corroboration only and never the sole oracle.

The gate also records, on the actual stored grid:

- first BJ1/BJ2 timing and second BJ1/BJ2 recovery;
- `I(L1)`/`I(L2)` min/max, sign crossings, first sustained negative-to-positive
  crossing, and positive/negative dwell in `[121,130) ps`;
- reset-voltage signed integrals for L1/L2/L3/RJ1/RJ2;
- `I(B_JSL8)`, `I(T_BVM_QB)`, and `I(LIN|XBQ1)` signed recovery profiles,
  including first positive-to-negative crossing, negative dwell and minimum;
- COMMON_SL, QBIN, JSL1..JSL8, active BVM JS1/JS2, LS3, R_S, LM3, L_SL,
  and JM1/JM2 raw trajectories;
- JS1/JS2 same-JJ phase/voltage-area checks in `[110,121) ps`, using direct
  same-JJ voltage and actual-grid trapezoidal integration.

“Sustained negative-to-positive” means a sign transition followed by three
consecutive stored samples strictly greater than zero. Dwell is the sum of
actual stored-grid intervals whose left sample has the relevant sign. Zero
values are neutral for sign-transition counting.

`2*TD` is only a propagation-scale intuition and is not a measured return
delay. No incident/reflected wave decomposition, reflection coefficient,
matching claim, SFQ count, or hardware claim is allowed.

## Evidence and stop contract

Each new run keeps its exact `deck.cir`, `raw.csv`, and `run.log`. Machine
provenance records HEAD, solver identity, source hashes, transformations,
raw hashes before/after analysis, artifact validity, and all actual solves.
Standalone and paired descriptive plots use `scripts/josim-plot2.py` with
actual-grid focused pages. Plots do not certify switching, SFQ delivery, or a
mechanism.

The result fields explicitly distinguish:

- `mechanical_analysis_performed`;
- `bounded_experiment_interpretation_performed`;
- `independent_scientific_review_performed`.

The final marker is `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
The raw evidence ZIP is Drive-only; its package/Drive identity is kept in the
external `delivery_manifest.json`. No automatic follow-up is permitted.
