# Test and execution record

This file records the commands used for this exploratory task. Exit codes are
the observed exit codes; physical artifacts are never overwritten.

| command | exit code |
|---|---:|
| `python3 -m py_compile generate_decks.py analysis/*.py` | 0 |
| `python3 generate_decks.py --check-only` | 0 |
| `python3 analysis/static_preflight.py --check-only --require-clean` | 0 |
| `./run.sh` | 0 |
| `python3 analysis/analyze.py --write` | 0 |
| `python3 analysis/independent_check.py` | 0 |
| `python3 analysis/render_plots.py` | 0 |
| `env PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q test/tools` | 0 |

The physical run is exactly the ten masks declared in `experiment.yaml`.
Visualization uses `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`.

`./run.sh` completed all ten masks with exit code 0; each mask has an
independent deck/raw/log/metadata set and no `Missing model:` or
`Using default model` warning. The independent check was written once with
exit code 0 and is intentionally not rerun because it refuses to overwrite
its immutable JSON output. The final test-suite result was `48 passed`.

During analysis/renderer development, several failed attempts exposed and
were corrected in task-local tooling (KCL variable name, unit scaling,
single-reference pairing, branch-label mapping, and comparison-output path).
No raw CSV was rewritten and no physical rerun was triggered by those fixes;
the final commands above are the accepted results.
