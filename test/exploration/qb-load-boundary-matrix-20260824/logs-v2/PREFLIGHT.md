# v2 preflight and provenance

Preflight timestamp: `2026-08-24T08:49:12+08:00`

## Frozen provenance

- Parent HEAD: `30590c9d9d4831f98c2a3f1db28ee7f6813eee59`
- JoSIM: `build/josim-cli`, `v2.7.2837d13`
- JoSIM SHA-256: `48655cb31d6297ba571a300c3c7e0b5665d11c8cc1f02b5b4f6e9b0db50440b2`
- `jjmit.cir` SHA-256: `19862d1fd1f1f44dfa1523848d7d3b5e2594a6c5da8fdd80144b449e5312a336`
- Standard `JTL.cir` SHA-256: `ac02fc931742bb857723f9fbb57ac97a179beb6a6466d5a1184e7cf937f599aa`
- Q0 `bq_cell.cir` SHA-256: `5ee4e8f054a9a49aea7e48493b20ef3d794db01b2902f15a439b0ea31f2276a2`
- Q5 `bq_cell.cir` SHA-256: `4ecedca8eba9e80b47294900485723aee4017cffc256ad42777a76f184ac14dc`

## Static checks

- A/B/D/E: `R_LOAD OUT 0 10` absent and `I(R_LOAD)` absent.
- C: exactly one `R_LOAD OUT 0 10` and its current probe retained.
- B/C/E: exactly one copied standard JTL source and two `THmitll_JTL` instances.
- Q0 source and timing are unchanged: six periodic pulses, `dt=0.1 ps`, stop `300 ps`.
- Q5 replay sources and timing are unchanged: four matched cases, `dt=0.0125 ps`, stop `170 ps`.
- No BVM, transformer, conditioner, T1, or parameter change was introduced.

The first generated v1 batch failed artifact validity because a removed load
was still requested by a current probe. It is retained but excluded; see
`ATTEMPT-01-INVALID.md`. The v2 batch is the only conclusion-grade batch for
this Exploration.
