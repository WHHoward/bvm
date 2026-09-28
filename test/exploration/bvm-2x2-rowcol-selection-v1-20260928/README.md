# 2×2 BVM shared row/column selection platform v1

This is a render-first 2×2 BVM → independent QB → sJTL → post-CB platform.
The four outputs are separate; there is no diagonal merge and no T1. Canonical
BVM/QB/CB/sJTL source files are included read-only and their SHA-256 values are
checked before every preview or run.

Each cell uses the same frozen load chain:

```text
BVM.SL → BQ → one sJTL → one CB → independent VOUT_rc → R_TERM=2 Ω to ground
```

## Row/column mapping

Cell names are row-major: `R1C1`, `R1C2`, `R2C1`, `R2C2`. In both bit strings,
the leftmost bit addresses row/column 1 and the rightmost bit addresses 2.
`ROW_BITS=10`, `COL_BITS=10` therefore selects only `R1C1`; `R1C2` is row-only
half-selected, `R2C1` is column-only half-selected, and `R2C2` is unselected.
The two column BL buses and two column SE buses are distinct electrical nodes.

Every cell gets the same pre-final sequence: WRITE0, READ0 control, WRITE1,
then FINAL READ. Row/column bits affect only FINAL READ. BL is zero throughout
FINAL READ; a cell is at an active crosspoint only when its row WL and column
SE are both enabled.

The four amplitude fields are positive magnitudes. WRITE0 applies negative WL
and BL pulses; WRITE1 applies positive WL and BL pulses; READ0 applies positive
WL and SE pulses to all rows/columns; FINAL READ applies positive WL only on
enabled rows and positive SE only on enabled columns. The read amplitude fields
are used for both READ0 control and FINAL READ. Final-read BL remains zero.

`INDEPENDENT` gives every cell separate WL/BL/SE nodes and three cell-level
current-source drivers. `SHARED` uses exactly two row-WL, two column-BL, and
two column-SE nodes, each driven by one independent PWL current source. Its
200 µA line values are candidates, not physical equivalents of four 100 µA
cell drivers; the raw records source and per-cell BVM input branch currents.

## Presets and operation

The checked-in `USER_CASE.env` starts with preset A:

```bash
./try.sh --dry-run
```

The three editable presets are:

```bash
./try.sh --preset A_INDEPENDENT_10_10 --dry-run
./try.sh --preset B_SHARED_10_10 --dry-run
./try.sh --preset C_SHARED_11_11 --dry-run
```

To execute exactly one current configuration manually, omit `--dry-run`:

```bash
./try.sh
./try.sh --preset B_SHARED_10_10
```

Each invocation executes at most one physical solve, allocates a fresh
`runs/Axxx_<MODE>_R<bits>_C<bits>/` directory, and refuses to overwrite an
existing run. This platform does not automatically execute A/B/C as a batch.
The default dry-run is compact: it shows topology, row/column mapping, the four
cells' final-read WL/BL/SE levels, source counts/amplitudes, timing, load chain,
probe count, and static-QA result. It creates no run directory and never
invokes JoSIM. Use `./try.sh --dry-run --verbose` only when you want the full
manifests, every PWL line, all probe names, and the complete rendered deck.

The initial stage schedule mirrors the current array platform: WRITE0
50–61 ps, READ0 70–81 ps, WRITE1 90–101 ps, FINAL READ 110–121 ps. Default
`DT=0.01p`, `STOP=250p`. Edit `USER_CASE.env` and `STIMULUS.env`, or edit one
of the preset files, before a manual run.

After an authorized manual run, the runner preserves deck, PWL stimulus,
snapshots, raw, stdout/stderr, solver log, manifests, actual-grid raw QA,
branch-current and per-cell arithmetic metrics, and a concise set of classic
`josim-plot2.py` HTML pages. Phase is raw radians; displayed phase turns are
`rad/(2*pi)` navigation arithmetic, never an SFQ count. The current task
creates no raw and makes no physical claim.
