# BVM R-loop branch timing decomposition — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration

- Experiment: `bvm-rloop-branch-timing-decomposition-v1-20260916`
- Study phase: `EXPLORATORY`
- Role: `Experimental Operator + Evidence Packager`
- Registration HEAD: `7ade840c731bc078eae0c87e42ca983aa74700dd`
- Remote `bvm/master` at registration: `7ade840c731bc078eae0c87e42ca983aa74700dd`
- Previous total-bridge replay, QBIN-boundary replay, LS3 static intervention,
  and TLINE experiments are read-only references. They are not rerun,
  modified, or repackaged.

## Single question

This experiment decomposes the prior 0.3-ps total-bridge-current replay effect:

> Is the strong N3 JS1 retrigger suppression mainly due to R_S timing, L_S3
> timing, or coordinated timing/current sharing of both branches?

This is an ideal current-forcing causal replay, not a physical delay network,
physical current-source proposal, or R_S/L_S3 equivalent.

The loaded forward path remains canonical:

```text
BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> JTL1..6 -> 10 ohm terminal
```

## Frozen branch families

Canonical bridge:

```text
R_S  6 10 3.0
L_S3 6 10 0.5P
```

Both branches are verified before source construction to use positive direction
`node6 -> node10`. The canonical audit checks `V(R_S)=3*I(R_S)`, parallel
voltage equality, node6/node10 KCL, and branch voltage/current signs.

Family A, `RS`: remove only `R_S`, retain physical `L_S3`, and inject each
instance's own canonical `I(R_S)` through `I_RS_REPLAY 6 10 PWL(...)`.

Family B, `LS3`: retain physical `R_S`, remove only `L_S3`, and inject each
instance's own canonical `I(L_S3)` through `I_LS3_REPLAY 6 10 PWL(...)`.

No single waveform is shared between BVM instances. QB, JSL, JTL, terminal,
stimulus, solver, timestep, and all other BVM parameters remain unchanged.

## Exactly authorized solves

First run exactly four EXACT cases:

| run | family | mask | replay branch |
|---|---|---|---|
| `RS_EXACT_0011` | RS-only | `0011` | canonical `I(R_S)` |
| `RS_EXACT_0111` | RS-only | `0111` | canonical `I(R_S)` |
| `LS3_EXACT_0011` | LS3-only | `0011` | canonical `I(L_S3)` |
| `LS3_EXACT_0111` | LS3-only | `0111` | canonical `I(L_S3)` |

Each family is gated independently. A family may run its own two delayed cases
only when both of its EXACT masks pass. The only delayed cases are:

| run | family | mask | delay |
|---|---|---|---:|
| `RS_DELAY0P3_0011` | RS-only | `0011` | 0.3 ps / 3 samples |
| `RS_DELAY0P3_0111` | RS-only | `0111` | 0.3 ps / 3 samples |
| `LS3_DELAY0P3_0011` | LS3-only | `0011` | 0.3 ps / 3 samples |
| `LS3_DELAY0P3_0111` | LS3-only | `0111` | 0.3 ps / 3 samples |

Maximum total new physical solves is eight. If a family fails EXACT, its
delayed cases are not materialized; the other family can continue.

## Exact-grid replay rule

For the replayed branch and each BVM instance, with `t0=110.0 ps`:

- `t < 110 ps`: canonical same-sample branch current;
- `110 <= t < 110.3 ps`: hold the canonical 110-ps sample;
- `t >= 110.3 ps`: canonical value at exact stored index `i-3`.

The canonical actual stored time grid is retained. No interpolation, smoothing,
resampling, amplitude scaling, sign modification, or raw mutation is allowed.
Source CSVs record the canonical raw hash, generated replay values, source hash,
shift, start index, pre-110 equality, hold rule, and post-shift rule.

## EXACT fidelity gate

Each family must match its canonical N2/N3 raw chronology on the registered
mechanical screen before its delayed cases can run:

- N2 ordered QB/JTL candidates = 2; N3 = 4;
- first BJ1/BJ2 timing drift <= 0.2 ps;
- every BVM JS1/JS2 `[110,121) ps` p2p drift <= 0.25 turns;
- key trajectory normalized RMS <= 0.50 for JSL8, COMMON_SL, QBIN, LIN,
  L1/L2, QBOUT, JTL6_OUT, and terminal current.

Actual errors are retained. The screen is mechanical replay fidelity, not a
physical tolerance or a claim of equivalence.

## Registered measurements

For N2 and N3, retain active-cell JS1/JS2 phase navigation, endpoint delta and
same-JJ voltage-area checks; JM1/JM2; first/later BJ1/BJ2; ordered QB/JTL
chronology; I(L1)/I(L2) recovery; JSL8/source current; COMMON_SL; QBIN; all
JTL stages; and terminal corroboration. Phase values are raw radians and turns
are only independent `rad/(2*pi)` navigation, never SFQ counts.

For every branch case, also retain:

- imposed replay current;
- the physical other branch current;
- `I_TOTAL = imposed + physical`;
- `Vbridge = V(6)-V(10)`;
- `[110,121)` and `[110,130)` ideal-source power/energy using
  `P_absorb=Vbridge*I_source`;
- direct comparison of branch total current with canonical total and previous
  total-bridge EXACT/DELAY0P3 raw.

The normalized branch-effect fraction is registered as
`F_B=(C-P_B)/(C-T)` for N3 JS1 p2p, with `C=canonical/EXACT`, `T=previous
total-bridge DELAY0P3`, and `P_B=branch delayed`. It is descriptive only; no
0.5/0.7 threshold is a scientific rule.

## Evidence boundary and stop

Mechanical tags such as branch-effect fraction, branch compensation, and large
ideal-source compliance are evidence labels only. Outcome A-D and mechanism
ranking remain unassigned until explicit scientific review. The final fields
must distinguish `mechanical_analysis_performed`,
`bounded_experiment_interpretation_performed`, and
`independent_scientific_review_performed`.

The final state is `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`. No 0.6-ps
case, other delay, transformer, mutual coupling, LC/all-pass network, sentinel,
QB sweep, LS3 sweep, or timestep sweep is authorized. Raw ZIP delivery is
Drive-only with delivery identity outside the ZIP.
