---
task_id: M7-LITE-001
parent_todo_id: M7
task_type: calibration-regression
study_phase: CALIBRATION
risk: CRITICAL
evidence_mode: LITE
status: ISSUED
---

# TASK M7-LITE-001 — independent metric tests and regression characterization

Risk: **CRITICAL**
Evidence mode: **LITE**
Study phase: **CALIBRATION**

Task revision commit: resolve as the first Git commit containing this immutable `TASK.md`.
Execution baseline commit: the same resolved task-revision commit.
Delivery snapshot owner: **CODEX**.

## Goal

Complete the three bounded M7 calibration components against the accepted M4/M5/M6 implementation:

1. **M7A** — independent synthetic mathematical tests;
2. **M7B** — an instrumented canonical JTL measurement-pipeline replay;
3. **M7C** — deterministic historical-CSV regression characterization.

This task validates the measurement implementation and fixed historical arithmetic only. It does not evaluate BQ v4, DCSFQ_BVM, BVM, JTL logic, a route, or any system Gate.

## Fixed scope and semantics

- JoSIM `P(...)` is raw phase in rad. Every reported phase turn is `delta_rad / (2*pi)`.
- Activity samples/clusters are never event, SFQ, pulse, or fluxoid counts.
- Any P/V comparison uses the same JJ, direction, selected endpoint samples, run and actual CSV time axis. The M7B JTL check is a pipeline-calibration check; it does **not** freeze a residual tolerance or establish a local/JTL event.
- All test or replay expected values must be first-principles constants or direct, independent raw-CSV arithmetic written in the test. They must not call `sfq_metrics_v2` helper functions to generate their oracle.
- M7C uses preserved historical inputs only. Do not regenerate or alter them. Historical BQ v4 is periodic regression evidence, not a single-input causal Gate.

## Allowed paths

- `test/metrics/test_sfq_metrics_v2_m7.py`
- `test/metrics/m7_canonical_jtl.cir`
- `research/tasks/M7-LITE-001/attempts/**`
- `research/mailbox/from-claude/**` — notification only

`TASK.md` is immutable. Do **not** modify `scripts/sfq_metrics_v2.py`, existing M4/M5/M6 tests, legacy `scripts/sfq_metrics.py`, historical CSV/netlist data, `memory/project-todo.md`, `docs/HANDOVER.md`, workflow/skill files, model files, or protocol files.

## Frozen read inputs

Before implementation and before delivery, record SHA-256 values for these inputs. They are LITE task inputs, not retroactive FROZEN evidence.

- `AGENTS.md`
- `docs/HANDOVER.md`
- `memory/project-todo.md`
- `scripts/sfq_metrics_v2.py`
- `test/metrics/test_sfq_metrics_v2.py`
- `test/metrics/test_sfq_metrics_v2_m5.py`
- `test/metrics/test_sfq_metrics_v2_m6.py`
- `test/standard/test_jtl.cir`
- `test/final/interface/data/test_dcsfq_behavior_bump_0.csv`
- `test/final/interface/data/test_dcsfq_behavior_bump_300u.csv`
- `test/final/qb/data/bq_v4_sweep110.csv`
- `test/final/qb/test_bq_v4_sweep.cir`
- `circuits/models/jjmit.cir`
- `circuits/standard/JTL.cir`

Use `build/josim-cli` only; record its absolute path, `--version`, and SHA-256. No network, dependency installation, executor commit, deletion, overwrite, rename, or worktree creation is authorized.

## Acceptance criteria

- [ ] **AC1 — preservation.** The existing M4/M5/M6 tests pass unchanged (currently 15 + 29 + 21). The new M7 test also passes. No frozen input or out-of-scope path is modified.

- [ ] **AC2 — M7A synthetic ground truth.** `test_sfq_metrics_v2_m7.py` uses independently constructed synthetic CSVs/arrays to test all of: raw-rad-to-turn conversion (including sign); non-uniform actual-time trapezoid integration; same-JJ P/V orientation sign; matched control subtraction; half-open window endpoints; strict threshold equality inactive; separated activity clusters not bridged; malformed/non-monotonic input rejected. The oracle must use literal constants and elementary arithmetic, not production helper calls.

- [ ] **AC3 — M7B canonical JTL calibration run.** Add `test/metrics/m7_canonical_jtl.cir`, derived only from `test/standard/test_jtl.cir`, with the same one-input PWL stimulus, loaded second JTL and `.tran 0.1p 50p`; additionally print direct `V(B1|XDUT)` and `V(B2|XDUT)` beside `P(B1|XDUT)` and `P(B2|XDUT)`. In a new unique attempt-local run directory, save input copy/hash, include/model closure hashes, binary version/hash, stdout/stderr, raw CSV, manifest and analysis. Analyze a predeclared post-bias/end-of-run window using actual CSV times and direct same-JJ pairs. The test independently recomputes the selected phase delta and trapezoid area and checks agreement with the production output at floating-point computational precision. Report raw signed residuals without accepting/rejecting them against a new tolerance.

- [ ] **AC4 — M7C independent historical regression.** Use only the frozen historical CSVs. Test the M5 matched-control DCSFQ replay with the predeclared windows `pre=[6e-12,9e-12)`, `activity=[9e-12,50e-12)`, `post=[100e-12,190e-12)`, threshold `0.3 rad`, directions B1/B2/B3 = `-1/+1/+1`. Independent expected control-corrected turns are B1 `0.999999982941839`, B2 `1.00000006251931`, B3 `1.00000001477283`; selected sample counts are pre/activity/post = `30/409/900`; signal activity clusters are `1/0/1`, control `0/0/0`. Also independently verify the historical `bq_v4_sweep110.csv` JTL-B1 phase increments relative to the actual 5 ps sample at actual samples 49/99/149/199/249/299 ps: `1.0133756508381797`, `2.0133738512446557`, `3.013374598130222`, `4.0133737534663565`, `5.013374500351922`, `6.013373655688058` turns (absolute numerical tolerance `1e-9`). State explicitly that these are periodic historical phase-platform regression constants, not a count of physical events or a BQ interface Gate.

- [ ] **AC5 — LITE evidence closure.** `RESULT.md` begins with immutable Preflight and contains `execution_status`, `executor_artifact_assessment`, and `proposed_physical_verdict: NOT_APPLICABLE`; it maps every AC to evidence, records commands/exit codes/hashes, lists all changed paths, limits/unknowns, binary provenance, before/after allowed-scope diff, and the canonical run manifest. Preserve failed attempts rather than deleting them. Claude then sends a mailbox `REVIEW_REQUEST` that names the attempt and waits for a stable delivery snapshot.

## Required review

Copilot reviews the delivery snapshot with adversarial, numerical, and JoSIM evidence rules. It must try to falsify: shared production-oracle tests; raw-rad/turn confusion; a test that only exercises synthetic data; non-direct JTL voltage mapping; incorrect P/V orientation or window endpoints; fixed-dt assumptions; periodic regression miscalled a one-input physical event; stale historical files; and any claim beyond CALIBRATION.

Codex will independently read raw inputs and recompute selected M7B/M7C quantities before any M7 status update.

## Stop conditions

Stop and record `BLOCKED` rather than guessing if:

- observed HEAD differs from the execution baseline, the worktree is unexpectedly dirty, frozen-input hashes differ, or an allowed-path conflict exists;
- the canonical JTL input cannot produce direct same-JJ `V(B...)`/`P(B...)` columns, contains solver/data QA errors, or requires a source/model/netlist change outside the two allowed new files;
- a required expected value needs to be obtained from the production analyzer rather than direct independent arithmetic;
- completion requires changing `scripts/sfq_metrics_v2.py`, existing tests, historical data, task semantics, numerical tolerance, or a task path outside the allowed list;
- execution would turn periodic BQ data, activity clusters, a local phase turn, or a residual into an SFQ/JTL/system/route conclusion.

After two attempts blocked by the same root cause, stop and escalate to Codex/User.

## Claim ceiling

M7A/M7B/M7C calibration implementation and deterministic regression behavior only. This task establishes no physical event count, local SFQ, downstream reception, closed-loop fluxoid, BVM/BQ/DCSFQ route result, metric tolerance, convergence result, interface Gate, candidate verdict, or paper claim. LITE evidence cannot be promoted retrospectively to FROZEN evidence.

## Explicit remainder

M8 owns pre-registered timestep convergence; M9 owns the frozen `METRIC_SPEC_V2`; M10 owns regenerated metrics/audit tables; M11A/M11B own measurement/scientific baseline closure. This task does not initiate Batch P0, W5, source/receiver characterization, candidate tuning, or external contact.
