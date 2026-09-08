# Preserved preflight utility failure

This is a preserved non-physics preflight attempt. It returned FAIL because
the first version of the checker compared unnormalized Decimal interval
strings and multiplied the tail adjacent step by 1e6 twice. No deck or
JoSIM solve was started from this attempt. The corrected PASS record is at
analysis/preflight.json and the final gate is at analysis/pre_solve_gate.json.
