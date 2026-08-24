# JTL_TRANSPORT_GATE_V1 strict numerical replay

## Verdict

`JTL_TRANSPORT_GATE_V1_STRICT_REPLAY_INCONCLUSIVE`

## Result

- R11 standard-JTL: four-stage `+1` settled transport across all three
  timesteps; numerical convergence and independent window robustness passed.
- Q0 pulse-5 original replay: four-stage `+1` settled transport across all
  three timesteps; numerical convergence passed, but the registered
  post-plus window family passed only `18/27` combinations.
- Q0 pulse-5 reverse replay: no four-stage `+1` or `−1` settled transport;
  convergence and window robustness passed.
- All nine JoSIM runs exited successfully; full-tail extra-event guards passed.

## Interpretation boundary

The current evidence supports a numerically stable positive/reverse fixture
classification under the timestep ladder, but it does not satisfy the full
pre-registered window robustness condition. Therefore `JTL_TRANSPORT_GATE_V1`
is not frozen by this package. This is not evidence against JTL transport
physics and does not authorize parameter tuning, physical BVM integration, or
T1 attachment.

See [the full report](analysis/REPORT.md),
[window disposition](analysis/WINDOW_DISPOSITION.md),
[preregistration](PREREGISTRATION.md), and
[pre-run hash record](inputs/PRE_RUN_SHA256SUMS.txt).
