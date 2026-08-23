# QB-Q2B preflight and provenance

- Recorded at: `2026-08-24T02:49:52+08:00`
- Parent repository HEAD: `58d35f96ab5a998fdb6697984a6e713332f94c4e`
- JoSIM binary: `build/josim-cli`, version `v2.7.2837d13`, compiled `2026-05-30 20:37:57`
- JoSIM binary SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- Metric specification: `docs/research/METRIC_SPEC_V2.md`, version `2.0.0`, SHA-256 `f88a36f4d310b2572efdc7408d734640f25dd5aea2246b74fbb8b7bb7f0be470`

## Frozen local models

| file | SHA-256 |
|---|---|
| `inputs/bq_cell.cir` | `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2` |
| `inputs/jjmit.cir` | `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336` |

The QB cell is the byte-preserved Q2A scaled cell. The Q2B decks change only the independent `IBIAS` source from the accepted 35 µA baseline to 30 µA or 40 µA.

## Frozen replay provenance

The canonical logical1/logical0 replay snapshots are byte-identical to QB-Q2A:

| snapshot | SHA-256 |
|---|---|
| `inputs/replay_sources/C-canonical-logical1-vsl.csv` | `6868a2bd41ccddaf9606b301d95877eeb574a58e9eafeea3ca7c854a99cac046` |
| `inputs/replay_sources/C0-canonical-logical0-vsl.csv` | `056083c6b205dd33e496732aefa0b862a603632650e9dbf54df41667b398e3d6` |
| `inputs/replay_sources/logical1-read0-control-vsl.csv` | `ddefa209d176423b6ee74d4b4a892d5350cba14a8c12f08fff72aeede87addf9` |
| `inputs/replay_sources/logical0-read0-control-vsl.csv` | `0b783d050f3c1ca6985ad5e50350378b799021c5243edf1315914fee5d1a1736` |

These are ideal voltage replays for standalone QB diagnosis, not a new physical BVM run. No BVM source/storage guard is therefore asserted by this Exploration.

## Execution gate

- Selected points: `IBIAS=30 µA` and `IBIAS=40 µA`; no 35 µA rerun and no other point.
- Per point order: logical1 READ=0 control, logical0 READ=0 control, logical1 READ, logical0 READ.
- Timestep/stop: `.tran 0.0125p 170p`.
- Controls were bounded before the corresponding READ cases were run.
- Complete-event evidence uses same-JJ continuous phase, same-segment voltage area, and bounded post behavior; no legacy fast-event metric is used as a gate.
