# Physical run preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

This PRE-FLIGHT is generated from frozen USER_CASE/STIMULUS snapshots. The exact
run is the single mask below; no other mask, sweep, or follow-up is authorized.

- run_id: `A028_T008_M11`
- parent HEAD: `e3c9df32c822e5cd43c7e4339eec7997a2927ae8`
- solver path: `/home/howard/JoSIM/build/josim-cli`
- solver SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- solver version: `JoSIM: Josephson Junction Superconductive SPICE Circuit Simulator
Copyright (C) 2020 by Johannes Delport (jdelport@sun.ac.za)
v2.7.2837d13 compiled on May 30 2026 at 20:37:57`
- ARRAY_SIZE: `2`
- probe profile: `core` (75 probes)
- FINAL READ MASK: `11` (leftmost bit is BVM1)
- topology: `{"POST_SJTL_CB": [1, 1], "QB_CB": [0, 0], "SJTL_COUNT": [1, 0]}`
- DT: `0.01p`; STOP: `200p`
- run matrix: exactly `A028_T008_M11` / mask `11`
- expected raw: `runs/A028_T008_M11/raw.csv`
- interpretation ceiling: mechanical QA and requested descriptive plots only
- follow-up solves, sweeps, T1, repeated-read, and rewrite-read: prohibited

## Source snapshots

- `circuits/bvm/bvm_cell_0923.cir` (ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7) → `snapshot/sources/bvm_tunable.cir` SHA-256 `ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7`
- `circuits/qb/BQ_0923.cir` (76a8b5acf5fb23c29f338e6b71ac69e2dae261f2b0b6d1f103b653a4ad6f92d2) → `snapshot/sources/BQ_tunable.cir` SHA-256 `d1be702c8277068c91dfd69f86a72a4ebc83c1cea8a4a6c9e3becbf35900b6e4`
- `circuits/CB/CB_0923.cir` (f2dd43a5177cbecc0abcc1125a7479659e21a8cbe46b88cabcb790e1036b4216) → `snapshot/sources/CB_tunable.cir` SHA-256 `c542e2437967ee5fbfd801fe77947518ea54e0d1ce4da8313263b7b4799dc375`
- `circuits/sJTL_0923.cir` (3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688) → `snapshot/sources/sJTL_tunable.cir` SHA-256 `3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688`

## Registered probes

- `I(I_WL1)`
- `I(I_BL1)`
- `I(I_SE1)`
- `P(B_JM1|XBVM1)`
- `V(B_JM1|XBVM1)`
- `P(B_JM2|XBVM1)`
- `V(B_JM2|XBVM1)`
- `P(B_JS1|XBVM1)`
- `V(B_JS1|XBVM1)`
- `P(B_JS2|XBVM1)`
- `V(B_JS2|XBVM1)`
- `I(L_M1|XBVM1)`
- `I(L_M2|XBVM1)`
- `I(L_M3|XBVM1)`
- `I(L_PM|XBVM1)`
- `I(L_SL|XBVM1)`
- `V(BVM1_SL)`
- `P(BJ1|XBQ1)`
- `V(BJ1|XBQ1)`
- `P(BJ2|XBQ1)`
- `V(BJ2|XBQ1)`
- `P(BJ3|XBQ1)`
- `V(BJ3|XBQ1)`
- `I(LIN|XBQ1)`
- `I(L1|XBQ1)`
- `I(L2|XBQ1)`
- `I(L3|XBQ1)`
- `V(MERGE1)`
- `I(I_WL2)`
- `I(I_BL2)`
- `I(I_SE2)`
- `P(B_JM1|XBVM2)`
- `V(B_JM1|XBVM2)`
- `P(B_JM2|XBVM2)`
- `V(B_JM2|XBVM2)`
- `P(B_JS1|XBVM2)`
- `V(B_JS1|XBVM2)`
- `P(B_JS2|XBVM2)`
- `V(B_JS2|XBVM2)`
- `I(L_M1|XBVM2)`
- `I(L_M2|XBVM2)`
- `I(L_M3|XBVM2)`
- `I(L_PM|XBVM2)`
- `I(L_SL|XBVM2)`
- `V(BVM2_SL)`
- `P(BJ1|XBQ2)`
- `V(BJ1|XBQ2)`
- `P(BJ2|XBQ2)`
- `V(BJ2|XBQ2)`
- `P(BJ3|XBQ2)`
- `V(BJ3|XBQ2)`
- `I(LIN|XBQ2)`
- `I(L1|XBQ2)`
- `I(L2|XBQ2)`
- `I(L3|XBQ2)`
- `V(MERGE2)`
- `P(BJ1|XPOSTCB1)`
- `V(BJ1|XPOSTCB1)`
- `P(BJ2|XPOSTCB1)`
- `V(BJ2|XPOSTCB1)`
- `I(L1|XPOSTCB1)`
- `I(L4|XPOSTCB1)`
- `V(L1_01)`
- `P(BJ1|XSJTL1_01)`
- `V(BJ1|XSJTL1_01)`
- `I(L1|XSJTL1_01)`
- `I(L2|XSJTL1_01)`
- `P(BJ1|XPOSTCB2)`
- `V(BJ1|XPOSTCB2)`
- `P(BJ2|XPOSTCB2)`
- `V(BJ2|XPOSTCB2)`
- `I(L1|XPOSTCB2)`
- `I(L4|XPOSTCB2)`
- `V(FINAL_OUT)`
- `I(R_TERM)`

## Required output artifacts

`actual_deck.cir`, `stimulus.inc`, `topology_manifest.json`, `source_manifest.json`,
`probe_manifest.json`, `parameter_manifest.json`, `raw.csv`, stdout/stderr, mechanical raw QA/metrics, and
the five requested plot pages. A failed attempt remains in this run directory.
