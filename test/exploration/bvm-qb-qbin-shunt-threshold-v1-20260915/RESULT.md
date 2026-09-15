# QBIN linear-shunt threshold-window experiment: bvm-qb-qbin-shunt-threshold-v1-20260915

- Workflow status: LINEAR_SHUNT_WINDOW_NOT_FOUND
- Final state: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
- Scientific interpretation: NOT_PERFORMED; classification: SCIENTIFIC_REVIEW_REQUIRED
- Physical solves: 12; Stage A authorized 12; Stage B maximum 3.
- Independent variable: conductance of one resistor R_QBIN_SHUNT from QBIN to ground.

## Threshold-result table

The response columns below are auxiliary mechanical navigation candidates.
They are not SFQ counts, event certification, or a physical verdict.

| Rsh (ohm) | G/G20 | N2 response candidates | N3 response candidates | N2 2nd | N3 4th | N2 JS1/JS2 read p2p turns | N3 JS1/JS2 read p2p turns |
|---:|---:|---:|---:|---|---|---:|---:|
| open | 0.00 | 2 | 4 | PRESENT | PRESENT | 3.16/3.163 | 6.386/6.361 |
| 100 | 0.20 | 1 | 4 | ABSENT | PRESENT | 3.112/3.17 | 6.476/6.438 |
| 66.667 | 0.30 | 1 | 4 | ABSENT | PRESENT | 3.109/3.174 | 6.434/6.403 |
| 50 | 0.40 | 1 | 4 | ABSENT | PRESENT | 3.109/3.178 | 6.434/6.396 |
| 40 | 0.50 | 1 | 4 | ABSENT | PRESENT | 3.109/3.181 | 6.337/6.332 |
| 33.333 | 0.60 | 1 | 4 | ABSENT | PRESENT | 3.111/3.184 | 6.292/6.3 |
| 25 | 0.80 | 1 | 3 | ABSENT | ABSENT | 3.118/3.19 | 6.182/6.219 |
| 20 | 1.00 | 1 | 3 | ABSENT | ABSENT | 3.128/3.195 | 6.012/6.06 |

## Required review answers

1. Earliest N3 fourth-response disappearance in the registered Stage A order: r25; scientific classification remains pending review.
2. Earliest N2 second-response disappearance in the registered Stage A order: r100; scientific classification remains pending review.
3. Mechanical threshold ordering: N2 second first absent at G/G20=0.2; N3 fourth first absent at G/G20=0.8.
4. Mechanical 2/3 points: none; no post-hoc interpolation is performed.
5. If a 2/3 trigger exists, Stage B uses only the maximum finite R point and
   masks 0000, 0001, 1111; otherwise the workflow stops without extra solves.
6. QBIN voltage, shunt fraction, L1 windows, BVM storage, symmetry, rollback,
   and non-monotonicity scalars are in result.json and remain review questions.

## Evidence boundary

P(...) is raw phase in radians. Phase turns are independent unwrap(rad)/(2*pi)
navigation values only; they are not SFQ counts. Terminal integrals and lobe
navigation are descriptive cross-checks, not event-count authority.

Open and R20 endpoints are referenced by path and SHA-256 only. No historical
raw is copied into this experiment. No focused plots, ZIP in Git, or automatic
post-Stage-B experiment is created.

Stop marker: EXPERIMENT_COMPLETE / AWAITING_SCIENTIFIC_REVIEW
