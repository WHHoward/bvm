# BVM -> QB -> T1 single-point T1 rerun — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

This is a new run ID because the prior `jtl6/0011` raw is immutable. The only
registered circuit change is the user's current `R_J4 4 -> 2` edit in
`circuits/t1/t1_cell.cir`. The canonical QB, BVM/JSL/JTL sources, topology,
stimulus, solver, probes and time grid are frozen from the completed v2 case.
No old raw is copied or overwritten; the prior raw is referenced by path/hash
in provenance only. The run directory contains only `deck.cir`, `raw.csv`,
`run.log` and `plots/`.

Registration HEAD: `65e93573c7c9447685009462665b467dabbcc7d3`.

Solver: `build/josim-cli` v2.7.2837d13; SHA-256
`48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`.

Frozen source hashes: canonical QB
`f676ba1ecb9b2607631a5cfc2f99b7d67e09b9e821457015fba375b8a39f13b0`;
global jjmit model
`19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`;
current T1 `df64b1985cfdbbf7a0589a35f5eafafeac7df0134e8484eed5171e221bb95a26`.

The prior comparison raw SHA-256 is
`a0f4e199575ab2e8332c3791c8552f959718d097d62eef1d06ae448ab67d27d1`;
it is not copied or overwritten.
