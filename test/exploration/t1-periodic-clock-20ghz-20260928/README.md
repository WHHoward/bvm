# T1 Scheme-B 20 GHz CLK-only verification

This is a standalone, one-run T1 clock-input check. It does not instantiate the
BVM array, QB, CB, sJTL, or any data source. The T1 data input `I` is tied to
ground. The canonical T1 netlist and internal `R_J4=4Ω` are left unchanged.

The experiment is governed by `docs/EXPERIMENT_CONTRACT.md`. Run only:

```bash
./run.sh --write-preflight
./run.sh --dry-run
./run.sh --run
```

`--run` creates the sole immutable run directory `runs/A001_T1_CLK_ONLY/` and
refuses to overwrite it. There is no retry or second run. The clock waveform is
an ideal periodic voltage source with a 5Ω series resistor; it is not asserted
to be an SFQ clock. Metrics use the actual stored time rows and report raw
phase radians, phase/radian-to-turn arithmetic, same-JJ voltage integrals, and
S/C voltage areas without interpreting them as SFQ events or logic truth.

The plots are generated with the repository's classic `josim-plot2.py`
`sep_comb`/dark/`2pi` layout. One whole-run key-signal view plus four registered
per-cycle zooms are stored locally; full DEBUG probes remain in raw. The scientific DELTA package excludes the
derived HTML by default and retains the raw, deck, source/probe manifests,
metrics, QA, and plotting provenance.
