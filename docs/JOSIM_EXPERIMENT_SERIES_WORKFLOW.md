# Lightweight JoSIM experiment-series workflow

This document defines the user-facing workflow for new JoSIM experiment
series. It is an interface convention, not a universal experiment manager and
not a replacement for `docs/EXPERIMENT_CONTRACT.md`, which remains the
authoritative evidence contract.

The workflow starts with the next new series. Existing experiments are not
retrofit, rewritten, or reinterpreted to match it.

## Design limits

The workflow deliberately does not introduce:

- a universal YAML schema;
- a database, GUI, web server, plugin system, or global manager;
- a `josim-exp new/clone/...` command hierarchy;
- an automatic scientific-verdict, optimizer, winner, or mechanism engine.

Codex creates a complete series directory for the scientific question. The
series owns its `run.sh`, `analyze.sh`, `plot.sh`, and any Python helpers. The
user edits those files directly and uses the same entrypoints as Codex.

## Series lifecycle

For a new series, Codex should:

1. freeze the question, changed item, controls, windows, and scope in
   `PREFLIGHT.md`;
2. create the series-specific `run.sh`, `analyze.sh`, `plot.sh`, and helpers;
3. put user-editable deck, stimulus, parameter, solver, and plot choices near
   the top of the relevant shell script;
4. run the registered default matrix through `./run.sh`;
5. analyze only existing raw files through `./analyze.sh`;
6. render descriptive HTML through `./plot.sh`;
7. stop at the series-defined evidence/review boundary.

The default run creates a new immutable attempt (`A001`, `A002`, ...). A
repeat run never overwrites an earlier attempt, even when the values are
identical. A failed attempt is retained with its logs and metadata.

Daily commands are intentionally small:

```bash
./run.sh --dry-run
./run.sh
./analyze.sh A001
./plot.sh A001
```

`latest` may be supported by `analyze.sh` and `plot.sh` as a convenience.

## Recommended series layout

The reference scaffold is
`test/exploration/_series_template/`:

```text
_series_template/
├── README.md
├── PREFLIGHT.md
├── run.sh
├── analyze.sh
├── plot.sh
├── circuits/
│   ├── top.cir
│   ├── bvm.cir
│   ├── qb.cir
│   ├── jtl.cir
│   └── optional_other.cir
├── stimuli/
│   └── manual.inc
├── scripts/
│   ├── build_cases.py
│   ├── analyze.py
│   └── render_plots.py
└── runs/
```

Not every series needs every module file. If a module is inline in the top
deck, leave its selector empty and print `INLINE_IN_TOP`; do not invent a
file path. If a module uses a canonical repository file, select and snapshot
that path. If a module changes, create the local experimental copy in the
series directory.

## `run.sh`: the control panel

`run.sh` is the main user control panel. Its top-level regions should remain
visible and in this order:

```text
1. CIRCUIT / DECK SELECTION
2. STIMULUS
3. EXPERIMENT PARAMETERS
4. SOLVER
5. RUN BEHAVIOR
```

### Circuit/deck selection

The first region exposes:

```bash
TOP_DECK="circuits/top.cir"
BVM_CIRCUIT=""
QB_CIRCUIT=""
JTL_CIRCUIT=""
COMMON_SL_CIRCUIT=""
JSL_CIRCUIT=""
```

`TOP_DECK` means the top-level testbench: system topology, instance
arrangement, stimulus attachment, `.tran`, and probe strategy. The BVM/QB/JTL
selectors mean module implementations. Empty selectors are valid only when
the module is inline or intentionally absent, and the dry-run must say so.

Source files are never modified in place. The build flow is:

```text
selected top + selected modules + selected stimulus + parameters
        -> build_cases.py
        -> runs/Axxx/cases/<case>/actual_deck.cir
        -> JoSIM
```

Every solved case must retain `actual_deck.cir`. It is the direct evidence of
what was actually executed. The deck should reference the attempt snapshot
where practical; any indirect include closure that is not handled by the
lightweight helper must be made explicit in the series-specific helper and
recorded in `source_manifest.json`.

### Stimulus

The second region exposes:

```bash
STIMULUS_MODE="generated"   # generated or manual
MANUAL_STIMULUS="stimuli/manual.inc"
MASKS=("EDIT_MASK_1" "EDIT_MASK_2")
```

Generated mode exposes only parameters that the particular series really
uses, such as write/read timing and amplitudes. The template contains no
canonical numerical values. A generated stimulus is saved for every case as
`stimulus.inc` (or an equivalent frozen representation).

Manual mode copies the selected manual source without changing it. The
runner snapshots its bytes and SHA-256 and must not silently combine it with
generated sources. Switching modes is an explicit edit to `run.sh`.

### Experiment parameters and solver

Experiment-specific values belong in region 3; they do not need to share a
global schema. Region 4 exposes the recorded solver and integration settings:

```bash
JOSIM_BIN="/home/howard/JoSIM/build/josim-cli"
DT="0.1p"
STOP_TIME="200p"
```

The concrete series must replace placeholders with values from its real
fixture. The template intentionally leaves them unset and refuses a physical
run until they are filled.

### Immutable attempts

Each actual invocation creates the next free attempt:

```text
runs/A001/
├── snapshot/
│   ├── run.sh
│   ├── top.cir
│   ├── selected module snapshots
│   ├── stimulus.inc or equivalent
│   └── source_manifest.json
├── cases/
│   └── <case>/
│       ├── actual_deck.cir
│       ├── stimulus.inc
│       ├── raw.csv
│       ├── stdout.txt
│       ├── stderr.txt
│       ├── run.log
│       └── metadata.json
├── analysis/
├── plots/
└── metadata.json
```

There is no overwrite-oriented `--force` path in the reference workflow.
Users change `run.sh`, a local `.cir`, or a manual stimulus and rerun; the
next attempt records the new state.

### Dry-run

`./run.sh --dry-run` is required to print, without creating an attempt or
calling JoSIM:

```text
EXPERIMENT
ATTEMPT would be: A00X
CIRCUITS
TOP:
BVM:
QB:
JTL:
COMMON_SL/JSL:
STIMULUS
mode:
mask(s):
write/read:
amplitudes:
EXPERIMENT PARAMETERS
SOLVER
JoSIM:
dt:
stop:
CASES
actual_deck:
raw:
exact command:
TOTAL SOLVES
```

It must also state whether a module is `INLINE_IN_TOP`, `NOT_SELECTED`, or a
real selected path.

## `analyze.sh`: mechanical facts only

Each series owns `analyze.sh` and `scripts/analyze.py`. The analyzer reads
existing raw files and writes at least:

```text
runs/A001/analysis/summary.json
runs/A001/analysis/summary.csv
```

The series may add crossing times, extrema, RMS, phase p2p, same-JJ voltage
area, chronology, re-arm crossings, power, or energy when they are registered
for that question. It must not automatically announce a physical mechanism,
final design, scientific winner, SFQ count from phase activity, or a Gate.

JoSIM `P(...)` remains raw radians. If an analyzer presents turns, it must say
`rad/(2*pi)` and `Phase [turns]`; turns are navigation/measurement units, not
literal SFQ counts. Raw, deck, and source hashes are checked without modifying
the raw file.

## `plot.sh`: existing visualization standard

The primary output is offline/local interactive HTML:

```text
Plotly HTML + scripts/josim-plot2.py + sep_comb + dark
```

The standard renderer is the existing `scripts/josim-plot2.py`; a new plotting
engine is not introduced. Default output is HTML only:

```bash
GENERATE_HTML=1
GENERATE_STATIC=0
```

For BVM→QB→JTL population series, Codex should fill the six visible groups
from the actual raw header:

```text
SIGNAL_PATH
BVM_STATE
BVM_OUTPUT
JSL_CHAIN
QB_STATE
JTL_CHAIN
```

The default is a compact whole-run view. Focused windows are opt-in:

```bash
./plot.sh A001 --window 110 121
```

The top of `plot.sh` must contain editable signal arrays. The helper must
support:

```bash
./plot.sh A001 --list-signals
./plot.sh A001 --group QB_STATE
./plot.sh A001 --signals 'I(L_S3|XBVM2)' 'V(QBIN)'
```

`--list-signals` reads the real raw CSV header and groups voltage, current,
phase, and other columns. An explicitly requested missing signal is a hard
error: print the exact missing label, show close matches, and suggest
`--list-signals`. Never silently select the first occurrence of a duplicate
label.

Standard plots go under `runs/A001/plots/`; ad hoc signal selections go under
`runs/A001/plots/<case>/adhoc/` and must not overwrite standard plots. A
`plot_manifest.json` records attempt, case, raw path/SHA, exact signals,
renderer arguments, time unit, phase conversion, output path, and HTML SHA.

## Provenance minimum

Every attempt records:

- parent/current Git commit and dirty-tree status;
- JoSIM path, version output, and binary SHA-256;
- Python version;
- selected TOP/BVM/QB/JTL/stimulus and run.sh SHA-256;
- actual deck SHA-256 and raw SHA-256 for every case;
- exact command, timestamps, exit code, stdout, stderr, and runtime.

A dirty tree does not automatically block an exploratory run. It must be
recorded as `working_tree_dirty=true`, and the attempt snapshot remains the
traceability boundary.

## Codex behavior for future series

When asked to create a new experiment series, Codex should use this workflow
as the interface layer:

1. create an independent series directory for the scientific question;
2. create the three thin shell entrypoints and series-specific helpers;
3. expose TOP/DECK, BVM/QB/JTL, stimulus, experiment parameters, solver, and
   editable plot groups visibly;
4. fill real fixture values and real raw-header signal names;
5. run the registered matrix through `./run.sh`, never a private temporary
   JoSIM command;
6. preserve immutable attempts and snapshots;
7. analyze mechanically and plot descriptively;
8. stop at the registered review boundary.

The user should be able to change parameters, `.cir`, stimulus, or signal
selection and repeat the same commands without finding Codex again. Scientific
interpretation, route changes, metric freezes, and follow-up experiments
remain separately authorized actions.

## Validation for the workflow itself

Workflow changes are validated without a new scientific solve:

```bash
bash -n run.sh
bash -n analyze.sh
bash -n plot.sh
python3 -m py_compile scripts/*.py
./run.sh --dry-run
./plot.sh --help
```

`--list-signals` may be tested against an explicitly named existing raw file;
that read-only check must not alter the historical experiment. If the
reference template still contains placeholders, its dry-run mock must remain
clearly labeled and no physical solver may be invoked.
