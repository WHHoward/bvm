# BVM array → QB/CB/sJTL topology platform v1

This is a parameterized, render-first experiment platform. It does not modify
the canonical component circuits. A render fixture is a netlist/stimulus
preview only, not JoSIM experiment evidence. No physical solve is run by the
render-only path.

## Architecture

`USER_CASE.env` selects array size, final-read masks, and per-level topology.
`STIMULUS.env` defines all WRITE0, CONTROL/READ0, WRITE1, and FINAL READ timing
and amplitudes. `topology.py`, `stimulus.py`, and `probes.py` render the circuit,
waveforms, topology manifest, and probes. `run_case.py --render-only` writes to
`tests/fixtures/rendered/`; only `run_case.py --mask MASK` creates an immutable
`runs/Axxx_Txxx_MMASK/` run and invokes JoSIM. Existing run IDs hard-stop.

The top-level source snapshots are copied byte-for-byte from:

- `circuits/bvm/bvm_cell_0923.cir`
- `circuits/qb/BQ_0923.cir`
- `circuits/CB/CB_0923.cir`
- `circuits/sJTL_0923.cir`

The generated deck includes those snapshots; Python does not duplicate their
component parameters. Every manifest binds original path and snapshot SHA-256.

## Configuration

Edit `USER_CASE.env` for `ARRAY_SIZE`, `MASKS`, `QB_CB`, `SJTL_COUNT`,
`POST_SJTL_CB`, output mode/load, timestep, and stop time. Each topology array
must contain exactly `ARRAY_SIZE` entries. Malformed arrays or masks fail
before any solver process can be created.

Edit `STIMULUS.env` for every stage start, rise, hold, fall, and per-branch
amplitude. PWL strings are generated from these values; they are not duplicated
as constants in the Python renderer.

`MASK` is the FINAL READ mask, not an active-population mask. All BVMs perform
WRITE0 → CONTROL/READ0 → WRITE1. Only FINAL READ is masked. Bit order is
leftmost=BVM1, rightmost=BVMN; a zero bit makes WL/BL/SE zero only in the final
read window.

## Topology variables and names

For each level `i`:

- `QB_CB[i]`: 0 or 1; whether a CB follows QB_i.
- `SJTL_COUNT[i]`: any nonnegative integer, including zero.
- `POST_SJTL_CB[i]`: 0 or 1; whether a CB follows the sJTL chain.

Instances use `XBVMi`, `XBQi`, optional `XQBCBi`, `XSJTLi_XX`, and optional
`XPOSTCBi`. Logical nodes use `BVMi_SL`, `QBi_RAW`, `MERGEi`, `L{i}_XX`,
`CARRYi`, and `FINAL_OUT`. A zero-stage direct carry may make two logical merge
roles the same electrical node; the manifest records the intentional alias.
The physical deck names a common carry/next-level merge as `MERGE_(i+1)`;
`CARRYi` is a manifest role alias, not a second net. When zero sJTL and no
post-CB collapse consecutive merge levels, the earliest physical node name is
retained and all logical merge aliases are recorded. No measurement inductor,
resistor, or merge cell is inserted.

## Render and run

Render-only preview (no Axxx run and no solver):

```bash
python3 scripts/run_case.py --render-only --mask 01
```

Inspect `actual_deck.cir`, `stimulus.inc`, `topology_manifest.json`,
`source_manifest.json`, and the `RENDER_FIXTURE_ONLY` marker. When separately
authorized, a physical run uses:

```bash
python3 scripts/run_case.py --mask 01
```

That command is not part of static fixture generation. It creates a new
non-overwriting Axxx run, records solver identity/provenance, preserves stdout,
stderr and raw, performs only mechanical raw QA, and produces the five
requested descriptive pages. It does not classify SFQ or interpret topology.
If a valid raw exists and only plotting needs repair, use
`python3 scripts/plot_run.py runs/<run-id>`; do not rerun `run_case.py` for a
plot-only failure.

## Plot pages

One run has at most five main pages: `01_overview.html`, `02_bvm.html`,
`03_qb.html`, `04_cb.html`, and `05_acc_gap.html`. For example,
`python3 scripts/plot_run.py tests/fixtures/rendered/2x1_M01 --plan-only`
creates/checks the signal plan without raw or waveform HTML. Real plots use
the repository's classic `scripts/josim-plot2.py` layout functions, full stored
time range, `sep_comb`, dark theme, and phase display in turns only after rad/2π.
The shared Plotly asset is `plots/assets/plotly.min.js`; per-page HTML references
it rather than embedding another copy. Plots are descriptive, not scientific
interpretation.

## Submit/package

`python3 scripts/inspect_runs.py` and `python3 scripts/inspect_runs.py --run-id
A001_T001_M01` report configuration/artifact status only; they do not interpret
physical behavior.

After a requested experiment is complete and mechanically QA'd, use the
series-local workflow:

```bash
python3 scripts/submit.py <TAG> --mode full --dry-run  # first explicit checkpoint
python3 scripts/submit.py <TAG> --mode full
python3 scripts/submit.py <TAG> --dry-run              # later DELTA
python3 scripts/submit.py <TAG>
```

Submit dry-run never runs JoSIM, creates a ZIP, mirrors, commits, or pushes. The
normal workflow commits experiment/source evidence, creates a DELTA archive,
checks ZIP CRC/member hashes and package/mirror SHA identity, appends
`analysis/PACKAGE_CHECKPOINTS.json`, commits package metadata separately, pushes,
then stops. `--no-push` skips Git push only; packaging and the `/mnt/d/BVM_Backages`
mirror still occur. ZIPs under `handoff/` are not committed to Git. `package.py
--mode full --tag <TAG>` is for an explicitly authorized FULL checkpoint; normal
submission defaults to DELTA and requires a verified checkpoint base. Existing
package or mirror names are never overwritten. The package includes changed
evidence but does not nest `handoff/*.zip`, Python caches, or unchanged historical
raw.
`--package-only` is for a packaging retry after the experiment/source commit;
it binds the package to the current HEAD.

The executor produces mechanical outputs only. User + ChatGPT own physical
interpretation and topology selection. No T1, repeated-read, rewrite-read,
parameter sweep, or next experiment is included in platform v1.
