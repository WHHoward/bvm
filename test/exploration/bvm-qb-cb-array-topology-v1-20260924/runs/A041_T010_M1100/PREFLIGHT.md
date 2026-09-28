# Physical run preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

This PRE-FLIGHT is generated from frozen USER_CASE/STIMULUS snapshots. The exact
run is the single mask below; no other mask, sweep, or follow-up is authorized.

- run_id: `A041_T010_M1100`
- parent HEAD: `41654a0a575a36baedd999255a27229bcd3dc05a`
- solver path: `/home/howard/JoSIM/build/josim-cli`
- solver SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- solver version: `JoSIM: Josephson Junction Superconductive SPICE Circuit Simulator
Copyright (C) 2020 by Johannes Delport (jdelport@sun.ac.za)
v2.7.2837d13 compiled on May 30 2026 at 20:37:57`
- ARRAY_SIZE: `4`
- probe profile: `core` (184 probes)
- OUTPUT_MODE: `T1`
- FINAL READ MASK: `1100` (leftmost bit is BVM1)
- topology: `{"POST_SJTL_CB": [1, 1, 1, 1], "QB_CB": [0, 0, 0, 0], "SJTL_COUNT": [1, 2, 2, 1]}`
- DT: `0.01p`; STOP: `250p`
- run matrix: exactly `A041_T010_M1100` / mask `1100`
- expected raw: `runs/A041_T010_M1100/raw.csv`
- interpretation ceiling: mechanical QA and requested descriptive plots only

## Source snapshots

- `circuits/bvm/bvm_cell_0923.cir` (ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7) → `snapshot/sources/bvm_tunable.cir` SHA-256 `ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7`
- `circuits/qb/BQ_0928.cir` (82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a) → `snapshot/sources/BQ_tunable.cir` SHA-256 `82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a`
- `circuits/CB/CB_0928.cir` (70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370) → `snapshot/sources/CB_tunable.cir` SHA-256 `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`
- `circuits/sJTL_0923.cir` (3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688) → `snapshot/sources/sJTL_tunable.cir` SHA-256 `3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688`
- direct include `circuits/t1/t1_cell.cir` SHA-256 `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237` as `../../../../../circuits/t1/t1_cell.cir` (no copied or patched T1 source)

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
- `I(I_WL3)`
- `I(I_BL3)`
- `I(I_SE3)`
- `P(B_JM1|XBVM3)`
- `V(B_JM1|XBVM3)`
- `P(B_JM2|XBVM3)`
- `V(B_JM2|XBVM3)`
- `P(B_JS1|XBVM3)`
- `V(B_JS1|XBVM3)`
- `P(B_JS2|XBVM3)`
- `V(B_JS2|XBVM3)`
- `I(L_M1|XBVM3)`
- `I(L_M2|XBVM3)`
- `I(L_M3|XBVM3)`
- `I(L_PM|XBVM3)`
- `I(L_SL|XBVM3)`
- `V(BVM3_SL)`
- `P(BJ1|XBQ3)`
- `V(BJ1|XBQ3)`
- `P(BJ2|XBQ3)`
- `V(BJ2|XBQ3)`
- `P(BJ3|XBQ3)`
- `V(BJ3|XBQ3)`
- `I(LIN|XBQ3)`
- `I(L1|XBQ3)`
- `I(L2|XBQ3)`
- `I(L3|XBQ3)`
- `V(MERGE3)`
- `I(I_WL4)`
- `I(I_BL4)`
- `I(I_SE4)`
- `P(B_JM1|XBVM4)`
- `V(B_JM1|XBVM4)`
- `P(B_JM2|XBVM4)`
- `V(B_JM2|XBVM4)`
- `P(B_JS1|XBVM4)`
- `V(B_JS1|XBVM4)`
- `P(B_JS2|XBVM4)`
- `V(B_JS2|XBVM4)`
- `I(L_M1|XBVM4)`
- `I(L_M2|XBVM4)`
- `I(L_M3|XBVM4)`
- `I(L_PM|XBVM4)`
- `I(L_SL|XBVM4)`
- `V(BVM4_SL)`
- `P(BJ1|XBQ4)`
- `V(BJ1|XBQ4)`
- `P(BJ2|XBQ4)`
- `V(BJ2|XBQ4)`
- `P(BJ3|XBQ4)`
- `V(BJ3|XBQ4)`
- `I(LIN|XBQ4)`
- `I(L1|XBQ4)`
- `I(L2|XBQ4)`
- `I(L3|XBQ4)`
- `V(MERGE4)`
- `P(BJ1|XPOSTCB1)`
- `V(BJ1|XPOSTCB1)`
- `P(BJ2|XPOSTCB1)`
- `V(BJ2|XPOSTCB1)`
- `I(L1|XPOSTCB1)`
- `I(L4|XPOSTCB1)`
- `V(L1_01)`
- `P(BJ1|XSJTL1_01)`
- `V(BJ1|XSJTL1_01)`
- `I(L2|XSJTL1_01)`
- `P(BJ1|XPOSTCB2)`
- `V(BJ1|XPOSTCB2)`
- `P(BJ2|XPOSTCB2)`
- `V(BJ2|XPOSTCB2)`
- `I(L1|XPOSTCB2)`
- `I(L4|XPOSTCB2)`
- `V(L2_02)`
- `P(BJ1|XSJTL2_01)`
- `V(BJ1|XSJTL2_01)`
- `I(L2|XSJTL2_01)`
- `V(L2_01)`
- `P(BJ1|XSJTL2_02)`
- `V(BJ1|XSJTL2_02)`
- `I(L2|XSJTL2_02)`
- `P(BJ1|XPOSTCB3)`
- `V(BJ1|XPOSTCB3)`
- `P(BJ2|XPOSTCB3)`
- `V(BJ2|XPOSTCB3)`
- `I(L1|XPOSTCB3)`
- `I(L4|XPOSTCB3)`
- `V(L3_02)`
- `P(BJ1|XSJTL3_01)`
- `V(BJ1|XSJTL3_01)`
- `I(L2|XSJTL3_01)`
- `V(L3_01)`
- `P(BJ1|XSJTL3_02)`
- `V(BJ1|XSJTL3_02)`
- `I(L2|XSJTL3_02)`
- `P(BJ1|XPOSTCB4)`
- `V(BJ1|XPOSTCB4)`
- `P(BJ2|XPOSTCB4)`
- `V(BJ2|XPOSTCB4)`
- `I(L1|XPOSTCB4)`
- `I(L4|XPOSTCB4)`
- `V(L4_01)`
- `V(FINAL_OUT)`
- `P(BJ1|XSJTL4_01)`
- `V(BJ1|XSJTL4_01)`
- `I(L2|XSJTL4_01)`
- `V(T1_I)`
- `V(CLK)`
- `V(S)`
- `V(C)`
- `V(CLK_RAW)`
- `I(R_TRIG_CLK)`
- `P(B_J1|XT1)`
- `V(B_J1|XT1)`
- `P(B_J7|XT1)`
- `V(B_J7|XT1)`
- `P(B_J9|XT1)`
- `V(B_J9|XT1)`
- `P(B_J11|XT1)`
- `V(B_J11|XT1)`
- `P(B_J2|XT1)`
- `V(B_J2|XT1)`
- `P(B_J3|XT1)`
- `V(B_J3|XT1)`
- `I(L1|XT1)`
- `I(L3|XT1)`
- `I(L11|XT1)`
- `I(L14|XT1)`
- `I(L17|XT1)`

## Registered mechanical arithmetic

- USER_CASE snapshot SHA-256: `5945450c18007cbe5ba108da4b27b9ae8e59497d417ebc5e7098325212500d19`; STIMULUS snapshot SHA-256: `b49ba232fee95723011370d3c2889596785e531cb6da2f2fb34738161192134a`.
- T1 zero-drop link: report `max |V(FINAL_OUT)-V(T1_I)|` over all exact stored raw rows.
- No interpolation/resampling; this is report-only with no pass/fail voltage threshold.
- T1 config: BIAS1=`1.8m`, BIAS2=`1.8m`, BIAS3 source=`VOLTAGE` value=`1.8m`, R_S=`12`, R_C=`12`, CLK_MODE=`PULSE`, CLK_R=`2`.
- T1 periodic drive: PULSE(0 1.2m 170p 1p 1p 2p 50p); R_TRIG_CLK=2Ω.
- This single run is not a matched-load causal comparison; A029 remains a reference for later user review.
- Timestep, parameter, and solver sensitivity are UNKNOWN; no additional solve is authorized.
- No additional mask, retry, sweep, or Phase 2 run is authorized.

## Required output artifacts

`actual_deck.cir`, `stimulus.inc`, `topology_manifest.json`, `source_manifest.json`,
`probe_manifest.json`, `parameter_manifest.json`, `raw.csv`, stdout/stderr, mechanical raw QA/metrics, and
the requested plot pages: `01_overview.html, 02_bvm.html, 03_qb.html, 04_cb.html, 05_acc_gap.html, 06_t1.html`. A failed attempt remains in this run directory.
