# Commands and exit codes

| command | exit code | purpose |
|---|---:|---|
| `python3 generate_decks.py --check-only` | 0 | frozen setup generator check |
| `python3 generate_decks.py` | 0 | write ten immutable deck artifacts |
| `python3 analysis/topology_preflight.py` | 0 | static topology proof |
| `git commit -m "experiment: preregister common-SL topology"` | 0 | preregistration/deck/static commit |
| `./run.sh` | 0 | ten independent JoSIM runs |
| `python3 analysis/analyze.py` | 0 | analysis dry run |
| `python3 analysis/analyze.py --write` | 0 | write metrics and report |
| `python3 analysis/independent_check.py` | 0 | independent compact recheck |
| `python3 analysis/render_plots.py` | 0 | standalone/comparison HTML and QA |

Physical run commit/HEAD: `d6a355b2` (`experiment: preregister common-SL topology`).

The first two visualization attempts stopped before producing a complete set: one
exposed a missing output-directory creation and one exposed an overly strict HTML
string check. Both were renderer-only failures; raw/deck artifacts were unchanged.
