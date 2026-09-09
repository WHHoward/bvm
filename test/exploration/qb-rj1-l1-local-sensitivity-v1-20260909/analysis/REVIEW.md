# Numerical and adversarial review

## Scope

This review checks the five immutable raw outputs and the registered derived
metrics for `qb-rj1-l1-local-sensitivity-v1-20260909`. It does not certify a
QB Gate, an SFQ event, a mechanism, an optimum, or convergence.

## Numerical review

| check | result | evidence |
|---|---|---|
| units | PASS | raw time is seconds; currents/voltages remain A/V; `P(...)` remains rad; turns are explicitly `continuous_unwrap(rad)/(2*pi)` |
| sign and direction | PASS | raw branch labels and signs are retained; L1 sign bracket uses negative-to-nonnegative stored samples without interpolation |
| windows | PASS | PRE_FINAL, EARLY_TRIGGER, FULL_READ, TAIL and FULL_FINAL are half-open and use actual stored timestamps; exact 110 ps sample exists |
| integration | PASS | waveform areas and `W_QBIN` use actual-time trapezoid integration; no fixed-dt assumption |
| time grid | PASS | all five raw files have 1999 samples, 0--199.9 ps, strict monotonicity, and the same stored time tokens; `dt` records a 0.2 ps gap (`dt_min` about 0.1 ps, `dt_max` 0.2 ps) |
| finite values | PASS | all raw values are finite |
| raw immutability | PASS | pre/post hashes are identical for all five runs |
| same-JJ phase/area | DERIVED | BJ1 direct P/V residuals are approximately -3.00e-4 turns in FULL_READ; no global acceptance tolerance was invented |
| L2 KCL | DERIVED | direct residual is about 5.0e-11 A maximum in FULL_READ; this is reported, not upgraded to a physical Gate |
| independent arithmetic | PASS | `analysis/independent_check.py` independently reproduces raw hashes, exact grids, L1@110, BJ1 progression, W_QBIN, KCL and BJ1 phase/area |
| timestep/solver sensitivity | UNKNOWN | no convergence or solver-sensitivity matrix was authorized |
| optional probe | UNKNOWN | `V(IB|XBQ1)` was requested but is not emitted by JoSIM in these raw files; `I(IB|XBQ1)` is present |

## Adversarial probes

| hidden-error hypothesis | probe | result |
|---|---|---|
| stale or wrong raw | per-run SHA-256, metadata/deck identity, pre/post hash, exact five-run set | no stale/duplicate output detected; NOMINAL is byte-identical to the recorded historical array raw, which is only deterministic replay evidence |
| no-op parameterization | deck diff and normalized-template check | PASS; variants differ from NOMINAL in exactly one registered `.param` line and normalize to the frozen ARRAY fixture template |
| wrong branch/label | full header QA and actual-label inspection | PASS; JoSIM emits `BJS` uppercase; the analyzer uses actual `P/V/I(BJS|XBQ1)` semantics; no signal was fabricated |
| weak phase oracle | independent unwrap plus same-JJ direct V-area check | PASS as arithmetic QA; not an event count |
| boundary/window error | exact 110 ps reference and half-open row selection | PASS; no interpolation or row-index shifting |
| overclaim | review of result wording against the contract | PASS; local changes are reported as bounded observations; SFQ count, root cause, optimality and hardware claims remain UNKNOWN/INCONCLUSIVE |

## Disposition

Artifact status: `VALID`. The registered metrics are mechanically reproducible.
Physical interpretation is limited to bounded local sensitivity under the fixed
historical fixture, parameters, stimulus, solver and 0.1 ps timestep. Any
system-level receiver/SFQ conclusion remains `INCONCLUSIVE` or `UNKNOWN`.
