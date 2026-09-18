# Adversarial and numerical review

This review covers artifact validity and implementation boundaries only. It is
not a scientific review of one-shot behavior or storage integrity.

## Strongest bounded claim reviewed

The registered Stage-A platform produced exactly 20 non-overwritten PASSIVE
JoSIM raw artifacts, with the requested parameterized BVM clone, mechanical
window metrics, compact plots, and an evidence package.

## High-value probes

| Hidden-error hypothesis | Probe | Result |
|---|---|---|
| A solver exit code hides missing/corrupt raw | 20 metadata records, raw existence/hash, 1999-row grid, finite-value scan | PASS: 20/20 `RUN_PASS`; all rows are `0…199.9 ps`; all values finite |
| Cases silently overwrite each other | Composite `(CASE_ID, run_id)` uniqueness and existing-case guard | PASS: 20 unique pairs; rerunning `A003` hard-stopped with no raw change |
| Mask or case branch is wrong | Registered mask vector and per-case metadata | PASS: each of the four candidates has exactly `0000,0001,0011,0111,1111` |
| Shunt is a no-op or attached to wrong nodes | Snapshot netlist inspection, shunt-specific raw column count, A000 passive topology check | PASS: A000 has no QB/JTL/terminal; A001 snapshot has exactly `R_JS1_SHUNT 5 6 20` and `R_JS2_SHUNT 9 10 20`; A001 raw header expands from 198 to 214 columns |
| Historical/canonical source was modified | Independent SHA-256 of current JJ and canonical BVM sources | PASS: authority hashes unchanged |
| Phase/area arithmetic uses wrong units or direction | Independent raw-only A001/N3/BVM2 JS1 calculation | PASS: raw-radian unwrap divided by `2π` and direct same-JJ voltage-area trapezoid match stored metrics to `<1e-12` turns |
| Population metric is copied or constant | Independent `I(B_JSL8)` peak recomputation | PASS: matches stored A001/N3 value; all 20 raw hashes are unique |
| Visualization creates hidden exhaustive/cross-run output | Filesystem and plot QA manifest | PASS: 100 grouped plots, 4 review pages, no atlas, no cross-run comparison |
| Execution continues beyond authorization | Run count, provenance, result status, process check | PASS: exactly 20 registered solves; no closed/5-ohm/sentinel solve; final stop is `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW` |

## Numerical review

- JoSIM `P(...)` is retained as raw radians.
- Navigation turns are explicitly derived as `rad/(2*pi)`; they are not event
  or SFQ counts.
- Voltage-area checks use the raw CSV time column and trapezoidal integration,
  with half-open windows such as `[110,121) ps`.
- S-loop and R-loop windows are recorded separately; no fixed 5% or 10%
  acceptance threshold was introduced.
- `I(B_JSL8)` signed and absolute areas retain sign and use `Phi0` only for
  navigation units.
- Numerical convergence across smaller time steps was not registered or run in
  this exploratory tuning platform. That remains `UNKNOWN` for any later
  scientific claim.

## Review-tool repairs

The first independent audit attempt used the experiment directory as the repo
root and stopped before source checks. A second draft used `len()` on the
integer header-count metadata field. Both were review-harness defects; neither
modified raw, deck, metadata, or analysis artifacts. The corrected audit above
passes `75/75` checks.

## Residual uncertainty

- No scientific Gate-S or Gate-R verdict is assigned.
- No one-shot classifier, SFQ count, mechanism, winner, or parameter
  recommendation is supported by this platform.
- The `closed` execution branch is implemented for future manually authorized
  cases but was not physically exercised in this Stage-A matrix.
- Time-step sensitivity/convergence and broader parameter sensitivity remain
  untested.

