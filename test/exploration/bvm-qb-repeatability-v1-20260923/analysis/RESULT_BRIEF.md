# BVM-QB repeatability platform — run summary

## OBSERVED

- Physical solves found: 5 total (4 new in this execution); registered A–E cases with raw: 5/5.
- Every per-run raw is hash-bound; analyses use actual stored-grid samples only.
- A/B/C historical raw prefix equality and input/deck comparison are recorded in `REGRESSION_COMPARISON.json`.
- D writes a single-read-to-STOP recovery trace; E's complete sequence schedule and computed STOP are recorded in snapshots.

## DERIVED

- Cycle phase/voltage-area arithmetic uses the same QB junction and the same half-open upstream cycle on the actual stored grid.
- Candidate pairing is voltage-threshold navigation only; assignments are monotonic, unique when possible, and otherwise `AMBIGUOUS`.
- BJ2→12 JTL-junction→terminal candidate paths are reported only when ordered and unique; `NO_COMPLETE_PATH_OBSERVED`, missing, or competing stage candidates remain explicit and are not mislabeled PASS.
- Component deltas and same-unit vector distances are relative to the median PRE_1 window; no recovery threshold is defined.

## PLATFORM LIMITATIONS

- P(...) is raw radians; turns are `rad/(2*pi)` navigation only, not SFQ counts.
- `V(IB|XBQ1)` is a known unsupported current-source branch voltage in this JoSIM build; it is recorded as `UNKNOWN` in each signal manifest while `I(IB|XBQ1)` remains probed.
- Voltage candidates and terminal assignments do not establish an event count, SFQ transmission, physical recovery, state retention, or population-preserving quantization.
- No timestep convergence, parameter sensitivity, hardware inference, or physical mechanism review was performed.

## REGRESSION STATUS

- Mechanical final QA: `PASS`; physical solve count=5 total, 4 new; authorized=5.
- A/B/C descriptive raw-prefix compatibility: `DESCRIPTIVE_EXACT_RAW_PREFIX_COMPATIBILITY` (not a physical verdict).
- See `analysis/FINAL_QA.json`, `analysis/summary.csv`, and `plots/REGRESSION_COMPARISON.html`.

## NEXT SCIENTIFIC EXPERIMENTS NOT YET RUN

- No recovery-boundary sweep, READ-period sweep, candidate tuning, additional fan-in, or follow-up solve was started.
- Further scientific interpretation awaits explicit review authorization.
