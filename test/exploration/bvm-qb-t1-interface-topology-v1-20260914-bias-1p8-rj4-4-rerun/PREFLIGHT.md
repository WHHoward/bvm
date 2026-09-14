# BVM -> QB -> T1 T1-netlist rerun — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

This is a new run because the prior bias-rerun raw is immutable. The deck is
copied byte-for-byte from the previous bias rerun and is not edited in this
experiment. The only registered circuit change is the current T1 netlist
change `R_J4 2 -> 4`; the current deck keeps `V_BIAS1=1.8m`,
`V_BIAS2=1.8m`, and `V_BIAS3=1.8m`. The canonical QB, BVM/JSL/JTL sources,
topology, mask, stimulus, time grid and solver are otherwise frozen.

Registration HEAD: `05f069d8205c73185c0146cde10acbcf9a4b6633`.

Frozen hashes: unchanged deck
`0d441ec28c3da9c5d55384659b747af17e66a0df6b97725e3b9c966893025c81`;
current T1 `828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`;
prior bias raw
`cdfea5122bfc478948190331deba9632ab9a1791dc075c2a6bd6584f158a03e4`.

The run directory contains only `deck.cir`, `raw.csv`, `run.log` and
`plots/`; no old raw is copied or overwritten.
