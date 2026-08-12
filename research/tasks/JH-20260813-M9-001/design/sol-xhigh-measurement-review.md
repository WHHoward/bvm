# M9 measurement-semantics design review

**Reviewer role:** Sol XHigh (read-only, pre-issuance)  
**Purpose:** constrain the M9 metric specification before any implementation.

## Decisions that M9 may freeze

1. The sole canonical specification path is `docs/research/METRIC_SPEC_V2.md`,
   with `metric_spec_version: 2.0.0` and a content SHA-256 recorded by later
   measurement artifacts.  No parallel root-level copy is permitted.
2. JoSIM `P(...)` values are raw, unwrapped phase in radians.  A reported turn
   value is `phase_delta_rad / (2*pi)`; no absolute value, integer rounding, or
   modulo operation is allowed before reporting.
3. Platform change and Josephson cross-check are separate measurements:
   `mean(P_post)-mean(P_pre)` for a platform result, versus `P_last-P_first`
   over the actual integration samples for the P/V identity.
4. A P/V mapping must name the junction, phase column, voltage column, branch
   endpoints, voltage-to-phase sign, reporting direction, run, and window.
   Direct `V(B...|X...)` is preferred.  Current DCSFQ B1/B2/B3 and canonical
   JTL XDUT/XLOAD mappings are verified calibration examples; BQ/BVM mappings
   remain `UNKNOWN` unless separately demonstrated.
5. Reporting direction and voltage-to-phase sign are distinct fields.  The
   former applies consistently to phase, area, and residual; the latter only
   aligns a voltage column with the declared P-branch orientation.
6. Windows are predeclared half-open intervals `[start,end)` in seconds,
   selected from actual CSV times.  Each must contain at least two finite
   samples and report requested and selected endpoints, count, mean, min, max,
   and peak-to-peak spread.  Fixture-specific M5/M8 windows are not global.
7. An input-induced result normally requires a matched zero-input control:
   topology/model/bias/load/solver/dt/windows are the same, only stimulation
   differs, and netlist closure—not aligned CSV rows alone—proves the match.
8. Activity is strictly `abs(delta P_rad) > threshold_rad` on adjacent samples
   wholly inside the activity window; consecutive qualifying increments form a
   cluster and gaps are never bridged.  Samples and clusters are not events,
   SFQs, pulses, or fluxoids.  The current 0.3 rad value is descriptive, not a
   universal frozen threshold.
9. Voltage area uses actual CSV time and trapezoidal integration with at least
   two samples: `area_turns = integral(V_JJ dt) / Phi0`,
   `Phi0 = 2.067833848e-15 Wb`.  No fixed-dt assumption, resampling, or
   interpolation is permitted.  Per-run values precede any control correction.
10. A convergence procedure must pre-register its ladder, matched controls,
    observables, windows, comparison bands, maximum depth, and stop rule.
    All adjacent refinements must satisfy every applicable predeclared band and
    preserve classification to be `CONVERGED`; otherwise the valid result is
    `INCONCLUSIVE`, while QA/provenance failure is `INVALID`.
11. The M8 0.1/0.05/0.025 ps ladder and its bands are only the
    `m8_loaded_canonical_jtl_v1` fixture-local calibration profile.  They must
    never become a universal candidate tolerance.
12. The output contract must include spec/schema/hash, study phase, complete
    provenance and QA, windows, mappings/signs, signal/control/corrected
    partitions, raw radians and turns, activity diagnostics, P/V area and
    residual, convergence information, and reasons for `UNKNOWN` or
    `NOT_APPLICABLE`.  It must reject JSON NaN/Inf and not emit event/SFQ/pulse
    or fluxoid-count fields.

## Values that M9 must not invent

Existing evidence is insufficient to freeze global integer residual,
phase-area residual, platform stability, BVM drift, amplitude, or jitter
acceptance thresholds.  M9 must define how such a tolerance is registered and
reported, mark it `UNFROZEN` when absent, and require an `INCONCLUSIVE` result
where a requested classification depends on it.

## Claim boundary

M9 defines *how to measure*, not whether a BQ, DCSFQ, BVM, JTL, or interface is
successful.  `INTERFACE_GATE_V1`, candidate success criteria, read1/read0,
repeatability, state preservation, route selection, and paper-level claims are
out of scope.

## Evidence consulted

- `research/tasks/JH-20260811-M4-003/audits/C01/verdict.yaml`
- `research/tasks/M5-LITE-PILOT-001/attempts/A02/CODEX-AUDIT.md`
- `research/tasks/JH-20260812-M6-002/audits/C01/verdict.yaml`
- `research/tasks/JH-20260812-M8-001/preregistration.yaml`
- `research/tasks/JH-20260812-M8-002/audits/C01/verdict.yaml`
- `scripts/sfq_metrics_v2.py`
