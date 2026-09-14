# BVM -> QB -> T1 same-configuration mask pair rerun — PREFLIGHT

This experiment is governed by docs/EXPERIMENT_CONTRACT.md.

This run keeps the current bias/T1/deck configuration and adds only the two
registered final-read masks `0111` and `1111`. The source deck is copied
byte-for-byte from the prior `bias-1p8-rj4-4` `jtl6/0011` deck; the two new
decks differ only in the header mask and the eight final-read WL/SE values.
The prior `0011` raw is preserved and referenced by path/hash only.

Registration HEAD: `1043b13044a9161167fc1695eaf5ace3c84b9cd2`.

Frozen deck-template SHA-256:
`0d441ec28c3da9c5d55384659b747af17e66a0df6b97725e3b9c966893025c81`.
Frozen current T1 SHA-256:
`828b873132b32af4fd3cebcbfa42a90fd50f15e75fdb976f1d13e07c3f1fe237`.
The run directory contains only `deck.cir`, `raw.csv`, `run.log` and
`plots/`.
