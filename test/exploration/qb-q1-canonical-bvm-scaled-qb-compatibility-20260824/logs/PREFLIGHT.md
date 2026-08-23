# QB-Q1 preflight and provenance

- Recorded at: `2026-08-24T01:48:36+08:00`
- Repository HEAD: `f800df0eab8c9402ec521d0c9e96fbc6d7a79e32`
- JoSIM binary: `build/josim-cli`, version `v2.7.2837d13`, compiled `2026-05-30 20:37:57`
- JoSIM binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Metric specification: `docs/research/METRIC_SPEC_V2.md`, version `2.0.0`, SHA-256 `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`
- Frozen logical semantics: `docs/research/BVM_LOGICAL_SEMANTICS_V1.md`, SHA-256 recorded in the final hash list.

## Local fixture snapshots

| file | SHA-256 |
|---|---|
| `inputs/bvm_cell.cir` | `ea7346546bef091dc2efa39ab6f0abcfa54f833aeeabb909dcf3815cdaea42a4` |
| `inputs/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |
| `inputs/bq_cell.cir` | `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2` |

The four no-receiver guard CSVs are append-only copies of the accepted canonical readout Exploration. Their source paths and hashes are listed in `reference/README.md`.

## Execution contract

- Direct galvanic `SL1 → QB IN`; canonical `R_SL/L_SL` is retained.
- Frozen scaled Q0 QB only; no transformer, conditioner, clamp, rectifier, hold, normalization, or parameter sweep.
- Four matched cases, with `logical1-read0-control` first and a hard stop on control instability/free-running/control event/source-storage failure.
- `.tran 0.0125p 170p`; all BVM/QB JJ P/V/I and source/storage guard probes are present.
