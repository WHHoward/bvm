# CODEX AUDIT M7-LITE-001 / A02

Audit disposition: **ACCEPTED**

Artifact status: **VALID**
Physical verdict: **NOT_APPLICABLE**
Claim ceiling: calibration implementation and deterministic regression behavior only.

## Bound delivery reviewed

- Task: `research/tasks/M7-LITE-001/TASK.md` at `a27750bc026ca0b9afc9d3d02464008630fdc9df`.
- A01 delivery evidence snapshot: `936df75af73ddaa1625e29dd65411ee50efa11b9`.
- A02 evidence-closure snapshot: `f2e20ea0b2ba92b9fa4634dba29a2778833124c1`.
- Copilot A02 independent review: `attempts/A02/REVIEW.md`, `PASS / AUDIT_READY`.

## Independent Codex checks

1. Re-ran all M4/M5/M6/M7 test files in the delivery worktree: **83/83 passed**.
2. Read the A01 canonical-JTL raw CSV directly. On the predeclared half-open actual-time window `[6e-12, 50e-12)`, selected indices are 60 through 498 (439 samples). Independent elementary trapezoid arithmetic gave:

   | JJ | phase turns | area turns | signed residual turns |
   |---|---:|---:|---:|
   | `B1|XDUT` | `1.014708971373932` | `1.0148502468834475` | `-1.4127550951559265e-4` |
   | `B2|XDUT` | `1.0093368076783251` | `1.007923877022203` | `+1.4129306561221355e-3` |

   These agree with A02's independent analysis. They are reported measurement-pipeline residuals only; M9 has not frozen an acceptance tolerance.
3. Recomputed M7C from preserved raw CSVs: DCSFQ control-corrected turns are B1 `0.9999999829418391`, B2 `1.0000000625193106`, B3 `1.0000000147728276`; the six BQ v4 JTL-B1 periodic phase-platform constants match the task values at the specified actual-time samples.
4. Confirmed the canonical JTL run uses direct same-JJ `V(B1|XDUT)`/`P(B1|XDUT)` and `V(B2|XDUT)`/`P(B2|XDUT)`, retains the source JTL input/load/transient setup, and does not turn the result into a JTL event or Gate claim.
5. Confirmed A02 only adds attempt-local evidence; A01 raw is still SHA-256 `728c112ec18864a9f84a0f73e3ffedf39051b528c8e3785b5632f409190cda52`. A02's analysis and complete scope evidence now satisfy the A01 rework requirements.

## Disposition rationale

M7A validates the specified mathematical and input-validation behavior. M7B validates agreement between independent raw arithmetic and the measurement pipeline on one canonical JTL transient, with direct same-JJ probes. M7C locks selected historical arithmetic against independent constants without treating either historical trace as physical ground truth. Together these meet M7's CALIBRATION completion criteria.

The self-reported SHA-256 inside `A02/logs/scope-check.log` is stale, but the authoritative `RESULT.md → scope-check.log` hash binding is correct and the log is committed in the reviewed snapshot. This is a non-blocking documentation-generator defect, not a failure of the delivered M7 evidence. Do not copy this self-hashing pattern into later evidence tooling.

## Explicit non-conclusions

This acceptance does **not** establish a local SFQ, downstream reception, fluxoid count, BQ/DCSFQ/BVM route result, numerical tolerance, timestep convergence, `METRIC_SPEC_V2`, interface Gate, candidate verdict, or paper claim. M8–M11 remain pending.

## Next state

M7 may be marked complete in the project task authority. Per the user's instruction, do not issue M8 or any new task until the user explicitly requests task issuance.
