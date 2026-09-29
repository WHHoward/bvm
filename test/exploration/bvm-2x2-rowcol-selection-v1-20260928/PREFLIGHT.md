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

## Authorized A/B/C shared-selection batch (2026-09-29)

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

- Parent HEAD: 5447f08ebbe367dd9d4f2ff2f072fa17c2cc1aac (master, synced to bvm/master).
- Recorded solver: build/josim-cli v2.7.2837d13, binary SHA-256 48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2.
- Frozen executor SHA-256: scripts/run_platform.py 4d2cea3de007c0211989b32976f38cda9be079c865d211b26b510dc75be7ea93; comparison builder SHA-256: scripts/build_batch_comparison.py 6e81c0848a8b32b333969b56408f709e1580c5c51cf968b7389452f65b834fcf.
- User authorization: current task dated 2026-09-29; exactly three independent physical solves, serially allocated, no follow-up.
- Historical evidence A001–A009 is immutable and hash-verified; A009 is the same-row ROW_BITS=10, COL_BITS=11 comparison. No historical run is re-solved or rewritten.
- Expected new run IDs in order: A010_SHARED_R11_C10, A011_SHARED_R11_C11, A012_SHARED_R11_C11.
- Canonical sources remain direct includes with the SHA-256 values registered in experiment.yaml; do not edit BVM, QB, CB, sJTL, or JJ model sources.
- Every case uses SHARED + CELL + CROSSPOINT; two row-WL sources, two column-BL sources, four independent cell-SE sources; 200 µA write WL/BL, 200 µA read WL, 100 µA read SE; DT=0.01 ps. Four independent BVM→QB→1 sJTL→1 CB→2 Ω VOUT chains; no merge and no T1.

### Exact run matrix

1. A — same-column dual read (A_SAME_COLUMN_DUAL_CROSSPOINT): ROW_BITS=11, COL_BITS=10, SECOND_READ_ENABLE=1, SECOND_ROW_BITS=10, SECOND_COL_BITS=10, original WRITE0/READ0/WRITE1/FINAL_READ times, SECOND_READ 170–181 ps, STOP=250 ps. At first read, only R1C1/R2C1 receive cell SE; both rows receive WL; second read gates R1C1 only. Compare its first response with A009 on exact common stored timestamps [110,170); no interpolation.
2. B — four-cell read (B_ALL_CELL_CROSSPOINT): ROW_BITS=11, COL_BITS=11, SECOND_READ_ENABLE=0, original four stage timing, STOP=250 ps. All four cell-SE sources are active during FINAL_READ.
3. C — mixed-store preparation/read (C_MIXED_STORAGE_SEQUENTIAL_WRITE): WRITE0 all shared lines at 50–61 ps; READ0 explicitly omitted; selective WRITE1 R1C1 via WL_R1+BL_C1 at 90–101 ps, then R2C2 via WL_R2+BL_C2 at 120–131 ps; ROW_BITS=11/COL_BITS=11 final read at 170–181 ps; STOP=300 ps. No independent WL/BL topology is permitted. For each write, record target, same-row WL-only, same-column BL-only, and unselected cells, plus every cell's actual WL/BL/SE branch current.

### Registered windows and arithmetic

- A first trigger [110,121), first response [110,170), second trigger [170,181), second response [170,250); responses are separately summarized, never combined across both reads.
- B trigger [110,121), full read response [110,250).
- C target-write windows [90,101) and [120,131); gaps [101,120) and [131,170); final trigger [170,181); full read response [170,300).
- Per cell: actual WL/BL/SE branch current extrema and charge on stored rows; BVM JM1/JM2/JS1/JS2 P/V, SL; QB, sJTL and CB JJ P/V; QB_OUT, SJTL_OUT and VOUT.
- Output arithmetic per read-response window: signed min/max/p2p, timestamp of positive maximum/negative minimum/max-absolute sample, and signed voltage-time area for BVM_SL, QB_OUT, SJTL_OUT, VOUT.
- Same-JJ phase-radian endpoint delta versus voltage integral/Phi0 arithmetic uses identical run, JJ, direction and actual stored timestamps. No phase turns or voltage area will be called an event count.
- No pulse/SFQ event detector or threshold is registered. SCIENTIFIC_REVIEW_AUTHORIZED was not supplied; event-count classification, physical Gate verdict, mechanism interpretation, or winner selection is NOT PERFORMED. Timestep convergence is UNKNOWN.
- A009 raw QA records actual intervals from 0.01 to 0.02 ps despite nominal DT=0.01p. Comparison plots use only exact common stored timestamps in their registered windows: A009/A010 orientation [110,170) ps, and the A010/A011/A012 VOUT overlay [0,250) ps (C's full standalone range remains through 300 ps). Interpolation/resampling is prohibited. Per-run plots use classic josim-plot2.py, full raw ranges plus the registered read-response windows.
- Artifact outcomes distinguish solver/artifact invalidity from physical behavior. If a raw is valid but post-processing fails, preserve that raw and repair only its analysis/plots; never rerun solely to repair analysis.

No additional masks, amplitude points, parameter sweep, altered topology, canonical source changes, or T1/4×4 work are authorized.
