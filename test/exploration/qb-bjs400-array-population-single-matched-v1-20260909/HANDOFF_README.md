# BJS400 ARRAY population + matched SINGLE-BVM functional experiment

This is an evidence-only handoff. Scientific interpretation is NOT_PERFORMED.

The experiment uses the 20260909 successful ARRAY -> QB -> 6JTL fixture as
physical and stimulus authority. The 20260904 experiment is used only for mask
bit ordering and flat whole-run visualization style.

Registered physical change: the experiment-local BQ copy uses BJs area=4,
corresponding to Ic=400uA for the local jjmit icrit=100uA model. All other
registered working-point, topology, history, timing, solver and probe choices
are frozen.

The exact matrix is 16 ARRAY runs (four settings times four masks) plus 8
matched SINGLE runs (four settings times final-read controls 0 and 1), for 24
physical solves. The only ARRAY masks are 0000, 1000, 0001 and 0011. No
combination tuning, extra mask, retry, ranking, mechanism analysis or
automatic follow-up is authorized.

Every standard plot is whole-run 0-200ps, uses scripts/josim-plot2.py with
sep_comb, dark and 2pi, and is descriptive evidence only. Standalone plots
read raw.csv directly. Comparison temporary CSV files are not experiment
artifacts and are not retained.

Git is the authoritative evidence archive. The detached PACKAGE_QA.json
records the immutable package hash and byte count. A matching byte-for-byte
copy is made to the configured BVM_Backages mirror after package QA and Git
commit.

