# 2×2 BVM row/column platform static preflight

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: `a155b7f820efbad4447c8d1985a66e4192b7e614`.
- Scope of this task: platform implementation, static topology/stimulus QA,
  regression tests, and dry-runs only. `physical_solves_authorized_in_this_task=0`.
- No canonical BVM, QB, CB, sJTL, or JJ model is copied, edited, or rendered
  with altered internal parameters.
- Four separate BVM→BQ→one sJTL→one post-CB→2 Ω termination chains; four
  separate VOUT nodes; no merge, diagonal combine, or T1.
- INDEPENDENT uses 12 cell-level PWL current drivers. SHARED uses exactly two
  row-WL, two column-BL, and two column-SE PWL drivers on six distinct nodes.
- Row and column bit order is left-to-right: `10/10` activates R1C1; row-only
  and column-only half-selected cells are recorded separately.
- All four cells receive WRITE0, READ0, and WRITE1. ROW_BITS/COL_BITS affect
  FINAL READ only; FINAL READ has zero BL drive.
- `./try.sh --dry-run` must not create a run directory or invoke JoSIM.
- A later manual `./try.sh` invocation, initiated by the user, allocates one
  immutable run ID and invokes the solver once for the current config only.
- No physical result, equivalence claim, or scientific interpretation is
  produced by this static-platform task.

## Incremental CELL-SE platform extension

- Compatibility base: `3d12e5c5252f02748f880f09027e70c8d0cfc3d8`.
- This extension changes only the existing runner/configuration/tests/docs.
  A001–A003 raw, run manifests, QA, and existing ZIP archives remain immutable.
- Missing `SE_TOPOLOGY`/`SE_GATE_MODE` defaults to
  `SHARED_COLUMN/COLUMN`; the existing A/B/C presets explicitly retain the
  legacy generated deck and stimulus behavior.
- `SHARED + CELL` uses two shared row-WL, two shared column-BL, and four
  electrically independent cell-SE sources. D0 gates final SE by column;
  D1 gates it by row AND column. Both retain the four canonical load chains.
- Scope remains static topology/stimulus/probe QA, regression tests, and
  dry-runs only. No JoSIM invocation, experiment run raw, or physical claim.
  One legacy mock-runner test in an earlier full test pass wrote a synthetic
  CSV only inside an automatically cleaned `TemporaryDirectory`; it did not
  enter this experiment's `runs/` tree or Git.

## Optional half-selected repeat-read extension

- Compatibility base: `f554cbc7aff90e9eb3a9cd8a07d99444ac1ea503`.
- A001–A006 raw, manifests, QA, plots, and existing handoff packages remain
  immutable; their complete run/archive file-set fingerprint is unchanged.
- SECOND_READ defaults off. E0/E1 enable only the user-registered
  170–181 ps second read, with R2C1 as the fixed CELL_CROSSPOINT SE target and
  STOP=300 ps.
- E0 first-read PWL is byte/grid-equivalent to A005 through 170 ps; E1 matches
  A006. Comparisons exclude the added second stage and STOP endpoint.
- Static tests and dry-runs only; no E0/E1 solve, synthetic raw, or physical
  result is produced by this platform update.

## Optional SECOND_READ platform extension

- Parent HEAD: `f554cbc7aff90e9eb3a9cd8a07d99444ac1ea503`.
- `SECOND_READ_ENABLE` defaults off; legacy USER_CASE/preset snapshots without
  the new fields render no SECOND_READ PWL stage.
- E0/E1 retain the existing eight sources and four independent load chains.
  Only the second read's cell-local SE gate is fixed to
  `SECOND_ROW_BITS AND SECOND_COL_BITS`; it does not inherit the first-read
  `SE_GATE_MODE`.
- The registered first-read, recovery, second-read, and post-second-read metric
  windows are half-open and use actual stored raw rows. Focused plots use the
  existing classic `josim-plot2.py` renderer on those stored rows.
- Static/dry-run validation only; no JoSIM, no generated raw, and no E0/E1
  physical result is authorized in this task.
