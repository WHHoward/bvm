# Current BVM Experiment Context

Engineering context only; verify the live HEAD, source hashes, and active env
before execution. This file is not scientific authority or solve authorization.
Last reconciled for the 4×4 BUS400 platform work, 2026-10-09.

## Role split

User + ChatGPT own experiment design, scientific interpretation, and next-step
decisions. Codex owns the explicitly requested implementation, exact solve set,
immutable evidence, mechanical QA, requested classic plots, and packaging; then
stops. No interpretation, sweep, or follow-up solve is inferred from results.

## Current platforms and sources

- The existing 2×2 row/column platform has COLUMN_MERGE and T1_C1 study evidence.
  Reuse its own manifests and current source hashes; do not infer new 4×4 behavior
  from the smaller topology.
- The current array platform is
  `test/exploration/bvm-4x4-diagonal-array-v1-20261009/`: 16 canonical BVMs, one
  independent QB per BVM, four shared row WLs, four shared column BLs, 16
  independent SEs, seven ascending-row serial diagonals, one CB per cell, and
  independent 2 Ω diagonal terminals. MERGE order is serial, not a balanced tree.
- Current source family actually used there:
  - BVM: `circuits/bvm/bvm_cell_0923.cir`
  - QB: `circuits/qb/BQ_0928.cir`
  - CB: `circuits/CB/CB_0928.cir`
  - sJTL: `circuits/sJTL_0923.cir`
  - shared JJ model: `circuits/models/jjmit.cir`
  These paths and their pinned SHA-256 values are recorded in the experiment
  source manifest; verify rather than assuming aliases or later revisions match.
- `SJTL_COUNT_D0…SJTL_COUNT_D6` define the per-level serial sJTL chain. Default
  is one per level, preserving the former topology; each level still has one CB.
  Zero and multi-stage forms are renderable but are not physically validated
  unless a later task explicitly authorizes runs.

## 4×4 evidence status and electrical semantics

- A001–A006 used 200 µA shared WL/BL source totals. User + ChatGPT raw review
  classified them `LOW_DRIVE_BASELINE / FUNCTION_NOT_ESTABLISHED`. Their artifact
  and mechanical QA remain valid; this does not establish normal 4×4 function.
  Do not alter their raw, manifests, or ZIP packages.
- New 400 µA settings are shared `BUS_SOURCE_TOTAL` candidates. A source value is
  not a per-cell current. Use raw `I(R_WL|XBVM_*)`, `I(R_BL|XBVM_*)`, and
  `I(R_SE|XBVM_*)` to report actual branch currents; equal sharing is only a
  diagnostic reference.
- The 4×4 default and registered terminal-mode cases have `T1_MODE=OFF`,
  `CBU_MODE=OFF`, `CARRY_MODE=NONE`; T1, bias, and clock are not electrically
  instantiated. `config/T1_PARAMS.env` is reference-only. Reserved future modes
  stay fail-closed.
- BUS400 diagnostic batch `BVM4X4_BUS400_20261009` completed exactly two solves:
  `A007_BUS400_D3_N0` and `A008_BUS400_D3_N1`; their only config difference is
  R1C1 FINAL_READ SE. Both artifacts and mechanical/standalone/paired-plot QA
  are PASS, and scientific interpretation remains NOT_PERFORMED. Raw SHA-256:
  A007 `eb6807ea87f2e19c92605e86a0b1ff53058d47ef1316e17366be1d88a78b9dc0`;
  A008 `6ff7e9676da5a87c334826aeed1e9b4eb81421a2fa77f7a523e1fa06c1b6bd7a`.
- Registered-interval current arithmetic reports about −90.991 µA per-cell WL
  and BL time mean during WRITE0, +90.991 µA during WRITE1, and about +90.991 µA
  WL plus each-cell SE during READ0. FINAL_READ N0 SE branch means are zero;
  N1 has about +90.991 µA at R1C1 SE and zero on the other 15 SE branches.
  These are branch-current arithmetic over stored samples, not a functional
  verdict. The new 400u source total is not declared optimal; no follow-up is
  authorized. Full cell/window ranges are in both `metrics.json` files and
  [BATCH_SUMMARY.md](../test/exploration/bvm-4x4-diagonal-array-v1-20261009/BATCH_SUMMARY.md).

## Measurement and workflow invariants

- JoSIM `P(...)` is radians. `Δphase/(2π)` is navigation arithmetic only, never
  an SFQ/event count. Pair phase and voltage integral only for the same JJ,
  direction, run, exact rows, and window.
- Mechanical QA and arithmetic do not decide storage success or physical
  mechanism. `PASS`, `FAIL`, `INCONCLUSIVE`, and artifact `INVALID` are distinct.
- Preserve raw, decks, failed attempts, and source provenance. Never overwrite
  or delete history. Do not rerun a completed batch to repair analysis.
- Active rules are `docs/EXPERIMENT_CONTRACT.md` and
  `docs/research/EXPERIMENT_WORKFLOW_V1.md`; `COMPACT_WORKFLOW_V2.md` is historical
  compatibility material. QUICK/NORMAL/FORMAL are experiment risk levels, not
  `Exploration/Candidate/Authority` research tiers.
