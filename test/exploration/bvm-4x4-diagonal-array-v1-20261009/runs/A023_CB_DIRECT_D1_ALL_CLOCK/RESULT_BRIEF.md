# A023_CB_DIRECT_D1_ALL_CLOCK

- CASE: `CB_DIRECT_D1_ALL_CLOCK`; ROW/COL=`1111/1111`; clock=`GLOBAL_ONESHOT`.
- Topology: 7 physical T1 + 6 physical CBU + D0 sJTL + DFF; no DOUT/carry termination loads.
- Artifact/QA: mechanical only; raw/provenance hashes in the run artifacts.
- Units: signed V·s/Φ0 arithmetic uses actual stored timestamps; P(...) remains radians; turns are navigation only.
- Descriptive lobe candidates are not event/SFQ counts; actual product-bit decoding is NOT_PERFORMED.
- Scientific interpretation: `NOT_PERFORMED`; authorized follow-up: none.

| Stage | D input | Previous C | CBU/JTL→T1 input | Sum | Carry |
|---|---:|---:|---:|---:|---:|
| D0 | 3.26339 | — | 3.14714 | 0.137394 | 2.12564 |
| D1 | 2.12564 | 2.12564 | 2.17312 | 1.13782 | 0.0831164 |
| D2 | 2.55768 | 0.0831164 | 2.162 | 0.0512743 | 1.07338 |
| D3 | 4.20165 | 1.07338 | 4.15492 | 0.0511158 | 2.07324 |
| D4 | 3.20154 | 2.07324 | 4.14949 | 1.13671 | 1.08096 |
| D5 | 2.20169 | 1.08096 | 3.15501 | 1.05112 | 1.0733 |
| D6 | 1.1999 | 1.0733 | 2.15487 | 1.05107 | 1.07059 |

- DFF.O signed voltage area: `0.174002 Φ0` arithmetic.
- Stage timings and same-JJ phase/voltage cross-checks: `metrics.json`.
- Plots: full-chain overview, carry propagation, selected stage focus; raw-backed and descriptive only.
