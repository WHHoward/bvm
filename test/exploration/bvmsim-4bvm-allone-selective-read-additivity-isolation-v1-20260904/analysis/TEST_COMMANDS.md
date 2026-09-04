# Test and execution record

This file records the commands used for this exploratory task. Exit codes are
filled after each command completes; physical artifacts are never overwritten.

| command | exit code |
|---|---:|
| `python3 -m py_compile generate_decks.py analysis/*.py` | pending |
| `python3 generate_decks.py --check-only` | pending |
| `python3 analysis/static_preflight.py --check-only --require-clean` | pending |
| `./run.sh` | pending |
| `python3 analysis/analyze.py --write` | pending |
| `python3 analysis/independent_check.py` | pending |
| `python3 analysis/render_plots.py` | pending |

The physical run is exactly the ten masks declared in `experiment.yaml`.
Visualization uses `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`.
