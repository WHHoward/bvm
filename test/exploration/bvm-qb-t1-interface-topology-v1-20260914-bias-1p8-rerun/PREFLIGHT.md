# BVM -> QB -> T1 deck-bias rerun — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

This is a new run because the prior `jtl6/0011` raw is immutable. The current
user-edited deck is copied verbatim into the new run. Its exact bias changes
are `V_BIAS1 1.67m -> 1.8m`, `V_BIAS2 1.67m -> 1.8m`, and replacement of
`I_BIAS3 35u` by `V_BIAS3 1.8m`; the source-type change is recorded literally.
The canonical QB, current T1 cell (including `R_J4=2`), BVM/JSL/JTL sources,
topology, mask, stimulus, time grid and solver are otherwise frozen. No old raw
is copied or overwritten.
