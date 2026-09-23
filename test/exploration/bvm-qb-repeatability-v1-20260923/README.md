# BVM array → JSL → QB → JTL repeatability platform

Edit `USER_CASE.env`, then run:

```bash
python3 scripts/run_case.py --dry-run
python3 scripts/run_case.py
```

Every physical run receives an immutable directory under `runs/`; an existing
run is never overwritten. The snapshot expands the selected fan-in-specific
profile together with any explicit `USER_CASE.env` overrides. `AUTO` means
inherit from the selected candidate profile or `REFERENCE.env`.

The checked-in control file uses `EXECUTION_SCOPE=REGRESSION_MATRIX`, so only
the hash-bound A–E regression runner can launch the five registered solves.
For a future separately authorized manual case, change
`EXECUTION_SCOPE=MANUAL` in `USER_CASE.env`, set the desired case values, and
then use the single `run_case.py` command above. The regression matrix and its
preflight remain immutable; a manual run is not folded into A–E.

Supported modes:

- `REPEAT_READ`: existing WRITE0/CONTROL/WRITE1 preamble, then `READ_COUNT`
  reads at `READ_START_PS + i*READ_PERIOD_PS`; no rewrite after WRITE1.
- `RECOVERY_PROBE`: the same preamble, one read, zero source currents for the
  configured `RECOVERY_TAIL_PS`.
- `REWRITE_READ`: each `STATE_SEQUENCE` element resets all cells, writes that
  state, and reads it. `STATE_INTERVAL_PS` and the three explicit delays govern
  cadence; the sequence length determines the read count.

The mask is left-to-right (`b[N-1] … b[0]`) and selects which BVMs receive
read-current pulses. The preserved repeated-read preamble writes all BVMs to
the same WRITE1 state before applying that read mask. Rewrite mode instead
resets all cells and writes each listed target state.

The frozen A–E regression batch is launched with
`python3 scripts/run_regression.py`. A validated recovery of the already-solved
A case uses `--resume`; it reanalyzes that raw without JoSIM, then runs only B–E.
If and only if the manager crashes before starting A reanalysis, the guarded
`--repair-interrupted-resume` command preserves that no-solve attempt and
restores the previous stopped-at-A ledgers; it refuses any case where a raw,
later run, or A recovery has already changed.
If a registered later case is rejected before solver launch after A is already
valid, `--resume-after-a` is a separate guarded path: it verifies that exact
zero-solve failure, preserves its receipt, revalidates A without changing its
run tree, then continues the still-authorized B–E matrix. Retried receipt names
are suffixed rather than overwriting the failed attempt.

`STOP_PS` is never a user-entered solver limit. It is computed from the last
stimulus endpoint and tail policy; recovery mode uses READ end plus recovery
tail. A preflight hard-stops if any stimulus or configured terminal candidate
search extends outside the simulated time range.

`python3 scripts/run_sweep.py --key READ_PERIOD_PS --values 20,25,30` is the
single-parameter sweep entry point after setting `EXECUTION_SCOPE=MANUAL` in
`USER_CASE.env`. It creates a separate immutable run per point and reuses the
same runner/analyzer; it is not used for the registered A–E platform regressions.

After the five registered platform regressions are finalized and the evidence
commit exists, create the requested delta handoff package with:

```bash
python3 scripts/package.py --dry-run --tag A-E
python3 scripts/package.py --tag A-E --create-only
```

Delta base identity comes from `analysis/PACKAGE_CHECKPOINTS.json`; the packager
hard-stops if the base package hash or commit ancestry cannot be verified. It
never falls back to a full archive or overwrites an existing ZIP/mirror. Commit
and push the ZIP/LFS pointer and package checkpoint, then finish the exact-byte
Drive mirror and `PACKAGE_QA` record with:

```bash
python3 scripts/package.py --tag A-E --complete-mirror
```

## Plot and page layout

Each run gets an independent `plots/review.html` in the compact style of the
one-shot tuning platform, with links to classic `josim-plot2.py` grouped plots.
For each BVM, its `I(I_WL*)`, `I(I_BL*)`, and `I(I_SE*)` excitations are plotted
in the same classic `sep_comb` figure as `V(QBOUT)` and `V(R_TERM)`; focused
READ-cycle plots likewise put the active excitation beside those outputs.
`plots/stimulus.html` is a page of links to those same plots, not a separate
custom chart. There are no visualization cards or custom SVG plots. The series
`plots/RESULT_OVERVIEW.html` links the run pages, and
`plots/REGRESSION_COMPARISON.html` shows only descriptive regression/QA
records. Plots are not cards, a custom chart renderer, or scientific gates.

The renderer is `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`. Every
focused READ figure is rendered from an exact stored-grid row subset with a
hash-bound sidecar; no interpolation or resampling is used. `P(...)` raw data
remain radians; `-j 2pi` is navigation only, not an SFQ count.

## Scope and evidence ceiling

The registered A–E batch is five platform/regression solves only. In this
turn, A–C compare against the hash-bound historical Phase-A raw runs; D
verifies that the recovery trace is emitted; E verifies that all sequence
stimuli are covered by the automatically calculated STOP. These do not judge
physical recovery, state retention, quantization, QB/JTL success, maximum
frequency, or mechanism. No automatic follow-up is performed.
