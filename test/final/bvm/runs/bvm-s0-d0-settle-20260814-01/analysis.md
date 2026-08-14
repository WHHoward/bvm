# Run analysis: `bvm-s0-d0-settle-20260814-01`

## Research question

For the three fixed write-only cases, which (if any) preregistered adjacent
settling-window pair first satisfies the fixed stability and
distinguishability rule and remains so through the final witness window?

## Predeclared hypotheses and outcomes

- Primary hypothesis: the initialized junction signatures settle monotonically;
  a preregistered adjacent settle-window pair eventually becomes stable and
  distinguishable and stays so through the final witness window.
- Alternative explanations:
  1. No pair qualifies (INCONCLUSIVE; S0 remains blocked).
  2. Stability is reached but distinguishability is lost (control drift).
- PASS observation: first adjacent pair in which both windows are stable
  (>=2 finite samples, p2p <= 0.020 rad, all cases and both JJ) and
  distinguishable (all three case-pair L-infinity >= 0.100 rad), with every
  later registered window also stable and distinguishable; the pair's earliest
  start is the operational readiness bound within the tested grid.
- FAIL observation: any guard fails or direct P/V output is unavailable;
  conclusion INCONCLUSIVE; S0 remains blocked.
- INCONCLUSIVE conditions: artifacts valid but no preregistered adjacent pair
  satisfies the rule, or only an operational readiness bound is established
  without logical read0/read1 identity.
- INVALID conditions: missing provenance/columns, nonmonotonic time,
  nonfinite values, solver error, truncated windows, pre-existing run root,
  binary mismatch, or raw overwrite.

## Inputs and provenance

- Manifest: `manifest.yaml`
- Netlist/include snapshot: `inputs/` (copied `jjmit.cir`, `bvm_cell.cir`
  closure; three instrumented netlists with the frozen PWL procedures and
  `.tran 0.1p 130p`)
- JoSIM binary/version/SHA-256: **`/home/howard/JoSIM/build/josim-cli`**
  v2.7.2837d13 compiled on May 30 2026 at 20:37:57
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
  (verified before any write/run; PATH name and `/usr/local/bin` prohibited
  per AC1)
- Metric specification/version: `METRIC_SPEC_V2.md` v2.0.0 (frozen)
  `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`
- Input, bias, load, timestep and windows: `XBVM1 WL1 BL1 SE1 SL1 BVM`,
  `R_LD SL1 0 12` (only load), `0.1 ps` step, `[0, 130) ps`; activity window
  `[9,31) ps`; settle windows `[35,45)`, `[55,65)`, `[75,85)`, `[95,105)`,
  `[115,125)` ps (all half-open, actual CSV samples)
- Closure hashes: `closure-hashes.txt`; copies match working tree hashes
  (bvm_cell `ea734654…`, jjmit `19862d1f…`)
- D0-001/D0-002 preserved as frozen lineage; no numerical merge or
  reinterpretation

## Artifact QA

- Exit/log status: all three `build/josim-cli` runs exit 0, empty stderr,
  stdout preserved; no solver warnings observed.
- CSV/time/column checks: 1298 samples per run; time strictly increasing to
  `1.298e-10 s`; no NaN/Inf; all 7 required columns present.
- Raw hashes: `closure-hashes.txt` (3 CSVs, 3 stdout, 3 stderr).
- Artifact verdict: `VALID`

## Observed

All numbers are raw radians unless noted; trapezoidal integration uses the
CSV actual time axis; JM1 positive orientation `N1 -> n_jm1o`, JM2
`n_jm2i -> N2` (design document); reporting direction and voltage-to-phase
sign both `+1`.

### Phase–area on fixed `[9,31) ps` (AC5)

| case | JJ | phase_delta_rad | phase_delta_turns | area_turns | residual_turns |
|---|---|---|---|---|---|
| init_positive | JM1 | +5.910265 | +0.940648 | +0.940710 | −0.000062 |
| init_positive | JM2 | +0.270974 | +0.043127 | +0.042948 | +0.000179 |
| init_negative | JM1 | −5.910265 | −0.940648 | −0.940710 | +0.000062 |
| init_negative | JM2 | −0.270974 | −0.043127 | −0.042948 | −0.000179 |
| no_init_control | JM1 | 0.0 | 0.0 | 0.0 | 0.0 |
| no_init_control | JM2 | 0.0 | 0.0 | 0.0 | 0.0 |

`voltage_to_phase_sign=+1`, `reporting_direction=+1`. Residuals are reported
descriptively; **no residual tolerance is declared**. `V(SL1)`/`I(L_SL|XBVM1)`
are preserved as raw fixture probes only, not source characterization.

### Settle-window signature means / p2p (AC4)

| window | case | JM1 mean | JM1 p2p | JM2 mean | JM2 p2p |
|---|---|---|---|---|---|
| settle_35 [35,45) | init_positive | +5.911000 | 0.005007 | +0.319093 | **0.070827** |
| settle_35 [35,45) | init_negative | −5.911000 | 0.005007 | −0.319093 | **0.070827** |
| settle_35 [35,45) | no_init_control | 0.0 | 0.0 | 0.0 | 0.0 |
| settle_55 [55,65) | init_positive | +5.911084 | 0.001436 | +0.316166 | **0.024016** |
| settle_55 [55,65) | init_negative | −5.911084 | 0.001436 | −0.316166 | **0.024016** |
| settle_55 [55,65) | no_init_control | 0.0 | 0.0 | 0.0 | 0.0 |
| settle_75 [75,85) | init_positive | +5.911078 | 0.000496 | +0.317184 | 0.008365 |
| settle_75 [75,85) | init_negative | −5.911078 | 0.000496 | −0.317184 | 0.008365 |
| settle_75 [75,85) | no_init_control | 0.0 | 0.0 | 0.0 | 0.0 |
| settle_95 [95,105) | init_positive | +5.911074 | 0.000172 | +0.316834 | 0.002907 |
| settle_95 [95,105) | init_negative | −5.911074 | 0.000172 | −0.316834 | 0.002907 |
| settle_95 [95,105) | no_init_control | 0.0 | 0.0 | 0.0 | 0.0 |
| settle_115 [115,125) | init_positive | +5.911077 | 0.000059 | +0.316945 | 0.001010 |
| settle_115 [115,125) | init_negative | −5.911077 | 0.000059 | −0.316945 | 0.001010 |
| settle_115 [115,125) | no_init_control | 0.0 | 0.0 | 0.0 | 0.0 |

JM2 p2p decays monotonically across the settle grid:
0.070827 → 0.024016 → 0.008365 → 0.002907 → 0.001010 rad (both init cases
identical at every window).

### Stability (AC4 rule, p2p <= 0.020 rad, all cases and both JJ)

| window | stable |
|---|---|
| settle_35 | **False** (JM2 p2p 0.070827) |
| settle_55 | **False** (JM2 p2p 0.024016) |
| settle_75 | **True** |
| settle_95 | **True** |
| settle_115 | **True** |

### Distinguishability (AC4 rule, all three case pairs L-inf >= 0.100 rad)

All five windows are distinguishable. Representative L-inf distances
(init_positive/init_negative, `(JM1, JM2)` mean vectors):

| window | p/n L-inf (rad) |
|---|---:|
| settle_35 | 11.82 |
| settle_75 | 11.82 |
| settle_115 | 11.82 |

JM1 dominates (≈ ±5.911 rad); JM2 contributes ≈ 0.63 rad. The
control/positive and control/negative pairs are likewise above 0.10 rad
(control means are exactly 0.0). Full per-pair numbers in `analysis.json`.

### Pair + persistence rule (AC4)

- (settle_35, settle_55): **fails** — both unstable.
- (settle_55, settle_75): **fails** — settle_55 unstable.
- **(settle_75, settle_95): qualifies** — both stable and distinguishable,
  and settle_115 (the only later registered window) is also stable and
  distinguishable.
- Readiness bound: **75 ps** (earliest start of the first qualifying pair,
  within the tested grid).

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
  timestep; operational readiness within the tested grid only.

## Inferred

- JM2 (stabilizer branch) settles monotonically: its state_early oscillation
  (0.071 rad p2p at 35–45 ps) decays to 0.024 rad by 55–65 ps, below the
  0.02-rad guard by 75–85 ps, and to 0.001 rad by 115–125 ps. The identical
  p2p between opposite initializations at every window is consistent with a
  symmetric settling transient rather than a numerical artifact.
- JM1 (S-loop main branch) is stable (p2p <= 0.005 rad) from the earliest
  settle window onward and carries the dominant signature (≈ ±5.91 rad).
- Together, the two procedures are operationally distinguishable from each
  other and from the zero-input control from 35 ps onward; full all-component
  stability is reached no later than 75 ps and persists through 125 ps.

## Unknown

- Whether the readiness bound transfers to a different timestep grid:
  UNKNOWN — D0 ran only 0.1 ps; S0 must preregister 0.1/0.05/0.025 ps.
- Whether either initialized signature is a published logical state or a
  non-destructive read result: UNKNOWN — requires separately authorized S0
  with read stimulus, matched zero controls, and its own windows/bands.
- Exact physical settling instant: UNKNOWN — the bound is "within the tested
  grid" (75 ps start of the first qualifying pair), not the exact instant.

## Verdict

`VALID`

Reason: all QA passed; the registered pair+persistence rule is satisfied by
adjacent pair (settle_75, settle_95) with the final witness settle_115 also
stable and distinguishable. The operational readiness bound within the tested
grid is **75 ps**. This is an operational readiness statement only: it does
not label either signature logical 0/1, fluxoid, SFQ, read result, source
characterization, or an S0 PASS.

## Next discriminating experiment

A separately issued S0 contract that (a) keeps the same closure and the same
two initialization procedures, (b) chooses a fixed wait time at or after
75 ps (per design document), (c) adds one read stimulus with matched
read0/read1 zero controls, (d) preregisters the full 0.1/0.05/0.025 ps
ladder, readout windows, task-local bands, and stop rule before execution,
and (e) keeps all read0/read1 differences confined to the initialization.
