# REVIEW — delta4 replay sensitivity

## Numerical review

- PASS: source values were read as signed Decimal values on the common
  actual stored timestamp grid.
- PASS: I_N3 + delta_I4 = I_N4 has zero Decimal residual at all 1999
  source timestamps; tolerance is 1e-21 A.
- PASS: the recorded 14.7 to 14.9 ps source-grid gap is preserved; delay
  lookup is by exact timestamp, not row index.
- PASS: delayed delta is zero for missing or out-of-range exact timestamps.
- PASS: gain transformations scale both signs with no rectification,
  clipping, resampling or reshaping.
- PASS: all raw grids are finite and strictly increasing; integration uses
  each raw file's actual time column.
- PASS: same-JJ P/V arithmetic uses the same JJ labels, direction and
  fixed [118,140) ps window.
- UNKNOWN: no timestep convergence or parameter/solver sensitivity was
  authorized or performed.

## Adversarial review

- No-op probe: PASS; the four generated replay sources differ according to
  their registered delay/gain transformations, and the four raw outputs have
  distinct hashes.
- Wrong-branch probe: PASS; decks contain one QB, six JTL stages and one
  10 ohm termination, with no BVM, passive JSL or COMMON_SL element.
- Boundary probe: PASS; the source-grid gap, exact 199.9 ps endpoint and
  out-of-range delay behavior are represented in the registry and independent
  checker.
- Stale-artifact probe: PASS; new evidence is under the 2026-09-08
  experiment directory and is bound to HEAD
  2a3e3caeaefd511aa6e555dff18e596bd968f3a2; N3/N4 controls retain their
  prior hashes.
- Weak-oracle probe: PASS; the classification requires both runs in a
  family to show the registered internal and downstream activity evidence;
  one partial BJ2 candidate does not qualify.
- Overclaim probe: PASS; phase, area, peaks, threshold clusters and
  terminal activity remain descriptive and are not called SFQ counts or
  root cause.

## Residual uncertainty

The current evidence does not distinguish recovery/timing, effective
marginal-stimulus/front-end acceptance and internal regeneration. The
MIXED_OR_UNRESOLVED bounded classification is therefore retained.
