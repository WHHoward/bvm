# Stage A raw review navigation

Scientific interpretation: `NOT_PERFORMED`.

The source is an immutable closed-loop raw current. The replay is ideal current forcing; it does not erase interaction history embedded in the recorded waveform. Phase navigation and activity segments are not SFQ counts.

## Stored-history and source fidelity

- source raw SHA-256: `3da7b754c990316ff8e5981692afa958d8056a61020a1912548bf6f2b7e0249c`
- source snapshot SHA-256: `1329ccd6fbe2eef0b3cd40816b3e59b9d6063414ec8a2c7d1d39e676092a6e17`
- replay raw SHA-256: `2ba9b57a659abafebb8c27650805fe9c3719521d811a442b1c09476d67d3813f`
- exact source/replay current mismatch: `0.0` A

| signal | 109.9 ps closed | 109.9 ps replay | difference |
|---|---:|---:|---:|
| `I(L1|XBQ1)` | -9.382264e-05 | -9.382264e-05 | 0 |
| `I(L2|XBQ1)` | 0.0001661774 | 0.0001661774 | 0 |
| `I(BJ1|XBQ1)` | 9.032541e-05 | 9.032541e-05 | 0 |
| `I(BJ2|XBQ1)` | 0.0001516785 | 0.0001516785 | 0 |
| `P(BJ1|XBQ1)` | 1.581809 | 1.581809 | 0 |
| `P(BJ2|XBQ1)` | 0.9710542 | 0.9710542 | 0 |

## Downstream raw navigation

| track | first threshold-support time (ps) |
|---|---:|
| `V(QBOUT)` | 110.0 |
| `V(JTL1_OUT)` | 114.8 |
| `V(JTL2_OUT)` | 117.8 |
| `V(JTL3_OUT)` | 120.60000000000001 |
| `V(JTL4_OUT)` | 123.6 |
| `V(JTL5_OUT)` | 126.60000000000001 |
| `V(JTL6_OUT)` | 129.3 |
| `I(R_TERM)` | 131.4 |

The registered phase landmarks use a 101 ps baseline and are `PHASE_NAVIGATION_ONLY`. The operator does not classify the response as 2/3/4 or start Stage B in this turn; that requires the declared scientific-review authorization.

Final stage status: `STAGE_A_EVIDENCE_READY / SCIENTIFIC_REVIEW_REQUIRED`.
