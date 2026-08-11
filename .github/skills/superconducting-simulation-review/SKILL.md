---
name: superconducting-simulation-review
description: Specialized evidence review for JoSIM, Josephson junction, SFQ/JTL, phase, voltage-area, event/activity, propagation, and superconducting-circuit simulation tasks. Use when these concepts appear in TASK, RESULT, code, or evidence. This is a WRAPPER: physics rules live in .agents/skills/josim-evidence-audit.
---

# Superconducting Simulation Review (wrapper)

> **Wrapper, not a rule source.** All physics rules (phase units, voltage-area
> consistency, activity vs event, local vs downstream, windows/controls,
> claim strength) are defined **once** in the canonical source:

```text
.agents/skills/josim-evidence-audit/SKILL.md
.agents/skills/josim-evidence-audit/references/phase-evidence-contract.md
```

## When to trigger

Use when the TASK/RESULT/code/evidence involves any of:

- JoSIM phase `P(...)` columns, raw rad, `Δφ/(2π)` turns;
- voltage-time-area cross-checks;
- SFQ / JTL / propagation / reception;
- event vs activity classification;
- event windows, zero-input controls, startup transients;
- timestep / solver sensitivity;
- any physical claim under review.

## What to do

1. **Read the canonical rules first** (both files above). Follow them exactly;
   do not restate or re-derive physics formulas here.
2. Check that the executor's claims and the evidence obey the canonical
   rules — especially:
   - raw rad preserved and turns derived as `Δφ/(2π)`;
   - same-junction / same-endpoint / same-direction / same-window discipline
     for any phase–area cross-check;
   - activity samples/intervals never named as events or SFQ counts;
   - local junction turns never upgraded to downstream reception or
     closed-loop fluxoid counts;
   - zero-input control and event windows present where the claim requires;
   - claim strength within the canonical PASS/FAIL/INCONCLUSIVE discipline.
3. If the canonical rule is ambiguous or missing for the task, **flag it in
   REVIEW.md** — do not invent a parallel rule.
4. Report findings per the REVIEW.md format; `Codex focus` should name the
   specific canonical sections the auditor should re-check.

## Boundaries

- No final physical verdict; no metric freeze; no paper-level claims.
- Read-only during review; write only the attempt-local REVIEW.md.
