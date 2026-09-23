# BVM → BQ → CB → ACC → GAP (2×1) exploratory experiment

This is an append-only, four-case physical experiment. It snapshots the current
0923 BVM, BQ, CB, and sJTL circuit sources and does not modify them.

Run from this directory:

> Incident stop: this directory is aborted pending user direction. Do not run
> the physical matrix from it. The commands below describe the intended flow
> only; a fresh, explicitly authorized experiment instance is required.

```bash
python3 -m unittest discover -s scripts -p 'test_platform.py' -v
python3 scripts/preflight.py --static-only
python3 scripts/preflight.py --freeze-source-lock
git add .
git commit -m "preregister 2x1 BVM-BQ-CB-GAP experiment"
python3 scripts/preflight.py --dry-run
python3 scripts/preflight.py --write
python3 scripts/run_matrix.py
python3 scripts/plot_run.py
python3 scripts/finalize.py
python3 scripts/package.py
```

The frozen masks are `00`, `01`, `10`, and `11`; every case writes both BVMs
through WRITE0, CONTROL, and WRITE1, and only the final READ mask varies. The
user-authorized timestep is `0.01p` (updated from the original `0.001p`
preference before preregistration. Recalculation from the reference raw and 169
planned CSV columns estimates four raws at about 1.81 GB for `0.001p` and
181 MB for `0.01p`, before observing actual output). STOP is `200p`. No
timestep or parameter sweep is part of this experiment.

Each run has an independent review page and classic `josim-plot2.py` plots.
Excitation-current branches are overlaid with outputs in the same classic
figures. The four run views are whole-chain overview, local branches, GAP2
merge debug (including all seven preregistered tracks in one figure), and BVM
state. Full, final-read and read-response views preserve only their registered
actual stored samples. `P(...)` remains raw radians; `-j 2pi` is a navigation display only.
Visualizations are descriptive evidence and do not classify SFQ events.

The default execution role is Experimental Operator + Evidence Packager. The
run manager stops after the four registered cases and final package QA. No
scientific mechanism interpretation or automatic follow-up is performed.
