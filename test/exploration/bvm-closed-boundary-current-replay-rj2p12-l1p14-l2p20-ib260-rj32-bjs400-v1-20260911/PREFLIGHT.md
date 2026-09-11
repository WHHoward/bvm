# Closed-boundary current replay — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-closed-boundary-current-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911`
- Initial registration HEAD: `4d810d5c2cc11b93e8fa1dbf00c706165f1aebe4`
- Sealed preflight HEAD: `a41d84e58036b4a36b9a4a2b2225cb2554d4830e`
- Remote `bvm/master`: `4d810d5c2cc11b93e8fa1dbf00c706165f1aebe4`
- Status: **PASS**
- Current-turn physical solve budget: exactly one Stage A N2 replay; physical solves before preflight: `0`.

## Stage A

The only current-turn solver case is `CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12`. Its source is the immutable current RJ2=12 `0011` full closed-loop raw `I(B_JSL8)`. The source case is not rerun. The replay deck has only `I_REPLAY 0 QBIN`, the current RJ2=12 QB, six-stage JTL and 10 ohm termination.

- Replay deck: `test/exploration/bvm-closed-boundary-current-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911/runs/CLOSED_CURRENT_REPLAY_N2_0011_RJ2P12/deck.cir`
- PWL pairs registered: `1999`
- Deck QA: `PASS`
- Orientation: positive `I(B_JSL8)` JSL7→QBIN maps directly to positive `I_REPLAY 0 QBIN`; no sign correction.

## Stage B early-stop boundary

N3 `CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12` is deferred and has no current-turn source copy, deck or solve. The repository contract requires explicit `SCIENTIFIC_REVIEW_AUTHORIZED` before scientific classification can trigger a successor solve. Therefore this turn stops after Stage A evidence and records Stage B as `DEFERRED_PENDING_SCIENTIFIC_REVIEW_AUTHORIZATION`, even if mechanical navigation is complete.

## Evidence ceiling

P values remain raw radians; displays use `rad/(2*pi)` turns. Phase landmarks, threshold activity, voltage area and terminal area are navigation evidence only, not SFQ counts. Replay is ideal current forcing and is not a source-impedance or circuit-equivalent reconstruction.

Machine record: `analysis/preflight.json`.
