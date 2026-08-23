# QB-Q2A preflight and provenance

- Recorded at: `2026-08-24T02:23:30+08:00`
- Parent repository HEAD: `4166fe683bdf4599d853546ba7bec64395105e76`
- JoSIM binary: `/home/howard/JoSIM/build/josim-cli`
- JoSIM version: `v2.7.2837d13`, compiled `2026-05-30 20:37:57`
- JoSIM binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Metric specification: `docs/research/METRIC_SPEC_V2.md`, version `2.0.0`, SHA-256 `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`

## Frozen model snapshots

| file | SHA-256 |
|---|---|
| `inputs/bq_cell.cir` | `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2` |
| `inputs/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |

## Replay source provenance

| source | SHA-256 |
|---|---|
| QB-Q1 logical1 raw | `0d01cd22661baa2b0b5f68f22b98bea5f2d14783ce6ac42e77993decfef2d073` |
| canonical logical1 no-receiver raw | `3674b974dc0c897402745436a083704c1320560242ac20ba0634d11f6d18d2fa` |
| canonical logical0 no-receiver raw | `f2c58c10de5f4ef91b10d7e8de72a420bf5238a19caf0b0106aa3b440ba99a4b` |

B/C/C0 use the source-port `V(SL1)` column as an ideal voltage-source replay. The companion branch currents are retained for scale diagnostics and are not substituted into the replay source.

## Execution closure

- A positive control was executed first and produced exit code 0.
- B/C/C0 were executed only after A passed the local Q0 pulse-by-pulse positive-control check.
- All four decks use the frozen QB cell; no BVM, DCSFQ, transformer, JTL or T1 is present.
