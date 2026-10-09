# A029_FULL_CB_CHAIN_3X3_CLOCK

- CASE: `FULL_CB_CHAIN_3X3_CLOCK`; ROW/COL=`1100/0011`; clock=`GLOBAL_ONESHOT`.
- Topology: 7 physical T1 + 6 carry stages (`CB_CARRY_BUFFER_ALL`) + D0 sJTL + DFF; no DOUT/carry termination loads.
- Artifact/QA: mechanical only; raw/provenance hashes in the run artifacts.
- Units: signed V·s/Φ0 arithmetic uses actual stored timestamps; P(...) remains radians; turns are navigation only.
- Descriptive lobe candidates are not event/SFQ counts; actual product-bit decoding is NOT_PERFORMED.
- Scientific interpretation: `NOT_PERFORMED`; authorized follow-up: none.

| Stage | D input | Previous C | CBU/JTL→T1 input | Sum | Carry |
|---|---:|---:|---:|---:|---:|
| D0 | 1.26753 | — | 1.15394 | 1.05153 | 0.0684171 |
| D1 | 2.21956 | 0.0684171 | 2.21956 | 0.0530117 | 1.06912 |
| D2 | 2.21962 | 1.06912 | 2.21962 | 0.0530133 | 1.06912 |
| D3 | 1.21962 | 1.06912 | 1.21962 | 1.05301 | 0.0691196 |
| D4 | 0.219623 | 0.0691196 | 0.219623 | 0.0530134 | 0.0691206 |
| D5 | 0.219633 | 0.0691206 | 0.219633 | 0.0530117 | 0.0690077 |
| D6 | 0.218477 | 0.0690077 | 0.218477 | 0.0532305 | 0.0891784 |

- DFF.O signed voltage area: `0.131988 Φ0` arithmetic.
- Stage timings and same-JJ phase/voltage cross-checks: `metrics.json`.
- Plots: full-chain overview, carry propagation, selected stage focus; raw-backed and descriptive only.
