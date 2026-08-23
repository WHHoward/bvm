# QB-Q0 preflight and provenance

- Recorded at: `2026-08-24T00:58:09+08:00`
- Repository HEAD: `f43422507195860075d077a5f692e41bf50cc0b0`
- JoSIM binary: `build/josim-cli`
- JoSIM version: `v2.7.2837d13`, compiled `2026-05-30 20:37:57`
- JoSIM binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Metric specification: `docs/research/METRIC_SPEC_V2.md`, version `2.0.0`, SHA-256 `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`

## Immutable input snapshots

| snapshot | SHA-256 |
|---|---|
| `inputs/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |
| `inputs/bq_cell.cir` | `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2` |
| `inputs/bq_cell_paper.cir` | `a3accfd49ea7bd1dab46f79f4856a0e0a6c781185c4671a78c863b2217bdb880` |
| `inputs/test_qb_final.cir` | `28ebef79bdb3223169610abaff793eab0cf50f1ad596fda42117d2bad5fd3a75` |
| `inputs/test_bvm_paper_bq.cir` | `c0b5c9187d08d2e5f913b2dd8ae189ccfe5a6dc6f0c394dcaf8396d6f584b679` |

## Execution contract

- Seven fixed standalone cases: scaled `0/45/68.4/90 µA`; paper `0/68.4/90 µA`.
- No BVM, transformer, DCSFQ, JTL, T1, parameter sweep, or optimization.
- Each wrapper uses `.tran 0.1p 300p` and `pulse(0 IIN 10p 1p 1p 5p 50p)`.
- Analysis uses direct raw `P`, `V`, and `I` columns and does not invoke `fast_events` or `scripts/sfq_metrics.py`.

## Commands

Each case was run from this exploration directory with the corresponding wrapper:

```text
../../../build/josim-cli -m -o raw/<group>/<case>.csv inputs/<wrapper>.cir
```

The exact command, stdout, stderr, and exit status are stored per case under `logs/`.
