# PREFLIGHT — read-count passive capture

- Status: **FAIL**
- Preflight time: `2026-09-07T16:34:29+08:00`
- HEAD at setup/preflight: `217305580f1c9cec17839896730fbe9b1016c837` / `217305580f1c9cec17839896730fbe9b1016c837`
- N1: existing `ARRAY_PASSIVE` raw is referenced by hash and is not rerun.
- New physical captures: exactly N2, N3 and N4.

## Passive fixtures

| case | final READ mask | BVM | JSL | JSL8 endpoint | QB/JTL/termination | result |
|---|---|---:|---:|---|---|---|
| `N2_PASSIVE` | `1100` | 4 -> `COMMON_SL` | 8 x `jjmit area=5.0` | GND | absent | `PASS` |
| `N3_PASSIVE` | `1110` | 4 -> `COMMON_SL` | 8 x `jjmit area=5.0` | GND | absent | `PASS` |
| `N4_PASSIVE` | `1111` | 4 -> `COMMON_SL` | 8 x `jjmit area=5.0` | GND | absent | `PASS` |

All three decks use the historical JM2-connected variant, exact registered model files, the common WRITE0 -> ZERO_STATE_READ_CONTROL -> WRITE1 history, and `.tran 0.1p 200p`. Only the final READ mask changes.

Replay decks are generated only after the passive raw captures and a separate exact-PWL preflight.

Machine record: `analysis/topology_preflight.json`.
