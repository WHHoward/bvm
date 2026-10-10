# Carry CB + canonical sJTL batch preflight

> This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `BVM4X4_CARRY_POST_CB_SJTL_20261010`; risk: `NORMAL`.
- Preflight revision: `4`.
- Parent HEAD: `a5168f187e97b23685863d3d0964e898bbf19863`; current preflight HEAD: `a5168f187e97b23685863d3d0964e898bbf19863`.
- Exact authorized runs: A030, A031, A032, A033; physical solve count is capped at four.
- Changed topology: one canonical `sJTL_0923` per Carry CB, D1-D6, using the pinned canonical source SHA.
- Frozen: all BVM/QB/CB/T1/DFF parameters, array topology and array-internal sJTL counts, D0 entrance JTL, shared stimulus, clock pulse shape, DT=0.01p and STOP=300p.
- Absolute one-shot clock starts: A030=200p, A031/A032/A033=210p. No per-stage staggering or periodic clock.
- `V(DOUT_Dk)` and `V(CBU_JOIN_Dk)` are shared boundary voltages separated by ideal 0-V current sensors; their voltage-area arithmetic is not an array-only pulse/count measure.
- Analysis is mechanical only: actual-grid extrema/areas/currents and same-JJ phase/voltage checks; no event classifier, bit decode, or mechanism interpretation.
- Execution gate: run A030 and A031 first. A solver/artifact hard failure stops the remainder; a functioning artifact with any physical outcome continues only through A032/A033 as authorized.
- A001-A029 are immutable; the A027/A028/A029 raw hashes below are regression references.

## Registered run matrix

| Run | ROW/COL | Clock start | Baseline | Diagonal population reference | Probes | Raw estimate | Deck SHA-256 |
|---|---|---:|---|---|---:|---:|---|
| A030_CARRY_POST_CB_SJTL_ALL_200 | 1111/1111 | 200p | A027_FULL_CB_CHAIN_ALL_CLOCK | [1, 2, 3, 4, 3, 2, 1] | 227 | 87680439 B | `6fc5b132b4b53b391bfe3790d28818c1b8f4c6df66c5e44620360b675edd91f9` |
| A031_CARRY_POST_CB_SJTL_ALL_210 | 1111/1111 | 210p | A027_FULL_CB_CHAIN_ALL_CLOCK | [1, 2, 3, 4, 3, 2, 1] | 227 | 87680439 B | `f49302c41c7c91c832bd921091462cc97113e4c7ded41aa3a0d60696fcbbf546` |
| A032_CARRY_POST_CB_SJTL_PAPER_210 | 1101/1101 | 210p | A028_FULL_CB_CHAIN_PAPER_CLOCK | [1, 1, 1, 3, 1, 1, 1] | 227 | 87680439 B | `f49302c41c7c91c832bd921091462cc97113e4c7ded41aa3a0d60696fcbbf546` |
| A033_CARRY_POST_CB_SJTL_3X3_210 | 1100/0011 | 210p | A029_FULL_CB_CHAIN_3X3_CLOCK | [1, 2, 1, 0, 0, 0, 0] | 227 | 87680439 B | `f49302c41c7c91c832bd921091462cc97113e4c7ded41aa3a0d60696fcbbf546` |

## Canonical sources and identities

- `JJMIT` SHA-256: `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`
- `BVM` SHA-256: `ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7`
- `QB` SHA-256: `82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a`
- `SJTL` SHA-256: `3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688`
- `CB` SHA-256: `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`
- `T1_REFERENCE` SHA-256: `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`

## Frozen configuration, probe and metric identities

- `STATIC_QA.json` SHA-256: `2067dfe5642b049f1507cc2d0edc77e03e559c260f248c8d089a6a0316562850`; it contains the exact effective case, stimulus and complete device-parameter map for each candidate.
- `PROBE_MANIFEST.json` SHA-256: `48790b2c558889af9891bd274d197f61598caa408cb2bb1daa266492c30ccc6e`; exact probe endpoints, directions, units and four subsystem plot groups.
- `METRIC_SPEC.json` SHA-256: `782670e4a9551f8ace987f80841f64387a359ebd4b960b8118030f5d9041eabc`.
- `experiment.yaml` SHA-256: `a26f4e404655bb2d7fc655f64db391bf561093438ef8bffe3012c7058568e7da`; `human-gate.yaml` SHA-256: `44293486f98f02a09ea273b62ec5b51c478d4fe6f0471419c7f2f86882c7d867`.
- `USER_CASE.env` SHA-256: `f2de584b3b4cfbb19423cda14a42a68f5c87a8bc7bb6a42ef98f33ed006914eb`
- `STIMULUS.env` SHA-256: `32868deffeead3e875ea029aeedcda2e077282b46e9851e67515f72ea5b1a1db`
- `T1_PARAMS.env` SHA-256: `b8d97894b4f4285f2433b363ae6aac061ab683b13a7425e1551c59d29d5b095a`
- `CBU_PARAMS.env` SHA-256: `173ff1a2b7dc0f352b6fb036722f24f9ec0a3ec12471e0c5fffbb6b46419b5a4`
- `DFF_PARAMS.env` SHA-256: `8e697a5bc227afbac19f9895b8c60df7f697c2a3ea3bb19e2f1b69d6e6402015`
- `D0_JTL_PARAMS.env` SHA-256: `d22c5595127e5095fcabedfd160dfda1aec6f5618e70bb1ef013959604043913`
- `presets/CARRY_POST_CB_SJTL_ALL_200.env` SHA-256: `eb42066c27dfd91ad7f112a0fbc1a64bc990f6a8b012dc348178120e20d4f2b5`
- `presets/CARRY_POST_CB_SJTL_ALL_210.env` SHA-256: `91898496d6408cf9d43e07ae88731c544b6ac0b0ebfb5833e044f7ec1ac6fef4`
- `presets/CARRY_POST_CB_SJTL_PAPER_210.env` SHA-256: `33c0778f261109f9cbb5b8cbf507564879605bb059e24b0905d908ff34f6744f`
- `presets/CARRY_POST_CB_SJTL_3X3_210.env` SHA-256: `83fd63f5ba954f724a5c347758df26af03515db53a385561c184ab2b49adc50f`

- Solver: `/home/howard/JoSIM/build/josim-cli`; SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Solver version: `v2.7.2837d13 compiled on May 30 2026 at 20:37:57`.
- josim-plot2 SHA-256: `0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6`; shared Plotly asset SHA-256: `122e3be346d66616944d0b83eaaf7242581508c3c1cfa0995a17af0d83eff770`.
- Local submit.py SHA-256: `0aa4cfdea1d05cee881b8f2a809e3f615b2a1d8b108a5f58e4b3e68921fc7a50`; submit.sh SHA-256: `c9af4fe21f280f0b31902fa9224655b77ba9eba16d7761dcb9ab0f49ac855876`.
- Legacy CB_CARRY_BUFFER_ALL render-only deck matches A027: `True`; terminal render-only QA: `PASS`.
- JoSIM `-s` syntax/model parse is static only; it does not execute transient solves.
- Prohibited: second Carry sJTL, clock later than 210p, parameter sweep, repeated 50ps clock, bit decode, or follow-up solve.
- After the four valid runs and evidence package: STOP / AWAITING_SCIENTIFIC_REVIEW.
