# LS3 ideal timing upper bound (bvm-rloop-ls3-delay-upper-bound-v1-20260917)

- Status: ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW
- Artifact status: VALID
- Scientific interpretation: NOT_PERFORMED; final classification: SCIENTIFIC_REVIEW_REQUIRED.
- Parent: 1348140f17f0d9467dc42238eaa1e252e877e07a; fixed 0.5-ps pair, with 0.6 ps only after the registered mechanical gate.

| delay | N2 count | N3 count | N2 second response | N3 fourth chain |
|---:|---:|---:|---|---|
| 0.2 ps | 2 | 4 | preserved | present |
| 0.3 ps | 2 | 3 | preserved | absent |
| 0.4 ps | 2 | 3 | preserved | absent |
| 0.5 ps | 2 | 3 | preserved | absent |
| 0.6 ps | 1 | 3 | — | absent |

- Mechanical candidate gate: LS3_DELAY0P5_MECHANICAL_GATE_PASS.
- No continuous boundary is inferred between discrete delays.

| run | first BJ1/BJ2 (ps) | second BJ1/BJ2 (ps) | chains | JTL6 clusters | terminal area / Phi0 | max timing drift (ps) |
|---|---|---|---:|---:|---:|---:|
| LS3_DELAY0P5_0011 | 115.6/116.4 | 129.3/130 | 2 | 2 | 2 | 3.6 |
| LS3_DELAY0P5_0111 | 114/115 | 118.6/119.8 | 3 | 3 | 2.9999999 | 2 |
| LS3_DELAY0P6_0011 | 115.7/116.5 | —/— | 1 | 1 | 0.99999996 | 0.5 |
| LS3_DELAY0P6_0111 | 114.1/115 | 119/120.2 | 3 | 3 | 3 | 2.3 |

N2/N3 chains, first missing stage, active JS1/JS2 phase-area checks, L1 re-arm, JSL8, bridge current/voltage and ideal-source power/energy are in analysis/mechanical_analysis.json. Phase turns are navigation diagnostics, not literal SFQ counts.

Stop marker: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW.
