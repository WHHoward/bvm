# M9-004 final guard boundary

Keep all predecessor artifacts immutable.  Parse YAML-like claim keys after
leading whitespace, case-fold their names, and reject candidate/read1/read0/
route/gate/success-criterion assertions regardless of case.  Add both valid
and poisoned tests for `  candidate: PASS`, `  read1: 1`, `  route: BQ`,
`  gate: success`, and `Gate: PASS`.  Do not add any actual Gate semantics.
