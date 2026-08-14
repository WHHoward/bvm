# Run analysis: `bvm-s0-canonical-20260814-01`

## Research question

Under the frozen BVM-S0 closure and one preregistered read pulse, what
`V(SL1)` and `I(L_SL|XBVM1)` waveforms occur for `init_positive` and
`init_negative` relative to their matched zero-read controls, and what
direct-JJ platform quantities are observed before and after the pulse?

## Predeclared hypotheses and outcomes

- Primary hypothesis: the read pulse produces a reproducible source-port
  waveform from each initialized procedure, distinct from its matched
  zero-read control, with direct-JJ pre/post platform quantities stable at
  every registered timestep.
- Alternative explanations:
  1. Control and read waveforms are indistinguishable (no read response).
  2. Pre/post platforms drift through the 170 ps window.
  3. Adjacent-timestep comparisons exceed the registered bands
     (INCONCLUSIVE).
- PASS observation: QA, pre-window admissibility, and all registered
  adjacent-refinement comparisons hold -> `CONVERGED` + `VALID`.
- FAIL observation: any QA/provenance failure -> `INVALID`; any
  admissibility/convergence shortfall -> `INCONCLUSIVE`.
- INCONCLUSIVE conditions: valid raw data but initial-state admissibility or
  a registered convergence comparison not met at the fixed ladder maximum, or
  valid source-side observation without physical success/Gate
  interpretation.
- INVALID conditions: wrong binary, missing probes, raw overwrite,
  solver/CSV failure, changed frozen stimulus/closure/window/band,
  pre-existing run root, out-of-scope write, or unregistered
  parameter/timestep.

## Inputs and provenance

- Manifest: `manifest.yaml`
- Netlist/include snapshot: `inputs/` (copied `jjmit.cir`, `bvm_cell.cir`
  closure; 12 instrumented netlists = 4 cases x 3 timesteps, `.tran` at
  0.1/0.05/0.025 ps through 170 ps)
- JoSIM binary/version/SHA-256: **`/home/howard/JoSIM/build/josim-cli`**
  v2.7.2837d13 compiled on May 30 2026 at 20:37:57
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
  (verified before any write/run; PATH name and `/usr/local/bin` prohibited
  per AC1)
- Metric specification/version: `METRIC_SPEC_V2.md` v2.0.0 (frozen)
  `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`
- Closure/load/stimulus: `XBVM1 WL1 BL1 SE1 SL1 BVM`, only `R_LD SL1 0 12`;
  init WL/BL ramp to ±100 uA over 10–11 ps, hold to 20 ps, return by 21 ps;
  read WL+SE 95p 0 → 96p +100 uA → 105p +100 uA → 106p 0 (project-derived
  from `test_bvm_final.cir` R1, delayed past the D0 75-ps bound); matched
  controls have only the read amplitudes zeroed
- Windows (half-open, actual CSV times): pre `[80,90)`, activity `[94,108)`,
  source `[94,130)`, post `[140,150)` ps
- Closure hashes: `closure-hashes.txt` (50 entries)
- D0 lineage preserved frozen; readiness bound 75 ps used as design input
  only

## Artifact QA

- Exit/log status: all 12 `build/josim-cli` runs exit 0, empty stderr;
  stdout preserved; no solver warnings observed.
- CSV/time/column checks: 1699 (0.1 ps), 3399 (0.05 ps), 6799 (0.025 ps)
  samples per case; time strictly increasing to the 170 ps endpoint; no
  NaN/Inf; all 9 required columns present (time, P/V JM1, P/V JM2, V(SL1),
  I(L_SL|XBVM1), I(I_WL1), I(I_SE1)).
- Raw hashes: `closure-hashes.txt` (12 CSVs, 12 stdout, 12 stderr, 12
  netlists, 2 closure copies).
- Artifact verdict: `VALID` (QA passed)

## Observed

All phase/area values are raw radians/turns unless noted; actual-time
trapezoidal integration; JM1 `N1 -> n_jm1o`, JM2 `n_jm2i -> N2`,
`voltage_to_phase_sign=+1`, `reporting_direction=+1`.

### Pre-window operational admissibility `[80,90) ps` (all timesteps)

| step | admissible | JM1 p2p (read) | JM2 p2p (read) | pos/neg L-inf |
|---|---:|---|---:|---:|
| 0.1 ps | True | 0.00039 | 0.00655 | 11.8221 |
| 0.05 ps | True | 0.00037 | 0.00581 | 11.8221 |
| 0.025 ps | True | 0.00036 | 0.00555 | 11.8221 |

All four cases pass the p2p <= 0.020 rad and L-inf >= 0.100 rad checks at
every timestep; controls behave identically to their init partners
(platforms are initialization-conditioned, read pulse arrives later).

### Activity `[94,108) ps` direct-JJ phase–area (AC4)

| case | step | JJ | phase_delta_rad | phase_delta_turns | area_turns | residual_turns |
|---|---|---|---|---|---|---|
| init_positive_read | 0.1 ps | JM1 | +0.108836 | +0.017322 | +0.017312 | +0.000010 |
| init_positive_read | 0.1 ps | JM2 | +0.001638 | +0.000261 | +0.000260 | +0.000001 |
| init_negative_read | 0.1 ps | JM1 | −0.108826 | −0.017320 | −0.017312 | −0.000008 |
| init_negative_read | 0.1 ps | JM2 | +0.001638 | +0.000261 | +0.000260 | +0.000001 |

Residuals are descriptive; **no residual tolerance is declared**. Full
per-case/per-step table in `analysis.json`. `V(SL1)`/`I(L_SL|XBVM1)` are
raw fixture probes; applied inputs `I(I_WL1)`/`I(I_SE1)` confirm the
registered read stimulus.

### Source-port waveform observables `[94,130) ps` (AC4)

Read cases (0.1 ps / 0.05 ps / 0.025 ps agree):

| case | key | abs peak | latency from 96 ps | FWHM |
|---|---|---|---:|---:|
| init_positive_read | V(SL1) | 0.890 / 0.901 / 0.901 mV | 5.0 ps (all) | 1.4 ps (all) |
| init_positive_read | I(L_SL) | 74.2 / 75.1 / 75.1 uA | 5.0 ps (all) | 1.4 ps (all) |
| init_negative_read | V(SL1) | 0.890 / 0.901 / 0.901 mV | 5.0 ps (all) | 1.4 ps (all) |
| init_negative_read | I(L_SL) | 74.2 / 75.1 / 75.1 uA | 5.0 ps (all) | 1.4 ps (all) |

Matched controls (no read stimulus): `V(SL1)`/`I(L_SL)` peaks are
noise-level residuals (~18 nV / ~1.5 uA at 0.1 ps), latency values are
numerical-peak artifacts, not read responses. FWHM for control peaks is
reported but carries no physical meaning (no half-height read signal).

### Pre/post storage signature (JM1/JM2 P means, rad)

| case | step | pre JM1 | post JM1 | pre JM2 | post JM2 |
|---|---|---|---:|---|---:|
| init_positive_read | 0.1 ps | +5.911050 | +5.911005 | +0.316535 | +0.316922 |
| init_positive_read | 0.025 ps | +5.911045 | +5.911029 | +0.316507 | +0.316904 |
| init_negative_read | 0.1 ps | −5.911050 | −5.911016 | +0.316535 | +0.316930 |
| init_negative_read | 0.025 ps | −5.911045 | −5.911029 | +0.316507 | +0.316912 |

Post-minus-pre platform deltas are ~5e-5 rad (JM1) / ~4e-4 rad (JM2)
descriptive only. **No storage-preservation tolerance is frozen** and no
non-destructive-read claim is made.

### Convergence (AC5, adjacent pairs 0.1/0.05 and 0.05/0.025)

| pair | result | failing comparison |
|---|---|---|
| 0.1 ps → 0.05 ps | **FAIL** | control-case V_SL1/I_LSL peak latency: 0.85 ps > 0.5 ps band (both controls; noise-level 18 nV peak) |
| 0.05 ps → 0.025 ps | PASS | none |

All other registered comparisons meet the bands at both pairs: JJ
pre/post platform means and corrected deltas (<= 0.020 rad), source
voltage/current peaks (<= max(5 uV / 0.5 uA, 5%)), read-case latency and
FWHM (<= 0.5 ps; both equal across steps).

Numerical status: **INCONCLUSIVE** (registered band exceeded at the fixed
ladder; no further timestep or parameter run is allowed).

## Evidence audit

- Local phase/area: direct-JJ P and V on both junctions, same run, same
  window, registered orientations, vts=+1/rd=+1; residuals descriptive.
- Loaded downstream response: none — 12-ohm passive load only, per design.
- Source-port waveform: V(SL1)/I(L_SL) read peaks reproducible across all
  three timesteps; controls show noise-level residual peaks only.
- read0/read1/repeat/state preservation: **not applicable** — this task
  reports source-side calibration facts; no logical read identity, storage
  preservation under read, or receiver result is claimed.
- Timestep convergence: partially met — fine pair (0.05/0.025) passes; coarse
  pair (0.1/0.05) fails on control-case noise-peak latency.
- Highest evidence level: direct-JJ phase + same-window voltage area +
  source-port waveform on a 3-timestep ladder; calibration facts only.

## Inferred

- The registered read pulse produces a reproducible source-port transient
  (~0.9 mV / ~75 uA peak, 5.0 ps latency, 1.4 ps FWHM) from both initialized
  procedures, identical in magnitude across both signs — consistent with the
  read coupling being dominated by the applied WL+SE stimulus rather than
  the stored initialization direction at this fixture. This is an
  observation, not a logical read0/read1 assertion.
- Pre-window admissibility holds at all timesteps (JM1/JM2 stable,
  pos/neg separation 11.82 rad), confirming the D0 75-ps readiness bound
  remains operationally adequate as a design input on the finer ladder.
- The control-case latency band failure arises from sub-nanovolt noise-level
  residual peaks whose extremum index shifts between coarse/fine sampling;
  it is a measurement artifact of the fixed rule applied to a zero-signal
  case, not a read-waveform convergence failure.

## Unknown

- Whether the source-port waveform constitutes a readable state or storage
  preservation under read: UNKNOWN — requires a separately authorized
  receiver/storage experiment; explicitly out of this calibration's scope.
- Whether a control-signal latency band should exclude noise-level peaks:
  UNKNOWN/not adjustable — the bands are frozen; no post-hoc criterion
  change is permitted.
- Exact physical settling/convergence beyond the fixed ladder: UNKNOWN — the
  ladder is nonextendable.

## Verdict

`INCONCLUSIVE`

Reason: artifact QA and pre-window admissibility pass at all three
timesteps, and the fine refinement pair (0.05/0.025 ps) fully converges;
however the coarse pair (0.1/0.05 ps) exceeds the registered 0.5 ps peak
latency band on the matched control cases (0.85 ps), where the "peak" is a
noise-level residual (18 nV). Per the frozen procedure, an exceeded
registered band at the fixed ladder maximum means INCONCLUSIVE; the ladder is
not extended and no band is relaxed. Source-side calibration facts are
reported; no receiver, Gate, logical, or route conclusion is made.

## Next discriminating experiment

A separately issued, preregistered receiver/interface task (BQ or DCSFQ_BVM)
that (a) attaches one fixed receiver with matched zero controls, (b) chooses
its own task-local bands (including an explicit control-signal peak-latency
rule that distinguishes noise-level from read-level peaks, or a minimum
abs-peak threshold below which latency/FWHM comparisons are
NOT_APPLICABLE), (c) preregisters its own 0.1/0.05/0.025 ps ladder and
windows, and (d) reports only interface-level facts without logical or Gate
claims. This task's INCONCLUSIVE status does not authorize any receiver or
candidate work.
