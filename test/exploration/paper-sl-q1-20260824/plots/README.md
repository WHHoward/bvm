# PAPER-SL-L0 classic visualization

These viewers visualize the previously accepted
`test/exploration/paper-sl-l0-20260824` raw CSVs without rerunning JoSIM or
changing the raw data.  They use the repository's classic visualization
convention:

- `scripts/josim-plot2.py`
- interactive HTML
- `sep_comb` layout
- dark theme
- `-j 2pi` for phase display in turns
- no smoothing, resampling, or event counting

The signal set is the familiar BVM source/storage group plus the first and
last JSL branch probes: WL/SE currents, JS1/JS2 phase and voltage, N6/SL,
PSL/SL currents, and JSL1/JSL12 current with JSL1 phase/voltage.

| viewer | source |
|---|---|
| `paper-sl-l0-classic/logical1-read.html` | external 12-JJ load, logical1 + READ |
| `paper-sl-l0-classic/logical0-read.html` | external 12-JJ load, logical0 + READ |
| `paper-sl-l0-classic/logical1-read0-control.html` | logical1 READ=0 control |
| `paper-sl-l0-classic/logical0-read0-control.html` | logical0 READ=0 control |

These plots are descriptive only.  `-j 2pi` changes the phase display unit;
it does not make a phase trace an SFQ event count.  The accepted
`PAPER_JSL_LOAD_VALID` verdict remains based on the committed raw and direct
phase/voltage-area analysis.

