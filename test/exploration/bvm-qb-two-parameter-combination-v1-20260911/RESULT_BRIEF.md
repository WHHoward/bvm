# Two-parameter full closed-loop QB combination

Scientific interpretation is bounded to the registered nine-point matrix,
the named BVM/JSL/QB/JTL model, stored history, load, solver and 0.1 ps grid.
Read `PREFLIGHT.md`, `screening/COMBINATION_MATRIX.md`, the QA records and raw
evidence before using any classification.

No phase landmark, voltage area, terminal area, threshold activity or current
peak is an SFQ count. The corrected CONTROL rule does not use FINAL/Tail phase
rollback. No third-parameter search, positional validation or timestep
robustness starts automatically.

## Final bounded outcome

- All 9 registered combination points and 18 logical cases completed.
- New physical solves: `18`; reused baseline raw cases: `2`.
- Classes: `C=5` (`N2=1, N3=3`), `D=4`; `S=0`, `A=0`, `B=0`.
- All 18 cases were `CLEAN` under the corrected 70–110 ps history/control
  rule; FINAL/Tail phase rollback was retained only as a separate diagnostic.
- No clean `N2=2 / N3=3` combination was found. No population validation,
  third-parameter search, positional validation or timestep sweep was started.
- Final bounded result: `NO_DIRECT_2_TO_3_TWO_PARAMETER_COMBINATION`.

This is bounded to the registered source, receiver, load, stimulus, solver and
0.1 ps grid. It is not a universal impossibility, hardware result or route
verdict.
