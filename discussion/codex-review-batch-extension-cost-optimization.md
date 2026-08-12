---
title: Codex review — WORKFLOW-lite 2.0 Batch Extension and Cost Optimization
document_type: discussion_review
status: CONDITIONAL_SUPPORT
date: 2026-08-11
reviews: workflowdiscuss/WORKFLOW-lite-2.0-batch-extension-and-cost-optimization.md
authority: advisory_only
---

# Codex review — Batch Extension and Cost Optimization

## Decision

**Conditionally support.** Part I is now a suitable basis for the formal Batch
Extension draft. Part II contains several high-value cost optimizations, but they
should be introduced as a tested pilot sequence rather than all at once.

## Strongly supported elements

- `BATCH.md + BATCH-MANIFEST + LEDGER` provide a discoverable fact layer for
  internal rework without requiring Codex to read every failed log.
- `SUBTASK_READY` is explicitly downgraded: it cannot establish a physical
  conclusion, close a todo item, or become authority outside its batch.
- The downstream-contamination rule correctly stops a dependency chain when a
  previously used subtask result is challenged.
- FROZEN semantic changes require a new attempt and immutable run ID.
- `CONTINUITY` versus `FRESH_CONTEXT` review disclosure is accurate.
- The M7/M8/M9 correction is necessary: M7 may be CRITICAL+LITE, but decisive
  M8 convergence evidence used by M9 must be generated FROZEN before the run.
- Route C/D remain blocked until M11, and M10 is not assumed deferrable.

## Required refinements before protocol adoption

### 1. Make fresh-context review initially blind to the Ledger

The formal reviewer should first read the Batch Contract, delivery snapshot,
machine-generated evidence index, and raw evidence, then independently construct
falsification hypotheses. Only afterwards should it compare its work with the
PRE-REVIEW Ledger. Otherwise a fresh context can still inherit earlier framing.

### 2. Use one canonical Semantic Lock per subtask

Create one machine-readable `SEMANTIC-LOCK.yaml` per subtask and let BATCH.md,
LEDGER, and run manifests reference its hash. Do not repeat independently edited
copies of windows, directions, thresholds, controls, or parameter envelopes.

For FROZEN it is immutable. For LITE, a semantic change creates an explicit
revision and new snapshot; it never overwrites the prior lock.

### 3. Build Audit Packet as a narrow, read-only, tested index

An Audit Packet should be mechanically generated from the fixed snapshot, Git
metadata, manifest, logs, hashes, RESULT/REVIEW headers, and declared evidence.
It must not rely on an executor-written narrative as its factual source.

A packet mismatch is a provenance or artifact-integrity problem, not a physical
`FAIL`. The underlying raw evidence must always remain directly accessible.

### 4. Pre-register deterministic sampling

If deterministic sampling is used for non-final batch audits, its seed must be
fixed in the signed Batch Contract (for example, from the contract hash), not
derived from the delivery snapshot. A delivery commit can otherwise be perturbed
to influence a commit-hash-derived sample.

Sampling never replaces full critical-evidence review for final physical Gates,
metric freeze, route decisions, or paper-critical claims.

### 5. Give Scientific ADRs a correct authority lifecycle

Use an explicit state model:

```text
PROPOSED → CODEX_AUDITED → USER_ADOPTED → SUPERSEDED
```

An ADR may preserve an audited interpretation, but Codex audit alone must not
freeze a metric, adopt a route, or authorize a paper-level claim.

### 6. Keep Exception-only notification discoverable

Reducing mailbox chatter is desirable, but it must not create silent long-running
work. Keep a machine-readable status surface or scheduled heartbeat. At minimum,
task/batch issuance, `BLOCKED`, `BATCH_READY`, and scientific-Gate readiness must
be discoverable without searching conversational traffic.

### 7. Restrict the “lowest sufficient assurance” principle

Apply it to mechanical work only. A safer formulation is:

> Use the lowest-cost mechanical assurance tier that still satisfies the task's
> predeclared risk and evidence mode.

It must never be used to downgrade CRITICAL/FROZEN raw evidence, convergence
checks, or independent recomputation.

### 8. Adjust P0 implementation order

Start with:

1. Batch fact layer and append-only manifest/ledger;
2. fresh-context formal review;
3. minimal canonical Semantic Lock;
4. Audit Packet format and a read-only prototype.

After one real Batch Pilot proves these fields useful, consider the full
`verify-batch`, Decision Cache, automatic routing, complexity scoring, and other
automation. This preserves the proposal's low-cost goal without prematurely
making unvalidated tooling authoritative.

## Recommended adoption boundary

Adopt Part I as the basis for a narrow Batch Extension chapter. Treat Part II as
a staged implementation backlog. The first pilot should prove that the facts,
locks, snapshot, and fresh review actually reduce context reconstruction while
still allowing Codex to find every relevant failed attempt and audit raw evidence.

This review changes no active protocol and grants no task authorization.
