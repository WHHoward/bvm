# A027_FULL_CB_CHAIN_ALL_CLOCK

- CASE: `FULL_CB_CHAIN_ALL_CLOCK`; ROW/COL=`1111/1111`; clock=`GLOBAL_ONESHOT`.
- Topology: 7 physical T1 + 6 carry stages (`CB_CARRY_BUFFER_ALL`) + D0 sJTL + DFF; no DOUT/carry termination loads.
- Artifact/QA: mechanical only; raw/provenance hashes in the run artifacts.
- Units: signed V·s/Φ0 arithmetic uses actual stored timestamps; P(...) remains radians; turns are navigation only.
- Descriptive lobe candidates are not event/SFQ counts; actual product-bit decoding is NOT_PERFORMED.
- Scientific interpretation: `NOT_PERFORMED`; authorized follow-up: none.

| Stage | D input | Previous C | CBU/JTL→T1 input | Sum | Carry |
|---|---:|---:|---:|---:|---:|
| D0 | 1.26753 | — | 1.15394 | 1.05153 | 0.0684171 |
| D1 | 2.21956 | 0.0684171 | 2.21956 | 0.0530117 | 1.06912 |
| D2 | 3.21962 | 1.06912 | 3.21962 | 1.05301 | 1.06912 |
| D3 | 4.21962 | 1.06912 | 4.21962 | 0.0530133 | 2.06912 |
| D4 | 4.21962 | 2.06912 | 4.21962 | 0.0530133 | 2.06912 |
| D5 | 4.21963 | 2.06912 | 4.21963 | 0.0530118 | 2.06901 |
| D6 | 3.21848 | 2.06901 | 3.21848 | 1.05323 | 1.08918 |

- DFF.O signed voltage area: `1.13199 Φ0` arithmetic.
- Stage timings and same-JJ phase/voltage cross-checks: `metrics.json`.
- Plots: full-chain overview, carry propagation, selected stage focus; raw-backed and descriptive only.
