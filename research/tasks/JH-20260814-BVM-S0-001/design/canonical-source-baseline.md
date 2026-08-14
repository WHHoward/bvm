# BVM-S0 — canonical source baseline preregistration

## Question and scope

In one fixed BVM closure and one fixed 12-ohm passive load, what source-port
current/voltage waveform follows one fixed single read pulse from each of two
operationally distinguishable initialized procedures, relative to its matched
zero-read control; and what direct-JJ pre/post platform observables change?

This is `CALIBRATION + CRITICAL + FROZEN`.  It is not a receiver experiment,
an interface Gate, an SFQ/event counter, a logical read0/read1 assertion, or a
route decision.  The labels `init_positive` and `init_negative` denote only
the two D0 procedures; they do not assign a logical value or published state.

## Fixed closure and stimuli

Each of twelve runs uses copied snapshots of `bvm_cell.cir` and `jjmit.cir`,
one `XBVM1 WL1 BL1 SE1 SL1 BVM`, and only `R_LD SL1 0 12`.

Initialization is exactly D0-003: WL and BL ramp to either `+100 uA` or
`-100 uA` at 10–11 ps, hold through 20 ps, and return to zero by 21 ps.  All
cases are then quiescent through the preregistered pre window.  The fixed read
stimulus is a **project-derived** (not published-parameter) single PWL copied
in shape/polarity from the historical `test_bvm_final.cir` R1 pulse and delayed
past D0's 75-ps tested-grid readiness bound:

```text
WL:  95 ps 0; 96 ps +100 uA; 105 ps +100 uA; 106 ps 0
SE:  95 ps 0; 96 ps +100 uA; 105 ps +100 uA; 106 ps 0
BL:  identically 0 after initialization
```

For each initialization, the matched zero-read control has identical netlist,
model, load, timestep, stop time, PWL knot times, and initialization; only the
two read-pulse amplitudes are changed to zero.  No other source varies.

The four cases are `init_positive_read`, `init_positive_control`,
`init_negative_read`, and `init_negative_control`.  Each is run once at
`0.1 ps`, `0.05 ps`, and `0.025 ps`, through `170 ps`; this is the complete
and nonextendable 12-run ladder.

## Probes, directions, and windows

| Observable | Probe/direction | Window |
|---|---|---|
| source voltage | `V(SL1)`, `SL1 -> 0` | source `[94,130) ps` |
| source current | `I(L_SL|XBVM1)`, `N8 -> SL1` | source `[94,130) ps` |
| applied inputs | `I(I_WL1)`, `I(I_SE1)` | source `[94,130) ps` |
| JM1 | direct `P/V(B_JM1|XBVM1)`, `N1 -> n_jm1o`, `vts=+1`, `rd=+1` | activity `[94,108) ps` |
| JM2 | direct `P/V(B_JM2|XBVM1)`, `n_jm2i -> N2`, `vts=+1`, `rd=+1` | activity `[94,108) ps` |
| storage signature | vector of direct JM1/JM2 P means | pre `[80,90) ps`; post `[140,150) ps` |

All intervals are half-open and use actual CSV times.  Source waveform reports
pre-window baseline, signed min/max, largest absolute baseline-subtracted peak,
its time/latency from 96 ps, and FWHM of the contiguous half-maximum interval.
FWHM is `NOT_APPLICABLE` with reason when no finite half-height crossing exists;
it is never invented by interpolation.

## Evidence-quality and convergence procedure

At every timestep, the pre-window is operationally admissible only if both
initializations and their controls have >=2 finite samples, JM1/JM2 p2p
`<= 0.020 rad`, and the two initialized mean vectors have L-infinity
separation `>= 0.100 rad`.  These are new S0 procedure-local readiness checks,
not global BVM tolerances and not a transfer of any D0 conclusion across
timestep.

For every case and both adjacent refinement pairs (0.1/0.05 and 0.05/0.025),
compare the preregistered scalars:

- each JM1/JM2 pre/post platform mean and control-corrected platform delta:
  absolute difference `<= 0.020 rad`;
- source-voltage absolute peak: difference `<= max(5 uV, 5% of the larger
  absolute peak)`;
- source-current absolute peak: difference `<= max(0.5 uA, 5% of the larger
  absolute peak)`;
- peak latency and FWHM: difference `<= 0.5 ps` when both values are
  applicable.

These are S0 numerical-comparison bands only; they are neither interface
acceptance limits nor physical success thresholds.  No integer/phase-area,
amplitude, jitter, source-output, or storage-preservation tolerance is frozen.
`CONVERGED` means all applicable registered comparisons meet these bands;
`INCONCLUSIVE` means a valid artifact lacks an applicable scalar or exceeds a
band at 0.025 ps; `INVALID` means QA/provenance failure.  No further timestep
or parameter run is allowed.

The S0 artifact is `VALID` only if QA, operational initial-state admissibility,
and the registered convergence procedure all hold.  Otherwise it is
`INCONCLUSIVE` (or `INVALID` for artifact failure).  Even `VALID` only reports
source-side facts under this fixture; it does not grant a physical Gate PASS.

## Required independent review

After Claude produces a sealed receipt, Codex must request a read-only Copilot
skeptical evidence review of the exact receipt/raw snapshot before final audit.
The review must try to falsify control matching, initial-state provenance,
same-JJ P/V mapping, source-port direction, actual-time integration, waveform
measurement, pre/post windows, convergence, and any claim above this task's
ceiling.  Copilot does not issue the final scientific disposition.
