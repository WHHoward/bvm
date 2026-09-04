# Commands and exit status

- `python3 analysis/analyze.py`: PASS (read-only raw analysis plus task-local derived CSV/HTML/report generation).
- JoSIM command: not run by authorization boundary.
- Plot renderer: `scripts/josim-plot2.py -t sep_comb -c dark -j 2pi`: all generated plots returned exit code 0.
- Raw SHA-256 before/after: identical; see `analysis/provenance.json`.
- Sol XHigh independent review: `NEED_REVISION` initially; four MAJOR items were corrected in the task-local analysis/report, with no new simulation.
- Sol XHigh post-fix confirmation: `OK`, no residual mandatory corrections.

The analysis script uses shared `bvmtools.raw`, `phase`, `metrics`, `compare`, `kcl`, `onset`, and `waveform`; no local raw parser or SFQ event counter was added.
