# Closed-boundary current replay — Stage B PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Experiment: `bvm-closed-boundary-current-replay-rj2p12-l1p14-l2p20-ib260-rj32-bjs400-v1-20260911`
- Stage A scientific review attachment SHA-256: `441a7707ec2d4c53322601e543c650f98ee8d80023349950c2c1149ee1104c3c`
- Stage B preflight HEAD: `f14124c28a87f643458a00742daa9fe70eb4d938`
- Remote `bvm/master`: `f14124c28a87f643458a00742daa9fe70eb4d938`
- Status: **PASS**
- Stage A consumed: `1` physical solve; Stage B authorized: exactly `1` additional solve; total maximum: `2`.

## Authorization

The current user supplied a completed direct raw review and explicitly recorded `STAGE_A_SCIENTIFIC_GATE = PASS` and `STAGE_B_AUTHORIZED = TRUE`, with scope restricted to the N3 replay. The attachment is hash-bound in `analysis/stage_b_authorization.json`.

## Stage B N3

The source is the existing current RJ2=12/0111 full closed-loop raw and is not rerun. The replay deck contains only `I_REPLAY 0 QBIN`, the current RJ2=12 QB, six-stage JTL and 10 ohm termination. No BVM, COMMON_SL or JSL source element is present in the active replay netlist.

- Case: `CLOSED_CURRENT_REPLAY_N3_0111_RJ2P12`
- Source raw SHA-256: `1ca15a938b23d4ed08eb964713f91476256c4caf0677d1bfd3dc43020271ec75`
- Source samples/PWL pairs: `1999` / `1999`
- Deck QA: `PASS`
- Orientation: direct positive JSL7→QBIN to 0→QBIN; no sign change.

## Evidence ceiling

P values remain raw radians. Phase displays use `rad/(2*pi)` and are `PHASE_NAVIGATION_ONLY`. Raw cumulative phase, voltage area, terminal area and activity tracks are not standalone SFQ counts. The recorded-current replay includes history formed under closed-loop interaction and is not evidence that back-action was irrelevant.

Machine record: `analysis/preflight_stage_b.json`.
