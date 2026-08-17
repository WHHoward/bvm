# BVM-S2 Architect Review (read-only)

Reviewer: `josim_architect` runtime role (Sol XHigh). Date: 2026-08-17.
No source file was modified and no JoSIM command was run.

## Recommendation

Approve the draft direction as a bounded `CALIBRATION + CRITICAL + FROZEN`
study after user review. Use only a fresh external resistor at `SL1`; retain
the BVM cell's internal 12 Ω `R_SL` unchanged. Do not attach BQ, DCSFQ_BVM or
JTL.

Recommended independent loads are 1 Ω, 12 Ω and 50 Ω. Two endpoint loads
determine an affine V–I line, while the third gives the minimum available
non-affinity test. The resulting fit is local to the declared load range,
state/protocol and waveform feature/time. It is not a universal Thevenin or
Norton model.

S1's sealed 12 Ω values are design context only: S1 raw was valid but its
registered convergence was INCONCLUSIVE. S2 should fresh-run 12 Ω together
with 1 Ω and 50 Ω rather than splice S1 into a new cross-load analysis.

## Numerical recommendation

Use 0.0125 ps as the primary S2 timestep. Add a two-run 0.00625 ps spot-check
only for 12 Ω positive-read/control, because S1's narrow 0.025→0.0125 ps
positive RMS failure is precisely the relevant decision risk. It tests whether
the central positive waveform descriptor changes discretely; it neither
reopens S1 nor establishes formal source convergence. The resulting minimum is
14 runs.

If a later task needs decision-grade endpoint convergence at all loads, it
would need its own expanded preregistration; do not add it adaptively here.

## Required observations and limits

Use source V/I, input currents, direct JM1/JM2 P/V and direct JS1/JS2 P/V as
listed in the draft. Same-JJ phase/area is a local consistency witness only.
Report waveform lobes, exact-time V–I residuals and separately any peak-envelope
fit; never align peaks to manufacture a common-time model.

A valid nonlinear result remains scientifically useful: it can show that the
empirical affine approximation is not supported over a named subset of 1–50 Ω.
Reserve `INCONCLUSIVE` for evidence-quality, control, readiness, timestamp,
conditioning or registered spot-check ambiguity.

## Issuance blockers

Before issuing execution, freeze JS1/JS2 probe headers/directions and a
METRIC_SPEC_V2 section 11.1-complete analysis/provenance schema. Do not copy
S1 A02's metadata or phase-area residual defects. The current facts are
otherwise concrete enough; exploratory tuning is not needed.
