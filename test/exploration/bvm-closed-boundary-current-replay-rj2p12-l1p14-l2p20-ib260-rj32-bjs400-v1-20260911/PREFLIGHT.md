# Closed-boundary current replay — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-closed-boundary-current-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911`
- Stage A sealed evidence: `1` physical solve; scientific gate: `PASS` (user review attachment hash-bound).
- Stage B sealed preflight HEAD: `f14124c28a87f643458a00742daa9fe70eb4d938`
- Remote `bvm/master`: `f14124c28a87f643458a00742daa9fe70eb4d938`
- Status: **PASS**
- Total authorized solve count: exactly `2`; no third solve.

## Stage A

N2 closed-boundary current replay is preserved unchanged in the Stage A package and raw artifacts. The current user has completed direct raw review and explicitly authorized the preregistered Stage B N3 replay.

## Stage B

Run exactly `CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12` from the immutable RJ2=12/0111 `I(B_JSL8)` source. The replay contains only the current RJ2=12 QB, six-stage JTL, 10 ohm load and `I_REPLAY 0 QBIN`; no BVM/COMMON_SL/JSL source network. `.tran 0.1p 200p` remains frozen.

- Source raw SHA-256: `1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75`
- PWL pairs: `1999`
- Deck QA: `PASS`
- No N4/passive/RJ2/timestep/sweep solve is authorized.

## Evidence ceiling

Raw is authoritative. Phase is radians; `rad/(2*pi)` turns are navigation only. A closed-loop current replay retains interaction history encoded in the recorded waveform and cannot prove back-action irrelevant. Final scientific outcome remains bounded to the tested replay abstraction.

Machine records: `analysis/preflight_stage_b.json`, `analysis/stage_b_authorization.json`.
