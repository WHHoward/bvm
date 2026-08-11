---
task_id: M5-LITE-PILOT-001
task_type: measurement-implementation
risk: CRITICAL
evidence_mode: LITE
status: ISSUED
---

# TASK M5-LITE-PILOT-001 — windowed phase metrics and matched zero-input control

Risk: **CRITICAL**  
Evidence mode: **LITE**

Task revision commit: resolve as the first Git commit containing this `TASK.md`.  
Execution baseline commit: the same resolved task-revision commit.  
Delivery snapshot owner: **CODEX**.

## Goal

Extend the accepted M4 unit foundation in `scripts/sfq_metrics_v2.py` with deterministic pre/activity/post windows, explicit phase direction, matched zero-input control correction, and contiguous activity clustering. This is an implementation-and-regression task only: it must not run JoSIM or issue a physical conclusion about the historical DCSFQ data.

## Fixed measurement semantics

- Window units are seconds and every window is half-open: `[start_s, end_s)`.
- Require `pre_end <= activity_start` and `activity_end <= post_start`. Pre, activity, and post windows each contain at least two finite samples.
- For each window, calculate the unrounded arithmetic mean in raw radians and report the requested bounds, selected first/last time, sample count, minimum, maximum, and peak-to-peak variation.
- `signal_delta_rad = signal_post_mean - signal_pre_mean`; `control_delta_rad = control_post_mean - control_pre_mean`.
- The mandatory declared direction for each analyzed `P(...)` column is exactly `+1` or `-1`. Compute `corrected_delta_rad = direction * (signal_delta_rad - control_delta_rad)`, then derive `corrected_delta_turns = corrected_delta_rad / (2*pi)`. Do not infer direction from observed sign; do not take absolute values.
- A matched zero-input control must have identical parsed headers and time arrays. Do not interpolate, resample, or nearest-match. Retain distinct `signal`, `zero_input_control`, and `control_corrected` output namespaces.
- Activity uses consecutive phase increments wholly inside the declared activity window, strict `abs(delta_rad) > threshold_rad`, and clusters only consecutive qualifying increments. Equality is inactive; do not bridge gaps. Report signal and control activity separately. Clusters and samples are **activity**, never events, pulses, SFQs, or fluxoids.
- Window plan, direction, threshold, and inclusion rule are explicit inputs. The M5 threshold is descriptive/unfrozen and must be labelled as such.

Use a JSON measurement plan through a reproducible CLI such as `--measurement-plan PLAN.json [--control-csv CONTROL.csv]`. At minimum the plan contains:

```json
{
  "schema_version": 1,
  "windows_s": {
    "pre": [6e-12, 9e-12],
    "activity": [9e-12, 50e-12],
    "post": [100e-12, 190e-12]
  },
  "phase_directions": {"P(B1|XDCSFQ)": -1},
  "activity_threshold_rad": 0.3
}
```

The existing M4 `analyze(csv_path, threshold_rad=...)` and its CLI behavior remain backward-compatible.

## Allowed paths

- `scripts/sfq_metrics_v2.py`
- `test/metrics/test_sfq_metrics_v2_m5.py`
- `research/tasks/M5-LITE-PILOT-001/attempts/**`
- `research/mailbox/from-claude/**` — notification only

`TASK.md` is immutable. Do not modify the accepted M4 test, legacy `scripts/sfq_metrics.py`, historical CSV/netlist data, `docs/HANDOVER.md`, `memory/project-todo.md`, protocol files, or any metric specification.

## Frozen read inputs

Verify these SHA-256 values before implementation and again before delivery. They are inputs to this LITE task, not a retroactive FROZEN evidence package.

| Path | SHA-256 |
|---|---|
| `scripts/sfq_metrics_v2.py` | `b654205a4408bb394d9bc5b69f197d348e4c386b7d17aed2cd2f8d3688c2d02e` |
| `test/metrics/test_sfq_metrics_v2.py` | `7f0898e965de32e04ca70a6d15b88c15e02c9aee9af01e9de367eb67cef8d597` |
| `test/final/interface/data/test_dcsfq_behavior_bump_0.csv` | `2420b99ae10135de14db2a4dd0ea63649e225ff6a467dabe6b7514c1096bd9c3` |
| `test/final/interface/data/test_dcsfq_behavior_bump_300u.csv` | `dfe20406ee1bc54be483b3bc5935cac87ab545af06c47082720523569b90549d` |
| `test/final/interface/test_dcsfq_behavior_bump_0.cir` | `0918141eb5b7dcea4dfb856a4a8a56184e5785b3e2b558b2f0eca2b20a41e043` |
| `test/final/interface/test_dcsfq_behavior_bump_300u.cir` | `4c7d3df3560ff6014599942033550d9d6b29964e8b10c00e1083873b68215818` |
| `circuits/standard/DCSFQ.cir` | `3452106b9a72de20e712c49f002b5dfddf9fba3337f8ca5b809336cd97f42337` |
| `circuits/models/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |

The two bump netlists may be used only as provenance evidence: their source diff must remain exactly `.param IIN=0u` versus `300u`. CSV alignment does **not** prove netlist equivalence; the direct netlist diff is the bounded basis here.

## Acceptance criteria

- [ ] **AC1 — M4 preservation.** All 15 existing M4 tests pass unchanged. Raw-radian preservation, explicit `/ (2*pi)`, activity-only terminology, and M4 limitations remain present.
- [ ] **AC2 — validation.** Reject nonfinite or nonmonotonic time, invalid/overlapping windows, missing or undersampled windows, missing phase columns, invalid/missing directions, nonfinite phase values, and misaligned control headers/times. CLI failures are nonzero and actionable.
- [ ] **AC3 — arithmetic and provenance.** Output requested and actual window details, raw signal/control deltas, directed corrected delta, turns derived after subtraction, source paths and SHA-256 values, and whether a control was applied. State that CSV alignment cannot prove the netlist control relationship.
- [ ] **AC4 — clustering.** Activity is limited to the declared activity window and uses the stated strict threshold. Output may use `activity_clusters` and `over_threshold_sample_count`; it must never contain `event_count`, `fast_events`, `pulse_count`, `sfq_count`, or fluxoid semantics.
- [ ] **AC5 — independent synthetic tests.** Cover: ten contiguous active increments → one cluster; two separated ramps → two clusters; equality at threshold inactive; activity outside the activity window ignored; common startup background cancellation; identical signal/control → zero corrected delta; direction reversal flips signed deltas but not activity locations; constant offsets do not alter deltas; malformed/misaligned controls fail. Expected values must be first-principles constants, not calls to the production helpers.
- [ ] **AC6 — frozen CSV arithmetic replay.** Without modifying/rerunning historical data, use the fixed plan in this task and the bump `0 uA` control. Confirm selected samples: pre 30, activity 409, post 900. Within `1e-9 rad` computational precision, report corrected directed deltas: B1 `6.2831852 rad` / `0.999999982941839 turns`; B2 `6.2831857 rad` / `1.00000006251931`; B3 `6.2831854 rad` / `1.00000001477283`. Under the descriptive `0.3 rad` threshold, signal cluster counts are B1/B2/B3 = `1/0/1`, control = `0/0/0`. This regression explicitly demonstrates that clusters are not physical event counts.
- [ ] **AC7 — evidence closure.** Preserve plan JSON, output JSON, unit-test log, CLI/replay log, hash/preflight log, and before/after allowed-scope diff in `attempts/A01/`; record their SHA-256 values in `RESULT.md`. `RESULT.md` has all three status fields and `proposed_physical_verdict: NOT_APPLICABLE`.

## Required review

Copilot reviews the delivery snapshot using the canonical adversarial, numerical, and JoSIM evidence rules. It must try to falsify: shared/weak test oracle; endpoint or half-open-window off-by-one; inferred/absolute direction; final-only rather than delta-of-deltas correction; time interpolation; threshold equality; samples mislabelled as events; stale CSV; and a claim beyond this implementation task.

Codex’s CRITICAL audit will independently recompute the three replay values from raw CSV, not from executor JSON or helper functions.

## Stop conditions

Stop and write `BLOCKED` rather than guessing if:

- observed HEAD differs from the execution baseline, the worktree is unexpectedly dirty, or an allowed-path conflict exists;
- any frozen input hash differs, the bump-netlist diff changes, or control header/time alignment fails;
- any direction, window, threshold, inclusion rule, or correction formula would need inference;
- completion requires interpolation, JoSIM execution, network/install, executor commit, deletion/overwrite, or paths outside those allowed;
- implementation would add M6 voltage integration, freeze M9 tolerances/thresholds, interpret clusters as events, or change physical conclusions;
- a test oracle uses production calculation logic; or the task contract needs changing to make the result pass.

After two attempts blocked by the same root cause, stop and escalate to Codex/User.

## Claim ceiling

M5 window/control/direction/activity-clustering implementation and deterministic regression behavior only. The historical DCSFQ replay is an arithmetic check of frozen CSVs. It establishes no local SFQ event, downstream/JTL reception, closed-loop fluxoid, circuit Gate, frozen metric/window/threshold tolerance, route comparison, or paper claim. LITE evidence cannot be promoted retrospectively to FROZEN evidence.

## Explicit remainder

M6 owns same-JJ voltage-area integration with matched endpoints/direction/window. M7 owns the full synthetic/JTL/DCSFQ/BQ regression suite. M8–M11 own convergence, tolerances, metric freeze, regenerated data, and baseline freeze. Do not implement any of them here.
