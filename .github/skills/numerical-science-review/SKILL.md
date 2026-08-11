---
name: numerical-science-review
description: Review numerical calculations, thresholds, integration, units, windows, tolerances, precision, sensitivity, and numerical stability. Use for metrics, scientific data processing, simulation outputs, or any numerical claim.
---

# Numerical Science Review

Numerically plausible is not the same as numerically correct.

## 1. Units and dimensions

Track units through:

```text
input
→ transformation
→ integration/differentiation
→ normalization
→ reported metric
```

Check:

- conversion factors;
- seconds vs ps/ns;
- volts vs mV/uV;
- radians vs cycles;
- normalized vs physical quantity.

## 2. Sign/reference convention

Check whether sign has physical/semantic meaning.

Watch for code that uses:

```text
abs(...)
```

and thereby hides a reversed orientation.

## 3. Window semantics

Verify:

- inclusive/exclusive endpoints;
- start/end sample;
- transient exclusion;
- event centered near boundary;
- pre/post padding;
- window relative to trigger vs absolute time.

Probe just-inside / just-outside boundaries when useful.

## 4. Integration/differentiation

Check:

- sampling interval;
- nonuniform spacing;
- trapezoid vs simple sum;
- index alignment;
- derivative noise;
- endpoint handling.

Prefer an independent calculation for one representative case.

## 5. Threshold/tolerance

Ask:

- why this threshold?
- how close are cases to it?
- does a small perturbation change classification?
- is tolerance masking a bug?

For CRITICAL claims near a threshold, perform a sensitivity check.

## 6. Precision/pathologies

Look for:

- NaN/Inf;
- overflow/underflow;
- division by near-zero;
- cancellation;
- integer truncation;
- dtype conversion;
- rounding before classification.

## 7. Sensitivity

Where relevant, vary one high-risk parameter slightly:

```text
window
threshold
timestep
tolerance
```

A robust conclusion should not flip under an unjustified microscopic change.

Do not demand insensitivity when the TASK explicitly studies a real boundary.

## 8. Independent route

For critical values, avoid validating with the exact same production helper.

Use:

- direct formula;
- short independent calculation;
- raw-data inspection;
- alternative trusted implementation.

## Output

Report exact discrepancy and whether it changes classification or only precision.

## Canonical source

This is a **wrapper**. The authoritative rules live in:

```text
.agents/skills/reviewer-numerical/SKILL.md
```

and the experiment-run discipline in:

```text
.agents/skills/josim-experiment/
```

Read the canonical files before applying this skill. Do not restate or
re-derive numerical rules here; follow the canonical versions. If a rule is
ambiguous, flag it in REVIEW.md rather than inventing a parallel rule.
