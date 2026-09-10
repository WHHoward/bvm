# RJ1 switched-regime characterization under D working point — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Authority

- Physical/stimulus authority: test/exploration/qb-l1-ibias-interaction-bjs400-v1-20260909
- Preflight HEAD: 015aff4b4663a0933dece4e265cd925760254fac
- Fixed point: L1=1.6pH, IBias=260uA, BJS area=4, BJS Ic=400uA.
- RJ1 values: new 10/14/16ohm; 12ohm reused by hash.
- Masks: 0001 and 0011 only; no older no-history stimulus.

## Frozen history

WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL

- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps.
- ZERO_STATE_READ_CONTROL 70–81ps; idle 81–90ps.
- WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.
- WL/BL/SE amplitude 100uA, 1ps edges, 9ps plateau, .tran 0.1p 200p.

## Exact matrix

- New physical solves: exactly 6.
- Reused historical cases: ARRAY_L1P16_IB260_0001 and ARRAY_L1P16_IB260_0011.
- No extra RJ1 value, mask, SINGLE run, retry, tuning or follow-up.

## Preflight results

- B reuse comparability: PASS.
- New deck diff: PASS.
- Mandatory BJS P/V/I and all JTL current probes are registered.
- Raw execution has not started at preflight.

Scientific interpretation is NOT_PERFORMED.
