# PAPER-SL-Q2 preflight and provenance

- Recorded: `2026-08-24T03:54:53+08:00`
- Parent HEAD: `5627a6386a143784db109138e953368f7ab8a4c2`
- JoSIM binary: `/home/howard/JoSIM/build/josim-cli`
- JoSIM version: `v2.7.2837d13`
- JoSIM binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Metric specification: `docs/research/METRIC_SPEC_V2.md`, version `2.0.0`, SHA-256 `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`
- Q1 replay source fixture: `test/exploration/paper-sl-q1-20260824/replay_sources`
- Q1 source byte identity was checked before execution; only the IBIAS PWL line differs in each generated deck.

## Frozen model snapshots

| file | SHA-256 |
|---|---|
| `inputs/bq_cell.cir` | `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2` |
| `inputs/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |

The first 37.5 µA control attempt failed before simulation because the
nested deck could not resolve `jjmit.cir`; that invalid attempt is preserved
under `reference/invalid-attempt-01`. It generated no raw CSV and is excluded
from the scientific verdict.

