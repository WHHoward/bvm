# BVM population passive source replay — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-population-passive-source-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911`
- Initial registration HEAD: `5a63b4b5d2de478e43e61889a091f2023a969c5d`
- Sealed preflight HEAD: `5a63b4b5d2de478e43e61889a091f2023a969c5d`
- Remote `bvm/master` observed at preflight: `5a63b4b5d2de478e43e61889a091f2023a969c5d`
- Status: **PASS**
- Physical solve count before preflight: `0`.

## Exact matrix

- Passive captures: N2 `0011`, N3 `0111`, N4 `1111`.
- Replay solves: the three exact passive source snapshots into the same RJ2=12 receiver.
- Total: exactly `6` physical solves; no extra mask, sweep, timestep, parameter or receiver case.

## Passive topology

The current BJS400 population BVM/JSL configuration is used byte-identically for the BVM/JJ model inputs. Four BVMs share `COMMON_SL`; eight `jjmit area=5.0` JSL junctions terminate at ground only in this passive counterfactual. QB, JTL and `R_TERM` are absent from the active passive netlist.

| passive case | JSL8 branch | controls | deck QA |
|---|---|---:|---|
| `PASSIVE_N2_0011` | `B_JSL8 JSL_NODE7 0 jjmit area=5.0` | 12 | `PASS` |
| `PASSIVE_N3_0111` | `B_JSL8 JSL_NODE7 0 jjmit area=5.0` | 12 | `PASS` |
| `PASSIVE_N4_1111` | `B_JSL8 JSL_NODE7 0 jjmit area=5.0` | 12 | `PASS` |

## Frozen protocol and replay boundary

Stored history is IDLE 0–50ps; WRITE0 50–61ps; IDLE 61–70ps; ZERO_STATE_READ_CONTROL 70–81ps; IDLE 81–90ps; WRITE1 90–101ps; SETTLE 101–110ps; selective final READ 110–121ps; TAIL 121–200ps, with 100uA amplitude, 1ps rise/fall, and `.tran 0.1p 200p`.
Replay decks are not generated until passive raw files exist. They will contain only `I_REPLAY 0 QBIN`, current RJ2=12 BQ, current six-stage JTL and current 10 ohm termination. Raw timestamps/current values will be retained exactly; no interpolation or waveform transformation is registered.

## Evidence ceiling

P values remain raw radians. Any phase-turn display is `rad/(2*pi)`. Phase landmarks, voltage/current activity, voltage area and terminal area are navigation evidence only, not SFQ counts. Passive source is a counterfactual and replay is ideal forcing, not a circuit-equivalent source. Scientific interpretation is `NOT_PERFORMED`.

Machine record: `analysis/preflight.json`.
