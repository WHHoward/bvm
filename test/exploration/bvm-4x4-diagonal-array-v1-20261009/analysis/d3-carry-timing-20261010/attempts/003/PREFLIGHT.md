# BVM 4x4 D3 Carry timing A040/A041 preflight

> This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Preflight attempt: 003. Attempts 001 (`bdbb75907bd6a8d55942cf8b0f01a96a70e02f689055ef6a6b4b6b2b2dc08a1a`) and 002 (`f01c30067112b09bf28fea8f441de6c85579261cfc342dc7ca5022476dec04f3`) are preserved and superseded before any solver run; attempt 003 is a single direct-child preflight commit.
- Registered start HEAD: `d7089ace75f1450b0f48c76762373c8d105d4549`; source/preflight parent HEAD: `bce51295d2d5543bb53ffd82529b66e9d8449388`.
- Risk: NORMAL. Exactly two new physical solves are authorized: A040 then A041.
- A036 is a read-only comparison baseline; no A027-A039 raw/deck is modified or recomputed.
- Only the D3 PRE-CB Carry sJTL count changes: 1→0 (A040) and 1→2 (A041). The canonical CB_0928 remains the last physical element before JOIN.
- All non-D3 topology, BVM/QB/CB/sJTL/T1/DFF sources and parameters, PWL stimulus, 400u shared WL/BL, 100u independent SE, 200p global clock, DT and STOP match A036.
- Probes include D3 array last-CB BJ1/BJ2 P/V and DOUT branch current; D2 Carry JJ; each configured D3 PRE-CB sJTL BJ1 P/V and interstage boundary/current; Carry-CB BJ1/BJ2; JOIN currents; T1_D3 B_J1/B_J2/B_J9/B_J10/B_J11 P/V; D4-D6 stage evidence; DFF data/clock/output.
- To control raw size, this task-local focus omits representative external bias-current and clock-series-current traces plus DFF internal JJ/bias/output-load-current traces; all physical bias, clock, and load settings remain unchanged, while clock voltage and DFF data/clock/output voltage plus data-link current are retained.
- A036 lacks D3 T1 B_J2/B_J9/B_J10 probes; those are UNKNOWN for A036 and will be plotted only for A040/A041.
- `P(...)` is radians. Same-JJ phase and voltage-area values use identical stored rows/windows and actual timestamps; no interpolation/resampling.
- DOUT_D3 and CBU_JOIN_D3 share the electrical boundary; DOUT voltage area is not an array-only event count.
- Descriptive local waveform candidates, if present in platform output, are not event classifications. Scientific interpretation: NOT PERFORMED.
- STOP after exact runs, mechanical QA, standard/local comparison plots, DELTA package QA, commit/push and archive handoff.

## Run matrix

| Run | D3 sJTL count | D1..D6 counts | Mask | Clock | Deck SHA-256 | Probes | Conservative raw projection |
|---|---:|---|---|---|---|---:|---:|
| A040_D3_PRE_CB_SJTL_0_ALL_200 | 0 | 1,1,0,1,1,1 | 110111 | 200p | `e7eb50473f5a9650bc9f0709084a17a63b2beaebed2ce984cb37574131742cd1` | 212 | 96070951 B |
| A041_D3_PRE_CB_SJTL_2_ALL_200 | 2 | 1,1,2,1,1,1 | 111111 | 200p | `a693d075efa013c38090723b173d95fcb8c48d1e23d8bd69d89cc92e83269cf9` | 222 | 99070851 B |

## Canonical sources and solver

- JJMIT: `circuits/models/jjmit.cir` — `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`
- BVM: `circuits/bvm/bvm_cell_0923.cir` — `ddf90076d40c0856f73dfcdcd22adeae6eddb7dd650798957a0d6c73953456b7`
- QB: `circuits/qb/BQ_0928.cir` — `82e6f6c7a95856c6d7bcdd28a56c009a815fc77e237a76af08fbebe45eed988a`
- SJTL: `circuits/sJTL_0923.cir` — `3cbc6889f9b4cd6b7764efa4a591f9d4dcdb0b2b86ded1f265dadabda1040688`
- CB: `circuits/CB/CB_0928.cir` — `70a6af05acccb7c354799d5b1b7542c86c677970681473f559bbf0f7e4d6d370`
- T1_REFERENCE: `circuits/t1/t1_cell.cir` — `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`
- Solver: `/home/howard/JoSIM/build/josim-cli`; SHA-256 `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`; version recorded in STATIC_QA.
- Shared Plotly asset SHA-256: `122e3be346d66616944d0b83eaaf7242581508c3c1cfa0995a17af0d83eff770`.
- Historical render-only regression covers A027-A039; solver static syntax checks are run only for the two new rendered decks.
