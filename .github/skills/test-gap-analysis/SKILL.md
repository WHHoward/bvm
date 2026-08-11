---
name: test-gap-analysis
description: Detect weak test oracles, missing negative/boundary cases, unexecuted branches, overfitted fixtures, flaky assumptions, and tests that can pass for the wrong reason. Use whenever tests are part of the acceptance evidence.
---

# Test Gap Analysis

The question is not:

```text
How many tests passed?
```

It is:

```text
Could the wrong implementation also pass these tests?
```

## 1. Oracle quality

Inspect whether assertions validate semantics.

Weak patterns:

- only exit code;
- only file existence;
- only non-empty output;
- broad exception suppression;
- snapshot regenerated from implementation;
- comparison to a value produced by the same helper;
- assertions too loose to distinguish wrong behavior.

## 2. Mutation thought experiments

Mentally substitute simple wrong implementations:

```text
return 0
return constant
return input unchanged
flip sign
off-by-one index
ignore last sample
use wrong window
use absolute value
```

Would tests fail?

If not, identify the missing test.

You do not need to modify source code to perform this reasoning.

## 3. Case coverage

Look for:

- positive case;
- negative/control case;
- boundary;
- empty/zero;
- sign;
- minimum/maximum;
- threshold edge;
- malformed input when relevant;
- multiple representative parameter values.

## 4. Branch/path coverage

Confirm the acceptance test actually reaches changed behavior.

Use code inspection, targeted commands, or existing coverage tooling if already available and non-destructive.

Do not install new coverage systems by default.

## 5. Tolerance quality

For numerical assertions:

- is tolerance justified?
- could a materially wrong value pass?
- is relative vs absolute tolerance appropriate?
- are NaN/Inf handled?

## 6. Flakiness/hidden state

Look for:

- random seeds;
- order dependence;
- shared fixtures;
- timing;
- filesystem state;
- cache;
- parallelism;
- environment variables.

## Output

Classify gaps as:

```text
material gap
nice-to-have gap
not relevant
```

A missing test is REWORK only when it materially weakens the TASK's acceptance claim.
