# REPLAY_PREFLIGHT — exact read-count passive JSL8 replay

- Status: **PASS**
- Preflight time: `2026-09-07T16:37:16+08:00`
- Source: N2/N3/N4 passive raw `I(B_JSL8)` snapshots; no interpolation or waveform transformation.

| replay case | source | PWL pairs | exact timestamp/value fidelity | result |
|---|---|---:|---|---|
| `N2_REPLAY` | `N2_PASSIVE` | 1999 | `True` | `PASS` |
| `N3_REPLAY` | `N3_PASSIVE` | 1999 | `True` | `PASS` |
| `N4_REPLAY` | `N4_PASSIVE` | 1999 | `True` | `PASS` |

Each replay deck contains only `I_REPLAY 0 QBIN`, the exact registered QB, the exact six-stage JTL and one 10 ohm termination. It contains no BVM, COMMON_SL or JSL element. Positive source orientation is direct JSL8 -> QBIN; no sign change was applied.

Machine record: `analysis/replay_preflight.json`.
