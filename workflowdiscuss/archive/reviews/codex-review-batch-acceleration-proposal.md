---
title: Codex review — WORKFLOW-lite 2.0 Batch Execution / Delegated Closure
document_type: discussion_review
status: CONDITIONAL_SUPPORT
date: 2026-08-11
reviews: workflowdiscuss/archive/proposals/WORKFLOW-lite-2.0-batch-acceleration-proposal.md
authority: advisory_only
---

# Codex review — Batch Acceleration Proposal

## Decision

**Conditionally support.** The proposal's central direction is sound: move Codex
from high-frequency task tracking to batch boundaries, exceptions, and scientific
Gates; keep Claude and Copilot responsible for iterative implementation and
evidence review. This can reduce coordination cost without reducing scrutiny of
scientific decisions.

The proposal must add the safeguards below before it changes the active protocol
or authorizes a research batch.

## What should be adopted

1. A bounded **Batch Contract** rather than a new Codex intervention for every
   low-risk implementation iteration.
2. The separation of **PRE-REVIEW** (internal defect-finding) from **FORMAL
   REVIEW** (review of a fixed delivery snapshot).
3. `SUBTASK_READY` as an internal execution state, not as an acceptance or a
   scientific conclusion.
4. Explicit escalation triggers for metric semantics, scope, evidence mode,
   raw-evidence conflict, convergence, repeated failure, and scientific claims.
5. The continued separation of mailbox notifications from formal facts.

## Required safeguards

### 1. Make a Batch Contract auditable

Each batch needs an immutable `BATCH.md` plus an append-only
`BATCH-MANIFEST.md`. The manifest must index every subtask and attempt, including
its input snapshot, allowed paths, lock, unique raw-run prefix, parameter
envelope, dependency, pre-review state, delivery snapshot, and escalation.

Codex should not need to read every failed log in full, but the final audit must
be able to discover every failed or superseded attempt. “Never send an unstable
attempt to Codex” must not become “hide failed evidence from Codex.”

### 2. Bound the free inner loop

Claude and Copilot may repair implementation, add tests, and repeat an already
pre-registered run. They may not silently change a scientific input. A new batch
revision or Codex escalation is required for any change to topology, stimulus,
control, window, direction, unit, threshold, tolerance, parameter range, or
interpretation target.

For FROZEN work, raw evidence generated after a semantic change is a new attempt
with a new immutable run ID; it is not merely an internal rework.

### 3. Preserve review independence

The same Copilot reviewer may do PRE-REVIEW and then a final continuity check,
but that formal review is not fully independent because the reviewer influenced
the candidate. Label it `continuity review`.

For `CRITICAL + FROZEN`, require either a fresh-context independent reviewer pass
or an explicitly independent Codex raw-evidence recomputation. All review modes
and prior reviewer involvement must be disclosed in the formal review.

### 4. Do not use a LITE M8 result as frozen scientific evidence

The proposed combined `M7 + M8 = CRITICAL + LITE` batch is unsafe if its timestep
results are later used to set M9 tolerances or support a physical conclusion.
LITE evidence cannot be promoted retrospectively to FROZEN evidence.

Recommended structure:

```text
B1: M7 regression implementation and pre-review       CRITICAL + LITE
B2: M8 convergence evidence used by M9                 CRITICAL + FROZEN
M9: metric freeze                                      CRITICAL + FROZEN
```

Alternatively, make the whole M7/M8 batch FROZEN before its decisive raw runs
begin. The choice is a planning trade-off, not an opportunity to lower M8 risk.

### 5. Define the meaning and limits of SUBTASK_READY

`SUBTASK_READY` means only that Claude and Copilot judge the subtask complete
inside the current contract: its local acceptance checks pass, no Major/Critical
finding remains, and no escalation trigger fired. It is not `ACCEPTED`, not a
physical PASS, and not authority to update todo/HANDOVER or become a formal
scientific dependency outside the batch.

Only Codex may issue `BATCH_ACCEPTED`; only the user adopts route, metric-freeze,
physical-Gate, and paper-level decisions.

### 6. Keep M9 and M11 as distinct scientific checkpoints

M9 must be accepted before M11 relies on frozen metric semantics. They may be
considered in one Codex session, but the records and decisions must remain
separate.

M10 must not be deferred by default. First produce a consumer/dependency map:
if M11's new baseline needs regenerated BASELINE/P0/P2/v4 metric outputs, M10 is
evidence production for M11 rather than archive hygiene.

### 7. Restrict Standing Authorization to the correct project phase

The proposed Route C/D exploration envelope is useful only after Phase −1
M4–M11 is complete. The current master todo explicitly makes Q1–Q6 and D1–D6
depend on M4–M11. `exploration_only` does not bypass that dependency.

W5 literature exploration can proceed independently, but it may not make a
novelty or paper-level claim before a later high-confidence review.

### 8. Define a complete Delivery Snapshot

The snapshot must either contain, or content-addressedly reference, the TASK/
Batch contract, netlist snapshots, include/model closure, raw CSV, command logs,
analysis-script version, test logs, reviewer report, and all required hashes.
Neither Copilot nor Codex should review a moving worktree.

## Recommended protocol addition

Add one narrow `Batch Execution / Delegated Closure` chapter to WORKFLOW-lite
2.0 rather than rewriting Lite or josim-handoff/v1. It should define:

1. Batch Contract and manifest;
2. subtask state machine and append-only attempt index;
3. the exact boundary of internal rework;
4. PRE-REVIEW versus continuity/independent FORMAL REVIEW;
5. snapshot contents and provenance requirements;
6. escalation triggers and waiver recording;
7. the rule that FROZEN evidence is pre-registered and never retroactively
   promoted from LITE.

## Answer to the proposal's central question

Codex should become a **batch architect, exception resolver, and scientific-Gate
auditor**, not a bottleneck for routine repair cycles. The reduction in Codex
touchpoints is acceptable only when the batch preserves a complete append-only
history and prevents internal iterations from quietly changing scientific
semantics.

This review changes no active protocol and grants no task authorization.
