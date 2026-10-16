# BVM4X4 V9 topology migration — 80/68 ps, three reads

## Execution state

- Experiment: `bvm4x4-v9-multiply-80p68-20261016`; batch: `BVM4X4_V9_MULTIPLY_80P68_20261016`.
- Registered cases: `A109_V9_A0_B0_80P68, A110_V9_A1_B1_80P68, A111_V9_A11_B13_80P68, A112_V9_A15_B15_80P68`.
- Physical solves completed: `4/4`.
- Artifact/mechanical batch status: `PASS`.
- Arithmetic status: `INCONCLUSIVE` unless a future separately authorized review supplies an accepted classifier; this work unit does not claim multiplication PASS/Gate.
- Event counts and observed bits: `UNKNOWN`; output integrals and same-JJ phase/area are preserved as navigation/mechanical quantities.
- Scientific interpretation: NOT PERFORMED; unauthorized follow-up: none.

## Artifact processing note

A109's initial postprocessor requested `P(B7|XDFF)`, which was not in the registered raw probe set. JoSIM had exited 0 and the raw was preserved. The analyzer was corrected to report the DFF internal same-JJ cross-check as `UNKNOWN`; A109 was reanalyzed from the identical raw SHA without another solve. The failed initial result and run manifest remain under `runs/A109_V9_A0_B0_80P68/postprocess_attempts/001/`. A110–A112 were then run once each under the original registered matrix.

## Frozen topology

The new runs render the current hash-pinned V9 reference deck with only registered `.print` and `.tran` changes. Per-cell BVM→QB and D0–D6 carry/CB/T1/DFF connectivity is checked against that actual deck. All eight clocks use the existing PWL→2 Ω→DCSFQ2→JTL2 path. The 11-file source closure is copied into each run and SHA-verified. No reference V9_analysis file is modified or used as a data oracle.

## Interpretation limits

The terminal voltage area divided by Φ0 is navigation arithmetic, not an event count. Phase differences are raw radians divided by 2π only for navigation and cross-checked against the same JJ/same rows/same window voltage integral. Peak-time deltas are not a timing margin. Timestep convergence, parameter sensitivity, system Gate, and hardware behavior remain UNKNOWN.

See `BVM4X4_V9_STATIC_QA.md`, `BVM4X4_V9_FUNCTIONAL_RESULTS.csv`, `BVM4X4_V9_CLOCK_TIMING.md`, and each immutable run's `raw.csv`, QA, provenance, and plots.
