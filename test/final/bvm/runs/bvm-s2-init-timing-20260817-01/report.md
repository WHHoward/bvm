# bvm-s2-init-timing-20260817-01 — BVM S2 initialization rising-edge timing

- run_id: bvm-s2-init-timing-20260817-01
- frozen spec identity: bvm-s2-timing-preregistration-v1 (task JH-20260817-BVM-S2-TIMING-001, design/preregistration.yaml + design/analysis-schema.json)
- metric spec: readiness threshold 0.020 rad; half-open actual CSV time windows; Decimal exact timestamps
- disposition: CONSISTENT_TIMING_SENSITIVITY_SUPPORTED
- provenance: build/josim-cli (v2.7.2837d13), dt=0.0125 ps, tstop=92.0 ps, R_LD=12 ohm, no read

## JM1/JM2 phase p2p (rad) by registered window

| run | timing | polarity | window | JM1 p2p | JM2 p2p |
|---|---|---|---|---|---|
| A-positive | S2_REGISTERED | positive | settling_early | 0.035811 | 0.64173913 |
| A-positive | S2_REGISTERED | positive | settling_mid | 0.014983 | 0.2338254 |
| A-positive | S2_REGISTERED | positive | settling_late | 0.005854 | 0.0913456 |
| A-positive | S2_REGISTERED | positive | readiness | 0.003528 | 0.0584342 |
| B-positive | S1_REGISTERED | positive | settling_early | 0.006392 | 0.0569526 |
| B-positive | S1_REGISTERED | positive | settling_mid | 0.001518 | 0.0232327 |
| B-positive | S1_REGISTERED | positive | settling_late | 0.000541 | 0.0090891 |
| B-positive | S1_REGISTERED | positive | readiness | 0.000351 | 0.0054827 |
| A-negative | S2_REGISTERED | negative | settling_early | 0.035811 | 0.64173913 |
| A-negative | S2_REGISTERED | negative | settling_mid | 0.014983 | 0.2338254 |
| A-negative | S2_REGISTERED | negative | settling_late | 0.005854 | 0.0913456 |
| A-negative | S2_REGISTERED | negative | readiness | 0.003528 | 0.0584342 |
| B-negative | S1_REGISTERED | negative | settling_early | 0.006392 | 0.0569526 |
| B-negative | S1_REGISTERED | negative | settling_mid | 0.001518 | 0.0232327 |
| B-negative | S1_REGISTERED | negative | settling_late | 0.000541 | 0.0090891 |
| B-negative | S1_REGISTERED | negative | readiness | 0.000351 | 0.0054827 |

## Readiness (co-primary, both JM1 and JM2 <= 0.020 rad in [80,90) ps)

| run | timing | polarity | co-primary ready |
|---|---|---|---|
| A-positive | S2_REGISTERED | positive | False |
| B-positive | S1_REGISTERED | positive | True |
| A-negative | S2_REGISTERED | negative | False |
| B-negative | S1_REGISTERED | negative | True |

## A/B contrasts (Delta = S1_REGISTERED - S2_REGISTERED, [80,90) ps)

| polarity | Delta JM2 (rad) | |Delta JM2| >= 0.020 | readiness classification changed |
|---|---|---|---|
| positive | -0.0529515 | True | True |
| negative | -0.0529515 | True | True |

## Claim ceiling

- Bounded fixed-closure, fixed-grid evidence for or against a reproducible association of the registered initialization rising-edge intervention with JM1/JM2 pre-read settling/readiness only.
- No detailed physical mechanism, convergence, logical-state, preservation, load-back-action, receiver, SFQ, fluxoid, interface, route, hardware, or universal claim.
- Disposition: CONSISTENT_TIMING_SENSITIVITY_SUPPORTED.
