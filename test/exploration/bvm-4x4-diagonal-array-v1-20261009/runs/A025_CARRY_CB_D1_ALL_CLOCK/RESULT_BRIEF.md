# A025_CARRY_CB_D1_ALL_CLOCK

- CASE: `CARRY_CB_D1_ALL_CLOCK`; ROW/COL=`1111/1111`; clock=`GLOBAL_ONESHOT`.
- Topology: 7 physical T1 + 6 physical CBU + D0 sJTL + DFF; no DOUT/carry termination loads.
- Artifact/QA: mechanical only; raw/provenance hashes in the run artifacts.
- Units: signed V·s/Φ0 arithmetic uses actual stored timestamps; P(...) remains radians; turns are navigation only.
- Descriptive lobe candidates are not event/SFQ counts; actual product-bit decoding is NOT_PERFORMED.
- Scientific interpretation: `NOT_PERFORMED`; authorized follow-up: none.

| Stage | D input | Previous C | CBU/JTL→T1 input | Sum | Carry |
|---|---:|---:|---:|---:|---:|
| D0 | 1.26753 | — | 1.15394 | 1.05153 | 0.0684172 |
| D1 | 2.21956 | 0.0684172 | 2.21956 | 0.0530138 | 1.07426 |
| D2 | 3.20165 | 1.07426 | 3.15493 | 1.05112 | 1.07331 |
| D3 | 4.20165 | 1.07331 | 5.15492 | 1.05112 | 2.0733 |
| D4 | 3.20165 | 2.0733 | 4.15492 | 1.05112 | 2.07324 |
| D5 | 2.20155 | 2.07324 | 4.14949 | 1.13671 | 1.08096 |
| D6 | 1.19993 | 1.08096 | 2.15496 | 1.05107 | 1.07059 |

- DFF.O signed voltage area: `0.174002 Φ0` arithmetic.
- Stage timings and same-JJ phase/voltage cross-checks: `metrics.json`.
- Plots: full-chain overview, carry propagation, selected stage focus; raw-backed and descriptive only.
