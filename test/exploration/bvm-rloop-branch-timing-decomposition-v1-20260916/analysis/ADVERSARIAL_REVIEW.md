# Adversarial review probes - mechanical only

- Branch direction/KCL audit: `{"0011": "PASS", "0111": "PASS"}`.
- Per-instance coupling probe: each clone has a distinct branch PWL column; no common waveform is used.
- Weak-oracle probe: ordered internal BJ1->BJ2->JTL1..6 chronology; terminal is corroboration only.
- Stale-artifact probe: current raw hashes unchanged `True` and references unchanged `True`.
- Boundary probe: exact 3-sample shift, 110-ps hold, half-open windows, no interpolation/resampling.
- Overclaim guard: no physical delay, current-only sufficiency, SFQ count, root-cause, or final branch category assignment.
