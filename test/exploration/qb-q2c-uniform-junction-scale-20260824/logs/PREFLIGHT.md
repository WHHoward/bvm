# QB-Q2C preflight and provenance

- Recorded at: `2026-08-24T03:01:22+08:00`
- Parent repository HEAD: `0799d0daefd87701bfbc2a9b3552924905f1d502`
- Working tree: dirty only because this new untracked QB-Q2C Exploration is being created; the parent scientific tree is unchanged.
- JoSIM binary: `/home/howard/JoSIM/build/josim-cli`, version `v2.7.2837d13`, compiled `2026-05-30 20:37:57`
- JoSIM binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Metric specification: `/home/howard/JoSIM/docs/research/METRIC_SPEC_V2.md`, version `2.0.0`, SHA-256 `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`
- Requested timestep/stop: `0.0125 ps` / `170 ps`
- Fixture builder SHA-256: `f6b55c7a8ccd02a95c7e9614126ed77ad2cce56c91767def5a738391b6ca366e`
- Analysis script SHA-256: `8e574e7263ed9f3c74e85284d64e85293b9ae33880cd72001c8fa7ac87b389ac`

## Frozen model and scale snapshots

| file | SHA-256 |
|---|---|
| `inputs/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |
| `inputs/S085/bq_cell.cir` | `63251b8be15a23f31bacd9bbe74f930be1f09f30dcf5809defe8ccf5555fafef` |
| `inputs/S070/bq_cell.cir` | `fd3d6db520e94342c79e363a36cdce2b3c4d73dc5991b5eb6e7f0ae6e3485179` |
| `inputs/S055/bq_cell.cir` | `d4d13e8c397752390162e2be8bc5b83c402df57ce9b0be8800fb43c65825cc8d` |

## Replay provenance

The four source snapshots are copied byte-for-byte from the accepted QB-Q2B replay fixture, whose logical1/logical0 canonical replay originates in QB-Q2A:

| snapshot | SHA-256 |
|---|---|
| `inputs/replay_sources/C-canonical-logical1-vsl.csv` | `6868a2bd41ccddaf9606b301d95877eeb574a58e9eafeea3ca7c854a99cac046` |
| `inputs/replay_sources/C0-canonical-logical0-vsl.csv` | `056083c6b205dd33e496732aefa0b862a603632650e9dbf54df41667b398e3d6` |
| `inputs/replay_sources/logical1-read0-control-vsl.csv` | `ddefa209d176423b6ee74d4b4a892d5350cba14a8c12f08fff72aeede87addf9` |
| `inputs/replay_sources/logical0-read0-control-vsl.csv` | `0b783d050f3c1ca6985ad5e50350378b799021c5243edf1315914fee5d1a1736` |

No physical BVM, transformer, DCSFQ, JTL or T1 is present. s=1 is an accepted Q2A/Q2B reference and is not rerun.
