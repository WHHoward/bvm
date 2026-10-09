# A024_CB_DIRECT_D1_PAPER_CLOCK

- CASE: `CB_DIRECT_D1_PAPER_CLOCK`; ROW/COL=`1101/1101`; clock=`GLOBAL_ONESHOT`.
- Topology: 7 physical T1 + 6 physical CBU + D0 sJTL + DFF; no DOUT/carry termination loads.
- Artifact/QA: mechanical only; raw/provenance hashes in the run artifacts.
- Units: signed V·s/Φ0 arithmetic uses actual stored timestamps; P(...) remains radians; turns are navigation only.
- Descriptive lobe candidates are not event/SFQ counts; actual product-bit decoding is NOT_PERFORMED.
- Scientific interpretation: `NOT_PERFORMED`; authorized follow-up: none.

| Stage | D input | Previous C | CBU/JTL→T1 input | Sum | Carry |
|---|---:|---:|---:|---:|---:|
| D0 | 1.26803 | — | 1.15474 | 0.0523961 | 1.11985 |
| D1 | 1.11985 | 1.11985 | 1.18023 | 1.05292 | 0.075339 |
| D2 | 0.557555 | 0.075339 | 0.161913 | 0.0512903 | 0.074494 |
| D3 | 2.55754 | 0.074494 | 2.16189 | 0.0512719 | 1.07338 |
| D4 | 1.20165 | 1.07338 | 1.15493 | 1.05114 | 0.0744162 |
| D5 | 0.557562 | 0.0744162 | 0.161902 | 0.0512898 | 0.0744794 |
| D6 | 0.55454 | 0.0744794 | 0.16194 | 0.0515111 | 0.0882792 |

- DFF.O signed voltage area: `0.131983 Φ0` arithmetic.
- Stage timings and same-JJ phase/voltage cross-checks: `metrics.json`.
- Plots: full-chain overview, carry propagation, selected stage focus; raw-backed and descriptive only.
