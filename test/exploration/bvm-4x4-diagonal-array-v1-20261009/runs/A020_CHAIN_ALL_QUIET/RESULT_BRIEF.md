# A020_CHAIN_ALL_QUIET

- CASE: `CHAIN_ALL_QUIET`; ROW/COL=`1111/1111`; clock=`QUIET`.
- Topology: 7 physical T1 + 6 physical CBU + D0 sJTL + DFF; no DOUT/carry termination loads.
- Artifact/QA: mechanical only; raw/provenance hashes in the run artifacts.
- Units: signed V·s/Φ0 arithmetic uses actual stored timestamps; P(...) remains radians; turns are navigation only.
- Descriptive lobe candidates are not event/SFQ counts; actual product-bit decoding is NOT_PERFORMED.
- Scientific interpretation: `NOT_PERFORMED`; authorized follow-up: none.

| Stage | D input | Previous C | CBU/JTL→T1 input | Sum | Carry |
|---|---:|---:|---:|---:|---:|
| D0 | 1.26291 | — | 1.14633 | 0.13686 | 0.08224 |
| D1 | 1.55706 | 0.08224 | 1.15634 | 0.136733 | 0.0821776 |
| D2 | 2.55767 | 0.0821776 | 2.16198 | 0.0511845 | 1.07338 |
| D3 | 4.20165 | 1.07338 | 4.15492 | 0.0510258 | 2.0731 |
| D4 | 3.20137 | 2.0731 | 4.14098 | 0.0280484 | 1.29917 |
| D5 | 2.20235 | 1.29917 | 3.15239 | 0.136665 | 1.081 |
| D6 | 1.19993 | 1.081 | 2.15496 | 0.0509814 | 1.07059 |

- DFF.O signed voltage area: `0.174002 Φ0` arithmetic.
- Stage timings and same-JJ phase/voltage cross-checks: `metrics.json`.
- Plots: full-chain overview, carry propagation, selected stage focus; raw-backed and descriptive only.
