# Full closed-loop QB parameter screening — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-full-closed-loop-qb-parameter-screening-v1-20260911`
- Initial registration HEAD: `a9a048fd2f48ce727098dfbed14425b84ce77c58`
- Sealed preflight HEAD: `0fd51ae6ab2a56d9024e280ddadf74307105fd32`
- Remote `bvm/master`: `a9a048fd2f48ce727098dfbed14425b84ce77c58`
- Status: **PASS**
- Solver has not been invoked at preflight.

## Exact matrix

The 37 non-baseline one-factor points are each paired with masks `0011` (N2) and `0111` (N3), for 74 logical screening cases. Strictly equivalent RJ2=10/0011 and RJ2=10/0111 raw cases are reused, so the maximum number of new screening solves is 72; logical and physical counts will be reported separately. RJ2=12 baseline 0011/0111 and RJ2=11 context cases are immutable references.

Priority order: `BJ2_area → Lin_pH → L1_pH → L2_pH → RJ1_ohm → IBias_uA → BJ1_area → BJS_area → RJ2_ohm(14,16) → L3_pH`.
Each generated deck retains full BVM/COMMON_SL/JSL/QB/JTL/terminal topology, `.tran 0.1p 200p`, and the stored protocol. Exactly one QB parameter is changed per point; no JTL/BVM/stimulus/timestep change is registered.

## Early stop

A raw-supported `N2=2` and `N3=3` point is `DIRECT_2_TO_3_CANDIDATE` (class S): broad screening stops, then only the registered 0001 and 1111 full-population validation solves may be run. No combinations, positional checks or timestep checks start automatically. If no S point is found, stop with the bounded screening result and at most two promising A directions.

## Evidence ceiling

Raw CSV is authoritative. Phase is stored in radians; `rad/(2*pi)` is display/navigation only. Current threshold activity, voltage area, terminal area and response candidates are not SFQ counts. CONTROL contamination is a guardrail classification, not a parameter winner.

Machine record: `analysis/preflight.json`.
