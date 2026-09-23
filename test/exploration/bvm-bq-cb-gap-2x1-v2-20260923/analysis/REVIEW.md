# Adversarial pre-solve review

Scope: v2 registration, platform, plotting and packaging code before any v2
physical solve. This is an executor self-review, not an independent review and
not a scientific review.

## Testable hidden-error hypotheses

| Hypothesis | Probe | Result |
|---|---|---|
| Mask bit order could swap BVM1/BVM2 or permit extra cases. | `test_exact_matrix_and_masks`, `test_stimulus_has_six_sources_and_all_write_preambles`, and Python-only matrix preflight. | PASS: exactly `00,01,10,11`; `01` selects BVM2 and `10` selects BVM1; WRITE0/CONTROL/WRITE1 sources are shared and only final READ differs. |
| Shared GAP2 wiring could be altered or gain an unregistered cell. | `test_rendered_topology_has_direct_gap2_contributions`; exact instance list in preflight. | PASS: the ten registered cells are present exactly once; XACC2 and XGAP1 share GAP2_IN; no `ACC2_OUT` measurement node is requested. |
| A nonexistent hierarchical component could silently appear as a probe. | `probe_inventory_errors()` over the active subcircuit element names; `test_registered_probe_closure`. | PASS for registered hierarchical element names; the absent/commented CB RJ2 is explicitly not probed. |
| Half-open window selection could shift a boundary sample through float rounding. | Decimal boundary test in `test_actual_grid_helpers` and `test_plot_projection_keeps_original_value_tokens`. | PASS: 110 ps is included, 121 ps excluded, and stored timestamp/value text tokens are preserved in plot projections. |
| Phase could be reduced modulo 2π or plotted in the wrong units. | `test_actual_grid_helpers` keeps a raw 7 rad endpoint delta; `test_classic_plotter_phase_conversion_and_axis_qa` renders synthetic raw P values 0, 2π, 4π through the repository plotter. | PASS: plotted y values are 0, 1, 2 turns; axis says `Phase (turns) [rad/2π]`; no Unknown axis remains after classic-runtime externalization. |
| Integration could assume fixed DT or the analyzer could self-certify. | `integrate_actual` uses Decimal differences of original stored seconds tokens; `test_independent_decimal_raw_recalculation` compares the production metrics with a separate raw→Decimal implementation. | PASS on synthetic irregular-grid fixture; all 35 registered arithmetic rows match within the implementation-only tolerances. |
| A failed/stale run could be reused or overwritten. | Preflight and runner source inspection: refuse an existing run directory, existing EXECUTION.json, stale source-lock/input hash, or changed HEAD. | PASS by static guard inspection; actual physical execution has not yet exercised these guards. |
| A successful solve or phase-area residual could be upgraded into the target truth table. | Inspect result/report schemas and metric tolerance registry. | PASS by static inspection: no event counter, population verdict, physical pass/fail, or residual acceptance threshold is generated; report stops at AWAITING_SCIENTIFIC_REVIEW. |

## Residual uncertainty

- No v2 JoSIM transient has been run. Therefore actual raw availability of each
  hierarchical print column remains unverified; complete-probe QA will stop the
  matrix if required columns are absent.
- JoSIM `--sanitycheck` is deliberately not used: it launched a transient in
  the v1 incident. v2 Python static preflight never invokes JoSIM transient
  execution.
- The phase/voltage sign mapping is registered from direct same-JJ probes and
  literal device pin order but remains unaccepted for this BQ/sJTL fixture under
  METRIC_SPEC_V2. Residuals have no physical acceptance tolerance.
- This review does not authorize a fifth solve, retries, parameter changes,
  scientific interpretation, or a follow-up experiment.

No v2 physical solve has been executed at the time of this review.
