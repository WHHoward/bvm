# BVM array → QB/CB/sJTL topology platform v1

## Quick Start

1. Edit `USER_CASE.env`, for example:

   ```text
   NAME=test_qb_bj3
   MASKS=01,11
   QB_BJ3_AREA=2.2
   ```

2. Edit `STIMULUS.env` only when stimulus timing or amplitude should change.
3. Preview every configured mask without a solve:

   ```bash
   ./try.sh --dry-run
   ```

4. After reviewing the preview, run exactly the listed masks once each:

   ```bash
   ./try.sh
   ```

5. Inspect `analysis/LATEST_BATCH.json`, then its
   `batches/Uxxx_NAME/BATCH_SUMMARY.md`. Each completed run has five pages:
   `plots/01_overview.html`, `02_bvm.html`, `03_qb.html`, `04_cb.html`, and
   `05_acc_gap.html`.
6. Before submission, check the complete batch gate:

   ```bash
   ./submit.sh B001-example --dry-run
   ```

   Then submit with `./submit.sh B001-example`. A dry-run creates no package,
   mirror, commit, or push. With no registered package checkpoint, the first
   normal submit defaults to FULL; after a checkpoint exists, the default is
   DELTA. `--mode full|delta` can explicitly select the mode.

### Temporary overrides

`--set KEY=VALUE` accepts any registered `USER_CASE.env` or `STIMULUS.env` key,
without editing either file:

```bash
./try.sh --dry-run --set QB_BJ3_AREA=2.2
./try.sh --dry-run --set QB_BJ3_AREA=2.2 --set READ_ACTIVE_SE=110u
./try.sh --dry-run --set PROBE_PROFILE=debug
```

Overrides are validated, shown relative to the frozen component baseline when
applicable, and copied into effective snapshots and run provenance. Unknown or
duplicate keys hard-stop. A real `./try.sh --set ...` uses the same effective
configuration for every requested mask in that batch.

## Configuration and component rendering

`USER_CASE.env` contains case identity, topology, solver settings, and shared
parameters for all BVM, QB, CB, and sJTL instances. `STIMULUS.env` remains
separate and defines WRITE0, READ0/CONTROL, WRITE1, and FINAL READ. MASK only
changes the FINAL READ. The leftmost mask bit is BVM1; a zero suppresses that
BVM's WL/BL/SE only during FINAL READ.

`config/component_reference.env` records parameter defaults and SHA-256 hashes
for the four canonical 0923 component sources. If a canonical source hash
changes, preview stops with `REFERENCE_SOURCE_CHANGED`; update the reference
only after explicit human review. The renderer writes per-run snapshots:

```text
snapshot/sources/bvm_tunable.cir
snapshot/sources/BQ_tunable.cir
snapshot/sources/CB_tunable.cir
snapshot/sources/sJTL_tunable.cir
```

The rendered deck includes those snapshots, not the canonical sources. It also
defines the frozen shared `jjmit` model at top level before the includes, so the
BVM subcircuit resolves the model; its parameters match the QB/CB/sJTL local
cards. `source_manifest.json` records canonical and rendered hashes plus
effective role parameters. `parameter_manifest.json` groups BVM, QB, CB, sJTL,
topology, solver, and stimulus-reference values. The model is not
user-parameterized. Resistor value `OPEN` means the branch is commented/open,
not a large-resistance approximation. All component overrides are shared by
every instance of that role; per-instance overrides are not supported.

### Probe profiles

`PROBE_PROFILE` is part of the effective case snapshot, acquisition/parameter
manifest, source provenance, probe manifest, and dry-run summary. Only `core`
and `debug` are accepted. The default is `core`:

- BVM/QB/CB/sJTL JJ phase and voltage; selected inductor currents; required
  component boundaries and write/read stimulus branches.
- No default JJ current, inductor voltage, or `V(R_TERM)` probe.
- `debug` restores the historical detailed JJ P/V/I and inductor I/V probe set.

Old immutable snapshots without the profile field are interpreted as `debug`
for mechanical validation; they are not edited. Profile changes do not alter
the circuit topology or component parameters. Phase plots continue to show
`phase turns = raw phase / (2*pi)`, never an SFQ count.

The `core` default is the project owner's explicit acquisition-policy override
for future runs through this platform relative to the broader full-probe
preference in `docs/EXPERIMENT_CONTRACT.md` §V. It intentionally limits
after-the-fact internal diagnostics; each physical-run preflight records the
selected profile and exact probe list. This maintenance change does not rewrite
historical run snapshots or raw data.

## Batch and immutable run model

Each real `./try.sh` creates one `batches/Uxxx_NAME/` with effective config
snapshots, `parameter_manifest.json`, `batch_manifest.json`, and
`BATCH_SUMMARY.md`. The batch references, but does not contain, immutable
`runs/Axxx_Txxx_MMASK/` directories. `analysis/LATEST_BATCH.json` changes only
after a real batch attempt; previews/render fixtures never update it.

The batch status describes mechanical completeness only:
`COMPLETE_MECHANICAL`, `INCOMPLETE`, or `SOLVER_FAILURE`. It is not a physics
verdict. A solver/raw failure preserves the failed run and stops remaining
masks without retry. A valid raw with plot failure is retained, is marked for
plot repair, and is never re-solved automatically. Running
`python3 scripts/plot_run.py runs/<run-id>` repairs against that same raw and
refreshes the batch mechanical status; the batch cannot be submitted until
that plot/evidence validation passes.

`./submit.sh` prioritizes `LATEST_BATCH.json` and verifies every requested mask
has exactly one run, each run/raw exists, artifact status is VALID, plot QA is
PASS, recorded/raw SHA-256 values agree, and physical-solve totals match. It
checks artifact completeness, not whether the physical result meets an expected
value. The advanced single-mask command remains available:

```bash
python3 scripts/run_case.py --mask 01
```

Use `python3 scripts/run_case.py --render-only --mask 01` only for a static
fixture preview. Real waveforms use the five classic per-run pages above; no
batch atlas or comparison dashboard is generated.

`05_acc_gap.html` is a focused propagation view: per-level local/upstream
contributions → `MERGE_i` → sJTL JJ P/V and stage output → optional post-CB
representative output JJ/output → `CARRY_i` → `FINAL_OUT`. It does not repeat
the complete `cb:*` or `sjtl:*` internal groups already shown on pages 04/03.
All five pages use the full stored time range.

## Scientific package selection

Packages are selected from direct `batches/*/batch_manifest.json` references,
not by walking the working tree. Only `COMPLETE_MECHANICAL` batches and their
referenced VALID runs enter the scientific evidence set. `FULL` is a
self-contained checkpoint of those batches/runs, not a copy of the whole
series; `DELTA` adds only newly referenced batches/runs after its verified
checkpoint and records reused raw by source case/path/SHA instead of copying
it again. Incomplete/failed batches, unreferenced runs, tests/fixtures, caches,
and historical ZIPs are excluded.

By project-owner instruction, derived HTML is excluded from scientific ZIPs by
default, while every referenced run still requires and verifies its five-page
plot manifest/QA and raw SHA. The package carries the versioned `josim-plot2.py`
and shared Plotly asset plus their hashes so plots can be regenerated. Use
`./submit.sh <tag> --include-plots` or
`python3 scripts/package.py --mode delta --tag <tag> --include-plots` only when
the HTML itself is needed in the archive. The dry-run reports per-category
file counts/bytes/percentages and the 20 largest members; PACKAGE_QA records
actual compressed/uncompressed sizes and compression ratio.

## Platform boundaries

This is a parameterized, render-first platform. `./try.sh --dry-run` renders all
requested configurations under a temporary fixture directory and removes it
on exit; it does not create a batch/run, call JoSIM, generate raw, package,
commit, or update pointers. The ordinary `./try.sh` command is the sole
multi-mask solve entry point and performs no retry, sweep, next topology,
repeated read, rewrite read, or T1 work. The executor records mechanical
outputs only; scientific interpretation remains separate.
