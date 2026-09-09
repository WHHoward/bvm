# BJS400 ARRAY population + matched SINGLE functional experiment — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Frozen authority

- Physical/stimulus authority: test/exploration/qb-l1-ibias-rj1-independent-characterization-v1-20260909
- Mask bit-order and flat visualization style reference only: test/exploration/bvmsim-4bvm-paperlike-common-sl-accumulation-isolation-v1-20260904
- Preflight HEAD: dfb0e2cf4d3dbcf261e49e0854b8ce35f77939d9
- Preregistration/base HEAD: dfb0e2cf4d3dbcf261e49e0854b8ce35f77939d9
- Solver: build/josim-cli; SHA-256 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2
- Solver version: JoSIM: Josephson Junction Superconductive SPICE Circuit Simulator
Copyright (C) 2020 by Johannes Delport (jdelport@sun.ac.za)
v2.7.2837d13 compiled on May 30 2026 at 20:37:57

The 20260904 experiment is not used for physical topology, source or stimulus.

## Registered physical change

- Experiment-local BQ copy changes exactly BJs 1 2 jjmit area=3 to area=4.
- The local jjmit model has icrit=100uA; the registered BJS current is therefore 400uA.
- All other BQ, BVM, JSL, JTL, termination, solver, timestep and stop-time values are frozen.

## Frozen history

Every ARRAY and SINGLE run uses:

WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 -> SETTLE -> mask-selective FINAL READ -> TAIL

- 0–50ps idle; WRITE0 50–61ps; idle 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps.
- idle 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps.
- FINAL READ 110–121ps; TAIL 121–200ps; .tran 0.1p 200p.
- ARRAY bit order is b3b2b1b0 = BVM1/BVM2/BVM3/BVM4.
- Authorized masks only: 0000, 1000, 0001, 0011.
- SINGLE_0 final controls are WL=BL=SE=0; SINGLE_1 is WL=SE=+100uA and BL=0.

## Exact matrix

- ARRAY: 16 runs = 4 working points × 4 masks.
- SINGLE: 8 runs = 4 working points × 2 final-read controls.
- Total authorized physical solves: 24.
- No combination intervention, extra mask, extra parameter, retry, tuning or follow-up is authorized.

## Preflight checks

- BJS400 source diff: PASS (exactly one active line changed).
- All ARRAY cases are identical before 110ps except registered working-point parameters.
- All SINGLE cases are identical before 110ps except registered working-point parameters.
- Full raw probe declarations include mandatory P/V/I(BJS), JTL current probes and all requested boundaries.
- Raw is not yet present; execution has not started.

## Interpretation ceiling

scientific_interpretation = NOT_PERFORMED; this directory records evidence only.
No SFQ/event count, mechanism, ranking, equivalence, Gate or next-experiment claim is authorized.
