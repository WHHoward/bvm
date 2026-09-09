# V2_RESULT_ADDENDUM — system-chain visualization repair

## V2 purpose

This addendum repairs the presentation organization of the existing
`qb-rj1-l1-local-sensitivity-v1-20260909` result. It makes each run directly
navigable as:

`signal timing -> BVM state -> JSL1..JSL8 -> QB state -> JTL1..JTL6 -> terminal`.

The original [RESULT_BRIEF.md](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/RESULT_BRIEF.md) and original visualization remain unchanged.

## Read-only confirmation

- V2 physical solves: **0**.
- Original physical solve count: **5** (`NOMINAL`, `L1_DOWN`, `L1_UP`,
  `RJ1_UP_05`, `RJ1_UP_10`).
- Raw files modified: **0**; each V2 page is hash-bound to the existing raw.
- Historical plots deleted: **0**.
- Historical result files overwritten: **0**.
- No event detector, threshold, filtering, interpolation, resampling, alignment
  or new metric was introduced.

Raw paths and before/after hashes are recorded in [raw_reference.json](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/raw_reference.json); per-page provenance is in [manifest.json](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/manifest.json).

## Visualization structure

Every standalone and family comparison uses the same five main categories:

1. `01_SIGNAL_TIMING`
2. `02_BVM_STATE`
3. `03_JSL_CHAIN`
4. `04_QB_STATE`
5. `05_JTL_CHAIN`

Standalone has the requested full/final/read, BVM, JSL, QB and JTL windows.
Comparison has `OVERVIEW_0_200ps`, `SYSTEM_CRITICAL_101_135ps`,
`FINAL_READ_110_121ps`, plus the registered QB/JTL `110_130ps` view. All
phase displays independently unwrap each run's raw radians and then display
`rad/(2*pi)` turns. The JSL numerical diagnostic is
`max_t |I(B_JSLk)-I(B_JSL1)|`, `k=2..8`; it is a series-current consistency
diagnostic, not an SFQ criterion.

## Per-run system-chain links

- [NOMINAL summary](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/run_summaries/NOMINAL.md)
- [L1_DOWN summary](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/run_summaries/L1_DOWN.md)
- [L1_UP summary](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/run_summaries/L1_UP.md)
- [RJ1_UP_05 summary](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/run_summaries/RJ1_UP_05.md)
- [RJ1_UP_10 summary](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/run_summaries/RJ1_UP_10.md)

Each summary links to all five category directories and their registered
windows. The machine-readable JSL check is [jsl_current_consistency.json](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/jsl_current_consistency.json).

## L1 family comparison links

- [01 signal timing overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_l1/01_SIGNAL_TIMING/OVERVIEW_0_200ps.html)
- [02 BVM state overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_l1/02_BVM_STATE/OVERVIEW_0_200ps.html)
- [03 JSL chain overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_l1/03_JSL_CHAIN/OVERVIEW_0_200ps.html)
- [04 QB state overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_l1/04_QB_STATE/OVERVIEW_0_200ps.html)
- [05 JTL chain overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_l1/05_JTL_CHAIN/OVERVIEW_0_200ps.html)

Each category directory also contains the `SYSTEM_CRITICAL`, `FINAL_READ` and
registered QB/JTL extra windows listed in `manifest.json`.

## RJ1 family comparison links

- [01 signal timing overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_rj1/01_SIGNAL_TIMING/OVERVIEW_0_200ps.html)
- [02 BVM state overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_rj1/02_BVM_STATE/OVERVIEW_0_200ps.html)
- [03 JSL chain overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_rj1/03_JSL_CHAIN/OVERVIEW_0_200ps.html)
- [04 QB state overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_rj1/04_QB_STATE/OVERVIEW_0_200ps.html)
- [05 JTL chain overview](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/compare_rj1/05_JTL_CHAIN/OVERVIEW_0_200ps.html)

## OBSERVED

These values are carried from the existing registered raw analysis; V2 only
reorganizes the evidence view.

- RJ1 increase from 12.0 to 13.0 ohm produces a small monotonic increase in
  BJ1 maximum relative progression: `0.188484175`, `0.189896198`,
  `0.191231985` turns. Maximum time is `120.9 ps` in all three runs.
- RJ1 maximum `V(BJ1)` is `0.1227016`, `0.1242360`, `0.1256916 mV`; positive
  voltage duration is `8.4`, `8.5`, `8.4 ps`, so that duration is not monotonic.
- L1 values `1.9`, `2.0`, `2.1 pH` give maximum `I(L1)` of
  `-17.92837`, `-20.59924`, `-22.96358 uA`, BJ1 progression of
  `0.194062238`, `0.188484175`, `0.183404745` turns, and maximum `I(L2)` of
  `232.0716`, `229.4008`, `227.0364 uA`.
- No stored-sample negative-to-nonnegative `I(L1)` crossing occurs in these
  three L1 cases.

## BOUNDED_RESULT

The repaired V2 view makes the existing bounded local-trajectory observations
traceable from BVM through all eight JSL stages, QB, all six JTL stages and the
terminal. It does not change their interpretation: L1 shows a registered
directional trajectory change without a nonnegative crossing; RJ1 changes
local magnitude metrics without a consistent duration/max-time persistence
change; source-side tracks remain visible for direct comparison.

## UNKNOWN

Convergence, system-level event classification, SFQ count, mechanism, hardware
behavior, optimality and any interpretation beyond the fixed five-run raw
matrix remain `UNKNOWN` or `INCONCLUSIVE`. `V(IB|XBQ1)` remains an un-emitted
optional column and is not fabricated.

No additional mechanism plot was generated. Final state: `AWAITING_USER_REVIEW`.
