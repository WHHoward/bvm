# BVM 4×4 diagonal-array platform

This render-first platform maps 16 independent `BVM → QB` cells onto seven
ascending-row serial diagonal chains. It uses the canonical BVM, QB, sJTL, CB,
and shared jjmit model without modifying their sources. In
`DIAGONAL_TERMINAL` mode, each diagonal output has its own 2 Ω resistor and T1,
CBU and DFF are not instantiated. `DIAGONAL_T1_INDEPENDENT` replaces those
terminal loads with seven isolated T1 channels. `DIAGONAL_T1_CHAIN` connects
seven T1s through six physical two-input CBU candidates, adds a physical D0
entrance sJTL and a DFF on C6. The current manual `USER_CASE.env` selects the
registered chain configuration; historical D3/PAPER presets explicitly pin
`DIAGONAL_TERMINAL` and remain independent of that manual selection.

## Cell and diagonal mapping

The leftmost ROW bit selects R1; the leftmost COL bit selects C1. The optional
`SE_ENABLE_MASK` is a row-major 4×4 matrix (`R1/R2/R3/R4`); `ALL` means sixteen
ones. During FINAL_READ a cell receives SE only if its row bit, column bit, and
mask bit are all 1. WL and BL remain physically shared during every stage.

For cell `(r,c)`, `d=r+3-c`. Within each diagonal, cells are ordered by
ascending row and use separate QB instances serially merged at successive
levels. Each configured level has zero or more serial sJTLs followed by one CB:

```text
BVM_r_c.SL → QB_r_c → MERGE_Dd_Lk → sJTL × SJTL_COUNT_Dd[k] → CB_Dd_Lk
```

Each CB output feeds the next MERGE level; the last CB feeds `DOUT_Dd` and its
own `R_TERM_Dd=2 Ω`. The MERGE labels are actual electrical shared nodes, not
subcircuits.

`USER_CASE.env` exposes one comma-separated count per diagonal level, e.g.
`SJTL_COUNT_D3=1,2,1,3`. List lengths must match the diagonal's 1/2/3/4/3/2/1
levels. A singleton preserves the historical instance/node names; multiple
stages receive unique `_S1`, `_S2`, … names; zero connects that level's MERGE
directly to its one CB. The current task only render-tests multi/zero counts;
the two authorized solves use one sJTL per level. The serial MERGE order and
one-CB-per-cell structure are unchanged.

## Run controls

Edit `USER_CASE.env`, `STIMULUS.env`, `config/T1_PARAMS.env`, and (for chain
mode) `config/CBU_PARAMS.env`, `config/DFF_PARAMS.env`, and
`config/D0_JTL_PARAMS.env`. The output modes are `DIAGONAL_TERMINAL`,
`DIAGONAL_T1_INDEPENDENT`, and `DIAGONAL_T1_CHAIN`; their required `T1_MODE`
values are `OFF`, `ALL_INDEPENDENT`, and `CHAIN`, respectively. `T1_MODE=OFF`
leaves T1 parameters out of terminal-mode decks.

The default `USER_CASE.env` uses the new 400 µA shared-source candidate. WL/BL
values are `BUS_SOURCE_TOTAL` setpoints, not per-BVM amplitudes. Real branch
currents are measured from raw `I(R_WL|XBVM_*)` and `I(R_BL|XBVM_*)`; equal
division is only a diagnostic reference. The older `D3_N0`…`D3_N4` and
`PAPER_1101_1101` presets explicitly retain the historical 200 µA setpoints and
are labeled legacy low-drive cases; A001–A006 raw and ZIPs are unchanged.

Probe profiles are:

- `compact`: shared bus-source currents plus all cell SL/MERGE and seven output boundaries.
- `focus` (default): all 48 per-cell input branch currents, D3 storage JM1/JM2
  P/V, all D3 QB output boundaries, focused QB internals, every D3 sJTL/CB JJ
  P/V, seven DOUTs, and terminal currents. Current default: 124 signals.
- `debug`: opt-in internal probes for all BVM/QB/sJTL/CB instances. The preview
  reports its raw estimate; execution stops before solving if it exceeds the
  ordinary single-raw storage guard.

The old names `diagonal_core` and `diagonal_focus` remain accepted aliases.

Preview the exact two-case 400 µA batch and its PWL/netlist match:

```bash
./try.sh --bus400-batch --dry-run
```

Run one editable/manual case, or the exact serial two-solve diagnostic batch:

```bash
./try.sh --preset BUS400_D3_N0 --dry-run
./try.sh --preset BUS400_D3_N0
./try.sh --bus400-batch
```

The BUS400 batch runs only `BUS400_D3_N0` then `BUS400_D3_N1`, allocating A007
and A008. The second case differs only in R1C1 FINAL_READ SE. A solver, raw,
mechanical, or standalone-plot failure in the first case stops the batch; no
retry or follow-up is automatic. The original six-run command is historical and
must not be rerun over A001–A006.

An additional manually completed run, when recorded in `experiment_manifest.json`
as A009, is included only by the explicit delta submission path. The incremental
delta uses the existing immutable BUS400 package as its base: A007/A008 raw is
not copied again, while their later visualization QA sidecars and A009 evidence
are included. A001–A006 remain referenced by their original package/raw hashes;
generated HTML stays local.

```bash
./try.sh --registered-batch
```

The scoped submit command is used after the two new cases pass QA; for this
batch use its `--delta` mode so the six unchanged legacy raws are referenced,
not copied. HTML stays local:

```bash
./submit.sh BVM4X4_BUS400_20261009 --delta --dry-run
./submit.sh BVM4X4_BUS400_20261009 --delta
```

The delta package contains only changes since the verified BUS400 checkpoint,
exact prior package/raw references, and a detached PACKAGE_QA. Generated HTML
and Plotly JS are excluded from the ZIP.

The A010–A012 append-only delta uses the A009 delta package as its base and
splits the changed source/manifest from one package per new raw. A001–A009 raw
is referenced by package/raw SHA and is not copied again.

The A017–A019 append-only delta uses the A013–A016 T1 checkpoint as its base.
A017's solver raw is preserved with `artifact_status=INVALID` because its
post-processing probe set mismatched the T1-loaded topology; A018/A019 have
mechanical QA PASS. Each new raw is packaged once, and A001–A016 raw is
referenced by exact package/raw SHA rather than recopied.

The registered T1 integration batch connects all seven DOUTs to independent T1
channels, removes the seven DOUT 2 Ω terminations, and preserves the serial
BVM/QB/sJTL/CB topology. Each T1 has its own `V_T1_LINK`, Bias1/2/3, CLK, S and
C nodes, and 12 Ω S/C loads. QUIET uses an independent 5 Ω clock clamp per
channel; PULSE uses seven identical, independent source/2 Ω branches. Run the
four-case batch once with:

```bash
./try.sh --t1-array-batch
```

Its preflight, metric specification and result table are under
`analysis/t1-array-20261009/`. Three responsive classic pages are generated per
run and remain local. T1 internal values are rendered from
`config/T1_PARAMS.env` into each run's `sources/t1_cell_tunable.cir`; the
canonical `circuits/t1/t1_cell.cir` remains unchanged and default-body
equivalence is checked.

For a manual `DIAGONAL_T1_INDEPENDENT` run, set
`PROBE_PROFILE=t1_array_focus`. The terminal-mode `focus`/`compact`/`debug`
probe sets request `R_TERM_D0…D6` and do not collect T1 inputs, clocks, S/C or
internal JJ signals; the runner rejects that mismatch before invoking JoSIM.
Select the manual T1 clock directly with `T1_CLK_MODE=QUIET` or `PULSE` in
`USER_CASE.env`; pulse start/period/amplitude/edge/series-resistance settings
remain in `config/T1_PARAMS.env`.
T1 pages use the historical `josim-plot2.py` canvas defaults (no per-trace
height override), with a shared relative Plotly JS asset and responsive width.

### Seven-stage ripple carry + global synchronous clock (A020-A022)

The chain uses D0→one experiment-local sJTL→T1_D0. For D1-D6, each DOUT and
the previous T1 Carry enter different pins of one physical `THmitll_MERGE`
instance; its output feeds that stage's T1. S0-S6 remain separate product
outputs. C0-C5 directly drive the next CBU; C6 drives `THmitll_DFF`, whose O is
bit7. The array's one-input `CB_0928.cir` remains unchanged and is not used as a
two-input CBU.

The CBU/DFF sources are run-local parameterized copies of the ColdFlux
`circuits/standard/MERGE.cir` and `DFF.cir`; only the MERGE smart-quote syntax
is corrected in the local rendered copy. Defaults are compared with the
candidate bodies, and canonical source files are never changed. The D0 JTL
copy uses the exact default active values from canonical `sJTL_0923.cir`; its
count and parameters are separately configurable. The initial DFF.O 12 Ω
load is an explicit measurement-load candidate, not a validated optimum.
Compatibility details and source hashes are in
`analysis/t1-chain-20261009/CBU_COMPATIBILITY.md` and the run manifests.

One-shot global clock configuration is in `USER_CASE.env` and
`config/T1_PARAMS.env`. `GLOBAL_ONESHOT` produces eight independent branches
(seven T1 and one DFF), each with a single PWL at 200 ps, 1.2 mV, 1/2/1 ps
rise/hold/fall and 2 Ω series resistance. `QUIET` clamps all eight clock pins
independently; no clock pin is left floating. There is no periodic repetition
or staggered clock in this mode.

The three editable presets reproduce the registered cases:

```bash
./try.sh --preset CHAIN_ALL_QUIET --dry-run
./try.sh --preset CHAIN_ALL_GLOBAL_CLOCK --dry-run
./try.sh --preset CHAIN_PAPER_GLOBAL_CLOCK --dry-run
```

Run the unified static/preflight check without solving:

```bash
./try.sh --t1-chain-batch --dry-run
```

After the preflight is locked, the bounded batch command is:

```bash
./try.sh --t1-chain-batch
```

It is limited to A020-A022 in order and halts on the first solver or artifact
failure. It does not decode output bits, tune parameters, or launch a follow-up.
The chain work unit, registered windows, and result tables live under
`analysis/t1-chain-20261009/`; each run preserves its actual deck, all effective
configuration snapshots, rendered CBU/DFF/JTL/T1 source snapshots, solver logs,
immutable raw, QA, and three classic `josim-plot2.py` pages. HTML stays local.

After results are complete, the existing local submit workflow creates a DELTA
against the A017-A019 checkpoint; it does not repackage A001-A019 raw:

```bash
./submit.sh 20261009 --delta --dry-run
./submit.sh 20261009 --delta
```

Because each new raw is near the ordinary single-file storage limit, this
chain DELTA groups the changed source once, the three runs' non-raw evidence in
one metadata ZIP, and each immutable raw in its own ZIP. It is five new ZIPs in
total; A001-A019 raw is referenced by SHA and not copied.

The six presets are `D3_N0` through `D3_N4` and `PAPER_1101_1101`. The latter
uses ROW/COL `1101/1101` with all SE mask bits on. The preregistered diagonal
target vector is `[1,1,1,3,1,1,1]`; it is not an event classifier or a result.

### D1 shared-node canonical CB candidate (A023/A024)

`CBU_OVERRIDE_D1` selects a local D1 implementation while `CBU_TYPE` remains
the default for D2-D6:

- `NONE`: all six CBU stages use `CBU_TYPE` (`THmitll_MERGE` by default).
- `CB_DIRECT`: DOUT_D1 and T1_D0.C each connect through their own 0-V current
  sensor to `CBU_JOIN_D1`; one canonical `CB_0928` (`IN,OUT`) feeds T1_D1.
  There is no isolator or added sJTL. The shared node permits reverse coupling.
- `CB_CARRY_BUFFER`: only C_D0 passes through one canonical `CB_0928`; its
  output and the existing array DOUT_D1 CB output join at `CBU_JOIN_D1` and
  directly feed T1_D1. No additional sJTL/JTL is inserted.

The two exact presets are:

```bash
./try.sh --dry-run --preset CB_DIRECT_D1_ALL_CLOCK
./try.sh --dry-run --preset CB_DIRECT_D1_PAPER_CLOCK
./try.sh --dry-run --preset CHAIN_ALL_GLOBAL_CLOCK --set CBU_OVERRIDE_D1=CB_DIRECT
```

### Per-level Carry sJTL count (D3 timing A040/A041)

`CARRY_SJTL_COUNT_BY_STAGE` optionally accepts six nonnegative integers in
`D1,D2,D3,D4,D5,D6` order. When set, `CARRY_SJTL_STAGE_MASK` must match which
counts are nonzero; a mismatch or simultaneous legacy
`CARRY_POST_CB_SJTL_COUNT=1` is rejected. Leave the list empty to retain the
historical stage-mask and legacy POST-CB behavior. A single sJTL retains the
old instance/node names; additional serial devices use `_S2`, `_S3`, … names
and explicit zero-volt interstage current sensors.

Render the two registered D3 candidates without solving:

```bash
./try.sh --dry-run --preset D3_PRE_CB_SJTL_0_ALL_200
./try.sh --dry-run --preset D3_PRE_CB_SJTL_2_ALL_200
./try.sh --dry-run --preset D3_PRE_CB_SJTL_0_ALL_200 \
  --set CARRY_SJTL_COUNT_BY_STAGE=1,1,2,1,1,1 \
  --set CARRY_SJTL_STAGE_MASK=111111
```

The A040/A041 batch preflight and execution are task-local under
`analysis/d3-carry-timing-20261010/`; it is strictly limited to those two run
IDs and requires the locked preflight commit before solver execution.

The bounded batch executor is:

```bash
python3 scripts/d3_carry_timing_batch.py --check
python3 scripts/d3_carry_timing_batch.py --prepare-preflight
# Commit the preflight/source changes, then:
python3 scripts/d3_carry_timing_batch.py --execute
./submit.sh A040_A041_20261010 --d3-carry-timing --dry-run
./submit.sh A040_A041_20261010 --d3-carry-timing
```

In this focus profile, the T1/DFF bias and clock settings are retained in the
configuration, deck, source and provenance, while representative bias-current,
clock-series-current, DFF-internal-JJ and DFF load-current traces are omitted;
the registered boundary voltages and DFF data-link current remain recorded.

The registered two-run workflow is bounded to A023/A024 and first performs
static deck, source, probe and JoSIM `-s` checks without a transient solve:

```bash
python3 scripts/cb_direct_d1_batch.py --prepare-preflight
# Commit the platform/preflight changes; then, on the clean preflight commit:
python3 scripts/cb_direct_d1_batch.py --run-batch
python3 scripts/submit.py 20261009 --delta --dry-run
```

It pairs A023 with A021 and A024 with A022. Per-run focus pages and two paired
classic `josim-plot2.py` pages stay local. The DELTA contains only new platform,
analysis and A023/A024 evidence; A001-A022 raw are referenced by exact hashes,
not recopied. This study uses a single active D1 source branch per matched
condition and does not test two simultaneously active D1 inputs or decide
functional success.

### D1 carry-side CB_0928 buffer (A025/A026)

Preview the two exact registered cases with:

```bash
./try.sh --dry-run --preset CARRY_CB_D1_ALL_CLOCK
./try.sh --dry-run --preset CARRY_CB_D1_PAPER_CLOCK
```

The bounded A025/A026 batch is preflighted and run by:

```bash
python3 scripts/cb_carry_buffer_d1_batch.py --prepare-preflight
# Commit the platform/preflight changes; then execute only the two registered runs.
python3 scripts/cb_carry_buffer_d1_batch.py --run-batch
./submit.sh A025_A026_20261009 --delta --dry-run
./submit.sh A025_A026_20261009 --delta
```

The D1 focus captures both incoming branches, the new CB input/output and
BJ1/BJ2 P/V, the D1 array final-CB BJ1/BJ2 P/V, and the downstream T1. All
seven T1 external boundaries and D2-D6 CBU boundaries remain; T1 internal
P/V is retained for D0/D1 only in this focused batch to keep each raw under
the existing single-file size guard without changing DT or sampling. Reports
contain registered actual-grid arithmetic and paired values only; scientific
interpretation remains with the user. Generated HTML is local and excluded
from the DELTA ZIP.

### Full six-stage CB-only Carry chain (A027-A029)

`CBU_CHAIN_TOPOLOGY=CB_CARRY_BUFFER_ALL` replaces every D1-D6 two-input CBU
stage with two sensed branches: the existing array `DOUT_Dk` goes directly to
`JOIN_Dk`; `C_D(k-1)` passes through exactly one canonical `CB_0928`, whose
output joins at `JOIN_Dk`; the join directly feeds `T1_Dk.I`. D0's entrance
JTL and C6-to-DFF connection remain unchanged. No ColdFlux MERGE instance,
extra sJTL/JTL, or post-JOIN CB is instantiated. The selector conflicts with
any non-`NONE` `CBU_OVERRIDE_D1` and fails closed.

Preview each registered full-chain case without solving:

```bash
./try.sh --dry-run --preset FULL_CB_CHAIN_ALL_CLOCK
./try.sh --dry-run --preset FULL_CB_CHAIN_PAPER_CLOCK
./try.sh --dry-run --preset FULL_CB_CHAIN_3X3_CLOCK
```

The exact three-run static gate and physical batch are managed by:

```bash
python3 scripts/cb_carry_buffer_all_batch.py --prepare-preflight
# Commit the locked preflight/source changes; then run exactly A027-A029.
python3 scripts/cb_carry_buffer_all_batch.py --run-batch
./submit.sh A027_A029_20261009 --delta --dry-run
./submit.sh A027_A029_20261009 --delta
```

Each run keeps the full chain boundaries, all T1 critical JJ P/V, all six
Carry-CB BJ1/BJ2 P/V and branch sensors. Eight classic pages are generated per
run: full-chain overview, carry propagation, and a focused page for each
D1-D6 stage. All HTML stays local; the DELTA references A001-A026 raw SHA and
contains only A027-A029 raw/evidence.

### Carry CB followed by one canonical sJTL (A030-A033)

`CARRY_POST_CB_SJTL_COUNT=0|1` is an optional extension of
`CBU_CHAIN_TOPOLOGY=CB_CARRY_BUFFER_ALL`: `0` keeps the A027-A029 topology;
`1` places exactly one canonical `sJTL_0923` after each D1-D6 Carry `CB_0928`
and before that stage's JOIN. The field is fail-closed to 0/1. It does not
change array-internal sJTL counts, BVM/QB/CB/T1/DFF parameters, or the D0 JTL.

The fixed four-run matrix is:

| Run | ROW/COL | Carry post-CB sJTL | Global one-shot start |
|---|---|---:|---:|
| A030 `CARRY_POST_CB_SJTL_ALL_200` | 1111/1111 | one at D1-D6 | 200 ps |
| A031 `CARRY_POST_CB_SJTL_ALL_210` | 1111/1111 | one at D1-D6 | 210 ps |
| A032 `CARRY_POST_CB_SJTL_PAPER_210` | 1101/1101 | one at D1-D6 | 210 ps |
| A033 `CARRY_POST_CB_SJTL_3X3_210` | 1100/0011 | one at D1-D6 | 210 ps |

All clocks remain synchronous across seven T1s and the DFF; only their absolute
start time changes as registered. 210 ps is not a validated frequency or
hardware delay claim. The four local classic pages per run separate ARRAY,
CARRY, JOIN and T1. The DOUT/JOIN voltage is a shared boundary voltage; use the
array-final-CB JJ P/V and `I(V_CBU_A_Dk)` for source-attributed array evidence,
not DOUT voltage-area as an array event count.

```bash
./try.sh --dry-run --preset CARRY_POST_CB_SJTL_ALL_200
./try.sh --dry-run --preset CARRY_POST_CB_SJTL_ALL_210
./try.sh --dry-run --preset CARRY_POST_CB_SJTL_PAPER_210
./try.sh --dry-run --preset CARRY_POST_CB_SJTL_3X3_210
python3 scripts/carry_post_cb_sjtl_batch.py --prepare-preflight
# Commit the locked source/preflight state before executing the four authorized runs.
python3 scripts/carry_post_cb_sjtl_batch.py --run-batch
./submit.sh CARRY_POST_CB_SJTL_A030_A033_20261010 --delta --dry-run
./submit.sh CARRY_POST_CB_SJTL_A030_A033_20261010 --delta
```

The batch runner executes A030/A031 first and stops on a solver or artifact
failure; valid physical outcomes, whether expected or not, do not change the
remaining registered run set. The DELTA references A001-A029 and packages only
A030-A033 raw/evidence. HTML remains local and is excluded from packages.

### Carry sJTL placement and stage-mask comparison (A034-A039)

The historical `CARRY_POST_CB_SJTL_COUNT=0|1` control remains compatible:
`1` means one canonical post-CB sJTL at every stage D1-D6. New runs should set
that legacy field to `0` and use:

```ini
CARRY_SJTL_POSITION=PRE_CB|POST_CB
CARRY_SJTL_STAGE_MASK=010000
```

The six mask bits map left-to-right to D1-D6 (`010000` selects D2,
`111111` selects all, `000000` selects none). PRE_CB renders
`T1.C -> sJTL_0923 -> CB_0928 -> JOIN`; POST_CB renders
`T1.C -> CB_0928 -> sJTL_0923 -> JOIN`. The array DOUT branch, D0 JTL, CB,
all upstream device parameters, and global clock conditions are unchanged.
If the legacy nonzero count and a nonzero new mask are both requested, config
validation stops with an ambiguity error rather than stacking devices.

The six exact cases are:

| Run | ROW/COL | Carry sJTL | Clock |
|---|---|---|---:|
| A034 `CARRY_SJTL_D2_ONLY_ALL_200` | 1111/1111 | POST_CB at D2 only | 200 ps |
| A035 `CARRY_SJTL_D2_ONLY_PAPER_200` | 1101/1101 | POST_CB at D2 only | 200 ps |
| A036 `CARRY_SJTL_PRE_ALL_200` | 1111/1111 | PRE_CB at D1-D6 | 200 ps |
| A037 `CARRY_SJTL_PRE_ALL_210` | 1111/1111 | PRE_CB at D1-D6 | 210 ps |
| A038 `CARRY_SJTL_PRE_PAPER_210` | 1101/1101 | PRE_CB at D1-D6 | 210 ps |
| A039 `CARRY_SJTL_PRE_3X3_210` | 1100/0011 | PRE_CB at D1-D6 | 210 ps |

Every new run has full-chain, ARRAY, CARRY, JOIN, T1/DFF and six stage-focused
classic `josim-plot2.py` pages. Paired comparisons use each raw's native stored
grid independently; no interpolation or resampling is performed. Shared
`V(DOUT_Dk)`/JOIN voltages are source-mixed boundaries, not array-only event
counts. `P(...)` remains radians; signed and positive/negative phase variation
are descriptive arithmetic, not SFQ/event counts.

```bash
./try.sh --dry-run --preset CARRY_SJTL_D2_ONLY_ALL_200
./try.sh --dry-run --preset CARRY_SJTL_D2_ONLY_PAPER_200
./try.sh --dry-run --preset CARRY_SJTL_PRE_ALL_200
./try.sh --dry-run --preset CARRY_SJTL_PRE_ALL_210
./try.sh --dry-run --preset CARRY_SJTL_PRE_PAPER_210
./try.sh --dry-run --preset CARRY_SJTL_PRE_3X3_210
python3 scripts/carry_sjtl_position_batch.py --prepare-preflight
# Commit the locked source and preflight snapshot before running the authorized matrix.
python3 scripts/carry_sjtl_position_batch.py --run-batch
python3 scripts/analyze_carry_sjtl_position.py
./submit.sh BVM4X4_CARRY_SJTL_POSITION_20261010 --delta --dry-run
./submit.sh BVM4X4_CARRY_SJTL_POSITION_20261010 --delta
```

The batch runner checks and executes only A034-A039 serially, stopping on a
solver/artifact-integrity failure. A valid but unexpected physical output is
preserved as evidence and does not alter the remaining registered run set.
The DELTA references A001-A033 by their existing package/raw identities and
adds only A034-A039 evidence; all generated HTML remains local.

## Evidence and plots

Each run records actual deck, exact PWL stimulus, effective topology/config
snapshots, solver identity and logs, immutable raw, raw/mechanical QA, actual
branch-current and same-JJ phase/voltage arithmetic for WRITE0, READ0, WRITE1,
FINAL READ, and FINAL READ RESPONSE. Each run gets two compact classic
`josim-plot2.py` pages; the matched pair gets one focused comparison. All use
native samples without interpolation or resampling. Generated HTML and Plotly
JS are not included in ZIPs. `P(...)` raw values are radians; `rad/(2π)` is
navigation arithmetic, never an SFQ count.

T1 parameters are managed by `config/T1_PARAMS.env`. Independent T1 channels do
not connect to one another. The chain mode is an exploratory physical candidate
and does not establish multiplier function, bit decoding, or a 20 GHz system
claim.

### Manual-run DELTA submission

New unregistered manual runs (`batch_id=null`) are automatically routed by
`--delta` when they are present in `experiment_manifest.json` but not in the
latest package checkpoint. Preview, then submit with:

```bash
./submit.sh <unique-tag> --delta --dry-run
./submit.sh <same-tag> --delta
```

Use `--manual-runs` instead of `--delta` to explicitly select this route. The
workflow validates every newly discovered run and raw SHA, commits only the
run metadata/manifest (raw CSVs are not committed directly), makes one raw ZIP
per run plus one metadata ZIP, excludes HTML, records the checkpoint for the
next call, pushes, and verifies the D-drive mirror (`/mnt/d/BVM_Backages`) SHA-256. It
references prior raw/package identities rather than repackaging them and makes
no retroactive authorization or scientific claim. Do not combine manual runs
with an unfinished registered batch; the workflow stops on that ambiguity.

If the raw CSVs should also be tracked directly in Git after they are already
present in the ZIP checkpoint, use this separate command. It verifies each raw
against its run QA, checkpoint reference, and raw-package member SHA; it does
not rebuild or replace the existing ZIPs:

```bash
./submit.sh RAW_A076_A078 --track-packaged-raws --dry-run
./submit.sh RAW_A076_A078 --track-packaged-raws
```

Raw files over the repository's 100 MB single-file limit, or files with an
implicit Git LFS/filter rule, are rejected before staging.
