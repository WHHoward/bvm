# REVIEW — N1-N4 read-count passive/replay exploration

- Status: **PASS**
- Method: independent standard-library CSV/Decimal/hash/PWL re-read; no solver call.
- New physical runs checked: six (`N2_PASSIVE`/`N2_REPLAY`, `N3_PASSIVE`/`N3_REPLAY`, `N4_PASSIVE`/`N4_REPLAY`). N1 is a hash-bound reference and was not rerun.

## Numerical review

| check | result |
|---|---:|
| raw hashes unchanged during check | `True` |
| all source snapshot token pairs exact | `True` |
| all replay PWL pairs exact | `True` |
| all replay inputs match QB LIN | `True` |
| production comparisons | `True` |

The independent integrals use each raw file's actual stored time column and trapezoids. Phase is unwrapped before endpoint displacement; any turns are `rad/(2*pi)`. The KCL equation is explicitly `sum_i I(L_SL|XBVMi) - I(B_JSL1)`.

## Adversarial checks and limits

- N1 raw is referenced from the prior experiment by fixed hash; no historical raw was copied or overwritten.
- The three new passive decks differ only in final READ mask; pre-final control history and topology were independently preflighted.
- Replay decks were parsed for exact PWL pairs, direct positive orientation, one QB, six JTL stages and one 10 ohm termination.
- The first bad control-template generation is retained under `analysis/attempts/20260907-control-template-preflight-fail/`; it produced no raw and was excluded from analysis.
- Convergence and sensitivity remain **UNKNOWN**. This record does not establish a hardware result, mechanism, Gate, event count or universal read-count law.

Machine record: `analysis/independent_check.json`.
