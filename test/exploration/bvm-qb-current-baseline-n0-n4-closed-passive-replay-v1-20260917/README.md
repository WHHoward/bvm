# Current QB N0–N4 closed/passive/replay baseline

This series is a fresh 15-solve baseline and exhaustive visualization atlas.
It uses the current canonical QB source and the established BVM/JSL/JTL
topology. Existing experiments are read-only implementation references; their
raw files are never copied into this series.

Normal operation:

```bash
./run.sh --dry-run
./run.sh
./analyze.sh A001
./plot.sh A001 --list-signals
./plot.sh A001
```

`run.sh` creates one immutable `Axxx` attempt. The default run is the only
registered 15-case matrix. `--only` and `--case` are available for dry-run
inspection but are rejected for a physical baseline invocation because this
series is registered as exactly 15 solves.

`plot.sh` creates standalone grouped pages and a per-signal, per-window atlas;
it never creates cross-run comparison plots. Phase pages show raw radians,
unwrapped radians, and `rad/(2*pi)` navigation turns. Turns are not formal SFQ
counts.
