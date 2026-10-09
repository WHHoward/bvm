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
