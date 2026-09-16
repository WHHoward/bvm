# LS3 timing-window closure — bvm-rloop-ls3-delay-window-v1-20260916

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

## Registration

- Frozen parent HEAD: `b904851be588ca88d40cf1700d5fef7ce3d889ed`; remote `bvm/master`: `b904851be588ca88d40cf1700d5fef7ce3d889ed`.
- Study phase: `EXPLORATORY`; role: `Experimental Operator + Evidence Packager`.
- Scientific review authorization: `false`; only mechanical evidence packaging is performed.
- The 0.3-ps N2/N3 exact/delay raw from the prior branch-decomposition experiment is read-only context and is not rerun or copied.

## Single question

Is the registered 0.3-ps LS3-only population-selective timing observation part of a finite timing window rather than a single tested point?

## Frozen fixture

- Working point: L1=1.4 pH, L2=2.0 pH, IBias=260 µA, RJ1=32 Ω, RJ2=12 Ω, BJS area=4.
- Forward path: canonical BVM → COMMON_SL → JSL1..8 → canonical QB → JTL1..6 → 10 Ω terminal.
- LS3-only fixture: retain `R_S 6 10 3.0`; remove physical `L_S3 6 10 0.5P`; impose each same-instance canonical `I(L_S3)` from node6 to node10.
- QB/QBIN/JSL/JTL/terminal/BVM/stimulus/timestep are unchanged.
- `.tran 0.1p 200p`; actual stored 0.1-ps sample semantics; no interpolation, smoothing, resampling, scaling or sign modification.

## Read-only 0.3-ps reference

- Prior branch experiment: `test/exploration/bvm-rloop-branch-timing-decomposition-v1-20260916`.
- Reused runs: `LS3_EXACT_0011`, `LS3_DELAY0P3_0011`, `LS3_EXACT_0111`, `LS3_DELAY0P3_0111`.

## New authorized solves, exact order

1. `LS3_DELAY0P2_0011` — 2 stored samples.
2. `LS3_DELAY0P2_0111` — 2 stored samples.
3. `LS3_DELAY0P4_0011` — 4 stored samples.
4. `LS3_DELAY0P4_0111` — 4 stored samples.

For every delay: t<110 ps uses the canonical same sample; [110,110+delay) holds the 110-ps value; later samples use exact stored index i−shift. No other solve is authorized. N1/N4, 0.3 reruns, sweeps, sentinel, timestep refinement, QB/receiver/topology changes are prohibited.

## Mechanical oracle and limits

- N2: ordered QB→JTL phase-chain count, first/second BJ1/BJ2, L1 re-arm, JSL8 behavior, active JS1/JS2, with phase raw radians and turns only as navigation.
- N3: response 1..4 BJ1/BJ2/JTL1..6 chains, first missing stage, JS1/JS2 p2p and JSL8 behavior.
- Navigation/area/cluster quantities are not literal SFQ counts. Historical strict counts remain contextual where they disagree with multi-evidence records.
- Timing-window labels are mechanical candidates only; final scientific classification remains `NOT_ASSIGNED_SCIENTIFIC_REVIEW_REQUIRED`.

## Source audit

Canonical branch audits before source construction: `{"0011": "PASS", "0111": "PASS"}`. Checks include V(R_S)≈3I(R_S), V(L_S3)=V(R_S), orientation and node6/node10 KCL.

## Stop

After the four new raw files, QA, visualization, package, commit and Drive delivery: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`. No automatic follow-up.
