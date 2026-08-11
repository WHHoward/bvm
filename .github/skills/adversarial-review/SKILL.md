---
name: adversarial-review
description: Hunt for subtle failures that can make an implementation or result look correct while being wrong. Use for any nontrivial review, especially when tests pass suspiciously easily or the result supports an important claim.
---

# Adversarial Review

Use this skill to search for **plausible hidden failure modes**, not to invent arbitrary doubts.

## Method

1. Identify the executor's strongest bounded claim.
2. Ask what bug could make that claim appear true.
3. Generate 3–5 hypotheses for NORMAL work, 5–10 for CRITICAL work.
4. Rank by:
   - impact;
   - plausibility;
   - ease of testing.
5. Test the highest-value hypotheses.
6. Stop when the remaining hypotheses are low-value or already covered.

## High-value hidden-error patterns

### No-op implementation
Would the tests pass if the changed function did nothing?

### Constant output
Could the implementation return a fixed value and still pass?

### Wrong branch
Is the edited code path actually executed by the reported verification?

### Wrong file/module
Could tests import a different implementation than the edited file?

### Tautological oracle
Does the expected value come from the same function/helper being tested?

### Stale output
Could RESULT reference an artifact generated before the current implementation?

### Happy-path-only
Would a nearby boundary, zero, negative, empty, or failure case expose the bug?

### Hidden state
Could cache, environment, ordering, randomness, or previous execution make the test pass?

### Silent fallback
Could an error path fall back to a default value while still exiting successfully?

### Partial success presented as full success
Did only one node/window/case pass while RESULT generalizes to all cases?

## Counterfactual questions

Ask:

```text
If this implementation were wrong in the simplest plausible way, what would I expect to observe?
```

Then look for that observation.

Examples:

```text
wrong sign → compare signed quantity, not absolute value
wrong unit → check dimensional magnitude and conversion
stale artifact → regenerate or inspect provenance
unused branch → instrument through targeted test or inspect call path
threshold bug → test just below / at / above threshold
```

## Output

Report only material findings and the most informative probes.

Do not dump the full hypothesis brainstorm into REVIEW.md unless it is useful.

## Canonical source

This is a **wrapper**. The authoritative rules live in:

```text
.agents/skills/reviewer-adversarial/SKILL.md
```

Read the canonical file before applying this skill. Do not restate or
re-derive the probe taxonomy here; follow the canonical version. If the
canonical rule is ambiguous, flag it in REVIEW.md rather than inventing a
parallel rule.
