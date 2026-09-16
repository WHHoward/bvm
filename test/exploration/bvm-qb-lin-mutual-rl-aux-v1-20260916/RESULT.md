# Minimal Lin-coupled mutual-RL auxiliary (bvm-qb-lin-mutual-rl-aux-v1-20260916)

- Status: `ANALYSIS_COMPLETE_AWAITING_SCIENTIFIC_REVIEW`
- Artifact status: `VALID`
- Scientific interpretation: `NOT_PERFORMED`; final assignment: `SCIENTIFIC_REVIEW_REQUIRED`.
- Frozen parent `b904851be588ca88d40cf1700d5fef7ce3d889ed`; K=0/.1/.2/.3 only; positive K only; no negative K sweep.
- Canonical galvanic path remains JSL8 → QBIN → Lin → BJs → QB core; auxiliary is inside an experimental QB clone.

## K matrix

| K point | K | M (pH) | 0011 ordered chains | 0111 ordered chains | 0011 candidate | 0111 candidate |
|---|---:|---:|---:|---:|---|---|
| `K000` | 0.00 | 0 | 2 | 4 | `MUTUAL_AUX_FIXTURE_K0_PASS` | `MUTUAL_AUX_FIXTURE_K0_PASS` |
| `K010` | 0.10 | 0.38729833 | 2 | 4 | `MUTUAL_TOO_WEAK` | `MUTUAL_TOO_WEAK` |
| `K020` | 0.20 | 0.77459667 | 2 | 4 | `MUTUAL_TOO_WEAK` | `MUTUAL_TOO_WEAK` |
| `K030` | 0.30 | 1.161895 | 2 | 4 | `MUTUAL_TOO_WEAK` | `MUTUAL_TOO_WEAK` |

K=0 no-op gate status: `PASS`.

## Conditional population validation

- Selected K by preregistered smallest-positive mechanical rule: `None`.
- Conditional N1/N4 solves are added only when fixed K evidence has N2=2 and N3=3 mechanically; no subjective waveform ranking is used.


## Auxiliary measurements

Per-K auxiliary I/V, R_AUX signed V·I energy, I²R dissipation, Lin/QBIN/BVM/JSL8 deltas, and all internal/downstream records are in `analysis/mechanical_analysis.json`.
The R_AUX nonnegative dissipation check is a numerical property of this finite passive model, not a claim of directional isolation or hardware realizability.

Phase is raw radians; turns are navigation only. Navigation/area/cluster quantities are not literal SFQ counts.

Stop marker: `EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW`.
