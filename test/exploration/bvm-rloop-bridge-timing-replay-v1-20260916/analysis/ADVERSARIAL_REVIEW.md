# Adversarial review probes — mechanical only

- No-op/wrong-branch probe: canonical direction audit status `PASS` / `PASS`; replay source direction is registered as 6 -> 10.
- Coupling probe: four BVM instances have separate PWL source columns and separate cloned subcircuits; no common replay waveform is used.
- Weak-oracle probe: ordered navigation uses internal BJ1, BJ2, JTL1..6; terminal is corroboration only.
- Stale-artifact probe: current raw before/after equal `True` and read-only reference hashes equal `True`.
- Boundary probe: exact stored-grid delay shifts, 110-ps hold, half-open windows; no interpolation or resampling.
- Overclaim guard: no current-is-fundamental claim, no physical delay implementation claim, no SFQ count, no root-cause claim, and no Outcome A/B/C assignment.
