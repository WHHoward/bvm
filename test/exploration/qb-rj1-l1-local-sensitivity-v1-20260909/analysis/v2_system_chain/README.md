# V2 system-chain visualization repair

This is a versioned read-only presentation repair for
`qb-rj1-l1-local-sensitivity-v1-20260909`. It reads only the five existing
immutable raw files. It performs zero new physical solves and does not modify
the original `plots/`, `analysis/` artifacts or `RESULT_BRIEF.md`.

## Fixed five-layer structure

Every standalone run and every family comparison uses the same physical order
and signal ordering:

1. `01_SIGNAL_TIMING`: controls and system timing landmarks from the final
   READ through terminal;
2. `02_BVM_STATE`: active BVM storage/R-loop/output plus independent quiet-cell
   traces for BVM2--BVM4;
3. `03_JSL_CHAIN`: all eight JSL phase, voltage and current traces;
4. `04_QB_STATE`: `QBIN -> Lin -> BJS -> BJ1/RJ1 -> L1/IB/L2 -> BJ2/RJ2 -> L3 -> QBOUT`;
5. `05_JTL_CHAIN`: all six JTL levels, output nodes and termination.

The standalone windows are the registered full/final/read, BVM, JSL, QB and
JTL windows. Each family comparison includes `OVERVIEW_0_200ps`,
`SYSTEM_CRITICAL_101_135ps`, and `FINAL_READ_110_121ps`; QB/JTL comparisons
also include `110_130ps`.

## Data handling

The source raw paths and SHA-256 values are in `raw_reference.json` and every
page entry in `manifest.json`. Window inputs are exact half-open stored-row
slices. Phase pages independently unwrap each run's raw radians and let
`josim-plot2.py -j 2pi` display `rad/(2*pi)` turns; this is a display/derived
operation, never an SFQ count. The only additional numerical diagnostic is the
registered JSL series-current residual
`max_t |I(B_JSLk)-I(B_JSL1)|`, for `k=2..8`.

The optional `V(IB|XBQ1)` probe remains `UNKNOWN` because the current raw files
do not emit that column. No replacement signal is fabricated.

See `manifest.json`, `visualization_qa.json`, `V2_RESULT_ADDENDUM.md` and
`run_summaries/` for the complete navigation and audit trail.
