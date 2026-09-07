# REPLAY_PREFLIGHT — exact passive JSL8 current replay

- Status: **PASS**
- Preflight time: `2026-09-07T15:32:58+08:00`
- Source: passive raw `I(B_JSL8)` snapshots; no interpolation or waveform transformation.

| replay case | source | PWL pairs | exact timestamp/value fidelity | result |
|---|---|---:|---|---|
| `REPLAY_SINGLE` | `SINGLE_PASSIVE` | 1999 | `True` | `PASS` |
| `REPLAY_ARRAY` | `ARRAY_PASSIVE` | 1999 | `True` | `PASS` |

Both replay decks contain only `I_REPLAY 0 QBIN`, the exact registered QB, the exact six-stage JTL and one 10 Ω termination. They contain no BVM or JSL. The positive source orientation is the direct `JSL8 -> QBIN` sense; no sign change was applied.

Machine record: `analysis/replay_preflight.json`.
