# Timestep spot-check review

Classification: `TIMESTEP_ROBUST_CANDIDATE_WITHIN_TESTED_DT`.

The canonical 0.1ps pair is exact reuse; only 0.05ps and 0.025ps were newly solved. The comparison uses actual stored time grids and does not alter the canonical timestep.

| dt (ps) | mask | control | oracle/response | terminal cluster | terminal final area / Phi0 |
|---:|:---:|:---|:---|:---|---:|
| 0.1 | 0001 | CLEAN | BOUNDED_RESULT | ONE_RESPONSE_CLUSTER | 0.9999999974216752 |
| 0.1 | 0011 | CLEAN | BOUNDED_RESULT | TWO_SEPARATED_PULSES | 2.000000004504597 |
| 0.05 | 0001 | CLEAN | BOUNDED_RESULT | ONE_RESPONSE_CLUSTER | 0.9999999138391351 |
| 0.05 | 0011 | CLEAN | BOUNDED_RESULT | TWO_SEPARATED_PULSES | 1.9999999397796284 |
| 0.025 | 0001 | CLEAN | BOUNDED_RESULT | ONE_RESPONSE_CLUSTER | 0.9999999495559827 |
| 0.025 | 0011 | CLEAN | BOUNDED_RESULT | TWO_SEPARATED_PULSES | 1.9999999423915038 |

The timing/area deltas for 0.1→0.05 and 0.05→0.025ps are machine-readable in `qa/timestep_qa.json`.

No phase turn, voltage area or terminal area is an SFQ count. This finite spot-check does not establish full numerical convergence.
