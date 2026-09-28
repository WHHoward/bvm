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
