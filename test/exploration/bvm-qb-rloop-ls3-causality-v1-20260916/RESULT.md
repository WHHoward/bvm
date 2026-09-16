# BVM R-loop bridge causality experiment: bvm-qb-rloop-ls3-causality-v1-20260916

- Stage A status: STAGE_A_COMPLETE
- Final state: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
- Physical solves: 6
- Scientific interpretation: NOT_PERFORMED.
- Scientific classification: SCIENTIFIC_REVIEW_REQUIRED.
- Independent variable: only experiment-local L_S3; canonical BVM source is immutable.

## Stage A source-side normalization

| L_S3 (pH) | N2 JS1/JS2 read p2p turns | N3 JS1/JS2 read p2p turns | N3/N2 signed L_SL area ratio | N3 bridge fraction [113,115) |
|---:|---:|---:|---:|---:|
| 0.75 | 2.9548/3.1478 | 6.4555/6.4009 | 1.7108 | 0.65053 |
| 1.00 | 2.8147/3.1322 | 6.2125/6.2422 | 1.6512 | 0.54138 |
| 1.50 | 2.6437/3.0924 | 5.913/5.984 | 1.5553 | 0.39614 |

## Required answers for scientific review

1. Canonical chronology is remeasured in each candidate through the exact-grid
   N3-minus-N2 records in stage_a.per_point.first_divergence_N3_minus_N2.
2. I(L_S3) versus I(R_S) min/max/mean/signed-area/absolute-area and bridge
   fractions are stored for every active cell and every registered window.
3. JS2-side and JS1-side first-divergence timestamps, directions and magnitudes
   are recorded without assigning causal direction.
4. BJ2 handoff and JS1 navigation timestamps are retained per candidate; any
   locking, delay, or disappearance requires scientific review.
5. N2 read-attractor preservation is represented by the N2 phase/current/storage
   records and same-JJ phase/voltage-area cross-checks.
6. N3 JS1/JS2 read p2p values are in the table above; they are phase navigation
   observables, not event or SFQ counts.
7. Per-active-cell L_SL source normalization and N3/N2 ratio are recorded above.
8. COMMON_SL, JSL8 and QBIN boundary scalars are retained in each run metric.
9. JM1/JM2 storage phase records and rollback values are retained per active cell.
10. JM1/JM2 timing is recorded separately from JS1/JS2 and bridge chronology.
11. QB BJ1/BJ2/L1 records and same-JJ phase/area checks are retained.
12. QB downstream records include JTL6 B02 and terminal voltage integral.
13. No receiver-side versus source-side explanation is assigned automatically.
14. Stage B was not executed: its qualitative mechanism-success predicate has
    no frozen numerical threshold and scientific review authorization is absent.
15. No complete population map is generated in this Stage A-only run.

## Evidence boundary

P(...) is raw radians. Turns are only independent unwrap(rad)/(2*pi) navigation.
Phase thresholds, branch activity, terminal peaks and mechanical summaries do
not certify SFQ events. Raw CSV files are immutable authority; all comparisons
use exact stored timestamps and no interpolation.

The experiment root intentionally contains only experiment.yaml, RESULT.md,
result.json, provenance.json, runs and plots. ZIP delivery is Drive-only.
