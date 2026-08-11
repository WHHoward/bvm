---
name: reproducibility-review
description: Detect results that depend on hidden environment, cache, working directory, randomness, ordering, mutable state, or non-repeatable execution. Use when a task's correctness may depend on execution state.
---

# Reproducibility Review

The goal is not to recreate the entire machine.
The goal is to detect whether the claim depends on hidden state.

## Check selectively

### Working directory
Does behavior change based on where the command is launched?

### Config discovery
Are defaults loaded from implicit files?

### Environment variables
Could an unset/set variable change behavior?

### Cache
Could output come from prior execution?

### Randomness
Are seeds controlled when needed?

### Ordering
Do tests depend on execution order or filesystem ordering?

### Parallelism
Could race conditions or nondeterministic reductions matter?

### Global state
Does one test or script mutate state consumed by another?

### Dependency/version assumption
Is a critical API or numerical behavior version-sensitive?

Do not install packages or change lock files merely to review.

## Practical probes

When low-cost:

- rerun the critical command;
- run a focused test twice;
- run an isolated test before/after another test;
- inspect cache/config paths;
- compare outputs or critical metrics.

## Output

State whether reproducibility is:

```text
supported
partially supported
not established
contradicted
```

and identify the hidden-state risk if present.
