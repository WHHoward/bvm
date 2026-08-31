# PAPER-SL-Q1 preflight and provenance

- Recorded: `2026-08-24T03:38:44+08:00`
- Parent HEAD: `0bf84c438d4890b7ed095fe526711eafab520ada`
- JoSIM binary: `/home/howard/JoSIM/build/josim-cli`
- JoSIM version: `v2.7.2837d13`
- JoSIM binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Metric specification: `docs/research/METRIC_SPEC_V2.md`, version `2.0.0`, SHA-256 `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`

## Frozen inputs

| file | provenance | SHA-256 |
|---|---|---|
| `inputs/bq_cell.cir` | copied from accepted QB-Q2A scaled fixture | `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2` |
| `inputs/jjmit.cir` | repository JJ model snapshot | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |
| PAPER-SL-L0 logical1 raw | accepted external-series-load raw | `6ddc85050294fd38be0f55602af3517ec6bcfcd00794128f69dee545bf82ef65` |
| PAPER-SL-L0 logical0 raw | accepted external-series-load raw | `8b9c1d10d4547db0fcb8cd172eea72d4e917aa91b124b4759bd8e1405b843951` |

The replay builder additionally verifies all twelve JSL branch-current
columns. Its maximum series spread was `0 A` for logical1/logical0 READ and
`1.0e-18 A` for both READ=0 controls.

