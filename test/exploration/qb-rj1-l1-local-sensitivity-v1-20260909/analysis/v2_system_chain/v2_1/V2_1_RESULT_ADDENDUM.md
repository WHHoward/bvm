# V2.1_RESULT_ADDENDUM — boundary-complete system-chain views

## Purpose

V2.1 is a versioned presentation repair on top of V2. It makes the semantic
boundary of every subsystem explicit:

`INPUT BOUNDARY -> INTERNAL STATE -> OUTPUT BOUNDARY`.

It preserves V2 provenance and does not overwrite V2 or V1 artifacts.

## Read-only confirmation

- New physical solves: `0`.
- Original physical solves: `5`; no rerun was executed.
- Raw files modified: `0`; all five raw SHA-256 values remain bound to the
  pre-V2.1 reference.
- Historical V2/V1 plots deleted: `0`.
- Historical result files overwritten: `0`.
- Extra phase-plane, ranking, dashboard or mechanism plots: `0`.

Parent V2 provenance is preserved through [raw_reference.json](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/v2_1/raw_reference.json), which records the parent manifest/reference hashes.

## Semantic structure

All standalone and comparison pages use the five unchanged main categories:

1. `01_SIGNAL_TIMING`
2. `02_BVM_STATE`
3. `03_JSL_CHAIN`
4. `04_QB_STATE`
5. `05_JTL_CHAIN`

The new V2.1 standalone set has 75 pages: every one of the five runs has all
five categories, and every category contains `OVERVIEW_0_200ps` plus its
registered focused windows. The comparison set has 34 pages: 17 for the L1
family and 17 for the RJ1 family.

Boundary details:

- BVM output is the semantic `SL output -> COMMON_SL` boundary. No fictitious
  `BVMOUT` JJ or P/V/I signal is introduced.
- JSL input is `V(COMMON_SL)` and `I(B_JSL1)`; JSL internal is all
  `P/V/I(B_JSL1..8)`; JSL output is `I(B_JSL8)` and `V(QBIN)`.
- QB output includes `I/V(L3|XBQ1)`, `V(QBOUT)` and the contextual JTL1
  handoff `P/V/I(B01|XJTL1_1)`.
- JTL input is `V(QBOUT)`; the internal chain contains all six stages; output
  is `V(JTL6_OUT)` and `I(R_TERM)`.
- `V(IB|XBQ1)` remains explicitly absent/UNKNOWN in raw output and is not
  fabricated.

## Per-run V2.1 navigation

- [NOMINAL](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/v2_1/run_summaries/NOMINAL.md)
- [L1_DOWN](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/v2_1/run_summaries/L1_DOWN.md)
- [L1_UP](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/v2_1/run_summaries/L1_UP.md)
- [RJ1_UP_05](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/v2_1/run_summaries/RJ1_UP_05.md)
- [RJ1_UP_10](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/v2_1/run_summaries/RJ1_UP_10.md)

Each summary links to the full, final/read and focused V2.1 page set for all
five categories.

## L1 family comparison

- [01_SIGNAL_TIMING](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_l1/01_SIGNAL_TIMING/OVERVIEW_0_200ps.html)
- [02_BVM_STATE](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_l1/02_BVM_STATE/OVERVIEW_0_200ps.html)
- [03_JSL_CHAIN](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_l1/03_JSL_CHAIN/OVERVIEW_0_200ps.html)
- [04_QB_STATE](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_l1/04_QB_STATE/OVERVIEW_0_200ps.html)
- [05_JTL_CHAIN](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_l1/05_JTL_CHAIN/OVERVIEW_0_200ps.html)

## RJ1 family comparison

- [01_SIGNAL_TIMING](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_rj1/01_SIGNAL_TIMING/OVERVIEW_0_200ps.html)
- [02_BVM_STATE](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_rj1/02_BVM_STATE/OVERVIEW_0_200ps.html)
- [03_JSL_CHAIN](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_rj1/03_JSL_CHAIN/OVERVIEW_0_200ps.html)
- [04_QB_STATE](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_rj1/04_QB_STATE/OVERVIEW_0_200ps.html)
- [05_JTL_CHAIN](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/plots/v2_system_chain/v2_1/compare_rj1/05_JTL_CHAIN/OVERVIEW_0_200ps.html)

Focused comparison windows are listed in [manifest.json](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/v2_1/manifest.json).

## OBSERVED

V2.1 changes navigation and semantic grouping only. The existing registered
values are unchanged: RJ1 increases from 12 to 13 ohm show a small monotonic
increase in BJ1 progression and peak voltage but no monotonic positive-voltage
duration change; L1=1.9/2.0/2.1 pH retain the registered directional BJ1/L1/L2
trajectory values with no stored-sample nonnegative L1 crossing.

## BOUNDED_RESULT

The existing bounded local-trajectory evidence is now directly traceable from
input boundary through internal state to output boundary for BVM, JSL, QB and
JTL, with intentional cross-view boundary overlap. No physical claim is
strengthened by the V2.1 organization.

## UNKNOWN

Convergence, event/SFQ classification, system Gate status, mechanism, hardware
behavior and any parameter recommendation remain `UNKNOWN` or `INCONCLUSIVE`.

## QA and status

The three semantic completeness gates and all hash/window checks are recorded
in [visualization_qa.json](/home/howard/JoSIM/test/exploration/qb-rj1-l1-local-sensitivity-v1-20260909/analysis/v2_system_chain/v2_1/visualization_qa.json). Final status: `AWAITING_USER_REVIEW`.
