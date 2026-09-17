# Physical LS3 mutual-RL loop — bvm-rloop-ls3-mutual-rl-v1-20260917

- Status: `ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW`
- Artifact status: `VALID`
- Scientific interpretation: `NOT_PERFORMED`; candidate labels require review.
- Physical `R_S=3 ohm` and `L_S3=0.5 pH` are retained; `L_AUX=10 pH`, `R_AUX=20 ohm`, with M-derived K.

| M (pH) | K | N2 ordered chains | N3 ordered chains | N3 fourth BJ1 (ps) | mechanical label |
|---:|---:|---:|---:|---:|---|
| 0.00 | 0 | 2 | 4 | 124.2 | `LS3_MUTUAL_M0_NOOP_GATE_PASS` |
| 0.25 | 0.1118034 | 2 | 4 | 124.2 | `LS3_MUTUAL_TOO_WEAK` |
| 0.50 | 0.2236068 | 2 | 4 | 124.4 | `LS3_MUTUAL_TOO_WEAK` |
| 0.75 | 0.3354102 | 2 | 4 | 124.4 | `LS3_MUTUAL_TOO_WEAK` |

Per-run active JS1/JS2 phase-area cross-checks, physical I/V LS3 and RS, total bridge current, V6-V10, JSL8, Lin/QBIN, L1 re-arm, auxiliary I/V, I²R and signed power/energy records are in `analysis/mechanical_analysis.json`.
M=0 is a no-op gate. N1/N4 are conditional only; the smallest positive M is recorded if the fixed pair mechanically gives N2=2 and N3=3.
P(...) is raw radians; rad/(2*pi) turns are navigation only, not literal SFQ counts. No scientific mechanism or winner conclusion is assigned.

Stop marker: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
