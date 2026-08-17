# bvm-s2-stable-load-20260817-01 — stable-initialization BVM load characterization

- disposition: BOUNDED_SOURCE_CHARACTERIZATION_REPORTED
- frozen spec: bvm-s2-stable-load-preregistration-v1 (task JH-20260817-BVM-S2-STABLE-LOAD-001); attempt A01
- provenance: build/josim-cli (v2.7.2837d13), dt=0.0125 ps, tstop=170.0 ps

## Strata readiness (JM1/JM2 PRE [80,90) p2p <= 0.020 rad)

| stratum | load (ohm) | polarity | ready |
|---|---|---|---|
| L01-positive | 1 | positive | True |
| L01-negative | 1 | negative | True |
| L12-positive | 12 | positive | True |
| L12-negative | 12 | negative | True |
| L25-positive | 25 | positive | True |
| L25-negative | 25 | negative | True |
| L50-positive | 50 | positive | True |
| L50-negative | 50 | negative | True |

## Endpoint-VI (exact Decimal tokens 97-105 ps)

| polarity | eligible | compatible | not_supported | ill_conditioned |
|---|---|---|---|---|
| positive | 5 | 0 | 5 | 0 |
| negative | 5 | 0 | 5 | 0 |

## Claim ceiling

- Bounded fixed-closure fixed-grid per-load terminal observations and matched-control-corrected endpoint-VI compatibility at registered exact tokens only.
- No numerical convergence, mechanism, logical-state, preservation, load-back-action, receiver, BQ, SFQ, fluxoid, interface, route, hardware, or universal-impedance claim.
