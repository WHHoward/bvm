# Physical run preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

This PRE-FLIGHT is generated from frozen USER_CASE/STIMULUS snapshots. The exact
run is the single mask below; no other mask, sweep, or follow-up is authorized.

- run_id: `A008_T002_M1`
- parent HEAD: `d0464843b0ce74cfc4ac6210b0172b4d36079e2a`
- solver path: `/home/howard/JoSIM/build/josim-cli`
- solver SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- solver version: `JoSIM: Josephson Junction Superconductive SPICE Circuit Simulator
Copyright (C) 2020 by Johannes Delport (jdelport@sun.ac.za)
v2.7.2837d13 compiled on May 30 2026 at 20:37:57`
- ARRAY_SIZE: `1`
- FINAL READ MASK: `1` (leftmost bit is BVM1)
- topology: `{"POST_SJTL_CB": [0], "QB_CB": [1], "SJTL_COUNT": [3]}`
- DT: `0.01p`; STOP: `200p`
- run matrix: exactly `A008_T002_M1` / mask `1`
- expected raw: `runs/A008_T002_M1/raw.csv`
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
- `I(B_JM1|XBVM1)`
- `P(B_JM2|XBVM1)`
- `V(B_JM2|XBVM1)`
- `I(B_JM2|XBVM1)`
- `P(B_JS1|XBVM1)`
- `V(B_JS1|XBVM1)`
- `I(B_JS1|XBVM1)`
- `P(B_JS2|XBVM1)`
- `V(B_JS2|XBVM1)`
- `I(B_JS2|XBVM1)`
- `I(L_M1|XBVM1)`
- `V(L_M1|XBVM1)`
- `I(L_M2|XBVM1)`
- `V(L_M2|XBVM1)`
- `I(L_M3|XBVM1)`
- `V(L_M3|XBVM1)`
- `I(L_PM|XBVM1)`
- `V(L_PM|XBVM1)`
- `I(L_SL|XBVM1)`
- `V(L_SL|XBVM1)`
- `I(R_SL|XBVM1)`
- `V(R_SL|XBVM1)`
- `V(BVM1_SL)`
- `P(BJ1|XBQ1)`
- `V(BJ1|XBQ1)`
- `I(BJ1|XBQ1)`
- `P(BJ2|XBQ1)`
- `V(BJ2|XBQ1)`
- `I(BJ2|XBQ1)`
- `P(BJ3|XBQ1)`
- `V(BJ3|XBQ1)`
- `I(BJ3|XBQ1)`
- `I(LIN|XBQ1)`
- `V(LIN|XBQ1)`
- `I(L1|XBQ1)`
- `V(L1|XBQ1)`
- `I(L2|XBQ1)`
- `V(L2|XBQ1)`
- `I(L3|XBQ1)`
- `V(L3|XBQ1)`
- `V(QB1_RAW)`
- `P(BJ1|XQBCB1)`
- `V(BJ1|XQBCB1)`
- `I(BJ1|XQBCB1)`
- `P(BJ2|XQBCB1)`
- `V(BJ2|XQBCB1)`
- `I(BJ2|XQBCB1)`
- `I(L1|XQBCB1)`
- `V(L1|XQBCB1)`
- `I(L2|XQBCB1)`
- `V(L2|XQBCB1)`
- `I(L3|XQBCB1)`
- `V(L3|XQBCB1)`
- `I(L4|XQBCB1)`
- `V(L4|XQBCB1)`
- `V(MERGE1)`
- `V(FINAL_OUT)`
- `P(BJ1|XSJTL1_01)`
- `V(BJ1|XSJTL1_01)`
- `I(BJ1|XSJTL1_01)`
- `I(L1|XSJTL1_01)`
- `V(L1|XSJTL1_01)`
- `I(L2|XSJTL1_01)`
- `V(L2|XSJTL1_01)`
- `V(L1_01)`
- `P(BJ1|XSJTL1_02)`
- `V(BJ1|XSJTL1_02)`
- `I(BJ1|XSJTL1_02)`
- `I(L1|XSJTL1_02)`
- `V(L1|XSJTL1_02)`
- `I(L2|XSJTL1_02)`
- `V(L2|XSJTL1_02)`
- `V(L1_02)`
- `P(BJ1|XSJTL1_03)`
- `V(BJ1|XSJTL1_03)`
- `I(BJ1|XSJTL1_03)`
- `I(L1|XSJTL1_03)`
- `V(L1|XSJTL1_03)`
- `I(L2|XSJTL1_03)`
- `V(L2|XSJTL1_03)`
- `V(R_TERM)`
- `I(R_TERM)`

## Required output artifacts

`actual_deck.cir`, `stimulus.inc`, `topology_manifest.json`, `source_manifest.json`,
`probe_manifest.json`, `parameter_manifest.json`, `raw.csv`, stdout/stderr, mechanical raw QA/metrics, and
the five requested plot pages. A failed attempt remains in this run directory.
