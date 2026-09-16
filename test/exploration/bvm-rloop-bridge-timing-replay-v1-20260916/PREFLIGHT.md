# BVM R-loop bridge-current timing replay — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration

- Experiment: `bvm-rloop-bridge-timing-replay-v1-20260916`
- Study phase: `EXPLORATORY`
- Role: `Experimental Operator + Evidence Packager`
- Registration HEAD: `3523c8c6edfaeb2b880302cf2281857134501774`
- Remote `bvm/master` at registration: `3523c8c6edfaeb2b880302cf2281857134501774`
- Existing canonical, replay, LS3, and TLINE experiments are read-only. No
  existing raw, deck, result, or provenance is overwritten or repackaged.

## Single question and intervention

This counterfactual replay asks whether timing-only forcing of the canonical
internal BVM R-loop bridge current can preserve the N2 two-response trajectory
while reducing the N3 retrigger/runaway trajectory. It is not a physical
delay-line design, current-source implementation proposal, R_S/L_S3 equivalent,
or circuit-equivalent reconstruction.

The forward path remains:

```text
BVM -> COMMON_SL -> JSL1..8 -> canonical QB -> canonical JTL1..6 -> 10 ohm terminal
```

For each BVM instance separately, the active canonical bridge elements

```text
R_S  6 10 3.0
L_S3 6 10 0.5P
```

are removed from a cloned BVM body and replaced by one ideal PWL current source
from local node `6` to local node `10`. The PWL values are the sum
`I(R_S|XBVMn)+I(L_S3|XBVMn)` from that same instance and mask's canonical raw.
QB, JSL, JTL, terminal, stimulus, solver, timestep, and all other BVM
parameters remain unchanged.

## Direction and KCL preflight

The canonical netlist establishes both branch orders as `6 -> 10`. Before any
PWL is generated, canonical N2 and N3 raw are checked for every BVM instance:

- `V(R_S) = 3 * I(R_S)` with the printed branch orientation;
- `V(R_S) = V(L_S3)` for the parallel branches;
- node-6 residual: `I(R_S)+I(L_S3)-I(B_JS1)-I(L_PSE)`;
- node-10 residual: `I(R_S)+I(L_S3)+I(B_JS2)-I(L_PSL)`;
- the R_S voltage/current signs agree on nonzero samples.

The measured residuals, per-instance values, and PASS/FAIL result are stored in
`provenance.json.direction_audit` and `analysis/SOURCE_MANIFEST.json`. The
replay sign convention is explicitly `positive = node6 -> node10`; no sign is
inferred from a column name alone.

## Exact authorized matrix and gate

The first physical stage is exactly two solves:

| run | mask | bridge source | purpose |
|---|---|---|---|
| `EXACT_0011` | `0011` | each instance's canonical N2 bridge current | fidelity gate |
| `EXACT_0111` | `0111` | each instance's canonical N3 bridge current | fidelity gate |

Delayed cases are not materialized before the exact gate. If and only if both
exact cases pass the pre-registered mechanical fidelity screen, the following
four and only four delayed solves may run:

| run | mask | delay | stored shift |
|---|---|---:|---:|
| `DELAY0P3_0011` | `0011` | 0.3 ps | 3 samples |
| `DELAY0P3_0111` | `0111` | 0.3 ps | 3 samples |
| `DELAY0P6_0011` | `0011` | 0.6 ps | 6 samples |
| `DELAY0P6_0111` | `0111` | 0.6 ps | 6 samples |

Maximum new physical solves: `2 + 4 = 6`. There are no 1.0/1.2-ps points,
other delays, transformer, sentinel, LS3 sweep, QB sweep, or timestep sweep.

The exact mechanical screen is deliberately not a 1e-9-V identity requirement.
It records the actual errors and uses these pre-registered structural screens:

- N2 ordered QB/JTL candidates equal canonical `2`; N3 equal canonical `4`;
- first BJ1/BJ2 `+0.5` timing drift no more than `0.2 ps`;
- every BVM JS1/JS2 `[110,121) ps` phase-navigation p2p drift no more than
  `0.25 turns`;
- key focus-waveform normalized RMS drift no more than `0.50`.

These are mechanical replay-fidelity screens, not universal physical tolerances.
The bridge voltage comparison is always reported separately: canonical direct
`V(R_S)` versus replay `V(6)-V(10)`. A current match does not make current the
only sufficient state variable.

## Exact-grid delayed waveform rule

The canonical raw's actual stored timestamps are retained. For each instance:

- `t < 110 ps`: canonical bridge current at the same stored sample;
- `110 ps <= t < 110 ps + Δ`: hold the canonical 110-ps sample;
- `t >= 110 ps + Δ`: use the canonical sample at index `i - shift`.

`Δ=0.3 ps` is exactly three stored samples and `Δ=0.6 ps` exactly six. No
interpolation, smoothing, resampling, amplitude scaling, sign correction, or
time-axis modification is permitted. The generated source CSV records the
source raw hash, source PWL hash, shift, start index, pre-110 equality, hold
check, and post-shift check.

## Probes, windows, and semantics

- `.tran 0.1p 200p`; expected stored grid 1999 samples, 0 to 199.9 ps.
- Windows are half-open actual-grid windows: full `[0,200) ps`, control
  `[70,110) ps`, focus `[110,121) ps`, and recovery `[121,130) ps`.
- Full raw probes retain BVM storage, R-loop, output, quiet branches and
  per-instance bridge replacement observables; COMMON_SL; P/V/I JSL1..8;
  QB input/LIN/BJS/L1/BJ1/RJ1/L2/IB/BJ2/RJ2/L3/QBOUT; every JTL1..6 B01/B02
  and stage output; and terminal voltage/current.
- Replay bridge current: `I(I_BRIDGE_REPLAY|XBVMn)`.
- Replay bridge voltage equivalent: `V(6|XBVMn)-V(10|XBVMn)`.
- Canonical bridge voltage: direct `V(R_S|XBVMn)=V(L_S3|XBVMn)`.
- `P(...)` is raw radians. Phase turns are only independently unwrapped
  `rad/(2*pi)` navigation values and never SFQ counts.
- JS1/JS2 phase-area checks use the same JJ, same endpoints/direction, the same
  `[110,121) ps` window, and trapezoidal integration on the actual time grid.
- Terminal traces are downstream corroboration only, never the sole oracle.

Required comparisons include `I(B_JSL8)`, `V(COMMON_SL)`, `V(QBIN)`,
`I(LIN|XBQ1)`, active JS1/JS2 P/V/I and phase-area, JM1/JM2, first BJ1/BJ2,
ordered QB/JTL chronology, I(L1)/I(L2), recovery source profiles, bridge
voltage, JSL chain, all JTL stages, and terminal corroboration.

## Interpretation ceiling and stop

This run records mechanical evidence only. `mechanical_analysis_performed` may
be true after raw QA; `bounded_experiment_interpretation_performed` and
`independent_scientific_review_performed` remain false. Outcome A/B/C labels
are not assigned without `SCIENTIFIC_REVIEW_AUTHORIZED`.

The final state is `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`. No
automatic transformer, sentinel, LC-network, delay, or parameter follow-up is
allowed. The ZIP is Drive-only; its Drive identity is outside the ZIP in
`delivery_manifest.json`.
