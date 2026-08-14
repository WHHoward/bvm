# Run analysis: `bvm-s0-d0-20260814-02`

## Research question

Using the exact recorded `build/josim-cli` executable, do the same three fixed
write-only initialization procedures meet the predeclared D0
operational-signature guards in the fixed 12-ohm BVM fixture?

## Predeclared hypotheses and outcomes

- Primary hypothesis: the two write-only initialization procedures produce
  two distinct, stable operational phase signatures on the direct JJ probes;
  the no-init control stays at the startup reference.
- Alternative explanations:
  1. Both initialized cases settle to the same signature (no separation).
  2. Signatures differ but drift inside a state window (p2p > 0.02 rad).
  3. Initialization never settles before simulation end.
- PASS observation: all three D0 guards hold in both state windows.
- FAIL observation: any guard fails or direct P/V output is unavailable;
  conclusion INCONCLUSIVE; D0 does not advance S0.
- INCONCLUSIVE conditions: artifacts valid but guards unmet; or only
  operational distinctness established without logical read0/read1 identity.
- INVALID conditions: missing column, NaN/Inf, non-monotonic time, truncated
  window, nonzero solver exit, pre-existing run root, binary provenance
  mismatch, unregistered change.

## Inputs and provenance

- Manifest: `manifest.yaml`
- Netlist/include snapshot: `inputs/` (copied `jjmit.cir`, `bvm_cell.cir`
  closure; three instrumented netlists identical to the D0 design document
  PWL cases)
- JoSIM binary/version/SHA-256: **`/home/howard/JoSIM/build/josim-cli`**
  v2.7.2837d13 compiled on May 30 2026 at 20:37:57
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
  (verified before any run input was written; PATH name and
  `/usr/local/bin/josim-cli` prohibited per AC1)
- Metric specification/version: `METRIC_SPEC_V2.md` v2.0.0 (frozen)
  `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`
- Input, bias, load, timestep and windows: `XBVM1 WL1 BL1 SE1 SL1 BVM`,
  `R_LD SL1 0 12` (only load), `0.1 ps` step, `[0, 80) ps`; windows
  `pre_init [4,9)`, `init_activity [9,31)`, `state_early [35,45)`,
  `state_late [65,75)` ps (all half-open, actual CSV samples)
- Closure hashes: `closure-hashes.txt`; copies match working tree hashes
  (bvm_cell `ea734654…`, jjmit `19862d1f…`)
- D0-001/A01 preserved as INVALID lineage; no numerical comparison is made
  against it (retry-rationale.md)

## Artifact QA

- Exit/log status: all three `build/josim-cli` runs exit 0, empty stderr,
  stdout preserved; no solver warnings observed.
- CSV/time/column checks: 798 samples per run; time strictly increasing to
  `7.98e-11 s`; no NaN/Inf; all 7 required columns present.
- Raw hashes: `closure-hashes.txt` (3 CSVs, 3 stdout, 3 stderr).
- Artifact verdict: `VALID`

## Observed

All numbers below are raw radians unless noted; trapezoidal integration uses
the CSV actual time axis on the registered half-open windows; JM1 positive
orientation `N1 -> n_jm1o`, JM2 `n_jm2i -> N2` (design document).

### init_activity `[9,31) ps` phase–area (AC4)

| case | JJ | phase_delta_rad | phase_delta_turns | area_turns | residual_turns |
|---|---|---|---|---|---|
| init_positive | JM1 | +5.910265 | +0.940648 | +0.940710 | −0.000062 |
| init_positive | JM2 | +0.270974 | +0.043127 | +0.042948 | +0.000179 |
| init_negative | JM1 | −5.910265 | −0.940648 | −0.940710 | +0.000062 |
| init_negative | JM2 | −0.270974 | −0.043127 | −0.042948 | −0.000179 |
| no_init_control | JM1 | 0.0 | 0.0 | 0.0 | 0.0 |
| no_init_control | JM2 | 0.0 | 0.0 | 0.0 | 0.0 |

Residuals are reported descriptively (METRIC_SPEC_V2 §7.2); **no tolerance is
declared** and no event/fluxoid/downstream conclusion is made.

### Source port (12-ohm load) — descriptive (AC4)

- `V(SL1)` and `I(L_SL|XBVM1)` are numerically zero for `no_init_control`.
- Both init cases produce bounded nonzero transient activity on `V(SL1)` /
  `I(L_SL|XBVM1)`; reported descriptively in `analysis.json`, no tolerance.

### State-window signatures (AC4) — raw-radian means / p2p

| window | case | JM1 mean | JM1 p2p | JM2 mean | JM2 p2p |
|---|---|---|---|---|---|
| state_early [35,45) | init_positive | +5.911000 | 0.005007 | +0.319093 | **0.070827** |
| state_early [35,45) | init_negative | −5.911000 | 0.005007 | −0.319093 | **0.070827** |
| state_early [35,45) | no_init_control | 0.0 | 0.0 | 0.0 | 0.0 |
| state_late [65,75) | init_positive | +5.911048 | 0.000875 | +0.316922 | 0.013602 |
| state_late [65,75) | init_negative | −5.911048 | 0.000875 | −0.316922 | 0.013602 |
| state_late [65,75) | no_init_control | 0.0 | 0.0 | 0.0 | 0.0 |

### D0 observability guards (AC4)

1. >= 2 actual samples, no NaN/Inf: **PASS** (100 samples per window per case).
2. per-component p2p <= 0.02 rad in both state windows:
   **FAIL** — JM2 state_early p2p 0.0708 rad in both init cases (0.02-rad
   guard exceeded); JM1 passes both windows; JM2 passes state_late.
3. L-inf separation >= 0.10 rad between init means in both windows:
   **PASS** — JM1: 11.82 rad both windows (~1.88 turns); JM2: 0.638 rad
   state_early, 0.634 rad state_late.

## Evidence audit

- Local phase/area: direct-JJ P and V probed on both junctions in the same
  run and same window; phase–area residuals ~1e-4 turns (descriptive only).
- Loaded downstream response: none — 12-ohm passive load only, per design.
- read0/read1/repeat/state preservation: **not applicable** — D0 performs no
  read stimulus and makes no state-preservation claim.
- Timestep convergence: **not applicable to D0** — 0.1 ps nominal ladder only;
  the design preregisters that S0 must separately run 0.1/0.05/0.025 ps and
  that D0 transfers no tolerance to it.
- Highest evidence level: direct-JJ phase + same-window voltage area on one
  timestep; operational-signature discrimination only.

## Inferred

- JM1 (S-loop main branch) carries the dominant initialization signature:
  the two procedures move it to approximately equal-magnitude opposite
  phase offsets (±5.91 rad ≈ ±0.94 turns), stable to <= 0.005 rad in the
  early window and <= 0.0009 rad late. This is consistent with the S-loop
  storing opposing circulating currents, but D0 does **not** label either
  signature logical 0/1, a fluxoid count, or a readable state.
- JM2 (stabilizer branch) shows smaller separation (0.638 rad) and a
  state_early residual oscillation (p2p 0.071 rad) that decays to 0.014 rad
  by state_late; the oscillation amplitude is identical in both init cases,
  consistent with a symmetric settling transient rather than a numerical
  artifact (identical p2p under opposite initializations).

## Unknown

- Whether either initialized JM1/JM2 signature is a published logical state
  or a non-destructive read result: UNKNOWN — requires separate S0
  read-stimulus characterization with matched zero controls and the full
  timestep ladder.
- Whether the JM2 state_early oscillation is an intrinsic settling transient
  of the stabilizer branch at this closure: not resolved by D0 (single
  timestep, no ladder).
- Source-port transient descriptors were recorded but no read/write
  transfer-level interpretation is made.

## Verdict

`INCONCLUSIVE`

Reason: artifacts are valid (QA passed, AC1 binary provenance verified,
direct-JJ probes present, closure immutable) and the init procedures produce
a large, stable JM1 separation (11.82 rad, guard 3 passed in both windows),
but guard 2 fails: JM2 p2p in state_early is 0.0708 rad > 0.02 rad in both
init cases. Per the design document, an unmet guard keeps D0 a valid
exploratory artifact with an INCONCLUSIVE conclusion; D0 does not advance S0.

## Next discriminating experiment

A separately issued S0 contract that (a) keeps the same closure and the same
two initialization procedures, (b) adds one read stimulus with matched
read0/read1 zero controls, (c) preregisters the full 0.1/0.05/0.025 ps
ladder, readout windows, task-local bands, and stop rule before execution,
and (d) decides whether the state_late platform (p2p <= 0.014 rad) can be
the operational readout witness, with JM2 state_early oscillation treated
as a settling transient pending the ladder comparison.
