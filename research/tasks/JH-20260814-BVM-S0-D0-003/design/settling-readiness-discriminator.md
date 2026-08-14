# D0 settling/readiness discriminator — preregistration

## One question

Under the fixed BVM/model/12-ohm fixture and the fixed write-only
initialization procedure, when do the two directly observed junction signatures
become sufficiently stable and mutually distinguishable to serve as a *future*
S0 initial-state procedure?

This is an operational readiness question only.  `init_positive` and
`init_negative` are procedure labels, not logical `read1`/`read0` labels,
published states, fluxoids, or SFQ counts.

## Fixed closure and cases

All cases use copied snapshots of `circuits/bvm/bvm_cell.cir` and
`circuits/models/jjmit.cir`, one `XBVM1 WL1 BL1 SE1 SL1 BVM`, and only
`R_LD SL1 0 12`.  They use the recorded repository executable
`/home/howard/JoSIM/build/josim-cli` and run at `0.1 ps` through `130 ps`.

The only cases are:

| Case | WL and BL PWL | SE |
|---|---|---|
| `init_positive` | 0 to `+100 uA` over 10–11 ps; hold to 20 ps; return to 0 by 21 ps | identically 0 |
| `init_negative` | 0 to `-100 uA` over 10–11 ps; hold to 20 ps; return to 0 by 21 ps | identically 0 |
| `no_init_control` | identically 0 | identically 0 |

There is no read stimulus, SE pulse, receiver, JTL, BQ, DCSFQ_BVM, extra
source load, parameter change, or parameter sweep.

## Direct observables and orientations

The run records `P(B_JM1|XBVM1)` and `V(B_JM1|XBVM1)` for JM1, whose declared
positive endpoint order is `N1 -> n_jm1o`; and `P(B_JM2|XBVM1)` and
`V(B_JM2|XBVM1)` for JM2, whose declared positive endpoint order is
`n_jm2i -> N2`.  It also preserves `V(SL1)` and `I(L_SL|XBVM1)` (`N8 -> SL1`)
as raw fixture probes only, not as source-characterization results.

For both junctions the report keeps raw radians, derives turns by division by
`2*pi`, and uses the CSV actual time axis to integrate the direct branch
voltage over the fixed initialization-activity window `[9,31) ps`.  The
reporting direction and voltage-to-phase sign are both `+1`.  No residual
tolerance is asserted.

## Fixed settling windows

All intervals are half-open and selected from the actual CSV time column:

| ID | Interval | Purpose |
|---|---:|---|
| `settle_35` | `[35,45) ps` | early decay diagnostic |
| `settle_55` | `[55,65) ps` | first readiness candidate |
| `settle_75` | `[75,85) ps` | second readiness candidate |
| `settle_95` | `[95,105) ps` | third readiness candidate |
| `settle_115` | `[115,125) ps` | final persistence witness |

No window may be moved, shortened, or added after raw data are inspected.

## Readiness criterion and output rule

A window is *stable* only when every case and both JM1/JM2 columns have at
least two finite samples and peak-to-peak spread `<= 0.020 rad`.  A window is
*distinguishable* only when the mean two-component vector `(JM1, JM2)` for
each of the three case pairs (`positive/negative`, `positive/control`,
`negative/control`) has L-infinity distance `>= 0.100 rad`.

The analysis reports the first preregistered adjacent pair among
`(settle_35, settle_55)`, `(settle_55, settle_75)`, `(settle_75, settle_95)`,
and `(settle_95, settle_115)` for which both windows are stable and
distinguishable.  It also requires every later registered window to remain
stable and distinguishable.  If this rule succeeds, the earliest start of that
pair is an **operational readiness bound within the tested grid**, not a claim
about the exact physical settling instant.  A later S0 contract must choose a
single fixed wait time at or after that bound before it executes any read
stimulus.

If no pair qualifies, the valid outcome is `INCONCLUSIVE`; S0 remains blocked.
Missing provenance/columns, nonmonotonic time, nonfinite values, solver error,
truncated windows, or raw overwrite makes the artifact `INVALID`.

## Stop rule and claim boundary

Exactly three cases and one nominal timestep are permitted.  If any additional
case, load, bias, device parameter, read/SE input, timestep, or post-hoc
window/criterion is needed, execution stops and reports the blocker.  This
task may report only `VALID`, `INCONCLUSIVE`, or `INVALID` evidence quality.
It cannot establish logical 0/1, fluxoid number, an SFQ event, a source output
characterization, receiver response, interface Gate, or route decision.
