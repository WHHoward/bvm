# METRIC_SPEC_V2 — Measurement & Reporting Contract

```yaml
metric_spec_version: 2.0.0
canonical_path: docs/research/METRIC_SPEC_V2.md
status: FROZEN
freeze_task: JH-20260813-M9-001
claim_ceiling: measurement_semantics_and_reporting_contract_only_no_physical_gate
```

## 0. Purpose, claim boundary, and evidence basis

This document freezes **how to measure and report** JoSIM phase-mode simulation
outputs. It does **not** define whether any circuit — BQ, DCSFQ, BVM, JTL, T1, or
an interface — is successful. Specifically it does not define
`INTERFACE_GATE_V1`, candidate success criteria, read1/read0, repeatability,
state preservation, route selection, or paper/hardware claims. Those are
separate contracts that other tasks may freeze later; this specification must
not be used as a substitute for them.

The semantic decisions below are grounded in the accepted M4–M8 calibration
evidence chain, which established the phase-unit foundation, window/control
semantics, same-JJ phase–voltage-area cross-check, unit/regression tests, and
the bounded timestep-convergence procedure. Accepted evidence:

- `research/tasks/JH-20260811-M4-003/audits/C01/verdict.yaml` — `P(...)` is raw
  phase in radians; `phase_delta_turns = phase_delta_rad / (2*pi)`; activity is
  reported only as samples/intervals, never as events.
- `research/tasks/M5-LITE-PILOT-001/attempts/A02/CODEX-AUDIT.md` — pre/activity/
  post half-open windows, explicit ±1 directions, matched zero-input controls,
  contiguous activity clustering.
- `research/tasks/JH-20260812-M6-002/audits/C01/verdict.yaml` — same-junction
  direct `P(B...)`/`V(B...)` mapping, identical orientation/window endpoints,
  actual-time trapezoidal voltage area, signed phase-area residuals.
- `research/tasks/JH-20260812-M8-002/audits/C01/verdict.yaml` — preregistered
  bounded convergence procedure (ladder, controls, observables, windows, bands,
  maximum depth, stop rule); CONVERGED / INCONCLUSIVE / INVALID classification.
- `scripts/sfq_metrics_v2.py` — implementation reference for the semantics
  frozen here (read-only; this spec does not modify it).

### 0.1 Content-hash procedure

Any measurement artifact that references this specification MUST record:

```yaml
metric_spec_path: docs/research/METRIC_SPEC_V2.md
metric_spec_version: 2.0.0
metric_spec_sha256: <sha256 of the canonical file bytes>
```

The SHA-256 is computed over the exact bytes of this file at the time the
artifact is produced, using the same `file_sha256` procedure as
`scripts/sfq_metrics_v2.py`. If the file bytes change, the recorded hash
changes; any artifact whose recorded hash does not match the current file MUST
either update its record (if the semantic change is accepted through the normal
contract flow) or be treated as referencing a superseded spec version. No
parallel root-level copy of this specification is permitted.

## 1. Raw phase and turns

1.1 JoSIM phase-mode `P(...)` columns are **raw, unwrapped phase in radians**.
A reported turn value is always derived as

```
phase_delta_turns = phase_delta_rad / (2*pi)
```

No absolute value, integer rounding, or modulo operation is applied before
reporting. Both `phase_delta_rad` and `phase_delta_turns` MUST be reported.

1.2 A single `P(J) = 6.28 rad` value is an absolute angle; only a declared
reference-window difference `DeltaP_rad` carries measurement meaning.

## 2. Platform change vs endpoint delta (two separate measurements)

2.1 **Platform result** (for a stability/pre/post comparison):
`platform_delta_rad = mean(P_post) - mean(P_pre)`, computed over the samples of
the predeclared post and pre windows. The per-window statistics (mean, min,
max, peak-to-peak, sample count) MUST be reported alongside.

2.2 **Endpoint result** (for the same-JJ phase–voltage-area identity):
`endpoint_delta_rad = P_last - P_first`, where first/last are the actual first
and last selected samples of the integration window.

2.3 These two deltas answer different questions and MUST NOT be conflated or
silently substituted for one another.

## 3. Same-JJ P/V mapping and signs

3.1 Any phase–voltage-area cross-check MUST declare, per junction:

```
junction:
  phase_column: P(<name>)
  voltage_column: V(<name>)        # direct branch voltage preferred
  branch_endpoints: (pos, neg)     # declared positive/negative terminals
  voltage_to_phase_sign: +1 | -1   # aligns the voltage column with the declared P-branch orientation
  reporting_direction: +1 | -1     # applies consistently to phase, area, and residual
  run: <run_id>
  window: <predeclared window name>
```

3.2 `reporting_direction` and `voltage_to_phase_sign` are **distinct fields**.
The reporting direction applies consistently to phase, area, and residual; the
voltage-to-phase sign only aligns a voltage column with the declared P-branch
orientation.

3.3 Direct `V(B...|X...)` branch voltages are preferred over node-to-ground
differences. Node-pair differences are only acceptable when the branch
endpoints and orientation are explicitly registered, and a node-to-ground
voltage equals a junction voltage only when the other terminal is grounded.

3.4 Verified calibration mappings (from accepted M6/M7 evidence):
- DCSFQ `B1`, `B2`, `B3` (`V(Bn|XDCSFQ)`/`P(Bn|XDCSFQ)`, orientation +1,
  matched 0/300 uA runs).
- Canonical JTL `B1|XDUT`, `B2|XDUT`, `B1|XLOAD`, `B2|XLOAD`
  (`V(Bn|X...)`/`P(Bn|X...)`, orientation +1, matched zero/single-input runs).

3.5 BQ/BVM junction mappings remain `UNKNOWN` unless separately demonstrated;
they MUST NOT be assumed to follow any of the verified examples above.

## 4. Windows

4.1 Windows are predeclared half-open intervals `[start, end)` in seconds,
interpreted against the CSV's **actual time column**: a sample at time `t`
belongs to the window iff `start <= t < end`.

4.2 Each window MUST contain at least two finite samples, and the report MUST
list requested start/end, selected first/last times, sample count, mean, min,
max, and peak-to-peak spread.

4.3 Fixture-specific windows (e.g., M5 event windows, M8 JTL windows) are
calibration data for those fixtures, not global defaults. Every experiment
predeclares its own windows before execution from the stimulus and run length;
windows must not be moved after inspecting outputs.

## 5. Matched controls

5.1 An input-induced result normally requires a matched zero-input control:
identical topology, models, bias, load, solver, timestep, and windows; only the
stimulus differs (e.g., the same PWL knot times with all voltage values set to
0 V).

5.2 Control matching is proven by **netlist closure** (identical source
netlists/includes), not by aligned CSV rows alone. Aligned time arrays are a
necessary practical precondition for per-sample subtraction but do not
themselves prove the control relationship.

5.3 Correction semantics: `corrected_delta_rad = direction * (signal_delta_rad
- control_delta_rad)`; turns are derived only after the subtraction. Per-run
signal and control values MUST be reported in full before any corrected value.

## 6. Activity

6.1 Activity is detected as `abs(delta P_rad) > threshold_rad` on **adjacent
samples wholly inside the activity window**, with a strict `>` (equality is
inactive). Consecutive qualifying increments form a contiguous cluster; gaps
are never bridged.

6.2 Activity samples and clusters are **activity**, not events, SFQs, pulses,
or fluxoids. Reporting MUST NOT use `fast_events`, `pulse_count`, `sfq_count`,
`event_count`, or equivalent event-naming fields.

6.3 The current 0.3 rad regression setting is **descriptive and unfrozen**; it
is not a universal threshold (see §8). No universal activity threshold is
frozen here.

## 7. Voltage area

7.1 Voltage area uses the CSV's **actual time column** and trapezoidal
integration with at least two samples:

```
area_vs  = trapezoid(V_jj, actual_time)
area_turns = area_vs / Phi0,  Phi0 = 2.067833848e-15 Wb
```

No fixed-dt assumption, resampling, or interpolation is permitted.

7.2 The phase–area identity used for cross-check:

```
(1/Phi0) * integral(V_jj dt)  ==  (P_last - P_first) / (2*pi)
```

holds only for the same junction, same endpoints, same voltage-to-phase sign,
same window, and same run. The signed residual is
`residual_turns = phase_delta_turns - area_turns` computed per run; per-run
values precede any control correction.

## 8. Tolerances: registration, UNFROZEN status, and classification

8.1 This specification does **not** freeze a universal activity threshold or
any global acceptance tolerance for: integer residual, phase-area residual,
platform stability, BVM drift, amplitude, or jitter.

8.2 A tolerance is registered only as a named, scoped object:

```
tolerance:
  id: <unique name>
  scope: <fixture|procedure|task-local>
  applies_to: <observable id>
  value: <number + units>
  status: FROZEN | UNFROZEN
  evidence: <accepted evidence path(s)>
```

8.3 The M8 0.1/0.05/0.025 ps ladder and its bands are only the
`m8_loaded_canonical_jtl_v1` fixture-local calibration profile. They must never
be promoted into a universal candidate tolerance.

8.4 Where a requested classification depends on a tolerance that is absent or
`UNFROZEN`, the result MUST be `INCONCLUSIVE` with the missing tolerance named
— never a `PASS`/`FAIL` invented from an unfrozen number.

## 9. Convergence

9.1 A convergence procedure MUST be preregistered before execution and state:
initial timestep, refinement ratio, maximum depth (ladder), matched controls,
observables, comparison windows, per-observable comparison bands, and stop
rule.

9.2 Classification:
- **CONVERGED** — all runs pass QA, every registered scalar is computable, and
  every adjacent refinement pair satisfies every applicable predeclared band,
  with the classification preserved across refinements.
- **INCONCLUSIVE** — the evidence is valid but a required scalar is missing,
  ambiguous, or outside its band at the maximum registered depth; the procedure
  must not be extended to search for a favorable outcome.
- **INVALID** — QA/provenance failure (see §10); the data cannot support any
  classification.

## 10. Data validity (QA) and three-state classification

10.1 Before analysis, each run MUST satisfy: zero exit status and no unhandled
solver errors; complete required columns; no NaN/Inf; strictly increasing
actual time; endpoint coverage through the declared post window; recorded
requested/actual timestep, stimulus, control, and load.

10.2 `INVALID` marks an artifact that cannot be used as evidence (QA failure,
missing provenance, hash mismatch, corruption) — it is not a circuit `FAIL`.
`FAIL`/`PASS` require valid evidence plus frozen acceptance criteria; without
frozen criteria the valid result is `INCONCLUSIVE`.

## 11. Output schema

11.1 Every measurement artifact conforms to a versioned schema
(`schema_version`) and MUST include:

```
metric_spec: path/version/sha256 (§0.1)
schema_version
study_phase: EXPLORATORY | CALIBRATION | CONFIRMATORY
provenance: csv path + sha256, netlist/include closure, binary path/version/sha256, git head, windows
windows: requested/selected endpoints, count, mean, min, max, p2p per window
mappings: junction, phase/voltage columns, endpoints, voltage_to_phase_sign, reporting_direction, run, window
namespaces: signal, zero_input_control, control_corrected  (each reported in full)
values: raw phase_rad AND phase_turns for every reported delta
activity: clusters, over-threshold sample count, peak-time/FWHM diagnostics when applicable (as activity diagnostics, never counts)
cross_check: phase_delta_turns, area_turns, residual_turns per junction (same JJ/endpoints/sign/window/run)
convergence: ladder, bands, per-adjacent-pair table, classification, stop rule compliance
unknown/na: explicit reason for every UNKNOWN or NOT_APPLICABLE field
```

11.2 The schema MUST reject JSON NaN/Inf (non-finite values are `INVALID`) and
MUST NOT emit event/SFQ/pulse/fluxoid-count fields.

## 12. Exclusions (explicit non-semantics)

The following are outside this specification and MUST NOT be derived from it:

- `INTERFACE_GATE_V1` and any interface/system Gate definition.
- Candidate success criteria or thresholds for BQ, DCSFQ, BVM, JTL, T1.
- read1/read0 semantics, repeatability, and state preservation.
- Route selection between candidate interfaces.
- Paper-level or hardware-level claims; simulation results are not hardware
  measurements.

## 13. Unknown / unfrozen registry (current state)

| Item | Status | Reason |
|---|---|---|
| Universal activity threshold | UNFROZEN | 0.3 rad is descriptive regression setting only |
| Integer residual acceptance tolerance | UNFROZEN | requires calibrated global data; M8 bands are fixture-local |
| Phase-area residual acceptance tolerance | UNFROZEN | M6 reports residuals; no frozen acceptance |
| Platform stability tolerance | UNFROZEN | no frozen global criterion |
| BVM drift tolerance | UNFROZEN | no frozen global criterion |
| Amplitude / jitter acceptance tolerance | UNFROZEN | no frozen global criterion |
| BQ/BVM P/V mappings | UNKNOWN | not separately demonstrated |
| Classification tolerance dependency | — | absent/UNFROZEN tolerance ⇒ INCONCLUSIVE (§8.4) |
