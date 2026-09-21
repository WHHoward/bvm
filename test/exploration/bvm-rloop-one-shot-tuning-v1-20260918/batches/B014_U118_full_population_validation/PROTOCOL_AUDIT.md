# B014 U118 full-population attempt audit

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

Status: `ARTIFACT_VALID / PROTOCOL_INVALID / SCIENTIFIC_REVIEW_REQUIRED`

The registered B014 rule required:

- `CLOSED_N0_0000`, `CLOSED_N1_0001`, `CLOSED_N2_0011`, and `CLOSED_N3_0111`
  as new physical solves;
- `CLOSED_N4_1111` to be strict-reused from U118;
- no N4 physical solve.

The preserved U119 attempt contains five run directories and reports
`physical_solve_count=5`, including a new `CLOSED_N4_1111/run.log` and
`metadata.json`. Its N4 raw SHA-256 equals the U118 raw SHA-256, but that only
shows deterministic replay; it does not satisfy the registered reuse rule.

No raw, deck, log, or plot is deleted or rewritten. This package is an
evidence package for the protocol-invalid attempt, not acceptance of U118 as a
validated BVM-to-QB interface candidate. Scientific interpretation and Gate
classification were not performed.
