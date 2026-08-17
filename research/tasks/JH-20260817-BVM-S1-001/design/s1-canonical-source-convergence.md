# BVM-S1 — canonical source numerical-convergence preregistration

## Question and claim boundary

Under one fixed BVM/model closure, one 12-ohm passive load, the two accepted
operational initialization procedures, one fixed single read PWL, and matched
zero-read controls, do the named source-port waveform observables satisfy the
registered **S1 numerical timestep-convergence procedure**?

`init_positive` and `init_negative` are operational procedure labels only.
They are not logical 1/0, published states, fluxoids, SFQs, or a
non-destructive-read assertion.  This is a new CALIBRATION + CRITICAL + FROZEN
experiment; it neither changes nor reinterprets BVM-S0.

Even if converged, the strongest permitted statement is: in this copied BVM
closure, fixed initialization/read protocol, and fixed 12-ohm simulated
fixture, the named source-port waveforms are numerically converged under the
registered S1 timestep procedure.  It is not a universal source specification,
receiver result, candidate/Gate verdict, or hardware/published-reproduction
claim.

## Fixed closure, cases, and windows

Every run copies the active `circuits/bvm/bvm_cell.cir` and
`circuits/models/jjmit.cir` closure, instantiates exactly one
`XBVM1 WL1 BL1 SE1 SL1 BVM`, and attaches only `R_LD SL1 0 12`.

WL and BL form either the positive or negative initialization: 0 to `+/-100
uA` over 10--11 ps, held to 20 ps, returned to zero by 21 ps.  The fixed read
is the project-derived, single PWL on WL and SE: 0 at 95 ps, `+100 uA` at
96 ps, held to 105 ps, 0 at 106 ps.  For a matched control, **the identical
PWL knot times remain present** but both read-segment amplitudes are zero;
all other netlist/model/load/bias/window/timestep fields are identical.

The complete four-case set is `init_positive_read`, `init_positive_control`,
`init_negative_read`, and `init_negative_control`.  All runs stop at 170 ps.
Intervals are half-open and use actual CSV time: pre `[80,90) ps`, activity
`[94,108) ps`, source `[94,130) ps`, post `[140,150) ps`.

## Registered probes and semantics

| Observable | CSV column | declared direction | windows |
|---|---|---|---|
| source voltage | `V(SL1)` | `SL1 -> 0` | source |
| source current | `I(L_SL|XBVM1)` | `N8 -> SL1` | source |
| input witness | `I(I_WL1)`, `I(I_SE1)` | source definitions | source |
| JM1 | `P(B_JM1|XBVM1)`, `V(B_JM1|XBVM1)` | `N1 -> n_jm1o`; `vts=+1`, `rd=+1` | pre/activity/post |
| JM2 | `P(B_JM2|XBVM1)`, `V(B_JM2|XBVM1)` | `n_jm2i -> N2`; `vts=+1`, `rd=+1` | pre/activity/post |

For every named pre/post platform, report its mean in raw rad and derived
turns (`rad/(2*pi)`).  For every activity-window same-JJ identity, report the
endpoint `Delta-phi` in raw rad and derived turns, actual-time voltage area in
turns, and signed residual.  Platform differences and activity-window endpoint
deltas are distinct measurements.  Turns are only a unit conversion and do
not mean an SFQ, event, or loop fluxoid.

## Initial-state admissibility

At every timestep and in every one of the four cases, pre `[80,90) ps` is
admissible only when both direct JM1 and JM2 columns have at least two finite
samples and peak-to-peak spread `<= 0.020 rad`.  At every timestep, the
positive/negative initialized two-component JM1/JM2 pre-window mean vectors
must have L-infinity separation `>= 0.100 rad` (the corresponding read/control
pairs must agree before the later read pulse within the separately reported
platform procedure).

These are timestep-comparability and operational-readiness checks inherited
from S0, not a memory/state-preservation Gate or logical-state criterion.

## Fixed ladder and comparison construction

The entire, nonextendable ladder is `0.05 ps -> 0.025 ps -> 0.0125 ps` (twelve
runs total).  The design input for this ladder is the sealed S0 source-waveform
FWHM: baseline-subtracted `V(SL1)` and `I(L_SL|XBVM1)` in
`test/final/bvm/runs/bvm-s0-canonical-20260814-01/analysis.json`,
`init_positive_read/0.025ps`, report `1.400000000000003e-12 s`; its raw and
analysis lineage is sealed by S0-002/003 and accepted in S0-004 C02.  It is a
source-observable FWHM, not a read-PWL width and not an S1 acceptance result.

For each adjacent pair, parse CSV time tokens as exact decimal values.  Every
coarse timestamp inside source `[94,130) ps` is the reference timestamp and
must occur exactly once in the fine CSV.  The match tolerance is exactly zero
seconds after decimal parsing.  No interpolation, resampling, cross-correlation
shift, peak alignment, or other time alignment is permitted.  Read/control
pairs at one timestep likewise require exact one-to-one decimal timestamps for
control-corrected waveform reporting.  Malformed/nonfinite/nonmonotonic/
duplicate time is INVALID; otherwise an unavailable required exact comparison
is numerically INCONCLUSIVE.

## Control applicability and convergence observables

For each source V or I waveform, subtract that run's own pre-window mean and
define `Aread=max(abs(read))`, `Actrl=max(abs(control))`, and
`rctrl=Actrl/max(Aread, Afloor)`, with `Afloor=5 uV` for voltage and `0.5 uA`
for current.

The following deliberate hierarchy applies:

| `rctrl` interval | residual requirement | latency / FWHM |
|---|---|---|
| `<= 0.01` | residual PASS region | NOT_APPLICABLE |
| `0.01 < rctrl < 0.05` | residual criterion not met | NOT_APPLICABLE |
| `>= 0.05` | residual criterion not met | applicable and compared |

Thus a sub-5-percent paired-read residual is not assigned a spurious pulse
time/width.  A control over 5 percent is recorded as a timing-bearing waveform,
but already cannot satisfy the small-residual requirement.  Intervals above
`0.01*Aread` are descriptive activity intervals only, never events and never
an acceptance quantity.

For read V and I, report signed and absolute baseline-subtracted peaks, latency
from 96 ps, FWHM when finite half-height crossings exist, pointwise waveform
difference, and RMS waveform difference.  For controls, report maximum,
RMS, time-normalized L1 residual, and corresponding adjacent-pair differences.
Direct-JJ pre/post platform means and control-corrected platform deltas are
also compared.  Phase-area residual has no acceptance tolerance and is
descriptive only.

## Task-local band rationale

| Item | Value | classification |
|---|---:|---|
| V / I floors | `5 uV` / `0.5 uA` | inherited S0 numerical floors; freshly registered, not global |
| JJ pre/post platform pair difference | `0.020 rad` | inherited S0 procedure-local comparability scale |
| read V/I peak and pointwise difference | `<= max(Afloor, 1%*Aref)` | new S1 numerical amplitude/shape criterion |
| read RMS difference | `<= max(0.2%*Aref, 0.2*Afloor)` | new S1 overall-shape criterion |
| read latency and applicable FWHM difference | `<= 0.25 ps` | new S1 temporal resolution criterion; not jitter tolerance |
| control max residual and pair max difference | `<= 1%` of paired-read scale | new S1 control-separation criterion |
| control RMS/L1 and pair RMS difference | `<= 0.2%` of paired-read scale | new S1 residual-energy criterion |
| latency/FWHM applicability | `rctrl >= 5%` | new measurement-definition rule, not PASS criterion |
| physical/interface tolerance | none | UNFROZEN; outside S1 |

`Aref` is the greater absolute read peak in an adjacent pair, and all values are
computed on the exact common timestamps.  These bands are task-local numerical
criteria selected before S1 data exist; they do not derive a BVM physical,
receiver, or interface tolerance from S0 residuals.

## Outcomes and predictions

Artifact `VALID` requires closure/binary/hash/QA/probe/window integrity.
Named timestep observations can be reported from a VALID artifact.  Numerical
`CONVERGED` requires every applicable registered comparison in both adjacent
pairs to pass; `INCONCLUSIVE` is a valid artifact with a failed/missing/
ambiguous required comparison at the fixed maximum depth; `INVALID` is a data
or provenance failure.  No physical PASS/FAIL is registered.

Falsifiable, non-acceptance predictions are: positive source peak about
`+0.904..+0.905 mV` and `+75.3..+75.4 uA`; negative source peak about
`-0.317 mV` and `-26.4 uA`; small 0.025-to-0.0125-ps read-waveform change; and
controls far below paired read scale.  Contradiction is reported, never
repaired by changing the procedure.

If preflight finds a concrete reproducible inconsistency in active closure,
stimulus, probe, or fixture, execution stops and reports it.
