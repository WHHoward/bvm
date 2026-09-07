# PREFLIGHT — passive capture + current replay

- Status: **PASS**
- Preflight time: `2026-09-07T15:30:31+08:00`
- HEAD at setup/preflight: `510cb59ebaa237268980133435aa2ff32468c935` / `510cb59ebaa237268980133435aa2ff32468c935`
- Scope: passive capture first; replay decks are generated only from the resulting exact raw `I(B_JSL8)` snapshots.

## Passive fixtures

| case | BVM | JSL | JSL8 endpoint | QB/JTL/termination | result |
|---|---:|---:|---|---|---|
| `SINGLE_PASSIVE` | 1 | 8 × `jjmit area=5.0` | GND | absent | `PASS` |
| `ARRAY_PASSIVE` | 4 → `COMMON_SL` | 8 × `jjmit area=5.0` | GND | absent | `PASS` |

The BVM input is the historical JM2-connected variant; the canonical BVM is not an input. All passive decks use `.tran 0.1p 200p` and the registered WRITE0 → ZERO_STATE_READ_CONTROL → WRITE1 → selective READ history.

## Replay contract

Replay decks will contain only `I_REPLAY 0 QBIN`, the exact `BVMSim/BQ.cir`, the exact six-stage `BVMSim/library_josim/jtl2.cir`, and `R_TERM ... 10`. The source snapshots will retain every passive raw timestamp/current pair without interpolation, smoothing, fitting, scaling, shifting, rectification or truncation. A separate post-capture replay preflight will verify the generated decks and source fidelity before either replay run.

Machine record: `analysis/topology_preflight.json`.
