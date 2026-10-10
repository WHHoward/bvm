# BVM 4x4 Carry sJTL placement and stage-mask preflight

> This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Starting HEAD: `9db7929608bf25fd8c2f86fb99e84b9a4387ba81`; authorized solves: exactly 6 (A034-A039).
- Risk: NORMAL. Only canonical sJTL placement/stage mask varies as registered; no device or clock sweep.
- Canonical BVM/QB/CB/sJTL/jjmit SHA-256 values are pinned below; T1/DFF/CBU snapshots must match A027-A033.
- All cases use SHARED 400u WL/BL, independent 100u SE, DT=0.01p, STOP=300p, synchronous GLOBAL_ONESHOT clock at only 200p/210p.
- Topology: 7 T1, six CB_0928 Carry buffers, D1-D6 JOINs with independent DOUT/Carry branches, no ColdFlux MERGE, no added output-side devices.
- Measurements: array final CB BJ1/BJ2 P/V, DOUT branch current, Carry CB BJ1/BJ2, selected sJTL BJ1 and boundary current, JOIN currents, T1 input/S/C/clock and DFF boundary/internal probes.
- P(...) is radians. Same-JJ phase and voltage area use identical stored rows and windows; positive/negative variation is navigation arithmetic, not an event count.
- Shared V(DOUT_Dk)/JOIN voltage is source-mixed and is not treated as array-only pulse count.
- Artifact validity and mechanical QA only; scientific interpretation, event classification, and bit decoding are NOT_PERFORMED.
- STOP: finish the six registered solves, QA, local classic plots, evidence package, commit/push, then await user/ChatGPT review.

## Registered matrix

| Run | Mask | Carry sJTL | Clock | Reference | Deck SHA-256 | Probe count | Raw estimate |
|---|---|---|---:|---|---|---:|---:|
| A034_D2_ONLY_POST_CB_SJTL_ALL_200 | 1111/1111 | POST_CB 010000 | 200p | A027_FULL_CB_CHAIN_ALL_CLOCK | `a87651b1bbd99526dd02210df30fd32b921bed2306203ebca5a317aad2e2855f` | 209 | 80727805 B |
| A035_D2_ONLY_POST_CB_SJTL_PAPER_200 | 1101/1101 | POST_CB 010000 | 200p | A028_FULL_CB_CHAIN_PAPER_CLOCK | `a87651b1bbd99526dd02210df30fd32b921bed2306203ebca5a317aad2e2855f` | 209 | 80727805 B |
| A036_PRE_CB_SJTL_ALL_200 | 1111/1111 | PRE_CB 111111 | 200p | A027_FULL_CB_CHAIN_ALL_CLOCK | `d68952978342590e076f76eb91b2b49932ae8caa6af0bd9010360d4c8170585c` | 234 | 90384241 B |
| A037_PRE_CB_SJTL_ALL_210 | 1111/1111 | PRE_CB 111111 | 210p | A027_FULL_CB_CHAIN_ALL_CLOCK | `379558280c914f3eb763366d950a07693148dfc7249789767978acfdeec799a8` | 234 | 90384241 B |
| A038_PRE_CB_SJTL_PAPER_210 | 1101/1101 | PRE_CB 111111 | 210p | A028_FULL_CB_CHAIN_PAPER_CLOCK | `379558280c914f3eb763366d950a07693148dfc7249789767978acfdeec799a8` | 234 | 90384241 B |
| A039_PRE_CB_SJTL_3X3_210 | 1100/0011 | PRE_CB 111111 | 210p | A029_FULL_CB_CHAIN_3X3_CLOCK | `379558280c914f3eb763366d950a07693148dfc7249789767978acfdeec799a8` | 234 | 90384241 B |

## Pinned source closure

- JJMIT: `circuits/models/jjmit.cir` — `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`
- BVM: `circuits/bvm/bvm_cell_0923.cir` — `ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7`
- QB: `circuits/qb/BQ_0928.cir` — `82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a`
- SJTL: `circuits/sJTL_0923.cir` — `3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688`
- CB: `circuits/CB/CB_0928.cir` — `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`
- T1_REFERENCE: `circuits/t1/t1_cell.cir` — `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`

Physical solves are not performed by preflight. JoSIM `-s` static syntax checks were run on all six rendered decks.
