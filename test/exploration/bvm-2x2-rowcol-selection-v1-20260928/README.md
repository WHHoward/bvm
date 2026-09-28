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
The two column BL buses and two column SE buses are distinct electrical nodes
in the legacy `SE_TOPOLOGY=SHARED_COLUMN` mode.

Every cell gets the same pre-final sequence: WRITE0, READ0 control, WRITE1,
then FINAL READ. Row/column bits affect only FINAL READ. BL is zero throughout
FINAL READ; a cell is at an active crosspoint only when its row WL and column
SE are both enabled.

The four amplitude fields are positive magnitudes. WRITE0 applies negative WL
and BL pulses; WRITE1 applies positive WL and BL pulses; READ0 applies positive
WL and SE pulses to all rows/columns; FINAL READ keeps BL at zero. SE gating is
selected by `SE_GATE_MODE`: `COLUMN` enables SE on each selected column,
whereas `CROSSPOINT` enables a cell-local SE source only when both its row and
column bits are 1. The read amplitude fields are used for READ0 and FINAL READ.

`INDEPENDENT` retains four cell-level WL/BL/SE driver triplets. In `SHARED`,
`SE_TOPOLOGY=SHARED_COLUMN` retains the legacy two row-WL, two column-BL, and
two column-SE sources (6 total). `SE_TOPOLOGY=CELL` keeps WL shared by row and
BL shared by column but uses four independent SE nodes/sources (8 total).
`CROSSPOINT` requires cell-local SE nodes. These configured source amplitudes
are not assumed equal to actual BVM input branch currents; those are probed for
later real solves. If an older USER_CASE or preset omits either new field, the
runner defaults to `SHARED_COLUMN/COLUMN`; the legacy A/B/C presets explicitly
retain that behavior. In `DRIVE_MODE=INDEPENDENT`, the four-cell independent
driver topology remains authoritative and its effective SE topology is
cell-local.

## Presets and operation

The checked-in `USER_CASE.env` is the direct one-run configuration (currently
`SHARED/SHARED_COLUMN/COLUMN`):

```bash
./try.sh --dry-run
```

Available presets:

```bash
./try.sh --preset A_INDEPENDENT_10_10 --dry-run
./try.sh --preset B_SHARED_10_10 --dry-run
./try.sh --preset C_SHARED_11_11 --dry-run
./try.sh --preset D0_CELL_SE_COLUMN_10_10 --dry-run
./try.sh --preset D1_CELL_SE_CROSSPOINT_10_10 --dry-run
```

To execute exactly one current configuration manually, omit `--dry-run`:

```bash
./try.sh
./try.sh --preset B_SHARED_10_10
./try.sh --preset D0_CELL_SE_COLUMN_10_10
./try.sh --preset D1_CELL_SE_CROSSPOINT_10_10
```

Each invocation executes at most one physical solve, allocates a fresh
`runs/Axxx_<MODE>_R<bits>_C<bits>/` directory, and refuses to overwrite an
existing run. This platform does not automatically execute A/B/C as a batch.
Dry-run does not reserve a number, so repeated previews may show the same next
ID. Actual invocations scan all existing Axxx directories; running D0 then D1
allocates distinct successive IDs (currently A004 then A005 if no other run is
added).
The default dry-run is compact: it shows topology, row/column mapping, the four
cells' final-read WL/BL/SE levels, source counts/amplitudes, timing, load chain,
probe count, and static-QA result. It creates no run directory and never
invokes JoSIM. Use `./try.sh --dry-run --verbose` only when you want the full
manifests, every PWL line, all probe names, and the complete rendered deck.

The initial stage schedule mirrors the current array platform: WRITE0
50–61 ps, READ0 70–81 ps, WRITE1 90–101 ps, FINAL READ 110–121 ps. Default
`DT=0.01p`, `STOP=250p`. Edit `USER_CASE.env` and `STIMULUS.env`, or edit one
of the preset files, before a manual run.

## D0/D1 cell-local SE conditions

D0 and D1 share the same 10×10 row/column bits and all WRITE0, READ0, and
WRITE1 settings: two shared WL row sources and two shared BL column sources
use 200 µA; READ0 uses 200 µA per row WL and 100 µA on each of four independent
cell SE sources. FINAL READ uses 200 µA on selected row WL, zero BL, and a
100 µA candidate on cell-local SE sources:

| Cell | WL FINAL | BL FINAL | D0 SE (COLUMN) | D1 SE (CROSSPOINT) |
|---|---:|---:|---:|---:|
| R1C1 | 200 µA | 0 | 100 µA | 100 µA |
| R1C2 | 200 µA | 0 | 0 | 0 |
| R2C1 | 0 | 0 | 100 µA | 0 |
| R2C2 | 0 | 0 | 0 | 0 |

Every BVM's SE pin is connected to its own node `SE_RxCy` and its own source;
CELL mode does not merely rename a shared column node: the four SE nodes are
electrically distinct. D0/D1 raw and QA will
be added under this same `runs/` tree and the root experiment manifest when
you manually execute each preset. This platform task performs dry-runs only.

After an authorized manual run, the runner preserves deck, PWL stimulus,
snapshots, raw, stdout/stderr, solver log, manifests, actual-grid raw QA,
branch-current and per-cell arithmetic metrics, and a concise set of classic
`josim-plot2.py` HTML pages. Phase is raw radians; displayed phase turns are
`rad/(2*pi)` navigation arithmetic, never an SFQ count. The current task
creates no experiment run/raw evidence and makes no physical claim.
