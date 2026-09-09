# Minimal L1 x IBias interaction under BJS400 — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Authority

- Physical/stimulus authority: test/exploration/qb-bjs400-array-population-single-matched-v1-20260909
- Preflight HEAD: e72b4f568a1d49100b5e4fefa60bee8955bb0db8
- BJS400 source: inputs/BQ_parameterized_bjs400.cir; area=4; Ic=400uA.
- The older no-history stimulus is not used.
- B reuse is historical immutable evidence, not a new solve.

## Exact matrix

- A: L1=2.0pH, IB=250uA; two new masks 0001 and 0011.
- B: L1=2.0pH, IB=260uA; reuse ARRAY_IB260_0001 and ARRAY_IB260_0011.
- C: L1=1.6pH, IB=250uA; two new masks 0001 and 0011.
- D: L1=1.6pH, IB=260uA; two new masks 0001 and 0011.
- New physical solves: exactly 6. Reused physical cases: exactly 2.
- No other masks, SINGLE runs, parameters, timestep sweep, retry or follow-up.

## Frozen history and controls

WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL

- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps.
- ZERO_STATE_READ_CONTROL 70–81ps; idle 81–90ps.
- WRITE1 90–101ps; SETTLE 101–110ps; FINAL READ 110–121ps; TAIL 121–200ps.
- WL/BL/SE amplitude 100uA, 1ps edges, 9ps plateau, .tran 0.1p 200p.
- ARRAY masks: 0001 activates BVM4; 0011 activates BVM3 and BVM4.

## Preflight results

- B reuse comparability: PASS.
- New deck diff: PASS.
- Required BJS P/V/I and JTL current probes are registered.
- Raw execution has not started at preflight.

Scientific interpretation is NOT_PERFORMED.
