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

Every cell gets the same sequence: WRITE0, READ0 control, WRITE1, then FINAL
READ. Row/column bits affect only FINAL READ. When enabled, SECOND_READ is
appended after a recovery interval; it uses its own row/column bits and always
uses per-cell crosspoint SE gating, independent of the first-read
`SE_GATE_MODE`. BL is zero in both reads.
`SECOND_READ_ENABLE` defaults to `0` (also when omitted in legacy configs or
presets), preserving the old netlist/PWL stage sequence.

The four amplitude fields are positive magnitudes. WRITE0 applies negative WL
and BL pulses; WRITE1 applies positive WL and BL pulses; READ0 applies positive
WL and SE pulses to all rows/columns; FINAL READ keeps BL at zero. SE gating is
selected by `SE_GATE_MODE`: `COLUMN` enables SE on each selected column,
whereas `CROSSPOINT` enables a cell-local SE source only when both its row and
column bits are 1. The read amplitude fields are used for READ0 and FINAL READ.
The optional second-read SE gate ignores `SE_GATE_MODE` and always uses the
intersection of `SECOND_ROW_BITS` and `SECOND_COL_BITS`.

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
./try.sh --preset E0_A005_CROSSPOINT_SECOND_READ --dry-run
./try.sh --preset E1_A006_COLUMN_SECOND_READ --dry-run
./try.sh --preset A_SAME_COLUMN_DUAL_CROSSPOINT --dry-run
./try.sh --preset B_ALL_CELL_CROSSPOINT --dry-run
./try.sh --preset C_MIXED_STORAGE_SEQUENTIAL_WRITE --dry-run
```

To execute exactly one current configuration manually, omit `--dry-run`:

```bash
./try.sh
./try.sh --preset B_SHARED_10_10
./try.sh --preset D0_CELL_SE_COLUMN_10_10
./try.sh --preset D1_CELL_SE_CROSSPOINT_10_10
./try.sh --preset E0_A005_CROSSPOINT_SECOND_READ
./try.sh --preset E1_A006_COLUMN_SECOND_READ
./try.sh --preset A_SAME_COLUMN_DUAL_CROSSPOINT
./try.sh --preset B_ALL_CELL_CROSSPOINT
./try.sh --preset C_MIXED_STORAGE_SEQUENTIAL_WRITE
```

Each invocation executes at most one physical solve, allocates a fresh
`runs/Axxx_<MODE>_R<bits>_C<bits>/` directory, and refuses to overwrite an
existing run. This platform does not automatically execute A/B/C as a batch.
Dry-run does not reserve a number, so repeated previews may show the same next
ID. Actual invocations scan all existing Axxx directories. At the 2026-09-29
batch parent, A001–A009 were present, so the newly authorized A/B/C cases are
allocated A010, A011, and A012 in serial order.
The default dry-run is compact: it shows topology, row/column mapping, the four
cells' final-read WL/BL/SE levels, source counts/amplitudes, timing, load chain,
probe count, and static-QA result. It creates no run directory and never
invokes JoSIM. Use `./try.sh --dry-run --verbose` only when you want the full
manifests, every PWL line, all probe names, and the complete rendered deck.

The initial stage schedule mirrors the current array platform: WRITE0
50–61 ps, READ0 70–81 ps, WRITE1 90–101 ps, FINAL READ 110–121 ps. E0/E1 add
SECOND_READ 170–181 ps. `SECOND_READ_ENABLE` defaults to `0`; the first four
stages and the rendered netlist/stimulus remain the legacy behavior when the
new fields are omitted or disabled. Default `DT=0.01p`, `STOP=250p`; E0/E1
override STOP to 300p. Edit `USER_CASE.env` and `STIMULUS.env`, or edit one
of the preset files, before a manual run. The 2026-09-29 E0/E1/A/B/C cases all
use preset-specific settings and do not require changing this editable file.

For a manual configuration, set `SECOND_READ_ENABLE=1`,
`SECOND_ROW_BITS=01`, and `SECOND_COL_BITS=10` in `USER_CASE.env`; set
`SECOND_READ_START=170p`, `SECOND_READ_RISE=1p`, `SECOND_READ_HOLD=9p`,
and `SECOND_READ_FALL=1p` in `STIMULUS.env`. Enabling SECOND_READ requires
effective `SE_TOPOLOGY=CELL`.

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
electrically distinct. Existing A001–A006 evidence is preserved.

## E0/E1 repeat-read conditions

E0 reuses A005's first-read CROSSPOINT gating; E1 reuses A006's first-read
COLUMN gating. Their first-read settings and all preparation stages are
otherwise identical. Both then perform a second, normal read of R2C1:

| Stage | Window | WL row sources (R1/R2) | BL column sources (C1/C2) | Cell SE sources (R1C1, R1C2, R2C1, R2C2) |
|---|---|---|---|---|
| WRITE0 | 50–61 ps | −200/−200 µA | −200/−200 µA | 0/0/0/0 |
| READ0 | 70–81 ps | +200/+200 µA | 0/0 | +100/+100/+100/+100 µA |
| WRITE1 | 90–101 ps | +200/+200 µA | +200/+200 µA | 0/0/0/0 |
| FINAL_READ (first read) | 110–121 ps | +200/0 µA | 0/0 | E0: 100/0/0/0; E1: 100/0/100/0 µA |
| Recovery | 121–170 ps | 0 | 0 | 0/0/0/0 |
| SECOND_READ | 170–181 ps | 0/+200 µA | 0/0 | 0/0/+100/0 µA |

These are programmed ideal-source PWL setpoints, not measured BVM branch
currents. Raw probes retain each BVM's actual WL, BL, and SE input currents.
The second-read SE gate is fixed to CELL_CROSSPOINT, so only R2C1 receives SE
in both E0 and E1 regardless of their first-read SE_GATE_MODE.

For a manual run, inspect FINAL_READ, RECOVERY_BEFORE_SECOND_READ, and
SECOND_READ as separate half-open windows. The runner computes per-window
same-JJ phase/voltage arithmetic and boundary metrics on actual stored rows;
it never treats 110–300 ps as one read area. Three focused R2C1 pages use the
existing classic `josim-plot2.py` renderer. Dry-run does not reserve a run
number; if no other run intervenes, E0 then E1 allocate A007 and A008.

## Authorized 2026-09-29 A/B/C batch

All three new presets preserve the eight-driver SHARED/CELL topology, canonical
source hashes, four independent BVM→QB→1 sJTL→1 CB→2 Ω VOUT chains, 200 µA
write amplitudes, 200 µA WL read amplitude, 100 µA cell-SE read amplitude, and
DT=0.01 ps. Run them serially so the non-overwriting allocator assigns A010–A012.

| Run | Read selection | Extra sequence | STOP |
|---|---|---|---:|
| A — `A_SAME_COLUMN_DUAL_CROSSPOINT` | first: rows 11 / columns 10; second: R1C1 only at 170–181 ps | A009 comparison uses first response [110,170) ps | 250 ps |
| B — `B_ALL_CELL_CROSSPOINT` | all four at 110–121 ps | no second read | 250 ps |
| C — `C_MIXED_STORAGE_SEQUENTIAL_WRITE` | all four at 170–181 ps | WRITE0 all lines; then R1C1 via WL_R1+BL_C1 at 90 ps and R2C2 via WL_R2+BL_C2 at 120 ps; READ0 omitted | 300 ps |

C intentionally keeps shared WL/BL buses. Its registered per-write map lists
the simultaneously exposed WL-only, BL-only, and unselected cells; no per-cell
WL/BL drivers are created. Actual input-branch currents are raw evidence, not
assumed from source setpoints. The whole response window is [170,300) ps.

Read-response arithmetic reports signed output min/max/p2p, positive-maximum
time, and signed V(t) area for BVM_SL, QB_OUT, SJTL_OUT, and VOUT using stored
raw rows. Same-JJ phase-radian delta and voltage-area/Phi0 arithmetic are
retained for BVM, QB, sJTL, and CB junctions. No pulse/SFQ event classifier or
threshold is registered; scientific interpretation remains NOT PERFORMED.
Per-run full-range classic `josim-plot2.py` pages and focused full-response
pages are generated locally. The registered exact-grid comparisons and
independent arithmetic audit are rebuilt with:

```bash
python3 scripts/build_batch_comparison.py
python3 scripts/audit_batch_arithmetic.py
```

This writes A009/A010 first-response and A010/A011/A012 full-output comparisons
under `plots/comparison/`, plus source-hash/alignment QA under `analysis/`.
Only exact common stored timestamps are retained; no interpolation occurs. The
arithmetic audit independently recomputes branch currents, output peak times
and signed areas, and same-JJ phase/voltage arithmetic from raw tokens; it does
not classify SFQ/pulse event counts. Generated HTML is excluded from evidence
ZIPs.

After an authorized manual run, the runner preserves deck, PWL stimulus,
snapshots, raw, stdout/stderr, solver log, manifests, actual-grid raw QA,
branch-current and per-cell arithmetic metrics, and a concise set of classic
`josim-plot2.py` HTML pages. Phase is raw radians; displayed phase turns are
`rad/(2*pi)` navigation arithmetic, never an SFQ count. The earlier static
platform update created no run/raw; the later authorized A010–A012 runs are
listed in `experiment_manifest.json`. Their event-count and physical
interpretation remain for scientific review.
