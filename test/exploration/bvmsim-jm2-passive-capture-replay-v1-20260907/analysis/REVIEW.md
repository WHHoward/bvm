# REVIEW — passive capture / replay exploration

- Status: **PASS**
- Independent method: standard-library CSV, SHA-256, exact Decimal source/PWL comparison, and actual-grid trapezoid/KCL checks. No solver call was made.
- Physical runs checked: exactly four new runs (`SINGLE_PASSIVE`, `ARRAY_PASSIVE`, `REPLAY_SINGLE`, `REPLAY_ARRAY`).

## Numerical review

| check | result |
|---|---:|
| raw hashes unchanged during check | `True` |
| passive source snapshot token fidelity | `True` |
| replay PWL exact numeric fidelity | `True` |
| replay input matches QB LIN branch | `True` |
| ARRAY final-read KCL max residual | `1.29e-05 uA` |
| SINGLE replay final-read I_REPLAY max abs | `85.01338 uA` |
| ARRAY replay final-read I_REPLAY max abs | `68.41421 uA` |

All phase quantities remain descriptive raw-radian trajectories; any turns shown in the machine record use `rad/(2*pi)`. The replay current signed areas use the actual recorded time grid.

## Adversarial checks and limits

- Raw hashes are pinned to the four captured files and were re-read before and after this check.
- Historical direct raw hashes were checked and are unchanged; those files are contextual and were not rerun.
- The replay deck was independently parsed for its exact PWL pairs, positive `I_REPLAY 0 QBIN` orientation, and six JTL instances.
- The first derived analysis pass with the wrong KCL sign is preserved under `analysis/attempts/ANALYSIS-01/` and is excluded from this review.
- `V(IB|XBQ1)` is an optional missing output column in this JoSIM raw schema.
- Convergence and sensitivity remain **UNKNOWN**; this exploration does not establish hardware behavior, an exactly-one event, an SFQ count, or a mechanism claim.

Machine record: `analysis/independent_check.json`.
