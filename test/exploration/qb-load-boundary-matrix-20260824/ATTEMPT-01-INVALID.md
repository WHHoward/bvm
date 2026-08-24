# Attempt 01 artifact disposition

The first generated batch is preserved under `inputs/`, `raw/`, and `logs/`.
It is excluded from all scientific metrics and verdicts.

When the 10 Ω output element was removed from A, B, D, and E, the parent
`.print` list still requested `I(R_LOAD)`. JoSIM exited with code 0 but wrote
the following invalid-probe diagnostic to the corresponding stderr files:

```text
W: Controls
Request for current of R_LOAD is invalid.
Cannot find device or cannot store current of a node.
```

This is an artifact-validity failure, not a physical result. C retained the
10 Ω element and did not show this diagnostic, but it was rerun in the matched
v2 batch so that all five fixtures share the same execution provenance.

The corrected independent batch is under `inputs-v2/`, `raw-v2/`, and
`logs-v2/`; only that batch is used by `analysis/analyze_matrix.py`.
