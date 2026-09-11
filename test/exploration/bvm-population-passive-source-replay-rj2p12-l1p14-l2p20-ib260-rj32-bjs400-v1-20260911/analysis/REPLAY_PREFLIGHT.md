# REPLAY_PREFLIGHT — exact passive JSL8 current replay

- Status: **PASS**
- HEAD: `953c938f87d1b7bd3a8e782e3b2a8d943364c07b`
- Source: passive raw `I(B_JSL8)` snapshots; direct exact stored pairs; no waveform transformation.

| replay case | source | expected pairs | actual pairs | fidelity | result |
|---|---|---:|---:|---|---|
| `REPLAY_N2_0011_RJ2P12` | `PASSIVE_N2_0011` | 1999 | 1999 | `True` | `PASS` |
| `REPLAY_N3_0111_RJ2P12` | `PASSIVE_N3_0111` | 1999 | 1999 | `True` | `PASS` |
| `REPLAY_N4_1111_RJ2P12` | `PASSIVE_N4_1111` | 1999 | 1999 | `True` | `PASS` |

All replay decks contain only the current RJ2=12 QB, six-stage JTL, 10 ohm termination and `I_REPLAY 0 QBIN`. No BVM/JSL active element or sign change is present. The replay is ideal forcing and is not a circuit-equivalent source reconstruction.

Machine records: `qa/replay_preflight.json`, `qa/replay_fidelity_qa.json`.
