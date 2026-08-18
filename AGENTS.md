# JoSIM × BVM repository instructions

These rules apply to the whole repository.

## Project context

- For BVM/BQ/DCSFQ/JTL/T1 research, read `docs/HANDOVER.md` before changing experiments or making physical claims.
- Treat `memory/project-todo.md` as the task authority and its completion criteria as binding.
- Use repository-local skills from `.agents/skills/`; choose the smallest skill set that covers the request.

## Measurement invariants

- JoSIM `P(...)` output is raw phase in radians. Convert a declared phase difference with `phase_delta_turns = phase_delta_rad / (2*pi)`.
- A local junction phase turn is not automatically an SFQ received downstream and is not a closed-loop fluxoid count.
- Cross-check phase and voltage area only for the same junction, endpoints, direction, run, and time window.
- Derivative thresholds and over-threshold samples identify activity only; they are not event counts.
- Until Phase −1 M4–M11 are complete, do not use `scripts/sfq_metrics.py`, its old JSON, or `scripts/run_exp.sh` as a physical Gate.
- Separate artifact validity, activity, local junction evidence, loaded downstream reception, and system logic evidence.
- Use `PASS`, `FAIL`, `INCONCLUSIVE`, and artifact `INVALID` distinctly.

## Experiment integrity

- Use the recorded `build/josim-cli`; record its version and binary hash for conclusion-grade runs.
- Preserve raw netlists, include/model provenance, CSVs, controls, logs, directions, windows, and metric-spec version.
- Never overwrite or silently delete raw or failed experiments. Create a new run ID and supersede conclusions explicitly.
- A repeated file hash proves deterministic replay only, not physical correctness or timestep convergence.
- Do not write a simulation result as hardware measurement or a bounded negative result as universal impossibility.

## Read/write boundary

- Status, review, explanation, and diagnosis requests are read-only unless the user also requests changes.
- Do not update every summary file mechanically. Update the lowest evidence layer first and only the higher layers affected by the change.
- Cleanup or deletion requires an explicit, exact target; ordinary project summarization never authorizes deletion.

## Codex–Claude handoff

- Use `research/WORKFLOW.md` and `.agents/skills/josim-handoff/` when Codex delegates implementation or experiment execution to Claude Code.
- `workflowdiscuss/` is a historical design archive, not authority; do not read it by default or infer active requirements from archived proposals/reviews.
- Mailbox operating rule (single canonical copy): `research/mailbox/README.md`. Mailbox is notification/index only — never authority; answer `NO_PENDING_WORK` when no relevant unprocessed message exists, and never start unrequested research from the todo list.
- LITE Scientific Implementation delivery snapshots are executor-created by default (`EXECUTOR`-owned, immutable, attempt-bound, per `research/WORKFLOW-lite.md` §8); FROZEN / Scientific Gate snapshots remain Codex-controlled. Snapshot ownership never confers scientific authority.
- Codex owns SHA-256-sealed task requests and audit verdicts; Claude owns preflight ACKs, in-scope implementation/run artifacts, and execution receipts. The hash seal detects content changes but is not identity authentication. The user retains final approval for route changes, metric freezes, and paper claims.
- An `ISSUED` request is immutable. Claude must ACK before editing, remain inside `scope.write_paths`, and stop when authorization or scope must expand.
- Keep execution, artifact validity, physical verdict, and audit disposition separate. A correctly executed experiment may validly return physical `FAIL`; an invalid artifact is not a physical failure.
- Update `memory/project-todo.md`, `docs/HANDOVER.md`, or paper-level claims only after an accepted audit. If Codex changes core task outputs, record it as co-execution and require another independent review.

## Controller escalation policy (2026-08-18)

A low-cost root controller (Luna XHigh) can handle routine orchestration, but
**model identity is not scientific authority**. Escalate when any of the
following applies:

1. New evidence conflicts with an ACCEPTED historical result
2. HANDOVER / todo / request / receipt / audit statuses contradict each other
3. The current action would change the active scientific route
4. Acceptance criteria or frozen metric semantics need reinterpretation
5. An attempt to upgrade `INCONCLUSIVE` into `PASS` / `FAIL`
6. An attempt to upgrade a bounded observation into a mechanism claim
7. Sealed contract scope needs to expand
8. Major engineering / debugging ambiguity appears
9. A metric freeze is involved
10. Physics interpretation is involved
11. A final audit disposition is involved
12. A paper-level claim is involved

Upgrade routing:

- routine orchestration → Luna root controller
- state / context / orchestration ambiguity → `josim_controller_review` (Terra Medium)
- engineering / debugging / conflicting execution evidence → `josim_reviewer` (Terra High)
- route / metric / physics / contract / final audit → `josim_architect` (Sol XHigh)

The user retains final approval for route changes, metric freezes, and paper claims.
