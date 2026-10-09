# BVM 4×4 diagonal-array platform v1

This render-first platform maps 16 independent `BVM → QB` cells onto seven
ascending-row serial diagonal chains. It uses the canonical BVM, QB, sJTL, CB,
and shared jjmit model without modifying their sources. Each diagonal output is
independent and terminated by its own 2 Ω resistor. T1/CBU/DFF are not
instantiated.

## Cell and diagonal mapping

The leftmost ROW bit selects R1; the leftmost COL bit selects C1. The optional
`SE_ENABLE_MASK` is a row-major 4×4 matrix (`R1/R2/R3/R4`); `ALL` means sixteen
ones. During FINAL_READ a cell receives SE only if its row bit, column bit, and
mask bit are all 1. WL and BL remain physically shared during every stage.

For cell `(r,c)`, `d=r+3-c`. Within each diagonal, cells are ordered by
ascending row and use separate QB instances serially merged at successive
levels:

```text
BVM_r_c.SL → QB_r_c → MERGE_Dd_Lk → sJTL_Dd_Lk → CB_Dd_Lk
```

Each CB output feeds the next MERGE level; the last CB feeds `DOUT_Dd` and its
own `R_TERM_Dd=2 Ω`. The MERGE labels are actual electrical shared nodes, not
subcircuits.

## Run controls

Edit `USER_CASE.env`, `STIMULUS.env`, and (for future reference only)
`config/T1_PARAMS.env`. Only `OUTPUT_MODE=DIAGONAL_TERMINAL` is executable.
`DIAGONAL_T1_INDEPENDENT` and `DIAGONAL_T1_CHAIN` are reserved and explicitly
rejected until their circuit implementations are validated. `T1_MODE=OFF`
leaves T1 parameters out of the netlist.

Preview all six registered configurations in one static pass:

```bash
./try.sh --dry-run --registered-matrix
```

Run one editable/manual case:

```bash
./try.sh --preset D3_N4 --dry-run
./try.sh --preset D3_N4
```

Run the exact authorized batch once, serially; the runner stops on any solver
or raw/mechanical-QA failure and never retries:

```bash
./try.sh --registered-batch
```

After the six runs and mechanical/visual QA pass, preview then create the
per-run raw handoffs plus shared metadata archive, commit, push, and mirror:

```bash
./submit.sh BVM4X4_20261009 --dry-run
./submit.sh BVM4X4_20261009
```

The submitter checks only this new experiment scope. HTML remains local; the
six raw-bearing run archives are separate because their aggregate raw bytes
exceed the single-file package guard.

The six presets are `D3_N0` through `D3_N4` and `PAPER_1101_1101`. The latter
uses ROW/COL `1101/1101` with all SE mask bits on. The preregistered diagonal
target vector is `[1,1,1,3,1,1,1]`; it is not an event classifier or a result.

## Evidence and plots

Each run records actual deck, exact PWL stimulus, effective config snapshots,
source/probe manifests, solver identity and logs, immutable raw, raw/mechanical
QA, output arithmetic, and three local classic `josim-plot2.py` pages. A
batch-level D3 comparison page uses the same raw signal and native timestamps;
no interpolation or resampling is performed. Generated HTML and Plotly JS are
not included in ZIPs. `P(...)` raw values are radians; `rad/(2π)` is navigation
arithmetic, never an SFQ count.

Future T1 parameters are recorded in `config/T1_PARAMS.env`, but this task has
no T1, CBU, carry-chain, or DFF implementation. Those modes fail closed.
