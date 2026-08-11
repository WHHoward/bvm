---
name: semantic-diff-review
description: Review code changes for semantic impact beyond line-by-line diff. Use when changed code may affect callers, data contracts, CLI behavior, units, defaults, state, or downstream scientific analysis.
---

# Semantic Diff Review

Line diffs show **what text changed**.
This skill asks **what behavior changed**.

## 1. Map the changed surface

For each meaningful changed symbol:

```text
changed function/class/config/schema
→ callers
→ consumers
→ tests
→ generated artifacts
→ downstream interpretation
```

Search repository references when needed.

## 2. Check contract changes

Look for silent changes to:

- units;
- default values;
- parameter meaning;
- return type;
- shape/dimension;
- missing-value behavior;
- ordering;
- time/window convention;
- CLI argument interpretation;
- file format/schema;
- sign/reference convention.

A small diff can be a large semantic change.

## 3. Check hidden coupling

Look for:

- global state;
- implicit config discovery;
- module-level caches;
- shared mutable fixtures;
- path-dependent behavior;
- code that assumes a previous filename/schema;
- downstream code that duplicates constants.

## 4. Check execution reachability

Verify the changed code can actually influence the claimed output.

Watch for:

- dead code;
- alternate implementations;
- feature flags;
- early returns;
- test mocks that bypass the changed path;
- stale generated code.

## 5. Check blast radius

If a helper is widely used, sample important callers.

A task may pass its local test but break another semantic contract.

## Output

In REVIEW.md, report:

```text
semantic impact checked
unexpected downstream effects
unverified high-risk consumers
```

Do not list every caller unless needed.
