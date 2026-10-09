This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

# Preflight — BVM 4×4 diagonal array

- Parent HEAD: `df0249419c7a91ceb72b1fb0ed1d04981a5f6c1b`; local `master` was
  clean and matched `bvm/master` at preflight.
- Scope: new 4×4 renderer/platform and exactly six authorized JoSIM solves:
  `D3_N0`, `D3_N1`, `D3_N2`, `D3_N3`, `D3_N4`, then `PAPER_1101_1101`.
- No existing 2×2 source, run, raw, plot, ZIP, or package metadata may be edited.
- Frozen sources and SHA-256 values are in `experiment.yaml`; T1 source is a
  reference for `T1_PARAMS.env` only. Current deck mode is
  `DIAGONAL_TERMINAL`, `T1_MODE=OFF`, `CBU_MODE=OFF`.
- Topology: 16 BVM + 16 independent QB; 4 shared row-WL nodes, 4 shared
  column-BL nodes, 16 independent SE nodes; seven electrically separate serial
  diagonal QB→sJTL→CB chains, with 1/2/3/4/3/2/1 stages and independent 2 Ω
  terminal loads.
- Bit order is leftmost-first: ROW bit 1 selects R1; COL bit 1 selects C1.
  The four-row SE mask is row-major `R1/R2/R3/R4`; it gates FINAL_READ SE only
  in addition to row/column crosspoint selection. Shared WL/BL write/read
  effects remain active on half-selected cells.
- The six exact masks and preregistered target counts are listed in
  `experiment.yaml`; no event threshold or pulse/SFQ classifier is registered.
- Timing and amplitudes reproduce A026: WRITE0 50–61 ps, READ0 70–81 ps,
  WRITE1 90–101 ps, FINAL_READ 110–121 ps; shared WL/BL setpoints ±200 µA,
  SE 100 µA; `DT=0.01 ps`, `STOP=250 ps`.
- Probe profile `diagonal_focus/D3` keeps all 16 cells' actual WL/BL/SE input
  currents, SL and QB/merge boundaries; all seven DOUT and terminal currents;
  each diagonal's terminal CB JJ P/V; and D3's four-stage QB/sJTL/CB P/V plus
  selected internal branch currents. The expected probe count is checked
  against the 100 MB raw safety estimate before solving.
- Registered arithmetic windows are `[110,121)`, `[121,250)`, and `[110,250)`
  ps. Integrals use only actual stored samples. Phase remains radians; phase
  divided by 2π and voltage area divided by Φ0 are arithmetic only.
- Unknowns: event count, propagation success/failure, T1/CBU/DFF operation,
  mechanism, and timestep convergence. No follow-up or tuning is authorized.
- Package scope: six per-run evidence ZIPs plus one shared metadata ZIP if the
  aggregate raw exceeds the generic single-archive guard; generated HTML and
  Plotly JS remain local. No historical raw/ZIP is included.

## Static acceptance receipt — 2026-10-09

- Solver: `/home/howard/JoSIM/build/josim-cli`, `v2.7.2837d13`, SHA-256
  `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.
- Executor `scripts/diagonal_platform.py` SHA-256:
  `a53c0675abc833c2d02973fff2ea46013e1861bee514a8bad121d2f83377ded5`.
- Static tests: 6 passed. The single `./try.sh --dry-run --registered-matrix`
  pass rendered all six effective cases and reported topology/source/probe QA
  PASS; it invoked no solver and created no run directory.
- Static test file `tests/test_platform.py` SHA-256:
  `0957d67aeb5c70e45f84227c950f9c4b8d17c7c8e993ae641a959382074de086`.
- Each registered case uses 242 probes; the A018 byte/probe ratio with 15%
  width margin estimates 93,474,300 raw bytes per run, below 100,000,000.
  Aggregate estimated raw is 560,845,800 bytes, so package plan is six
  per-run ZIPs plus one metadata ZIP; no HTML, Plotly JS, historical raw, or
  historical ZIP is included.
- Classic plotter SHA-256:
  `0aaf0b4bfd148e073d318c9a0762ec13995045abd88cad28336fb8128c33a1d6`.
- Shared Plotly asset SHA-256:
  `122e3be346d66616944d0b83eaaf7242581508c3c1cfa0995a17af0d83eff770`.
- Static solve count at gate: **0**. Exactly six physical solves remain
  authorized; any solver/raw/mechanical-QA failure stops the batch.

## BUS400 diagnostic amendment — 2026-10-09

- Starting parent HEAD: `3de08ba0fd5997b253269849dbc1a535786c8fd6`.
- This amendment authorizes exactly `BUS400_D3_N0` then `BUS400_D3_N1`
  (expected A007/A008), one solve each; first-run solver/raw/mechanical/standalone
  plot failure stops before the second. No A001–A006 run or raw is changed.
- Both cases use shared WL/BL source totals 400u, independent SE 100u, the
  unchanged four-stage stimulus, DT 0.01p, STOP 250p, one sJTL per level, one
  CB per cell, seven 2 Ω terminals, focus profile, and T1/CBU/DFF OFF.
- They differ only in `SE_ENABLE_MASK`: all zero versus R1C1 only. Static QA
  compares the exact rendered deck and all 24 PWL sources before solving.
- Probe set has 124 registered signals: 48 per-cell WL/BL/SE branch currents,
  D3 storage JM1/JM2 P/V, four D3 SL/output and QB boundaries, focused QB JJ
  P/V, every D3 sJTL/CB JJ P/V, all seven DOUTs, and all seven terminal currents.
- Arithmetic windows are generated from the snapshotted stimulus for WRITE0,
  READ0, WRITE1, FINAL_READ, POST_FINAL_READ, and FINAL_READ_RESPONSE; all are
  half-open and use exact stored samples. No classifier or event count is used.
- Full frozen cases, source hashes, output paths and interpretation ceiling are
  in `analysis/BUS400_PREREGISTRATION.yaml`. See run provenance for the exact
  committed execution HEAD, solver hash and raw/deck hashes.
- Risk level: NORMAL; this is not FORMAL/Authority and does not authorize
  physical interpretation, further solves, sweeps, or changes to T1/CBU/DFF.
- Only the new/changed files and two new raws enter one DELTA package; all old
  raw is referenced by prior package/raw SHA. HTML and Plotly JS remain local.
