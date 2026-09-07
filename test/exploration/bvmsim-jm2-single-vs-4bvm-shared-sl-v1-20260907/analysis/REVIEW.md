# REVIEW — numerical and adversarial QA

- Review time: `2026-09-07T13:22:40+08:00`
- Independent raw cross-check: **PASS**
- Scope: artifact integrity, exact-grid arithmetic, units/signs, window boundaries, phase unwrapping, stale-artifact and overclaim probes.

## Numerical checks

| check | result | evidence |
|---|---|---|
| exact stored grid | `PASS` | both independent CSV readers have 1999 rows; no interpolation |
| WL/BL/SE target controls | `PASS` | exact array BVM1 minus single is zero for all three |
| key metric arithmetic | `PASS` | independent CSV recomputation compared with metrics.json |
| phase units | `PASS` | continuous unwrapped radians; display conversion is separate |
| integration | `PASS` | trapezoid integration uses actual stored time values |
| finite/monotonic raw | `PASS` | bvmtools reader completed without NaN/Inf/time-axis error |
| convergence/sensitivity | `UNKNOWN` | no sweep was registered or run |

## Adversarial probes

| hidden failure hypothesis | probe | result |
|---|---|---|
| stale raw artifact | compare raw hashes before and after independent check | `PASS` |
| wrong branch/target | independently use array BVM1 labels and exact target control labels | `PASS` |
| wrapped-phase subtraction | compare direct wrapped delta with independently unwrapped delta and production metric | `PASS` |
| weak oracle | recompute four key FINAL_READ metrics with an independent CSV loop | `PASS` |
| boundary omission | inspect [110,121) first/last stored samples | `PASS` |
| overclaim | review labels for SFQ count, event count, mechanism or hardware claims | `PASS` | RESULT_BRIEF ceiling is bounded simulation evidence |

## Residual uncertainty

- `V(IB|XBQ1)` was requested in the deck but is not emitted by this JoSIM raw schema; `I(IB|XBQ1)` is present and retained. This is an optional probe limitation, not a physical inference.
- The final raw sample is 199.9 ps under `.tran 0.1p 200p`; this is recorded as solver output convention.
- No timestep convergence, parameter sensitivity, SFQ event identity, physical mechanism, hardware behavior, or universal isolation claim is established.

No scientific mechanism conclusion is made in this review.
