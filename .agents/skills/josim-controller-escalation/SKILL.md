---
name: josim-controller-escalation
description: Controller governance skill — decide whether the root controller may continue or must escalate/block. Use when the root controller is unsure whether to proceed, or when state/evidence/route ambiguity appears. Codex controller governance only; not a Claude executor skill.
---

# josim-controller-escalation

Small governance skill for the Codex root controller (Luna Max).  When the
root controller is unsure whether it may continue, run this check before
proceeding.  Do NOT copy HANDOVER or WORKFLOW content here; this is a
decision procedure only.

## Inputs (read as needed)

- `AGENTS.md`
- `docs/HANDOVER.md`
- `memory/project-todo.md`
- the active request
- the latest receipt
- the latest accepted audit

## Checks

- A. Is this only routine orchestration?
- B. Is there an evidence conflict?
- C. Is there a state conflict (HANDOVER / todo / request / receipt / audit)?
- D. Would this change the scientific route?
- E. Would this change the claim level?
- F. Does this touch a frozen metric?
- G. Does this require expanding contract scope?
- H. Does this require a final audit?

## Output

One of:

- `CONTINUE_LUNA`
- `ESCALATE_TERRA_MEDIUM` (state / context / orchestration ambiguity)
- `ESCALATE_TERRA_HIGH` (engineering / debugging / conflicting execution evidence)
- `ESCALATE_SOL` (route / metric / physics / contract / final audit)
- `BLOCK`

with:

- `reason`
- `evidence paths`
- `unresolved unknowns`

Never produce a physics verdict.
